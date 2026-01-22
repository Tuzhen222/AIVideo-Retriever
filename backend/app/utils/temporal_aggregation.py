"""
Temporal aggregation utilities for multi-stage search results.

Supports two temporal modes:
1. Tuple mode: Find tuples where id1 < id2 < ... < idN (same video, increasing keyframes)
2. ID mode: Aggregate by media id, sum scores across stages
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from itertools import product

logger = logging.getLogger(__name__)


def extract_video_and_frame(keyframe_path: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract video folder and frame index from keyframe_path.
    
    Supports both 2-level and 3-level structures:
    - 2-level: "/keyframe/L01_V001/123.webp" -> ("L01_V001", 123)
    - 3-level: "/keyframe/L02/L02_V001/123.webp" -> ("L02_V001", 123)
    - "L01_V001/123.webp" -> ("L01_V001", 123)
    - "L02/L02_V001/123.webp" -> ("L02_V001", 123)
    
    Returns:
        (video_folder, frame_index) or (None, None) if parsing fails
    """
    if not keyframe_path:
        return None, None
    
    # Normalize path
    path = keyframe_path.replace("\\", "/")
    if path.startswith("/"):
        path = path[1:]
    
    # Remove "keyframe/" prefix if present
    if path.startswith("keyframe/"):
        path = path[len("keyframe/"):]
    
    # Split into parts
    parts = path.split("/")
    if len(parts) < 2:
        return None, None
    
    # Handle both 2-level (folder/file) and 3-level (level/folder/file) structures
    # For 3-level: L02/L02_V001/file.webp -> video_folder = L02_V001
    # For 2-level: L01_V001/file.webp -> video_folder = L01_V001
    if len(parts) >= 3:
        # 3-level structure: level/folder/filename
        video_folder = parts[-2]  # Second-to-last part is the video folder
        filename = parts[-1]      # Last part is the filename
    else:
        # 2-level structure: folder/filename
        video_folder = parts[0]
        filename = parts[1]
    
    # Extract frame index from filename (e.g., "123.webp" -> 123)
    try:
        frame_idx = int(filename.split(".")[0])
        return video_folder, frame_idx
    except (ValueError, IndexError):
        return None, None


def aggregate_by_id(stage_results: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Aggregate results across stages by media id.
    
    For each unique id:
    - Sum scores across all stages where it appears
    - Track which stages contributed
    - Keep metadata from first occurrence
    
    Args:
        stage_results: List of stage result lists, each stage has list of {id, score, ...}
    
    Returns:
        List of aggregated results sorted by total score (descending)
    """
    aggregated = defaultdict(lambda: {
        "total_score": 0.0,
        "contributing_stages": [],
        "stage_scores": {},
        "metadata": None
    })
    
    for stage_idx, stage_res in enumerate(stage_results):
        stage_id = stage_idx + 1  # 1-indexed
        
        for result in stage_res:
            rid = result["id"]
            score = result.get("score", 0.0)
            
            agg = aggregated[rid]
            agg["total_score"] += score
            agg["contributing_stages"].append(stage_id)
            agg["stage_scores"][stage_id] = score
            
            # Keep metadata from first occurrence
            if agg["metadata"] is None:
                agg["metadata"] = result.copy()
    
    # Build final results
    final_results = []
    for rid, agg in aggregated.items():
        result = agg["metadata"].copy()
        result["id"] = rid
        result["score"] = agg["total_score"]
        result["contributing_stages"] = sorted(agg["contributing_stages"])
        result["stage_scores"] = agg["stage_scores"]
        result["num_stages"] = len(agg["contributing_stages"])
        final_results.append(result)
    
    # Sort by total score descending
    final_results.sort(key=lambda x: x["score"], reverse=True)
    
    logger.info(f"[TEMPORAL_AGG] ID mode: aggregated {len(final_results)} unique ids from {len(stage_results)} stages")
    return final_results


def find_temporal_tuples(stage_results: List[List[Dict[str, Any]]], max_tuples: int = 200) -> List[Dict[str, Any]]:
    """
    Find tuples where:
    - Each tuple has exactly 1 result from each stage
    - All results in tuple belong to same video
    - Frame indices are strictly increasing: frame1 < frame2 < ... < frameN
    
    Args:
        stage_results: List of stage result lists
        max_tuples: Maximum number of tuples to return
    
    Returns:
        List of tuples, each tuple is:
        {
            "tuple_id": int,
            "video": str,
            "results": [result1, result2, ...],  # One per stage
            "frame_indices": [idx1, idx2, ...],
            "total_score": float,
            "num_stages": int
        }
    """
    num_stages = len(stage_results)
    if num_stages == 0:
        return []
    
    logger.info(f"[TEMPORAL_AGG] Tuple mode: finding tuples from {num_stages} stages")
    
    # Parse all results to extract video and frame info
    # Structure: stage_data[stage_idx] = {video: [(result, frame_idx), ...]}
    stage_data = []
    for stage_idx, stage_res in enumerate(stage_results):
        video_groups = defaultdict(list)
        
        for result in stage_res:
            keyframe_path = result.get("keyframe_path")
            if not keyframe_path:
                continue
            
            video, frame_idx = extract_video_and_frame(keyframe_path)
            if video is None or frame_idx is None:
                continue
            
            video_groups[video].append((result, frame_idx))
        
        # Sort each video's results by frame_idx for efficient iteration
        for video in video_groups:
            video_groups[video].sort(key=lambda x: x[1])
        
        stage_data.append(video_groups)
        logger.info(f"[TEMPORAL_AGG] Stage {stage_idx+1}: {len(video_groups)} videos with results")
    
    # Find common videos across all stages
    if not stage_data:
        return []
    
    common_videos = set(stage_data[0].keys())
    for stage_dict in stage_data[1:]:
        common_videos &= set(stage_dict.keys())
    
    if not common_videos:
        logger.info(f"[TEMPORAL_AGG] No common videos across all stages")
        return []
    
    logger.info(f"[TEMPORAL_AGG] Found {len(common_videos)} common videos across all stages")
    
    # Generate tuples for each common video
    tuples = []
    tuple_id = 0
    
    for video in sorted(common_videos):
        # Get all results for this video from each stage
        stage_results_for_video = [
            stage_data[stage_idx][video]
            for stage_idx in range(num_stages)
        ]
        
        # Generate all combinations and filter for strictly increasing frame indices
        for combo in product(*stage_results_for_video):
            # combo = [(result1, frame1), (result2, frame2), ...]
            results = [item[0] for item in combo]
            frame_indices = [item[1] for item in combo]
            
            # Check if strictly increasing
            if all(frame_indices[i] < frame_indices[i+1] for i in range(len(frame_indices) - 1)):
                total_score = sum(r.get("score", 0.0) for r in results)
                
                tuples.append({
                    "tuple_id": tuple_id,
                    "video": video,
                    "results": results,
                    "frame_indices": frame_indices,
                    "total_score": total_score,
                    "num_stages": num_stages
                })
                
                tuple_id += 1
                
                # Limit tuples to avoid memory issues
                if len(tuples) >= max_tuples * 10:
                    break
        
        # Break if we have enough tuples
        if len(tuples) >= max_tuples * 10:
            break
    
    # Sort by total score and take top max_tuples
    tuples.sort(key=lambda x: x["total_score"], reverse=True)
    tuples = tuples[:max_tuples]
    
    logger.info(f"[TEMPORAL_AGG] Found {len(tuples)} valid tuples")
    return tuples
