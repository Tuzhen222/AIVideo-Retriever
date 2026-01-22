from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio
import time
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.logger.logger import log_search_query
from app.services.method.multimodel_search import get_multimodel_search
from app.services.method.asr_ocr import get_asr_ocr_search
from app.services.method.ic_search import get_ic_search
from app.services.method.object_filter import ObjectFilterSearch
from app.utils.scale import ScoreScaler
from app.utils.translator import get_translator
from app.services.gemini.query_augmentation import get_query_augmentor
from app.utils.temporal_aggregation import aggregate_by_id, find_temporal_tuples

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for parallel async operations
# Increased workers for better concurrency with multiple users
_search_executor = ThreadPoolExecutor(max_workers=20)


class StageQuerySection(BaseModel):
    """Single stage query with its own settings"""
    stage_id: int
    stage_name: Optional[str] = ""
    query: str
    ocr_text: Optional[str] = ""
    toggles: Dict[str, bool]
    selected_objects: Optional[List[str]] = None


class MultiStageSearchRequest(BaseModel):
    """Request with multiple query stages"""
    stages: List[StageQuerySection]
    top_k: Optional[int] = None
    mode: Optional[str] = "E"  # E = ensemble only, A = all methods
    temporal_mode: Optional[str] = None  # "tuple" or "id" for temporal aggregation


class StageSearchResult(BaseModel):
    """Search result for a single stage"""
    stage_id: int
    stage_name: Optional[str] = ""
    query_original: str
    query_0: str  # Q0 = original (or translated)
    query_1: str  # Q1 = augmented 1
    query_2: str  # Q2 = augmented 2
    results: List[Dict[str, Any]]  # Ensemble of Q0+Q1+Q2 (for mode E)
    total: int
    enabled_methods: List[str]
    per_method_results: Optional[Dict[str, List[Dict[str, Any]]]] = None  # For mode M
    # For mode A: separate results per query
    q0_results: Optional[List[Dict[str, Any]]] = None
    q1_results: Optional[List[Dict[str, Any]]] = None
    q2_results: Optional[List[Dict[str, Any]]] = None


class MultiStageSearchResponse(BaseModel):
    """Response with results from all stages"""
    stages: List[StageSearchResult]
    total_stages: int
    temporal_aggregation: Optional[Dict[str, Any]] = None  # Temporal aggregated results


def _ensemble_multimodal_results(clip_res, beit3_res, bigg_res, top_k):
    """Ensemble CLIP, BEiT3, BIGG results with z-score normalization."""
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
    """Ensemble results from multiple methods."""
    ensemble = defaultdict(float)
    meta = {}

    num_methods = len(method_results)
    if num_methods == 0:
        return []

    weight_per_method = 1.0 / num_methods

    for method_name, results in method_results.items():
        if not results:
            continue

        for r in results:
            rid = r["id"]
            score = r["score"]
            ensemble[rid] += score * weight_per_method
            if rid not in meta:
                meta[rid] = r

    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]

    final_results = []
    for rid, combined_score in ranked:
        item = meta.get(rid, {}).copy()
        item["score"] = combined_score
        item["id"] = rid
        final_results.append(item)

    return final_results


def _search_single_query_sync(query_text: str, enabled_methods: set, top_k: int, mode: str, ocr_query_text: str):
    """
    Synchronous single query search - executes all enabled methods.
    Returns (per_method_results, final_results)
    """
    per_method_results = {}
    
    # 1. Multimodal search
    if "multimodal" in enabled_methods:
        multimodel_search = get_multimodel_search()
        clip_res = multimodel_search.search_single_model(query_text, "clip", top_k * 2)
        beit3_res = multimodel_search.search_single_model(query_text, "beit3", top_k * 2)
        bigg_res = multimodel_search.search_single_model(query_text, "bigg", top_k * 2)
        
        multimodal_ensemble = _ensemble_multimodal_results(clip_res, beit3_res, bigg_res, top_k)
        per_method_results["multimodal"] = multimodal_ensemble
        
        if mode == "A":
            per_method_results["clip"] = clip_res[:top_k]
            per_method_results["beit3"] = beit3_res[:top_k]
            per_method_results["bigg"] = bigg_res[:top_k]
    
    # 2. IC search
    if "ic" in enabled_methods:
        ic_results = get_ic_search().search(query_text, top_k)
        if ic_results:
            raw_scores = [r["score"] for r in ic_results]
            scaled_scores = ScoreScaler.min_max_scale(raw_scores)
            for r, scaled in zip(ic_results, scaled_scores):
                r["score"] = scaled
        per_method_results["ic"] = ic_results
    
    # 3. ASR search
    if "asr" in enabled_methods:
        asr_results = get_asr_ocr_search().search_asr(query_text, top_k)
        if asr_results:
            raw_scores = [r["score"] for r in asr_results]
            scaled_scores = ScoreScaler.bm25_scale(raw_scores)
            for r, scaled in zip(asr_results, scaled_scores):
                r["score"] = scaled
        per_method_results["asr"] = asr_results
    
    # 4. OCR search
    if "ocr" in enabled_methods:
        ocr_results = get_asr_ocr_search().search_ocr(ocr_query_text, top_k)
        if ocr_results:
            raw_scores = [r["score"] for r in ocr_results]
            scaled_scores = ScoreScaler.bm25_scale(raw_scores)
            for r, scaled in zip(ocr_results, scaled_scores):
                r["score"] = scaled
        per_method_results["ocr"] = ocr_results
    
    # 5. Ensemble if multiple methods
    if len(enabled_methods) > 1:
        final_results = _ensemble_all_methods(per_method_results, top_k)
    else:
        final_results = list(per_method_results.values())[0] if per_method_results else []
    
    return per_method_results, final_results


