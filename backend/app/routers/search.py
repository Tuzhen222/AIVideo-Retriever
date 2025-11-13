from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json
import time
from pathlib import Path

from app.core.config import settings
from app.logger.logger import log_search_query
from app.services.multimodel_search import get_multimodel_search
from app.services.method.asr_ocr import get_asr_ocr_search
from app.utils.mapping import load_mapping_kf, load_mapping_scene

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    method: str
    top_k: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    method: str


def _resolve_data_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if not path.is_absolute():
        backend_root = Path(__file__).resolve().parents[2]
        path = backend_root / path
    return path


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON from {path}: {exc}")


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    start_time = time.time()
    method = (request.method or "ensemble").lower()
    top_k = request.top_k or settings.DEFAULT_TOP_K

    try:
        results: List[Dict[str, Any]] = []

        if method == "text":
            asr_ocr = get_asr_ocr_search()
            results = asr_ocr.search_asr(request.query, top_k=top_k)
        elif method == "ocr":
            asr_ocr = get_asr_ocr_search()
            results = asr_ocr.search_ocr(request.query, top_k=top_k)
        elif method in {"clip", "beit3", "bigg", "caption"}:
            search_engine = get_multimodel_search()
            target_model = method if method in {"clip", "beit3", "bigg"} else "clip"
            results = search_engine.search_single_model(request.query, model=target_model, top_k=top_k)
        elif method == "ensemble":
            search_engine = get_multimodel_search()
            results = search_engine.search(request.query, top_k=top_k)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported search method: {request.method}")

        duration_ms = (time.time() - start_time) * 1000
        log_search_query(
            query=request.query,
            method=method,
            top_k=top_k,
            filters=request.filters,
            results_count=len(results),
            duration_ms=duration_ms
        )

        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            method=method
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        log_search_query(
            query=request.query,
            method=method,
            top_k=top_k,
            filters=request.filters,
            results_count=0,
            duration_ms=duration_ms
        )
        raise HTTPException(status_code=500, detail=f"Search error: {exc}")


@router.get("/search/methods")
async def get_search_methods():
    return {
        "methods": [
            "ensemble",
            "clip",
            "beit3",
            "bigg",
            "caption",
            "text",
            "ocr",
        ]
    }


@router.get("/search/config")
async def get_search_config():
    return {
        "default_top_k": settings.DEFAULT_TOP_K
    }


@router.get("/media-index")
async def get_media_index():
    media_index_path = _resolve_data_path(Path(settings.INDEX_DIR) / "media_index.json")
    return _load_json(media_index_path)


@router.get("/fps-mapping")
async def get_fps_mapping():
    fps_path = _resolve_data_path(Path(settings.INDEX_DIR) / "fps_mapping.json")
    return _load_json(fps_path)


@router.get("/mapping-kf")
async def get_mapping_kf():
    return load_mapping_kf()


@router.get("/mapping-scene")
async def get_mapping_scene():
    return load_mapping_scene()
