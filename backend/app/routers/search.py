from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json
import time
from pathlib import Path
from collections import defaultdict
import logging

from app.core.config import settings
from app.logger.logger import log_search_query
from app.services.method.multimodel_search import get_multimodel_search
from app.services.method.asr_ocr import get_asr_ocr_search
from app.services.method.ic_search import get_ic_search
from app.utils.mapping import load_mapping_kf, load_mapping_scene
from app.services.method.object_filter import ObjectFilterSearch
from app.utils.scale import ScoreScaler
from app.utils.translator import get_translator

logger = logging.getLogger(__name__)
router = APIRouter()


class QuerySection(BaseModel):
    query: str
    ocrText: Optional[str] = ""
    toggles: Dict[str, bool]
    selectedObjects: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str  
    method: str
    top_k: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None
    queries: Optional[List[QuerySection]] = None  
    mode: Optional[str] = "E"  


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    method: str
    per_method_results: Optional[Dict[str, List[Dict[str, Any]]]] = None


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


def _ensemble_multimodal_results(clip_res, beit3_res, bigg_res, top_k):
    """
    Ensemble CLIP, BEiT3, BIGG results with z-score normalization.
    Returns list of results with ensembled scores.
    """
    clip_z = ScoreScaler.z_score_normalize([r["score"] for r in clip_res])
    beit3_z = ScoreScaler.z_score_normalize([r["score"] for r in beit3_res])
    bigg_z = ScoreScaler.z_score_normalize([r["score"] for r in bigg_res])

    # Weights for multimodal ensemble
    clip_weight = 0.25
    beit3_weight = 0.50
    bigg_weight = 0.25

    ensemble = defaultdict(float)
    meta = {}

    def accumulate(res, zlist, w):
        for r, z in zip(res, zlist):
            rid = r["id"]
            ensemble[rid] += z * w
            if rid not in meta:
                meta[rid] = r

    accumulate(clip_res, clip_z, clip_weight)
    accumulate(beit3_res, beit3_z, beit3_weight)
    accumulate(bigg_res, bigg_z, bigg_weight)

    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]
    final_scores = ScoreScaler.min_max_scale([s for _, s in ranked])

    results = []
    for (rid, _), s in zip(ranked, final_scores):
        item = meta.get(rid, {}).copy()
        item["score"] = s
        item["id"] = rid
        results.append(item)

    return results


