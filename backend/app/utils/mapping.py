import json
import os
from typing import Optional, Dict
from functools import lru_cache
from pathlib import Path
import re

try:
    from app.core.config import settings
except ModuleNotFoundError:
    import sys
    base = Path(__file__).resolve().parents[2]
    sys.path.append(str(base))
    from app.core.config import settings


@lru_cache(maxsize=1)
def load_mapping_kf() -> Dict[str, str]:
    mapping_path = settings.MAPPING_KF_PATH

    if not os.path.isabs(mapping_path):
        base = Path(__file__).resolve().parents[2]
        mapping_path = base / mapping_path

    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


@lru_cache(maxsize=1)
def load_mapping_scene() -> Dict[str, str]:
    mapping_path = settings.MAPPING_SCENE_PATH

    if not os.path.isabs(mapping_path):
        base = Path(__file__).resolve().parents[2]
        mapping_path = base / mapping_path

    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _normalize_keyframe_path(path: str) -> str:
    path = path.replace("\\", "/")

    remove_prefix = [
        "backend/app/data/keyframes/",
        "app/data/keyframes/",
        "backend/",
        "/app/data/keyframes/",
        "/app/app/data/keyframes/",
    ]

    for p in remove_prefix:
        if path.startswith(p):
            path = path[len(p):]
            break

    if "keyframe/" in path:
        path = path.split("keyframe/", 1)[1]

    return path


def get_keyframe_path(result_id: str) -> Optional[str]:
    mapping = load_mapping_kf()
    rid = str(result_id)

    if rid not in mapping:
        return None

    normalized = _normalize_keyframe_path(mapping[rid])
    return f"/keyframes/{normalized}"


def get_scene_keyframe_path(scene_id: str) -> Optional[str]:
    mapping = load_mapping_scene()
    sid = str(scene_id)

    if sid not in mapping:
        return None

    normalized = _normalize_keyframe_path(mapping[sid])
    return f"/keyframes/{normalized}"


def _natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def rebuild_mapping_kf(
    keyframe_dir: Optional[str] = None,
    output_path: Optional[str] = None
) -> int:
    keyframe_dir = keyframe_dir or settings.KEYFRAME_DIR
    output_path = output_path or settings.MAPPING_KF_PATH

    base = Path(__file__).resolve().parents[2]

    root = Path(keyframe_dir)
    if not root.is_absolute():
        root = (base / root).resolve()

    out_path = Path(output_path)
    if not out_path.is_absolute():
        out_path = (base / out_path).resolve()

    if not root.exists():
        return 0

    files = [str(p).replace("\\", "/") for p in root.rglob("*.webp")]
    files.sort(key=_natural_key)

    mapping = {}
    for idx, full in enumerate(files):
        rel = str(Path(full).resolve().relative_to(base)).replace("\\", "/")
        mapping[str(idx)] = rel

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    load_mapping_kf.cache_clear()
    return len(mapping)
