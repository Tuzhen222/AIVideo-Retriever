import os, json, glob
from queue import Queue
from threading import Thread, Lock

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import av
import faiss
from tqdm import tqdm
from PIL import Image
from natsort import natsorted

# Removed torchvision.transforms.functional import to avoid circular import issues
# Using torch.nn.functional.interpolate instead
from timm.data.constants import IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD
from timm.models.layers import trunc_normal_ as trunc_normal_fn
from huggingface_hub import hf_hub_download

# =======================
# CONFIG
# =======================
INPUT_JSON_DIR = "/kaggle/input/irscene/SceneIR"
OUTPUT_DIR     = "/kaggle/working/keyframes_out"

SAVE_FORMAT    = "webp"
SAVE_QUALITY   = 90
OUTPUT_SIZE    = (640, 360)

IMG_SIZE       = 384
BATCH_SIZE     = 128

# ✅ NGƯỠNG LỌC (THEO ĐÚNG LOGIC CỦA BẠN)
THRESH_KF      = 0.94     # so sánh với keyframe gần nhất (giảm để tăng keyframe)
THRESH_PREV    = 0.96    # so sánh với frame candidate trước đó trong danh sách (giảm để tăng keyframe)

STEP_CAND      = 6        # ✅ mỗi scene lấy frame cách nhau 6 (giảm từ 8 để tăng candidate)
MIN_SCENE_GAP  = 60       # ✅ nếu cách keyframe trước ≥ 60 → lấy luôn (giảm từ 75 để tăng keyframe)

NUM_PARTS     = 726
PART_ID       = 1

BEIT3_REPO    = "Quintu/beit3"
BEIT3_CKPT    = "beit3_large_patch16_384_coco_retrieval.pth"

# =======================
# GLOBAL
# =======================
# Store (video_name, scene_start, frame_num, path, embedding) for sorting
DATA_STORE = []
lock = Lock()

def ensure(p): os.makedirs(p, exist_ok=True)

# =======================
# BEiT-3 (vision only)
# =======================
class BEiT3Vision(nn.Module):
    def __init__(self):
        super().__init__()
        from torchscale.architecture.config import EncoderConfig
        from torchscale.model.BEiT3 import BEiT3 as M
        args = EncoderConfig(
            img_size=IMG_SIZE, patch_size=16, vocab_size=64010,
            multiway=True, normalize_output=True, no_output_layer=True,
            encoder_embed_dim=1024, encoder_ffn_embed_dim=4096,
            encoder_attention_heads=16, encoder_layers=24
        )
        self.backbone = M(args)
        self.head = nn.Linear(1024, 1024, bias=False)
        self.apply(self._init)
    def _init(self,m):
        if isinstance(m, nn.Linear):
            trunc_normal_fn(m.weight,std=.02)
    @torch.no_grad()
    def forward(self,x):
        out = self.backbone(textual_tokens=None, visual_tokens=x)
        v = self.head(out["encoder_out"][:,0])
        return F.normalize(v, dim=-1)

def load_model(device):
    ckpt = hf_hub_download(BEIT3_REPO, BEIT3_CKPT)
    model = BEiT3Vision().to(device)
    state = torch.load(ckpt,map_location="cpu")
    model.load_state_dict(state.get("model",state),strict=False)
    model.eval()
    mean = torch.tensor(IMAGENET_DEFAULT_MEAN, device=device).view(1,3,1,1)
    std  = torch.tensor(IMAGENET_DEFAULT_STD,  device=device).view(1,3,1,1)
    return model,mean,std

# =======================
# PyAV decode only needed frames
# =======================
def grab_frames(video, frame_list):
    out = {}
    container = av.open(video, options={"hwaccel":"cuda","hwaccel_output_format":"cuda"})
    stream = container.streams.video[0]

    fps = float(stream.average_rate) if stream.average_rate else float(stream.rate)
    tb = stream.time_base
    
    max_fr = max(frame_list)
    min_fr = min(frame_list)
    want = set(frame_list)
    
    # Seek to approximate position for speed
    if min_fr > 0:
        # Calculate PTS: frame_number = pts * time_base * fps
        # So pts = frame_number / (time_base * fps) = frame_number * time_base / fps
        # But PTS is in time_base units, so: pts = frame_number / fps / time_base
        seek_pts = int((min_fr / fps) / float(tb))
        container.seek(seek_pts, any_frame=False, backward=True, stream=stream)
    
    # Decode and calculate actual frame numbers from PTS
    for frame in container.decode(stream):
        if frame.pts is None:
            continue
        
        # Calculate frame number from PTS: frame = pts * time_base * fps
        actual_frame = int(round(frame.pts * float(tb) * fps))
        
        if actual_frame > max_fr:
            break
        
        if actual_frame in want:
            out[actual_frame] = frame.to_ndarray(format="rgb24")
            if len(out) == len(want):
                break

    container.close()
    return out


# =======================
# cosine
# =======================
def sim(a,b):
    return float(np.dot(a,b))

