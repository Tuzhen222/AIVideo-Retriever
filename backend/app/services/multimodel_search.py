"""
Multi-model ensemble search
Combines CLIP, BEiT3, and BLIP2 search results with weighted ensemble
"""
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.method.clip_client import CLIPClient
from app.services.method.beit3_client import BEiT3Client
from app.services.method.blip2_client import BLIP2Client
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
        blip2_weight: Optional[float] = None,
        scale_method: Optional[str] = None
    ):
        """
        Initialize multi-model search
        
        Args:
            clip_weight: Weight for CLIP model (default from settings)
            beit3_weight: Weight for BEiT3 model (default from settings)
            blip2_weight: Weight for BLIP2 model (default from settings)
            scale_method: Score scaling method ('min_max', 'z_score', 'percentile')
        """
        # Use settings if not provided
        clip_weight = clip_weight if clip_weight is not None else settings.CLIP_WEIGHT
        beit3_weight = beit3_weight if beit3_weight is not None else settings.BEIT3_WEIGHT
        blip2_weight = blip2_weight if blip2_weight is not None else settings.BLIP2_WEIGHT
        scale_method = scale_method if scale_method is not None else settings.SCORE_SCALE_METHOD
        
        # Normalize weights to sum to 1
        total_weight = clip_weight + beit3_weight + blip2_weight
        if total_weight > 0:
            self.clip_weight = clip_weight / total_weight
            self.beit3_weight = beit3_weight / total_weight
            self.blip2_weight = blip2_weight / total_weight
        else:
            # Equal weights if all zero
            self.clip_weight = self.beit3_weight = self.blip2_weight = 1.0 / 3.0
        
        self.scale_method = scale_method
        
        # Initialize clients
        self.clip_client = CLIPClient()
        self.beit3_client = BEiT3Client()
        self.blip2_client = BLIP2Client()
        self.qdrant_client = QdrantClient()
        
        # Collection names
        self.clip_collection = "clip"
        self.beit3_collection = "beit3"
        self.blip2_collection = "blip2"
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform ensemble search across multiple models
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional filters for search
            
        Returns:
            List of search results with ensemble scores
        """
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
        
        def extract_blip2_embedding():
            try:
                embedding = self.blip2_client.extract_text_embedding(query)
                if embedding.size == 0:
                    logger.warning("BLIP2 embedding extraction failed")
                    return None
                return embedding[0]
            except Exception as e:
                logger.error(f"BLIP2 embedding error: {e}")
                return None
        
        # Extract embeddings in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            clip_future = executor.submit(extract_clip_embedding)
            beit3_future = executor.submit(extract_beit3_embedding)
            blip2_future = executor.submit(extract_blip2_embedding)
            
            clip_embedding = clip_future.result()
            beit3_embedding = beit3_future.result()
            blip2_embedding = blip2_future.result()
        
        # Step 2: Search in each collection in parallel
        def search_clip():
            if clip_embedding is None:
                return []
            try:
                results = self.qdrant_client.search(
                    collection_name=self.clip_collection,
                    query_vector=clip_embedding,
                    top_k=top_k * 2,  # Get more results for better ensemble
                    filter=filters
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
                    top_k=top_k * 2,
                    filter=filters
                )
                logger.info(f"BEiT3 search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"BEiT3 search error: {e}")
                return []
        
        def search_blip2():
            if blip2_embedding is None:
                return []
            try:
                results = self.qdrant_client.search(
                    collection_name=self.blip2_collection,
                    query_vector=blip2_embedding,
                    top_k=top_k * 2,
                    filter=filters
                )
                logger.info(f"BLIP2 search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"BLIP2 search error: {e}")
                return []
        
        # Search in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            clip_future = executor.submit(search_clip)
            beit3_future = executor.submit(search_beit3)
            blip2_future = executor.submit(search_blip2)
            
            clip_results = clip_future.result()
            beit3_results = beit3_future.result()
            blip2_results = blip2_future.result()
        
        # Step 3: Scale scores for each model
        clip_results_scaled = scale_search_results(clip_results, method=self.scale_method)
        beit3_results_scaled = scale_search_results(beit3_results, method=self.scale_method)
        blip2_results_scaled = scale_search_results(blip2_results, method=self.scale_method)
        
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
        
        # Aggregate BLIP2 scores
        for result in blip2_results_scaled:
            result_id = result["id"]
            ensemble_scores[result_id] += result["score"] * self.blip2_weight
            if result_id not in result_metadata:
                result_metadata[result_id] = result.get("payload", {})
        
        # Step 5: Sort by ensemble score and return top_k
        sorted_results = sorted(
            ensemble_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        # Format results with keyframe paths
        final_results = []
        for result_id, ensemble_score in sorted_results:
            keyframe_path = get_keyframe_path(result_id)
            result = {
                "id": result_id,
                "score": ensemble_score,
                "payload": result_metadata.get(result_id, {})
            }
            if keyframe_path:
                result["keyframe_path"] = keyframe_path
            final_results.append(result)
        
        logger.info(f"Ensemble search completed: {len(final_results)} results")
        
        return final_results
    
    def search_single_model(
        self,
        query: str,
        model: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using a single model
        
        Args:
            query: Search query text
            model: Model name ('clip', 'beit3', 'blip2')
            top_k: Number of results to return
            filters: Optional filters for search
            
        Returns:
            List of search results
        """
        model = model.lower()
        
        if model == "clip":
            embedding = self.clip_client.extract_text_embedding(query)
            if embedding.size == 0:
                return []
            embedding = embedding[0]
            collection = self.clip_collection
        elif model == "beit3":
            embedding = self.beit3_client.extract_text_embedding(query)
            if embedding.size == 0:
                return []
            embedding = embedding[0]
            collection = self.beit3_collection
        elif model == "blip2":
            embedding = self.blip2_client.extract_text_embedding(query)
            if embedding.size == 0:
                return []
            embedding = embedding[0]
            collection = self.blip2_collection
        else:
            logger.error(f"Unknown model: {model}")
            return []
        
        try:
            results = self.qdrant_client.search(
                collection_name=collection,
                query_vector=embedding,
                top_k=top_k,
                filter=filters
            )
            # Scale results
            scaled_results = scale_search_results(results, method=self.scale_method)
            # Add keyframe paths to results
            for result in scaled_results:
                result_id = result.get("id")
                if result_id:
                    keyframe_path = get_keyframe_path(result_id)
                    if keyframe_path:
                        result["keyframe_path"] = keyframe_path
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