async def _search_single_query_async(query_text: str, enabled_methods: set, top_k: int, mode: str, ocr_query_text: str):
    """Async wrapper for single query search"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _search_executor,
        _search_single_query_sync,
        query_text, enabled_methods, top_k, mode, ocr_query_text
    )


async def _process_single_stage(stage: StageQuerySection, top_k: int, mode: str, augmentor) -> StageSearchResult:
    """
    Process a single stage:
    1. Query augmentation (Q0, Q1, Q2)
    2. Search with Q0, Q1, Q2 in parallel
    3. Ensemble Q0, Q1, Q2 results
    4. Apply object filter
    """
    logger.info(f"[MULTISTAGE] Processing stage {stage.stage_id}: '{stage.query}'")
    
    # Determine enabled methods from toggles
    enabled_methods = set()
    if stage.toggles.get("multimodal") or stage.toggles.get("multiModal"):
        enabled_methods.add("multimodal")
    if stage.toggles.get("ic") or stage.toggles.get("caption"):
        enabled_methods.add("ic")
    if stage.toggles.get("asr"):
        enabled_methods.add("asr")
    if stage.toggles.get("ocr"):
        enabled_methods.add("ocr")
    
    if not enabled_methods:
        logger.warning(f"[MULTISTAGE] Stage {stage.stage_id} has no enabled methods")
        return StageSearchResult(
            stage_id=stage.stage_id,
            stage_name=stage.stage_name or f"Stage {stage.stage_id}",
            query_original=stage.query,
            query_0=stage.query,
            query_1=stage.query,
            query_2=stage.query,
            results=[],
            total=0,
            enabled_methods=[],
            per_method_results={} if mode in ["A", "M"] else None
        )
    
    # Translate query if not using ASR
    query_text = stage.query
    if "asr" not in enabled_methods:
        translator = get_translator()
        if translator.is_vietnamese(query_text):
            query_text = translator.translate(query_text)
            logger.info(f"[MULTISTAGE] Stage {stage.stage_id} translated: '{query_text}'")
    
    # Augment query: Q0 (original/translated), Q1, Q2
    q1, q2 = augmentor.augment_query(query_text)
    q0 = query_text  # Q0 = original (or translated)
    
    logger.info(f"[MULTISTAGE] Stage {stage.stage_id} queries: Q0='{q0}', Q1='{q1}', Q2='{q2}'")
    
    # OCR text handling
    ocr_query_text = stage.ocr_text or query_text
    
    # Search Q0, Q1, Q2 in parallel
    q0_task = _search_single_query_async(q0, enabled_methods, top_k, mode, ocr_query_text)
    q1_task = _search_single_query_async(q1, enabled_methods, top_k, mode, ocr_query_text)
    q2_task = _search_single_query_async(q2, enabled_methods, top_k, mode, ocr_query_text)
    
    (q0_per_method, q0_results), (q1_per_method, q1_results), (q2_per_method, q2_results) = await asyncio.gather(
        q0_task, q1_task, q2_task
    )
    
    logger.info(f"[MULTISTAGE] Stage {stage.stage_id} Q0 results: {len(q0_results)}, Q1: {len(q1_results)}, Q2: {len(q2_results)}")
    
    # Ensemble Q0, Q1, Q2 results
    # Equal weight for each query variant
    ensemble = defaultdict(float)
    meta = {}
    
    for results in [q0_results, q1_results, q2_results]:
        for r in results:
            rid = r["id"]
            ensemble[rid] += r["score"] / 3.0  # Average of 3 queries
            if rid not in meta:
                meta[rid] = r
    
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]
    stage_results = []
    for rid, combined_score in ranked:
        item = meta.get(rid, {}).copy()
        item["score"] = combined_score
        item["id"] = rid
        stage_results.append(item)
    
    # Apply object filter if enabled
    if stage.selected_objects and len(stage.selected_objects) > 0:
        logger.info(f"[MULTISTAGE] Stage {stage.stage_id} applying object filter: {stage.selected_objects}")
        obj_filter = ObjectFilterSearch()
        
        # Filter ensemble results
        original_ids = [str(r["id"]) for r in stage_results]
        filtered_ids = obj_filter.filter(original_ids, stage.selected_objects)
        stage_results = [r for r in stage_results if str(r["id"]) in filtered_ids]
        
        # Also filter individual query results for mode A
        if mode == "A" or mode == "M":
            q0_filtered = [r for r in q0_results if str(r["id"]) in filtered_ids]
            q1_filtered = [r for r in q1_results if str(r["id"]) in filtered_ids]
            q2_filtered = [r for r in q2_results if str(r["id"]) in filtered_ids]
        else:
            q0_filtered = q1_filtered = q2_filtered = None
            
        logger.info(f"[MULTISTAGE] Stage {stage.stage_id} after object filter: {len(stage_results)} ensemble results")
    else:
        # No object filter
        if mode == "A" or mode == "M":
            q0_filtered = q0_results[:top_k]
            q1_filtered = q1_results[:top_k]
            q2_filtered = q2_results[:top_k]
        else:
            q0_filtered = q1_filtered = q2_filtered = None
    
    # Prepare per-method results (only Q0 for simplicity in mode M)
    stage_per_method = None
    if mode == "M":
        stage_per_method = q0_per_method
    
    return StageSearchResult(
        stage_id=stage.stage_id,
        stage_name=stage.stage_name or f"Stage {stage.stage_id}",
        query_original=stage.query,
        query_0=q0,
        query_1=q1,
        query_2=q2,
        results=stage_results,
        total=len(stage_results),
        enabled_methods=list(enabled_methods),
        per_method_results=stage_per_method,
        q0_results=q0_filtered,
        q1_results=q1_filtered,
        q2_results=q2_filtered
    )


@router.post("/search/multistage", response_model=MultiStageSearchResponse)
async def search_multistage(request: MultiStageSearchRequest):
    """
    Multi-stage search endpoint.
    Each stage:
    - Has its own query
    - Generates Q0, Q1, Q2 via query augmentation
    - Has its own enabled methods (multimodal, IC, ASR, OCR)
    - Has its own object filter
    - Returns independent results
    """
    start_time = time.time()
    
    try:
        top_k = request.top_k or settings.DEFAULT_TOP_K
        mode = (request.mode or "E").upper()
        
        if not request.stages:
            raise HTTPException(status_code=400, detail="At least one stage is required")
        
        logger.info(f"[MULTISTAGE] Processing {len(request.stages)} stages")
        for i, stage in enumerate(request.stages):
            logger.info(f"[MULTISTAGE] Stage {i}: id={stage.stage_id}, query='{stage.query}', toggles={stage.toggles}, objects={stage.selected_objects}")
        
        # Initialize query augmentor
        augmentor = get_query_augmentor()
        
        # Process all stages in parallel
        stage_tasks = [
            _process_single_stage(stage, top_k, mode, augmentor)
            for stage in request.stages
        ]
        
        stage_results = await asyncio.gather(*stage_tasks)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[MULTISTAGE] Completed {len(stage_results)} stages in {duration_ms:.2f}ms")
        
        # Temporal aggregation if requested
        temporal_aggregation = None
        if request.temporal_mode in ["tuple", "id"]:
            logger.info(f"[MULTISTAGE] Performing temporal aggregation mode: {request.temporal_mode}")
            
            # Extract ensemble_of_ensemble results from each stage (Q3 results)
            # For now, use the final stage results as proxy for ensemble_of_ensemble
            stage_result_lists = [stage.results for stage in stage_results]
            
            if request.temporal_mode == "id":
                aggregated_results = aggregate_by_id(stage_result_lists)
                temporal_aggregation = {
                    "mode": "id",
                    "results": aggregated_results[:top_k],  # Limit to top_k
                    "total": len(aggregated_results)
                }
                logger.info(f"[MULTISTAGE] ID aggregation: {len(aggregated_results)} unique ids")
            
            elif request.temporal_mode == "tuple":
                tuples = find_temporal_tuples(stage_result_lists, max_tuples=top_k)
                temporal_aggregation = {
                    "mode": "tuple",
                    "tuples": tuples,
                    "total": len(tuples)
                }
                logger.info(f"[MULTISTAGE] Tuple mode: {len(tuples)} valid tuples")
        
        # Log for monitoring
        log_search_query(
            query=f"multistage_{len(request.stages)}_stages",
            method="multistage",
            top_k=top_k,
            filters={},
            results_count=sum(s.total for s in stage_results),
            duration_ms=duration_ms
        )
        
        return MultiStageSearchResponse(
            stages=stage_results,
            total_stages=len(stage_results),
            temporal_aggregation=temporal_aggregation
        )
    
    except HTTPException:
        raise
    
    except Exception as exc:
        logger.error(f"[MULTISTAGE] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Multi-stage search error: {exc}")