# =======================
# PROCESS SCENE
# =======================
def process_scene(job, state):
    video,s,e,out_dir = job
    ensure(out_dir)

    # candidate frames mỗi 8 frame
    frame_order = list(range(s, e+1, STEP_CAND))
    frames = grab_frames(video, frame_order)
    # loại frame không decode được
    frame_order = [f for f in frame_order if f in frames]
    if len(frame_order) == 0:
        return

    model,mean,std,device = state["model"],state["mean"],state["std"],state["device"]

    # convert to tensor + embed
    imgs = [frames[f] for f in frame_order]
    embs=[]
    for i in range(0,len(imgs),BATCH_SIZE):
        x = torch.from_numpy(np.stack(imgs[i:i+BATCH_SIZE])).permute(0,3,1,2).float().to(device)/255
        x = F.interpolate(x, size=(IMG_SIZE, IMG_SIZE), mode='bicubic', align_corners=False, antialias=True)
        x = (x-mean)/std
        with torch.no_grad():
            v = model(x).cpu().numpy()
        embs.append(v)
    embs = np.concatenate(embs,0)

    # chọn keyframe theo đúng logic của bạn
    kf = [0]   # index trong frame_order, luôn lấy frame đầu tiên

    for i in range(1,len(frame_order)):
        f_i = frame_order[i]
        last_frame = frame_order[kf[-1]]

        # ✅ nếu cách keyframe trước ≥ 75 → lấy luôn
        if f_i - last_frame >= MIN_SCENE_GAP:
            kf.append(i)
            continue

        # ✅ nếu không → so sánh embedding
        if sim(embs[i], embs[kf[-1]]) < THRESH_KF and sim(embs[i], embs[i-1]) < THRESH_PREV:
            kf.append(i)

    # xuất và lưu embedding
    video_name = os.path.basename(out_dir)  # folder name = video name
    for idx in kf:
        fr = frame_order[idx]
        pil = Image.fromarray(frames[fr]).resize(OUTPUT_SIZE, Image.BICUBIC)
        path = os.path.join(out_dir, f"{fr}.{SAVE_FORMAT}")
        pil.save(path, SAVE_FORMAT.upper(), quality=SAVE_QUALITY)
        with lock:
            # Store with metadata for natural sorting: (video_name, scene_start, frame_num, path, embedding)
            DATA_STORE.append((video_name, s, fr, path, embs[idx].astype("float32")))

# =======================
# Worker
# =======================
def make_worker(device,pbar):
    def _work():
        model,mean,std = load_model(device)
        state={"model":model,"mean":mean,"std":std,"device":device}
        while True:
            try: job = task_queue.get_nowait()
            except: break
            try: process_scene(job,state)
            except Exception as e: print("⚠️",e)
            task_queue.task_done()
            pbar.update(1)
    return _work

# =======================
# MAIN
# =======================
def main():
    ensure(OUTPUT_DIR)
    all_json = natsorted(glob.glob(os.path.join(INPUT_JSON_DIR,"**/*.json"),recursive=True))

    sz=len(all_json)//NUM_PARTS
    rem=len(all_json)%NUM_PARTS
    pid=max(1,min(PART_ID,NUM_PARTS))
    start=(sz+1)*(pid-1) if pid<=rem else rem*(sz+1)+(pid-rem-1)*sz
    end=start+(sz+1 if pid<=rem else sz)
    selected = all_json[start:end]

    global task_queue, DATA_STORE
    task_queue = Queue()
    DATA_STORE = []  # Reset for this run

    for jp in selected:
        d=json.load(open(jp))
        video=d["video_path"]
        name=os.path.splitext(os.path.basename(video))[0]
        out_dir=os.path.join(OUTPUT_DIR,name)
        # Sort scenes by start frame to ensure consistent order
        scenes = natsorted(d["scenes"], key=lambda x: x[0])
        for s,e in scenes:
            task_queue.put((video,s,e,out_dir))

    total=task_queue.qsize()
    pbar=tqdm(total=total,desc=f"Part {PART_ID}",dynamic_ncols=True)

    t0=Thread(target=make_worker("cuda:0",pbar))
    t1=Thread(target=make_worker("cuda:1",pbar))
    t0.start(); t1.start()
    task_queue.join()
    t0.join(); t1.join()
    pbar.close()

    # write faiss
    if not DATA_STORE:
        print("⚠️ No embeddings, skip index.")
        return
    
    # Sort by video_name (natural), then scene_start, then frame_num
    # Use natsorted for video names to handle numeric sorting correctly
    DATA_STORE = natsorted(DATA_STORE, key=lambda x: (x[0], x[1], x[2]))
    
    # Extract paths and embeddings in sorted order
    PATH_STORE = [item[3] for item in DATA_STORE]
    EMB_STORE = [item[4] for item in DATA_STORE]
    
    embs=np.stack(EMB_STORE).astype("float32")
    embs/=np.linalg.norm(embs,axis=1,keepdims=True)
    index=faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    faiss.write_index(index,f"/kaggle/working/keyframes_part_{PART_ID:03d}.bin")
    open(f"/kaggle/working/keyframes_paths_part_{PART_ID:03d}.txt","w").write("\n".join(PATH_STORE))
    print("✅ DONE")

if __name__=="__main__":
    main()
