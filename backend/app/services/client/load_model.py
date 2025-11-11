"""
Model loading utilities for CLIP, BEiT3, and BLIP2
GPU allocation: CLIP & BEiT3 on GPU 0, BLIP2 on GPU 1
"""
import os
import torch
import gc
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Global model instances
_clip_model = None
_clip_preprocess = None
_beit3_model = None
_blip2_model = None
_blip2_processor = None


def load_clip_model(device: str = "cuda:0"):
    """Load CLIP model (ViT-H-14-378-quickgelu)"""
    global _clip_model, _clip_preprocess
    
    if _clip_model is not None:
        logger.info("CLIP model already loaded")
        return _clip_model, _clip_preprocess
    
    try:
        import open_clip
        
        MODEL_NAME = "ViT-H-14-378-quickgelu"
        PRETRAINED = "dfn5b"
        
        logger.info(f"📥 Loading CLIP model: {MODEL_NAME} ({PRETRAINED}) on {device}")
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME,
            pretrained=PRETRAINED,
            device=device
        )
        model = model.to(device).eval()
        _clip_model = model
        _clip_preprocess = preprocess
        logger.info(f"✅ CLIP model loaded on {device}")
        return model, preprocess
    except Exception as e:
        logger.error(f"❌ Failed to load CLIP model: {e}")
        raise


def load_beit3_model(checkpoint_path: str, device: str = "cuda:0"):
    """Load BEiT3 model"""
    global _beit3_model
    
    if _beit3_model is not None:
        logger.info("BEiT3 model already loaded")
        return _beit3_model
    
    try:
        import sys
        from pathlib import Path
        
        # Add beit3 path if needed
        beit3_path = Path(__file__).parent.parent.parent.parent / "unilm" / "beit3"
        if beit3_path.exists() and str(beit3_path) not in sys.path:
            sys.path.insert(0, str(beit3_path))
        
        from modeling_utils import BEiT3Wrapper, _get_large_config
        import torch.nn as nn
        import torch.nn.functional as F
        
        class BEiT3_Retrieval_Infer(BEiT3Wrapper):
            def __init__(self, args):
                super().__init__(args=args)
                dim = args.encoder_embed_dim
                self.vision_head = nn.Linear(dim, dim, bias=False)
                self.vision_head.apply(self._init_weights)
            
            @torch.inference_mode()
            def forward(self, image):
                out = self.beit3(
                    textual_tokens=None,
                    visual_tokens=image,
                    text_padding_position=None
                )
                x = out["encoder_out"][:, 0, :]
                x = self.vision_head(x)
                return F.normalize(x, dim=-1)
        
        logger.info(f"📥 Loading BEiT3 model from {checkpoint_path} on {device}")
        args = _get_large_config(img_size=384)
        args.normalize_output = False
        model = BEiT3_Retrieval_Infer(args)
        
        state = torch.load(checkpoint_path, map_location="cpu")
        model.load_state_dict(state["model"], strict=False)
        model = model.to(device).eval()
        _beit3_model = model
        logger.info(f"✅ BEiT3 model loaded on {device}")
        return model
    except Exception as e:
        logger.error(f"❌ Failed to load BEiT3 model: {e}")
        raise


def load_blip2_model(device: str = "cuda:1"):
    """Load BLIP2 model"""
    global _blip2_model, _blip2_processor
    
    if _blip2_model is not None:
        logger.info("BLIP2 model already loaded")
        return _blip2_model, _blip2_processor
    
    try:
        from transformers import AutoProcessor, AutoModelForVision2Seq
        
        logger.info(f"📥 Loading BLIP2 model on {device}")
        device_id = int(str(device).split(':')[-1]) if ':' in str(device) else 0
        
        processor = AutoProcessor.from_pretrained("Salesforce/blip2-flan-t5-xl")
        model = AutoModelForVision2Seq.from_pretrained(
            "Salesforce/blip2-flan-t5-xl",
            torch_dtype=torch.float16,
            device_map={"": device_id}
        )
        model.eval()
        
        _blip2_model = model
        _blip2_processor = processor
        logger.info(f"✅ BLIP2 model loaded on {device}")
        return model, processor
    except Exception as e:
        logger.error(f"❌ Failed to load BLIP2 model: {e}")
        raise


def load_all_models(
    beit3_checkpoint: Optional[str] = None,
    clip_device: str = "cuda:0",
    beit3_device: str = "cuda:0",
    blip2_device: str = "cuda:1"
):
    """Load all models with proper GPU allocation"""
    logger.info("🚀 Loading all models...")
    
    results = {}
    
    # Load CLIP on GPU 0
    try:
        clip_model, clip_preprocess = load_clip_model(clip_device)
        results["clip"] = {"model": clip_model, "preprocess": clip_preprocess, "device": clip_device}
    except Exception as e:
        logger.error(f"Failed to load CLIP: {e}")
        results["clip"] = None
    
    # Load BEiT3 on GPU 0
    if beit3_checkpoint:
        try:
            beit3_model = load_beit3_model(beit3_checkpoint, beit3_device)
            results["beit3"] = {"model": beit3_model, "device": beit3_device}
        except Exception as e:
            logger.error(f"Failed to load BEiT3: {e}")
            results["beit3"] = None
    
    # Load BLIP2 on GPU 1
    try:
        blip2_model, blip2_processor = load_blip2_model(blip2_device)
        results["blip2"] = {"model": blip2_model, "processor": blip2_processor, "device": blip2_device}
    except Exception as e:
        logger.error(f"Failed to load BLIP2: {e}")
        results["blip2"] = None
    
    logger.info("✅ All models loaded")
    return results


def cleanup_models():
    """Clean up all loaded models"""
    global _clip_model, _clip_preprocess, _beit3_model, _blip2_model, _blip2_processor
    
    logger.info("🧹 Cleaning up models...")
    
    if _clip_model is not None:
        del _clip_model
        _clip_model = None
    
    if _beit3_model is not None:
        del _beit3_model
        _beit3_model = None
    
    if _blip2_model is not None:
        del _blip2_model
        _blip2_model = None
    
    _clip_preprocess = None
    _blip2_processor = None
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    gc.collect()
    logger.info("✅ Models cleaned up")

