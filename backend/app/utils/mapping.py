"""
Utility functions for loading and accessing keyframe mapping files
"""
import json
import os
from typing import Optional, Dict
from functools import lru_cache
import logging
from app.core.config import settings

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
        
        # Extract relative path within keyframe directory
        # Mapping paths are like: "backend/app/data/keyframe/L01_V001/0.webp"
        # or "app/data/keyframe/L01_V001/0.webp"
        # We need: "L01_V001/0.webp"
        
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
        
        # Return path with /keyframes/ prefix for frontend
        return f"/keyframes/{path}"
    
    logger.warning(f"Keyframe path not found for ID: {result_id}")
    return None

