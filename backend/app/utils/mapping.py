""" 
Utility functions for loading and accessing keyframe mapping files
"""
import json
import os
from typing import Optional, Dict
from functools import lru_cache
import logging

# Allow running as a script: python backend/app/utils/mapping.py
try:
    from app.core.config import settings
except ModuleNotFoundError:
    import sys
    from pathlib import Path as _Path
    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from app.core.config import settings

from pathlib import Path
import re

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_mapping_kf() -> Dict[str, str]:
    """
    Load the keyframe mapping file (mapping_kf.json)
    Returns a dictionary mapping ID (as string) to keyframe path
    """
    mapping_path = settings.MAPPING_KF_PATH
    
    # Handle both absolute and relative paths
    if not os.path.isabs(mapping_path):
        # Try relative to app directory
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        mapping_path = os.path.join(app_dir, mapping_path)
    
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        logger.info(f"Loaded keyframe mapping with {len(mapping)} entries")
        return mapping
    except FileNotFoundError:
        logger.error(f"Mapping file not found: {mapping_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing mapping file: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading mapping file: {e}")
        return {}


@lru_cache(maxsize=1)
def load_mapping_scene() -> Dict[str, str]:
    """
    Load the scene mapping file (mapping_scene.json)
    Returns a dictionary mapping scene ID (as string) to keyframe path
    """
    mapping_path = settings.MAPPING_SCENE_PATH
    
    # Handle both absolute and relative paths
    if not os.path.isabs(mapping_path):
        # Try relative to app directory
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        mapping_path = os.path.join(app_dir, mapping_path)
    
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        logger.info(f"Loaded scene mapping with {len(mapping)} entries from {mapping_path}")
        return mapping
    except FileNotFoundError:
        logger.error(f"Scene mapping file not found: {mapping_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing scene mapping file: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading scene mapping file: {e}")
        return {}


def _normalize_keyframe_path(path: str) -> str:
    """
    Normalize a keyframe path from mapping file to frontend format
    
    Args:
        path: Raw path from mapping file (e.g., "backend/app/data/keyframe/L01_V001/0.webp")
        
    Returns:
        Normalized path for frontend (e.g., "L01_V001/0.webp")
    """
    # Normalize path separators
    path = path.replace('\\', '/')
    
    # Remove common prefixes
    prefixes_to_remove = [
        'backend/app/data/keyframe/',
        'app/data/keyframe/',
        'backend/',
        '/app/data/keyframe/',
        '/app/app/data/keyframe/',
    ]
    
    for prefix in prefixes_to_remove:
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    
    # If path still contains 'keyframe/', extract after it
    if 'keyframe/' in path:
        path = path.split('keyframe/', 1)[1]
    
    return path


def get_keyframe_path(result_id: str) -> Optional[str]:
    """
    Get keyframe path for a given result ID
    
    Args:
        result_id: The ID of the search result (as string)
        
    Returns:
        Keyframe path for frontend to use (with /keyframes/ prefix), or None if not found
        Example: "/keyframes/L01_V001/0.webp"
    """
    mapping = load_mapping_kf()
    
    # Convert ID to string if needed
    id_str = str(result_id)
    
    if id_str in mapping:
        path = mapping[id_str]
        normalized_path = _normalize_keyframe_path(path)
        
        # Return path with /keyframes/ prefix for frontend
        final_path = f"/keyframes/{normalized_path}"
        logger.debug(f"Keyframe path for ID {result_id}: {final_path} (from mapping: {mapping[id_str]})")
        return final_path
    
    logger.warning(f"Keyframe path not found for ID: {result_id} (mapping has {len(mapping)} entries)")
    return None


def get_scene_keyframe_path(scene_id: str) -> Optional[str]:
    """
    Get keyframe path for a given scene ID using mapping_scene.json
    Reuses the same path processing logic as get_keyframe_path() but with scene mapping
    
    Args:
        scene_id: The scene ID (as string)
        
    Returns:
        Keyframe path for frontend to use (with /keyframes/ prefix), or None if not found
        Example: "/keyframes/L01_V001/0.webp"
    """
    mapping = load_mapping_scene()
    
    # Convert ID to string if needed
    id_str = str(scene_id)
    
    if id_str in mapping:
        path = mapping[id_str]
        
        # Reuse the same path normalization logic as get_keyframe_path()
        normalized_path = _normalize_keyframe_path(path)
        
        # Return path with /keyframes/ prefix for frontend
        final_path = f"/keyframes/{normalized_path}"
        logger.debug(f"Scene keyframe path for ID {scene_id}: {final_path} (from mapping: {mapping[id_str]})")
        return final_path
    
    logger.warning(f"Scene keyframe path not found for ID: {scene_id} (mapping has {len(mapping)} entries)")
    return None


def _natural_key(s: str):
    """Sort helper that treats digit sequences as numbers"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def rebuild_mapping_kf(
    keyframe_dir: Optional[str] = None,
    output_path: Optional[str] = None
) -> int:
    """
    Rebuild mapping_kf.json by scanning the existing keyframe folder.
    
    Args:
        keyframe_dir: Directory containing keyframes (defaults to settings.KEYFRAME_DIR)
        output_path: Output mapping path (defaults to settings.MAPPING_KF_PATH)
    
    Returns:
        Number of entries written
    """
    keyframe_dir = keyframe_dir or settings.KEYFRAME_DIR
    output_path = output_path or settings.MAPPING_KF_PATH

    # Resolve base app dir (backend/app)
    app_dir = Path(__file__).resolve().parents[2]

    # Resolve full paths
    keyframe_root = Path(keyframe_dir)
    if not keyframe_root.is_absolute():
        keyframe_root = (app_dir / keyframe_root).resolve()

    out_path = Path(output_path)
    if not out_path.is_absolute():
        out_path = (app_dir / out_path).resolve()

    if not keyframe_root.exists():
        logger.error(f"Keyframe directory not found: {keyframe_root}")
        return 0

    # Collect all .webp files recursively
    files = [str(p) for p in keyframe_root.rglob("*.webp")]
    if not files:
        logger.warning(f"No keyframe files found under: {keyframe_root}")

    # Normalize and sort (folder, then natural filename)
    files = [f.replace("\\", "/") for f in files]
    files.sort(key=_natural_key)

    # Store mapping paths similar to existing convention:
    # "backend/app/data/keyframe/<subdir>/<file>.webp"
    stored_prefix = "backend/"
    app_rel = str(Path(settings.KEYFRAME_DIR).as_posix())
    if app_rel.startswith("backend/"):
        stored_prefix = ""
    elif not app_rel.startswith("app/"):
        # Fallback to raw relative if it's custom
        stored_prefix = ""

    mapping = {}
    for idx, full_path in enumerate(files):
        # Compute path relative to app_dir
        rel_to_app = str(Path(full_path).resolve().relative_to(app_dir))
        rel_to_app = rel_to_app.replace("\\", "/")

        # Ensure stored path has desired prefix if needed
        if stored_prefix and rel_to_app.startswith("app/data/keyframe/"):
            stored_path = stored_prefix + rel_to_app
        else:
            stored_path = rel_to_app

        mapping[str(idx)] = stored_path

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    logger.info(f"Wrote keyframe mapping with {len(mapping)} entries to {out_path}")
    # Invalidate cache for subsequent readers
    load_mapping_kf.cache_clear()
    return len(mapping)


if __name__ == "__main__":
    # Simple CLI usage: python -m app.utils.mapping
    entries = rebuild_mapping_kf()
    print(f"Rebuilt mapping_kf.json with {entries} entries.")
