from qdrant_client import QdrantClient as QdrantSDKClient, grpc
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Optional
import numpy as np
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantClient:
    """Qdrant client wrapper with gRPC only - simplified for search only"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        grpc_port: Optional[int] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize Qdrant client"""
        self.host = host or settings.QDRANT_HOST
        self.grpc_port = grpc_port or settings.QDRANT_GRPC_PORT
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.timeout = timeout or settings.QDRANT_TIMEOUT
        
        self._client = None
        self._connect()
    
    def _connect(self):
        """Connect to Qdrant server via gRPC"""
        try:
            self._client = QdrantSDKClient(
                host=self.host,
                grpc_port=self.grpc_port,
                prefer_grpc=True,
                api_key=self.api_key,
                timeout=self.timeout
            )
            logger.info(f"✅ Connected to Qdrant via gRPC at {self.host}:{self.grpc_port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise
    
    @property
    def client(self) -> QdrantSDKClient:
        """Get Qdrant client instance"""
        if self._client is None:
            self._connect()
        return self._client
    
    def _convert_filter(self, filter_dict: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """
        Convert frontend filter format to Qdrant Filter format
        Returns None if filter is invalid or empty
        
        Note: objectFilter and selectedObjects are for Elasticsearch only,
        not supported by Qdrant. These filters are automatically ignored.
        """
        if not filter_dict:
            return None
        
        # Remove Elasticsearch-specific filters (objectFilter, selectedObjects)
        # These are only used for Elasticsearch text search, not Qdrant vector search
        if 'objectFilter' in filter_dict or 'selectedObjects' in filter_dict:
            logger.debug("Ignoring Elasticsearch filters (objectFilter, selectedObjects) - not applicable to Qdrant")
            # Remove these keys and check if any valid Qdrant filters remain
            filter_dict = {k: v for k, v in filter_dict.items() 
                          if k not in ['objectFilter', 'selectedObjects']}
            if not filter_dict:
                return None
        
        # If filter already contains Qdrant-specific keys (must, should, must_not), 
        # assume it's already in Qdrant format
        if any(key in filter_dict for key in ['must', 'should', 'must_not']):
            try:
                return Filter(**filter_dict)
            except Exception as e:
                logger.warning(f"Invalid Qdrant filter format: {e}")
                return None
        
        # If filter is empty or doesn't match any known format, return None
        return None
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float] | np.ndarray,
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:

        try:
            # Convert numpy array to list if needed
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()
            
            # Convert filter to Qdrant Filter format
            qdrant_filter = self._convert_filter(filter)
            
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                score_threshold=score_threshold
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload or {}
                })
            
            logger.debug(f"✅ Found {len(formatted_results)} results in {collection_name}")
            return formatted_results
        except Exception as e:
            logger.error(f"❌ Search failed in {collection_name}: {e}")
            raise
    

