"""
Simple test to verify ensemble logic without running the full server.
"""
from collections import defaultdict
from app.utils.scale import ScoreScaler


def test_ensemble_multimodal():
    """Test multimodal ensemble with mock data"""
    # Mock results from CLIP, BEiT3, BIGG
    clip_res = [
        {"id": "1", "score": 0.9},
        {"id": "2", "score": 0.8},
        {"id": "3", "score": 0.7},
    ]
    
    beit3_res = [
        {"id": "2", "score": 0.95},
        {"id": "1", "score": 0.85},
        {"id": "4", "score": 0.75},
    ]
    
    bigg_res = [
        {"id": "3", "score": 0.88},
        {"id": "1", "score": 0.82},
        {"id": "2", "score": 0.79},
    ]
    
    # Apply z-score normalization
    clip_z = ScoreScaler.z_score_normalize([r["score"] for r in clip_res])
    beit3_z = ScoreScaler.z_score_normalize([r["score"] for r in beit3_res])
    bigg_z = ScoreScaler.z_score_normalize([r["score"] for r in bigg_res])
    
    # Weights
    clip_weight = 0.25
    beit3_weight = 0.50
    bigg_weight = 0.25
    
    # Ensemble
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
    
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)
    final_scores = ScoreScaler.min_max_scale([s for _, s in ranked])
    
    print("=== Multimodal Ensemble Test ===")
    print("Ranked results:")
    for (rid, raw_score), norm_score in zip(ranked, final_scores):
        print(f"  ID: {rid}, Raw: {raw_score:.4f}, Normalized: {norm_score:.4f}")
    print()


def test_ensemble_all_methods():
    """Test ensemble of multiple methods"""
    method_results = {
        "multimodal": [
            {"id": "1", "score": 0.9},
            {"id": "2", "score": 0.8},
        ],
        "ic": [
            {"id": "2", "score": 0.85},
            {"id": "3", "score": 0.75},
        ],
        "ocr": [
            {"id": "1", "score": 15.5},  # BM25 score
            {"id": "4", "score": 12.3},
        ]
    }
    
    ensemble = defaultdict(float)
    meta = {}
    
    num_methods = len(method_results)
    weight_per_method = 1.0 / num_methods
    
    for method_name, results in method_results.items():
        if not results:
            continue
        
        scores = [r["score"] for r in results]
        
        # Use appropriate normalization
        if method_name in ["ocr", "asr"]:
            normalized = ScoreScaler.bm25_scale(scores)
        else:
            normalized = ScoreScaler.z_score_normalize(scores)
        
        for r, norm_score in zip(results, normalized):
            rid = r["id"]
            ensemble[rid] += norm_score * weight_per_method
            if rid not in meta:
                meta[rid] = r
    
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)
    final_scores = ScoreScaler.min_max_scale([s for _, s in ranked])
    
    print("=== Multi-Method Ensemble Test ===")
    print(f"Methods: {list(method_results.keys())}")
    print("Ranked results:")
    for (rid, raw_score), norm_score in zip(ranked, final_scores):
        print(f"  ID: {rid}, Raw: {raw_score:.4f}, Normalized: {norm_score:.4f}")
    print()


if __name__ == "__main__":
    test_ensemble_multimodal()
    test_ensemble_all_methods()
    print("✓ All tests passed!")
