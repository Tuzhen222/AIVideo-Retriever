"""
Multi-model ensemble search
Combines CLIP, BEiT3, and CLIP bigG search results with weighted ensemble
"""
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.method.clip_client import CLIPClient
from app.services.method.beit3_client import BEiT3Client
from app.services.method.bigg_client import BigGClient
from app.services.vector_db.qdrant_client import QdrantClient
from app.utils.scale import scale_search_results
from app.utils.mapping import get_keyframe_path
from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiModelSearch:
    """Multi-model ensemble search engine"""
    
    def __init__(
        self,
        clip_weight: Optional[float] = None,
        beit3_weight: Optional[float] = None,
        bigg_weight: Optional[float] = None,
        scale_method: Optional[str] = None
    ):
        """
        Initialize multi-model search
        
        Args:
            clip_weight: Weight for CLIP model (default from settings)
            beit3_weight: Weight for BEiT3 model (default from settings)
            bigg_weight: Weight for CLIP bigG model (default from settings)
            scale_method: Score scaling method ('min_max', 'z_score', 'percentile')
        """
        clip_weight = 1.0
        beit3_weight = 2.0
        bigg_weight = 1.0
        scale_method = "min_max"
        
        # Normalize weights to sum to 1
        total_weight = clip_weight + beit3_weight + bigg_weight
        if total_weight > 0:
            self.clip_weight = clip_weight / total_weight
            self.beit3_weight = beit3_weight / total_weight
            self.bigg_weight = bigg_weight / total_weight
        else:
            # Equal weights if all zero
            self.clip_weight = self.beit3_weight = self.bigg_weight = 1.0 / 3.0
        
        self.scale_method = scale_method
        
        # Initialize clients
        self.clip_client = CLIPClient()
        self.beit3_client = BEiT3Client()
        self.bigg_client = BigGClient()
        self.qdrant_client = QdrantClient()
        
        # Collection names
        self.clip_collection = "clip"
        self.beit3_collection = "beit3"
        # Use the FAISS/Qdrant collection created from bigG embeddings
        self.bigg_collection = "bigg_clip"
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform ensemble search across multiple models
        
        Args:
            query: Search query text
            top_k: Number of results to return (defaults to settings.DEFAULT_TOP_K)
            
        Returns:
            List of search results with ensemble scores
        """
        # Use DEFAULT_TOP_K if top_k not provided
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K
        
        logger.info(f"Starting ensemble search for query: '{query}'")
        
        # Step 1: Extract embeddings from all models in parallel
        def extract_clip_embedding():
            try:
                embedding = self.clip_client.extract_text_embedding(query)
                if embedding.size == 0:
                    logger.warning("CLIP embedding extraction failed")
                    return None
                return embedding[0]
            except Exception as e:
                logger.error(f"CLIP embedding error: {e}")
                return None
        
        def extract_beit3_embedding():
            try:
                embedding = self.beit3_client.extract_text_embedding(query)
                if embedding.size == 0:
                    logger.warning("BEiT3 embedding extraction failed")
                    return None
                return embedding[0]
            except Exception as e:
                logger.error(f"BEiT3 embedding error: {e}")
                return None
        
        def extract_bigg_embedding():
            try:
                embedding = self.bigg_client.extract_text_embedding(query)
                if embedding.size == 0:
                    logger.warning("CLIP bigG embedding extraction failed")
                    return None
                return embedding[0]
            except Exception as e:
                logger.error(f"CLIP bigG embedding error: {e}")
                return None
        
        # Extract embeddings in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            clip_future = executor.submit(extract_clip_embedding)
            beit3_future = executor.submit(extract_beit3_embedding)
            bigg_future = executor.submit(extract_bigg_embedding)
            
            clip_embedding = clip_future.result()
            beit3_embedding = beit3_future.result()
            bigg_embedding = bigg_future.result()
        
        # Step 2: Search in each collection in parallel
        def search_clip():
            if clip_embedding is None:
                return []
            try:
                results = self.qdrant_client.search(
                    collection_name=self.clip_collection,
                    query_vector=clip_embedding,
                    top_k=top_k * 2  # Get more results for better ensemble
                )
                logger.info(f"CLIP search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"CLIP search error: {e}")
                return []
        
        def search_beit3():
            if beit3_embedding is None:
                return []
            try:
                results = self.qdrant_client.search(
                    collection_name=self.beit3_collection,
                    query_vector=beit3_embedding,
                    top_k=top_k * 2
                )
                logger.info(f"BEiT3 search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"BEiT3 search error: {e}")
                return []
        
        def search_bigg():
            if bigg_embedding is None:
                return []
            try:
                results = self.qdrant_client.search(
                    collection_name=self.bigg_collection,
                    query_vector=bigg_embedding,
                    top_k=top_k * 2
                )
                logger.info(f"CLIP bigG search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"CLIP bigG search error: {e}")
                return []
        
        # Search in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            clip_future = executor.submit(search_clip)
            beit3_future = executor.submit(search_beit3)
            bigg_future = executor.submit(search_bigg)
            
            clip_results = clip_future.result()
            beit3_results = beit3_future.result()
            bigg_results = bigg_future.result()
        
        # Step 3: Normalize scores for each model to same distribution before ensemble
        # Use z-score normalization to handle different score distributions (e.g., BM25 vs cosine similarity)
        from app.utils.scale import z_score_normalize
        
        # Extract raw scores and normalize to z-scores (mean=0, std=1)
        clip_scores = [r.get("score", 0.0) for r in clip_results]
        beit3_scores = [r.get("score", 0.0) for r in beit3_results]
        bigg_scores = [r.get("score", 0.0) for r in bigg_results]
        
        clip_z_scores = z_score_normalize(clip_scores) if clip_scores else []
        beit3_z_scores = z_score_normalize(beit3_scores) if beit3_scores else []
        bigg_z_scores = z_score_normalize(bigg_scores) if bigg_scores else []
        
        # Update results with normalized z-scores
        clip_results_scaled = [
            {**r, "score": clip_z_scores[i]} 
            for i, r in enumerate(clip_results)
        ]
        beit3_results_scaled = [
            {**r, "score": beit3_z_scores[i]} 
            for i, r in enumerate(beit3_results)
        ]
        bigg_results_scaled = [
            {**r, "score": bigg_z_scores[i]} 
            for i, r in enumerate(bigg_results)
        ]

        # Log per-model normalized results (ids and z-scores)
        try:
            if clip_results_scaled:
                logger.info("CLIP normalized (z-score) results (id: score): " + ", ".join(
                    f"{r.get('id')}:{r.get('score'):.4f}" for r in clip_results_scaled[:top_k]
                ))
            if beit3_results_scaled:
                logger.info("BEiT3 normalized (z-score) results (id: score): " + ", ".join(
                    f"{r.get('id')}:{r.get('score'):.4f}" for r in beit3_results_scaled[:top_k]
                ))
            if bigg_results_scaled:
                logger.info("CLIP bigG normalized (z-score) results (id: score): " + ", ".join(
                    f"{r.get('id')}:{r.get('score'):.4f}" for r in bigg_results_scaled[:top_k]
                ))
        except Exception as _:
            # Logging should never break search
            pass
        
        # Step 4: Ensemble scores by ID
        ensemble_scores = defaultdict(float)
        result_metadata = {}
        
        # Aggregate CLIP scores
        for result in clip_results_scaled:
            result_id = result["id"]
            ensemble_scores[result_id] += result["score"] * self.clip_weight
            if result_id not in result_metadata:
                result_metadata[result_id] = result.get("payload", {})
        
        # Aggregate BEiT3 scores
        for result in beit3_results_scaled:
            result_id = result["id"]
            ensemble_scores[result_id] += result["score"] * self.beit3_weight
            if result_id not in result_metadata:
                result_metadata[result_id] = result.get("payload", {})
        
        # Aggregate CLIP bigG scores
        for result in bigg_results_scaled:
            result_id = result["id"]
            ensemble_scores[result_id] += result["score"] * self.bigg_weight
            if result_id not in result_metadata:
                result_metadata[result_id] = result.get("payload", {})
        
        # Step 5: Sort by ensemble score and return top_k
        sorted_results = sorted(
            ensemble_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # Step 6: Scale ensemble scores to [0, 1]
        if sorted_results:
            ensemble_scores_list = [score for _, score in sorted_results]
            scaled_ensemble_scores = scale_search_results(
                [{"score": s} for s in ensemble_scores_list],
                method=self.scale_method
            )
            # Update sorted_results with scaled scores
            sorted_results = [
                (rid, scaled_ensemble_scores[i]["score"])
                for i, (rid, _) in enumerate(sorted_results)
            ]

        # Log ensemble results
        try:
            if sorted_results:
                logger.info("Ensemble results (id: score): " + ", ".join(
                    f"{rid}:{score:.4f}" for rid, score in sorted_results
                ))
        except Exception as _:
            pass
        
        # Format results - add keyframe_path for each ID using mapping_kf.json
        final_results = []
        for result_id, ensemble_score in sorted_results:
            result = {
                "id": result_id,
                "score": ensemble_score,
                "payload": result_metadata.get(result_id, {}),
                "keyframe_path": get_keyframe_path(result_id)
            }
            final_results.append(result)
        
        logger.info(f"Ensemble search completed: {len(final_results)} results")
        
        return final_results
    
    def search_single_model(
        self,
        query: str,
        model: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using a single model
        
        Args:
            query: Search query text
            model: Model name ('clip', 'beit3', 'bigg')
            top_k: Number of results to return (defaults to settings.DEFAULT_TOP_K)
            
        Returns:
            List of search results
        """
        # Use DEFAULT_TOP_K if top_k not provided
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K
        
        model = model.lower()
        
        if model == "clip":
            embedding = self.clip_client.extract_text_embedding(query)
            embedding = embedding[0]
            collection = self.clip_collection
        elif model == "beit3":
            embedding = self.beit3_client.extract_text_embedding(query)
            embedding = embedding[0]
            collection = self.beit3_collection
        elif model == "bigg":
            embedding = self.bigg_client.extract_text_embedding(query)
            embedding = embedding[0]
            collection = self.bigg_collection
        else:
            logger.error(f"Unknown model: {model}")
            return []
        
        try:
            results = self.qdrant_client.search(
                collection_name=collection,
                query_vector=embedding,
                top_k=top_k
            )
            scaled_results = scale_search_results(results, method=self.scale_method)
            try:
                if scaled_results:
                    logger.info(f"{model.upper()} results (id: score): " + ", ".join(
                        f"{r.get('id')}:{r.get('score'):.4f}" for r in scaled_results[:top_k]
                    ))
            except Exception as _:
                pass
            for item in scaled_results:
                item["keyframe_path"] = get_keyframe_path(item.get("id"))
            return scaled_results
        except Exception as e:
            logger.error(f"Search error for {model}: {e}")
            return []


# Global instance
_multimodel_search = None


def get_multimodel_search() -> MultiModelSearch:
    """Get or create global MultiModelSearch instance"""
    global _multimodel_search
    if _multimodel_search is None:
        _multimodel_search = MultiModelSearch()
    return _multimodel_search