def _ensemble_all_methods(method_results: Dict[str, List[Dict]], top_k: int):
    """
    Ensemble results from multiple methods (multimodal, IC, ASR, OCR).
    Each method's results should already be scaled to [0,1] range.
    We combine them directly without additional normalization to preserve rankings.
    """
    ensemble = defaultdict(float)
    meta = {}

    # Equal weight for each method
    num_methods = len(method_results)
    if num_methods == 0:
        return []

    weight_per_method = 1.0 / num_methods

    for method_name, results in method_results.items():
        if not results:
            continue

        # All scores are already scaled to [0,1], just weight them
        for r in results:
            rid = r["id"]
            score = r["score"]  # Already scaled [0,1]
            ensemble[rid] += score * weight_per_method
            if rid not in meta:
                meta[rid] = r

    # Rank by combined scores (already in [0,1] range)
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]

    final_results = []
    for rid, combined_score in ranked:
        item = meta.get(rid, {}).copy()
        item["score"] = combined_score  # Use combined score as-is
        item["id"] = rid
        final_results.append(item)

    return final_results


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    start_time = time.time()
    method = (request.method or "ensemble").lower()
    top_k = request.top_k or settings.DEFAULT_TOP_K
    mode = (request.mode or "E").upper()  # E = ensemble only, A = all methods

    try:
        # Check if we have multiple query sections with different toggles
        queries = request.queries or []
        
        # DEBUG: Log what we received
        logger.info(f"[ENSEMBLE DEBUG] Received queries: {queries}")
        logger.info(f"[ENSEMBLE DEBUG] Method: {method}")
        
        # Determine which methods are enabled
        enabled_methods = set()
        if queries:
            for q_section in queries:
                toggles = q_section.toggles or {}
                logger.info(f"[ENSEMBLE DEBUG] Query section toggles: {toggles}")
                if toggles.get("multimodal") or toggles.get("multiModal"):
                    enabled_methods.add("multimodal")
                if toggles.get("ic") or toggles.get("caption"):
                    enabled_methods.add("ic")
                if toggles.get("asr"):
                    enabled_methods.add("asr")
                if toggles.get("ocr"):
                    enabled_methods.add("ocr")
        
        # If no queries provided, fall back to old behavior based on method
        if not enabled_methods:
            if method == "ensemble":
                enabled_methods.add("multimodal")
            elif method == "caption":
                enabled_methods.add("ic")
            elif method == "text":
                enabled_methods.add("asr")
            elif method in {"clip", "beit3", "bigg"}:
                enabled_methods.add(method)
            else:
                enabled_methods.add(method)
        
        # WORKAROUND: If only IC detected but user wants ensemble behavior,
        # check if they're trying to use multiple methods via old API
        # This is a temporary fix until frontend properly sends queries array
        if len(enabled_methods) == 1 and method in ["ensemble", "caption"]:
            logger.info(f"[ENSEMBLE] WORKAROUND: Queries array empty, using method '{method}' as fallback")

        logger.info(f"[ENSEMBLE] Enabled methods: {enabled_methods}, Total: {len(enabled_methods)}")

        # Store results per method for plotting
        per_method_results = {}
        
        # Execute searches for each enabled method
        query_text = request.query
        
        # Translate Vietnamese to English if NOT using ASR
        # ASR should use original Vietnamese text
        if "asr" not in enabled_methods:
            translator = get_translator()
            if translator.is_vietnamese(query_text):
                query_text = translator.translate(query_text)
                logger.info(f"[TRANSLATE] Using translated query for non-ASR methods: '{query_text}'")
        
        # Determine if we should use ocrText instead of query for OCR search
        # OCR text is NOT translated - use original text
        ocr_query_text = query_text
        if queries and "ocr" in enabled_methods:
            # Use ocrText if provided in queries array
            for q_section in queries:
                if q_section.toggles.get("ocr") and q_section.ocrText:
                    ocr_query_text = q_section.ocrText  # Use original OCR text, no translation
                    logger.info(f"[ENSEMBLE] Using OCR text (no translation): '{ocr_query_text}'")
                    break

        # 1. Handle multimodal search (CLIP + BEiT3 + BIGG)
        if "multimodal" in enabled_methods:
            logger.info(f"[ENSEMBLE] Running multimodal search")
            multimodel_search = get_multimodel_search()
            
            # Get individual model results
            clip_res = multimodel_search.search_single_model(query_text, "clip", top_k * 2)
            beit3_res = multimodel_search.search_single_model(query_text, "beit3", top_k * 2)
            bigg_res = multimodel_search.search_single_model(query_text, "bigg", top_k * 2)
            
            # Log sub-method results
            clip_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in clip_res[:10]])
            beit3_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in beit3_res[:10]])
            bigg_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in bigg_res[:10]])
            logger.info(f"[ENSEMBLE] CLIP top results: {clip_top}")
            logger.info(f"[ENSEMBLE] BEiT3 top results: {beit3_top}")
            logger.info(f"[ENSEMBLE] BIGG top results: {bigg_top}")
            
            # Ensemble the 3 multimodal sub-methods
            multimodal_ensemble = _ensemble_multimodal_results(clip_res, beit3_res, bigg_res, top_k)
            per_method_results["multimodal"] = multimodal_ensemble
            
            multimodal_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in multimodal_ensemble[:10]])
            logger.info(f"[ENSEMBLE] Multimodal ensemble top results: {multimodal_top}")
            
            if mode == "A":
                per_method_results["clip"] = clip_res[:top_k]
                per_method_results["beit3"] = beit3_res[:top_k]
                per_method_results["bigg"] = bigg_res[:top_k]
        
        # 2. Handle IC (Image Captioning) search
        if "ic" in enabled_methods:
            logger.info(f"[ENSEMBLE] Running IC search")
            ic_results = get_ic_search().search(query_text, top_k)
            
            # Scale Cohere rerank scores to [0, 1] using min-max normalization
            if ic_results:
                raw_scores = [r["score"] for r in ic_results]
                scaled_scores = ScoreScaler.min_max_scale(raw_scores)
                for r, scaled in zip(ic_results, scaled_scores):
                    r["score"] = scaled
            
            per_method_results["ic"] = ic_results
            ic_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in ic_results[:10]])
            logger.info(f"[ENSEMBLE] IC top results (scaled): {ic_top}")
        
        # 3. Handle ASR search
        if "asr" in enabled_methods:
            logger.info(f"[ENSEMBLE] Running ASR search")
            asr_results = get_asr_ocr_search().search_asr(query_text, top_k)
            
            # Scale BM25 scores using sigmoid scaling
            if asr_results:
                raw_scores = [r["score"] for r in asr_results]
                scaled_scores = ScoreScaler.bm25_scale(raw_scores)
                for r, scaled in zip(asr_results, scaled_scores):
                    r["score"] = scaled
            
            per_method_results["asr"] = asr_results
            asr_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in asr_results[:10]])
            logger.info(f"[ENSEMBLE] ASR top results (scaled): {asr_top}")
        
        # 4. Handle OCR search
        if "ocr" in enabled_methods:
            logger.info(f"[ENSEMBLE] Running OCR search with text: '{ocr_query_text}'")
            ocr_results = get_asr_ocr_search().search_ocr(ocr_query_text, top_k)
            
            # Scale BM25 scores using sigmoid scaling
            if ocr_results:
                raw_scores = [r["score"] for r in ocr_results]
                scaled_scores = ScoreScaler.bm25_scale(raw_scores)
                for r, scaled in zip(ocr_results, scaled_scores):
                    r["score"] = scaled
            
            per_method_results["ocr"] = ocr_results
            ocr_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in ocr_results[:10]])
            logger.info(f"[ENSEMBLE] OCR top results (scaled): {ocr_top}")

        # 5. Ensemble all methods together if multiple methods enabled
        logger.info(f"[ENSEMBLE] Check: {len(enabled_methods)} enabled methods, per_method_results keys: {list(per_method_results.keys())}")
        if len(enabled_methods) > 1:
            logger.info(f"[ENSEMBLE] Ensembling {len(enabled_methods)} methods: {enabled_methods}")
            final_results = _ensemble_all_methods(per_method_results, top_k)
            final_top = ', '.join([f"{r['id']}:{r['score']:.4f}" for r in final_results[:20]])
            logger.info(f"[ENSEMBLE] Final ensemble top results: {final_top}")
        else:
            # Only one method enabled, use its results directly
            logger.info(f"[ENSEMBLE] Single method - using results directly from: {list(per_method_results.keys())}")
            final_results = list(per_method_results.values())[0] if per_method_results else []
        
        # 6. Apply object filtering to final ensemble if enabled
        filters = request.filters or {}
        selected_objects = filters.get("selectedObjects", [])
        object_filter_enabled = filters.get("objectFilter", False)

        if object_filter_enabled and selected_objects and final_results:
            logger.info(f"[ENSEMBLE] Applying object filter with {len(selected_objects)} objects")
            obj_filter = ObjectFilterSearch()
            original_ids = [str(r["id"]) for r in final_results]
            filtered_ids = obj_filter.filter(original_ids, selected_objects)
            final_results = [r for r in final_results if str(r["id"]) in filtered_ids]

        # 7. Determine what to return based on mode
        if mode == "E":
            # Mode E: return only ensemble result
            return_results = final_results
            return_per_method = None
        else:
            # Mode A: return ensemble + all per-method results
            return_results = final_results
            return_per_method = per_method_results

        duration_ms = (time.time() - start_time) * 1000
        log_search_query(
            query=request.query,
            method=f"ensemble_{'+'.join(enabled_methods)}" if len(enabled_methods) > 1 else method,
            top_k=top_k,
            filters=request.filters,
            results_count=len(return_results),
            duration_ms=duration_ms
        )

        return SearchResponse(
            results=return_results,
            total=len(return_results),
            query=request.query,
            method=method,
            per_method_results=return_per_method
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        log_search_query(
            query=request.query,
            method=method,
            top_k=top_k,
            filters=request.filters,
            results_count=0,
            duration_ms=(time.time() - start_time) * 1000
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
