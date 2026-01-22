#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemini_ocr.py — Giữ nguyên logic call giống gemini_ocr.py (batch, 15 calls/key, pacing, Files API fallback),
NHƯNG dùng prompt OCR và chỉ ghi NDJSON mỗi dòng: {"id": <int>, "ocr": "<str>"}.

- batch cố định (mặc định 50 trong file này; có thể đổi bằng --batch-size)
- sticky 15 calls/key + cooldown 429
- pacing ngẫu nhiên 1–3s giữa các call
- generate_content (KHÔNG response_schema, KHÔNG response_mime_type)
- parse JSON array "thoải mái" như gemini.py
- Files API fallback khi tổng inline vượt ngưỡng
- Ghi ID lỗi vào od_error.txt (mỗi ID một dòng) — GIỮ NGUYÊN
"""

import json, re, sys, time, random, argparse, os
from dataclasses import dataclass, field
from functools import lru_cache
from mimetypes import guess_type
from pathlib import Path, PurePosixPath
from typing import List, Optional, Dict, Tuple, Any, Set, Iterable

# --- Gemini SDK ---
from google import genai
from google.genai import types
from google.genai import errors as genai_errors  # APIError/ClientError/ServerError

# ============================== PROMPT (OCR) ==============================
# Áp dụng đúng system instruction OCR mà bạn cung cấp
PROMPT_HEADER = (
    "ROLE: You are a precise OCR engine.\n"
    "GOAL: Extract ALL visible textual characters from each image, and ONLY text.\n"
    "- Include printed/handwritten text in any language; preserve accents/diacritics and original script.\n"
    "- EXCLUDE icons, emojis.\n"
    "- Process EACH image independently; do NOT carry over text between images.\n"
    "- Normalize whitespace: keep reading order (left-to-right/top-to-bottom heuristics), join lines with single spaces, trim edges.\n"
    "- Do NOT translate or paraphrase. No summaries. No extra commentary.\n"
)

PROMPT_RULES = (
    "OUTPUT: Return exactly N JSON objects (same order as inputs), each with keys: id, ocr.\n"
    "If no readable text in an image, use empty string for ocr.\n"
    "Return ONLY a raw JSON array and nothing else.\n"
    "\n"
    "OUTPUT FORMAT RULES:\n"
    "1) Return ONLY the raw JSON array. Start with '[' and end with ']'. No extra text.\n"
    "2) EXACTLY N items; each item has ONLY keys: \"id\" and \"ocr\".\n"
    "3) \"id\" MUST be an integer (not a string); parse numeric ID from the marker line.\n"
    "4) \"ocr\" MUST be a string (may be empty if no text).\n"
)

# ============================== CẤU HÌNH ==============================
@dataclass(slots=True)
class Config:
    index_file: Path
 "/kaggle/working"mage_folder: Path
    key_file: Path
    out_file: Path

    # CỐ ĐỊNH theo yêu cầu
    batch_size: int = 50
    calls_per_key: int = 15

    # pacing nhẹ giữa các batch
    min_call_delay: float = 1.0
    max_call_delay: float = 3.0

    # lỗi 429 → cooldown key 60s; lỗi bất kỳ → chờ 30–35s trước retry
    error429_cooldown: float = 60.0
    err_retry_min: float = 30.0
    err_retry_max: float = 35.0

    # Model
    models: List[str] = field(default_factory=lambda: ["gemini-2.5-flash"])

    # Ngưỡng inline tổng (vượt sẽ dùng Files API như gemini.py)
    inline_soft_limit_bytes: int = 18 * 1024 * 1024

    # Giữ nguyên xử lý index: bỏ prefix 'output/' nếu có
    strip_prefix: Optional[str] = "output"

    # Parser cho code fences ```json
    json_block: re.Pattern[str] = field(default_factory=lambda: re.compile(r"```(?:json)?|```", re.I), init=False)

CFG: Config  # sẽ gán trong main()

# ============================== ARGPARSE ==============================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Gemini OCR — output NDJSON mỗi dòng: {id(int), ocr(str)}; chọn range KEY & INDEX"
    )
    p.add_argument("--index-file",   required=True, type=str, help="Đường dẫn index.json (DICT {id: path} hoặc LIST các object có id/path|image)")
    p.add_argument("--image-folder", required=True, type=str, help="Thư mục gốc chứa ảnh thực (vd: keyframe)")
    p.add_argument("--key-file",     required=True, type=str, help="File chứa các API key (mỗi dòng 1 key)")
    p.add_argument("--out",          required=True, type=str, help="Đường dẫn file NDJSON output")

    # KEY range (bắt buộc)
    p.add_argument("--start-api",    required=True, type=int, help="DÒNG BẮT ĐẦU (1-based, inclusive) để lấy API key")
    p.add_argument("--end-api",      required=True, type=int, help="DÒNG KẾT THÚC (1-based, inclusive) để lấy API key")

    # INDEX range (bắt buộc)
    p.add_argument("--start-index",  required=True, type=int, help="ID ảnh bắt đầu (inclusive) trong index.json")
    p.add_argument("--end-index",    required=True, type=int, help="ID ảnh kết thúc (inclusive) trong index.json")

    # (Tuỳ chọn) thay batch size nếu cần
    p.add_argument("--batch-size",   required=False, type=int, default=50, help="Số ảnh/call (mặc định 50)")
    return p.parse_args()

# ============================== I/O (INDEX → DANH SÁCH (id, path)) ==============================
def _parse_int_like(x: str) -> Optional[int]:
    try:
        return int(re.sub(r"[_\s]", "", str(x)).strip())
    except Exception:
        return None

def load_index_pairs(index_file: Path, image_root: Path, strip_prefix: Optional[str]) -> List[Tuple[str, Path]]:
    if not index_file.exists():
        sys.exit(f"❌ INDEX_FILE not found: {index_file}")

    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"❌ INDEX_FILE JSON lỗi: {e}")

    pairs: List[Tuple[str, Path]] = []

    def norm_path(rel: str) -> Path:
        posix = PurePosixPath(str(rel).strip())
        parts = posix.parts
        if strip_prefix and parts and parts[0].lower() == strip_prefix.lower():
            posix = PurePosixPath(*parts[1:])
        return (image_root / Path(posix.as_posix())).resolve()

    if isinstance(data, dict):
        for sid, rel in data.items():
            p = norm_path(rel)
            if not p.exists():
                print(f"⚠️  Bỏ qua id={sid}: không tìm thấy file {p}")
                continue
            pairs.append((str(sid), p))
    elif isinstance(data, list):
        for it in data:
            if not isinstance(it, dict): continue
            sid = it.get("id")
            rel = it.get("path") or it.get("image")
            if sid is None or not rel: continue
            p = norm_path(rel)
            if not p.exists():
                print(f"⚠️  Bỏ qua id={sid}: không tìm thấy file {p}")
                continue
            sid_norm = _parse_int_like(str(sid))
            pairs.append((str(sid_norm if sid_norm is not None else sid), p))
    else:
        sys.exit("❌ index.json phải là DICT hoặc LIST.")

    def key_sort(s: str):
        v = _parse_int_like(s)
        return v if v is not None else s
    pairs.sort(key=lambda t: key_sort(t[0]))
    if not pairs:
        sys.exit("❌ Index rỗng hoặc không khớp đường dẫn ảnh thực")
    return pairs

def filter_pairs_by_id_range(pairs: List[Tuple[str, Path]], start_idx: int, end_idx: int) -> List[Tuple[str, Path]]:
    if start_idx < 0: sys.exit("❌ --start-index phải ≥ 0")
    if end_idx < start_idx: sys.exit("❌ --end-index phải ≥ --start-index")
    out: List[Tuple[str, Path]] = []
    skipped_non_numeric = 0
    for (sid, p) in pairs:
        v = _parse_int_like(sid)
        if v is None:
            skipped_non_numeric += 1
            continue
        if start_idx <= v <= end_idx:
            out.append((str(v), p))
    if skipped_non_numeric > 0:
        print(f"ℹ️  Bỏ qua {skipped_non_numeric} id không phải số khi áp dụng range {start_idx}..{end_idx}.")
    return out

def chunked(xs: List[Any], n: int) -> List[List[Any]]:
    return [xs[i:i+n] for i in range(0, len(xs), n)]

def read_key_lines(path: Path) -> List[str]:
    if not path.exists():
        sys.exit("❌ KEY_FILE not found")
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    if not lines:
        sys.exit("❌ No API keys in file (sau khi loại dòng trống/comment)")
    print(f"🗝️  Loaded {len(lines)} keys (giữ nguyên thứ tự, có thể gồm trùng lặp)")
    return lines

def slice_keys_by_range(all_keys: List[str], start_line: int, end_line: int) -> List[str]:
    if start_line < 1:
        sys.exit("❌ --start-api phải ≥ 1 (1-based)")
    if end_line < start_line:
        sys.exit("❌ --end-api phải ≥ --start-api")
    n = len(all_keys)
    if start_line > n:
        sys.exit(f"❌ --start-api={start_line} > tổng số dòng {n}")
    end = min(end_line, n)
    sub = all_keys[start_line-1:end]
    print(f"🔎 Using key lines {start_line}..{end} / {n} → {len(sub)} keys")
    if not sub:
        sys.exit("❌ Range tạo ra danh sách key rỗng")
    return sub

def load_done_ids(out_path: Path) -> Set[str]:
    done: Set[str] = set()
    if not out_path.exists():
        return done

    skipped_lines = 0
    decoded_with_replacements = 0
    seen_bom = False

    try:
        with out_path.open("rb") as f:  # read bytes → tolerate junk per line
            for i, raw in enumerate(f, start=1):
                # tolerate any bad bytes so the scan continues
                line = raw.decode("utf-8", errors="ignore")

                # Handle BOM only once (very common if edited in some tools)
                if not seen_bom:
                    seen_bom = True
                    if line.startswith("\ufeff"):
                        line = line.lstrip("\ufeff")

                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "id" in obj:
                        v = _parse_int_like(obj["id"])
                        if v is not None:
                            done.add(str(v))
                        else:
                            skipped_lines += 1
                    else:
                        skipped_lines += 1
                except Exception:
                    # Not valid JSON → skip but continue scanning
                    skipped_lines += 1
    except Exception as e:
        print(f"⚠️  Không thể đọc NDJSON để lấy id đã xong (tolerant mode vẫn lỗi): {e}")
        return done

    print(f"📁 NDJSON hiện có {len(done)} id đã xong (sẽ được bỏ qua). "
          f"⤴︎ Bỏ qua {skipped_lines} dòng hỏng/không hợp lệ.")
    return done


class NDJSONWriter:
    def __init__(self, path: Path):
        self._path = path
        self._fh = None
    def __enter__(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)
        self._fh = self._path.open("a", encoding="utf-8")
        return self
    def write_line(self, obj: dict):
        json.dump(obj, self._fh, ensure_ascii=False)
        self._fh.write("\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())
    def __exit__(self, exc_type, exc, tb):
        if self._fh:
            self._fh.close()

# -------- Error logger: ghi ID vào od_error.txt (mỗi ID một dòng) --------
def append_error_ids(err_file: Path, ids: Iterable[str|int]) -> None:
    if not ids:
        return
    err_file.parent.mkdir(parents=True, exist_ok=True)
    with err_file.open("a", encoding="utf-8") as f:
        for _id in ids:
            f.write(f"{_id}\n")

# ============================== JSON PARSER (ARRAY) ==============================
def parse_json_array(text: Optional[str]) -> Optional[List[dict]]:
    if not text:
        return None
    s = CFG.json_block.sub("", text).strip()
    try:
        obj = json.loads(s)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    # fallback: quét mảng JSON đầu tiên
    start = s.find("[")
    while start != -1:
        depth = 0; in_str = False; esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc: esc = False
                elif ch == "\\": esc = True
                elif ch == '"': in_str = False
            else:
                if ch == '"': in_str = True
                elif ch == "[": depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        cand = s[start:i+1]
                        try:
                            obj = json.loads(cand)
                            if isinstance(obj, list):
                                return obj
                        except Exception:
                            break
        start = s.find("[", start+1)
    return None

# ============================== ERRORS ==============================
def is_rate_limit_error(err: Exception) -> bool:
    s = str(err).lower()
    if "429" in s or "resource_exhausted" in s or "limit exceeded" in s:
        return True
    try:
        if isinstance(err, (genai_errors.APIError, genai_errors.ServerError)):
            code = getattr(err, "status_code", None) or getattr(err, "code", None)
            reason = getattr(err, "status", None) or getattr(err, "reason", None)
            if code == 429: return True
            if isinstance(reason, str) and "resource_exhausted" in reason.lower(): return True
    except Exception:
        pass
    return False

def is_authz_error(err: Exception) -> bool:
    s = str(err).lower()
    if "403" in s or "401" in s or "permission" in s or "unauth" in s:
        return True
    try:
        if isinstance(err, genai_errors.ClientError):
            code = getattr(err, "status_code", None) or getattr(err, "code", None)
            if code in (401, 403): return True
    except Exception:
        pass
    return False

# ============================== KEY ROTATOR: 15 CALLS/KEY ==============================
class StickyKeyRotator:
    def __init__(self, keys: List[str], calls_per_key: int, cooldown: float):
        self.keys = list(keys)  # giữ nguyên thứ tự
        self.calls_per_key = max(1, calls_per_key)
        self.cooldown = cooldown
        self.cool_until: Dict[str, float] = {k: 0.0 for k in self.keys}
        self.dead: set[str] = set()
        self.usage_calls: Dict[str, int] = {k: 0 for k in self.keys}
        self._i = 0
        self._current: Optional[str] = None
        self._remaining: int = self.calls_per_key

    def _next_live_key_index(self) -> int:
        n = len(self.keys)
        for step in range(n):
            j = (self._i + step) % n
            k = self.keys[j]
            if k in self.dead: continue
            if time.time() < self.cool_until.get(k, 0.0): continue
            return j
        live = [k for k in self.keys if k not in self.dead]
        if not live:
            raise RuntimeError("No usable API keys (all dead).")
        soonest = min(live, key=lambda kk: max(0.0, self.cool_until.get(kk, 0.0) - time.time()))
        return self.keys.index(soonest)

    def current_key(self) -> str:
        if (
            self._current is None or self._remaining <= 0 or
            self._current in self.dead or time.time() < self.cool_until.get(self._current, 0.0)
        ):
            self._i = self._next_live_key_index()
            self._current = self.keys[self._i]
            self._remaining = self.calls_per_key
            print(f"🔁 Switch to key {self._current[:8]}… for next {self._remaining} calls.")
        return self._current

    def on_call_finished(self):
        if self._current:
            self.usage_calls[self._current] = self.usage_calls.get(self._current, 0) + 1
            self._remaining -= 1

    def mark_429(self, k: str):
        self.cool_until[k] = time.time() + self.cooldown
        print(f"⛔ Key {k[:8]}… 429 → cooldown {int(self.cooldown)}s")

    def ban(self, k: str):
        self.dead.add(k)
        print(f"🚫 Key {k[:8]}… bị loại (401/403)")

# ============================== GENAI CLIENT & CONTENTS ==============================
@lru_cache(maxsize=None)
def get_client(key: str) -> genai.Client:
    return genai.Client(api_key=key)

def build_contents_for_batch(
    client: genai.Client,
    items: List[Tuple[str, Path]],
    inline_soft_limit: int
) -> Tuple[List[Any], bool]:
    total_inline = 0
    for _, p in items:
        try:
            total_inline += p.stat().st_size
        except Exception:
            pass

    parts: List[Any] = []
    # Dùng prompt OCR 1 lần, không cộng dồn
    parts.append(f"{PROMPT_HEADER}\n{PROMPT_RULES}\nN = {len(items)}\n")

    used_files_api = False
    if total_inline > inline_soft_limit:
        used_files_api = True
        for i, (fid, img) in enumerate(items, start=1):
            parts.append(f"### IMG {i} | id={fid}")
            up = client.files.upload(file=img)  # Files API cho file lớn
            parts.append(up)
    else:
        for i, (fid, img) in enumerate(items, start=1):
            parts.append(f"### IMG {i} | id={fid}")
            mime = guess_type(img.name)[0] or "image/jpeg"
            with open(img, "rb") as f:
                b = f.read()
            parts.append(types.Part.from_bytes(data=b, mime_type=mime))
    return parts, used_files_api

def extract_resp_text(resp) -> Optional[str]:
    if getattr(resp, "text", None):
        return resp.text
    try:
        return resp.candidates[0].content.parts[0].text
    except Exception:
        return None

def generate_once(key: str, model_id: str, items: List[Tuple[str, Path]]) -> Tuple[Optional[List[dict]], str, bool]:
    client = get_client(key)
    contents, used_files_api = build_contents_for_batch(
        client, items, CFG.inline_soft_limit_bytes
    )
    # KHÔNG ép application/json, KHÔNG response_schema → đúng logic gemini_ocr.py
    resp = client.models.generate_content(model=model_id, contents=contents)
    raw = extract_resp_text(resp) or ""
    data = parse_json_array(raw)
    return data, raw, used_files_api

# ============================== MAIN ==============================
def main():
    global CFG
    args = parse_args()
    raw_out = args.out
    out_path = Path(raw_out)
    if out_path.exists() and out_path.is_dir():
        out_path = out_path / "output.ndjson"
    elif raw_out.endswith(("/", "\\")):
        out_path = out_path / "output.ndjson"
    CFG = Config(
        index_file=Path(args.index_file),
        image_folder=Path(args.image_folder),
        key_file=Path(args.key_file),
        out_file=out_path,
        batch_size=int(args.batch_size),
    )
    if not CFG.index_file.exists():
        sys.exit("❌ --index-file không tồn tại")
    if not CFG.image_folder.exists():
        sys.exit("❌ --image-folder không tồn tại")

    # Đọc index & áp dụng range
    all_pairs = load_index_pairs(CFG.index_file, CFG.image_folder, CFG.strip_prefix)
    target_pairs = filter_pairs_by_id_range(all_pairs, args.start_index, args.end_index)
    print(f"🖼️  Index có tổng {len(all_pairs)} item | Range {args.start_index}..{args.end_index} → {len(target_pairs)} item trước khi trừ id đã xong")

    # Bỏ qua id đã xong (từ NDJSON)
    done_ids = load_done_ids(CFG.out_file)
    todo_pairs = [(sid, p) for (sid, p) in target_pairs if sid not in done_ids]
    skipped = len(target_pairs) - len(todo_pairs)
    if skipped > 0:
        print(f"⏭️  Bỏ qua {skipped} id đã có trong NDJSON (giữ nguyên).")
    if not todo_pairs:
        print("✅ Không còn gì để chạy trong khoảng id yêu cầu (đã hoàn tất).")
        return

    batches: List[List[Tuple[str, Path]]] = chunked(todo_pairs, CFG.batch_size)
    print(f"🧰 Batch size (fixed): {CFG.batch_size} → {len(batches)} calls planned (todo={len(todo_pairs)})")

    # Key & rotator
    all_key_lines = read_key_lines(CFG.key_file)
    keys = slice_keys_by_range(all_key_lines, args.start_api, args.end_api)
    rot = StickyKeyRotator(keys, calls_per_key=CFG.calls_per_key, cooldown=CFG.error429_cooldown)

    err_file = CFG.out_file.with_name("od_error.txt")

    model_idx = 0
    with NDJSONWriter(CFG.out_file) as writer:
        for bi, batch in enumerate(batches, start=1):
            # pacing giữa các call (giống gemini_ocr.py)
            time.sleep(random.uniform(CFG.min_call_delay, CFG.max_call_delay))

            key = rot.current_key()
            model_id = CFG.models[model_idx % len(CFG.models)]
            model_idx += 1

            attempt, max_attempts = 0, 8
            while attempt < max_attempts:
                attempt += 1
                try:
                    results, raw, _ = generate_once(key, model_id, batch)
                    if not isinstance(results, list) or len(results) != len(batch):
                        raise ValueError(f"Invalid JSON array or wrong length (got {0 if results is None else len(results)} vs {len(batch)})")

                    wrote = 0
                    bad_ids: List[int] = []

                    # Duyệt cặp (expected_id, item) để log đúng ID lỗi
                    for (expected_sid, _img), item in zip(batch, results):
                        expected_int = _parse_int_like(expected_sid)
                        if not isinstance(item, dict):
                            if expected_int is not None: bad_ids.append(expected_int)
                            continue

                        # Kiểm tra key bắt buộc
                        if "id" not in item or "ocr" not in item:
                            if expected_int is not None: bad_ids.append(expected_int)
                            continue

                        # Ép id -> int
                        v = _parse_int_like(item["id"])
                        if v is None:
                            if expected_int is not None: bad_ids.append(expected_int)
                            continue

                        # Ép ocr -> string (cho phép rỗng)
                        ocr_text = item["ocr"]
                        if not isinstance(ocr_text, (str, int, float)):
                            # nếu không phải kiểu cơ bản chuyển sang chuỗi
                            if expected_int is not None: bad_ids.append(expected_int)
                            continue
                        ocr_text = str(ocr_text)

                        # Ghi dòng hợp lệ
                        writer.write_line({"id": v, "ocr": ocr_text})
                        wrote += 1

                    # Ghi file lỗi nếu có
                    if bad_ids:
                        append_error_ids(err_file, bad_ids)
                        print(f"📝 batch {bi:04d} | logged {len(bad_ids)} bad id(s) to {err_file.name}")

                    print(f"✅ batch {bi:04d}/{len(batches)} | key {key[:8]}… | model {model_id} | wrote {wrote}/{len(batch)} rows (immediate)")
                    break

                except Exception as err:
                    if is_rate_limit_error(err):
                        rot.mark_429(key)
                        key = rot.current_key()
                        wait = random.uniform(CFG.err_retry_min, CFG.err_retry_max)
                        print(f"↻ 429 → đổi sang key {key[:8]}… sau khi chờ {wait:.1f}s (attempt {attempt}/{max_attempts})")
                        time.sleep(wait)
                        continue
                    elif is_authz_error(err):
                        rot.ban(key)
                        key = rot.current_key()
                        wait = random.uniform(CFG.err_retry_min, CFG.err_retry_max)
                        print(f"↻ 401/403 → đổi sang key {key[:8]}… sau khi chờ {wait:.1f}s (attempt {attempt}/{max_attempts})")
                        time.sleep(wait)
                        continue
                    else:
                        wait = random.uniform(CFG.err_retry_min, CFG.err_retry_max)
                        print(f"⚠️ batch {bi:04d} | key {key[:8]}… | error: {err} → chờ {wait:.1f}s rồi retry (attempt {attempt}/{max_attempts})")
                        time.sleep(wait)
                        # nếu là lần cuối và vẫn fail → log toàn bộ ID batch là lỗi parsing
                        if attempt >= max_attempts:
                            all_ids = []
                            for sid, _ in batch:
                                v = _parse_int_like(sid)
                                if v is not None: all_ids.append(v)
                            append_error_ids(err_file, all_ids)
                            print(f"📝 batch {bi:04d} | final fail → logged {len(all_ids)} id(s) to {err_file.name}")
                        continue

            rot.on_call_finished()
            if attempt >= max_attempts:
                with open(CFG.out_file.with_suffix(".failed.log"), "a", encoding="utf-8") as flog:
                    flog.write(f"BATCH {bi} (size={len(batch)}) FAILED after {max_attempts} attempts | key={key[:8]}…\n")
                print(f"❌ batch {bi:04d}/{len(batches)} | bỏ sau {max_attempts} attempts")

    print("\n📊 Calls per key (batches attempted):")
    for k, c in rot.usage_calls.items():
        print(f"{k[:8]}… : {c}")

if __name__ == "__main__":
    main()