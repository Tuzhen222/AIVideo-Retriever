"""
Score scaling utilities for ensemble search
"""
import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def min_max_scale(scores: List[float], min_val: Optional[float] = None, max_val: Optional[float] = None) -> List[float]:
    """
    Scale scores to [0, 1] range using min-max normalization
    
    Args:
        scores: List of scores to scale
        min_val: Minimum value (if None, use min of scores)
        max_val: Maximum value (if None, use max of scores)
        
    Returns:
        Scaled scores in [0, 1] range
    """
    if not scores:
        return []
    
    scores_array = np.array(scores, dtype=np.float32)
    
    if min_val is None:
        min_val = np.min(scores_array)
    if max_val is None:
        max_val = np.max(scores_array)
    
    # Handle case where all scores are the same
    if max_val == min_val:
        return [1.0] * len(scores)
    
    # Min-max scaling: (x - min) / (max - min)
    scaled = (scores_array - min_val) / (max_val - min_val)
    
    return scaled.tolist()


def z_score_normalize(scores: List[float], mean: Optional[float] = None, std: Optional[float] = None) -> List[float]:
    """
    Normalize scores using z-score (mean=0, std=1) WITHOUT mapping to [0, 1]
    This is useful for ensemble when different methods have different score distributions
    
    Args:
        scores: List of scores to normalize
        mean: Mean value (if None, calculate from scores)
        std: Standard deviation (if None, calculate from scores)
        
    Returns:
        Normalized z-scores (can be negative, mean=0, std=1)
    """
    if not scores:
        return []
    
    scores_array = np.array(scores, dtype=np.float32)
    
    if mean is None:
        mean = np.mean(scores_array)
    if std is None:
        std = np.std(scores_array)
    
    # Handle case where std is 0
    if std == 0:
        return [0.0] * len(scores)
    
    # Z-score normalization: (x - mean) / std
    z_scores = (scores_array - mean) / std
    
    return z_scores.tolist()


def z_score_scale(scores: List[float], mean: Optional[float] = None, std: Optional[float] = None) -> List[float]:
    """
    Scale scores using z-score normalization (mean=0, std=1)
    Then map to [0, 1] range using sigmoid
    
    Args:
        scores: List of scores to scale
        mean: Mean value (if None, calculate from scores)
        std: Standard deviation (if None, calculate from scores)
        
    Returns:
        Scaled scores in [0, 1] range
    """
    if not scores:
        return []
    
    scores_array = np.array(scores, dtype=np.float32)
    
    if mean is None:
        mean = np.mean(scores_array)
    if std is None:
        std = np.std(scores_array)
    
    # Handle case where std is 0
    if std == 0:
        return [1.0] * len(scores)
    
    # Z-score normalization
    z_scores = (scores_array - mean) / std
    
    # Map to [0, 1] using sigmoid
    scaled = 1 / (1 + np.exp(-z_scores))
    
    return scaled.tolist()


def percentile_scale(scores: List[float], percentile: float = 0.95) -> List[float]:
    """
    Scale scores using percentile-based normalization
    Maps scores to [0, 1] where percentile becomes 1.0
    
    Args:
        scores: List of scores to scale
        percentile: Percentile to use as maximum (default 0.95)
        
    Returns:
        Scaled scores in [0, 1] range
    """
    if not scores:
        return []
    
    scores_array = np.array(scores, dtype=np.float32)
    
    # Get percentile value
    max_val = np.percentile(scores_array, percentile * 100)
    min_val = np.min(scores_array)
    
    # Handle case where all scores are the same
    if max_val == min_val:
        return [1.0] * len(scores)
    
    # Scale to [0, 1] with percentile as max
    scaled = (scores_array - min_val) / (max_val - min_val)
    
    # Clip values above 1.0
    scaled = np.clip(scaled, 0.0, 1.0)
    
    return scaled.tolist()


def scale_search_results(
    results: List[Dict[str, Any]],
    method: str = "min_max"
) -> List[Dict[str, Any]]:
    """
    Scale scores in search results
    
    Args:
        results: List of search result dicts with 'score' key
        method: Scaling method ('min_max', 'z_score', 'percentile')
        
    Returns:
        Results with scaled scores
    """
    if not results:
        return []
    
    scores = [r.get("score", 0.0) for r in results]
    
    if method == "min_max":
        scaled_scores = min_max_scale(scores)
    elif method == "z_score":
        scaled_scores = z_score_scale(scores)
    elif method == "percentile":
        scaled_scores = percentile_scale(scores)
    else:
        logger.warning(f"Unknown scaling method: {method}, using min_max")
        scaled_scores = min_max_scale(scores)
    
    # Update results with scaled scores
    scaled_results = []
    for i, result in enumerate(results):
        new_result = result.copy()
        new_result["score"] = scaled_scores[i]
        scaled_results.append(new_result)
    
    return scaled_results

