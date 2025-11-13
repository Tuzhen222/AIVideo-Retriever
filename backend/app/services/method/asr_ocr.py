"""
ASR and OCR search using Elasticsearch
- ASR: searches in 'asr' index, returns results mapped via mapping_scene.json
- OCR: searches in 'ocr' index, returns results mapped via mapping_kf.json
"""
import logging
from typing import List, Dict, Any, Optional

from elasticsearch import Elasticsearch
from app.core.config import settings
from app.utils.mapping import get_keyframe_path, get_scene_keyframe_path

logger = logging.getLogger(__name__)


class ASROCRSearch:
    """ASR and OCR search using Elasticsearch"""
    
    def __init__(self):
        """Initialize Elasticsearch client"""
        self.host = settings.ELASTICSEARCH_HOST or "localhost"
        self.port = settings.ELASTICSEARCH_PORT or 9200
        
        # Build Elasticsearch connection URL
        es_url = f"http://{self.host}:{self.port}"
        
        # Prepare client configuration
        client_config = {
            "hosts": [es_url],
            "request_timeout": settings.ELASTICSEARCH_REQUEST_TIMEOUT,
            "max_retries": settings.ELASTICSEARCH_MAX_RETRIES,
            "retry_on_timeout": settings.ELASTICSEARCH_RETRY_ON_TIMEOUT,
            # Set headers to use ES 8.x compatibility
            "headers": {
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        }
        
        # Add authentication if provided
        if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
            client_config["basic_auth"] = (
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD
            )
        
        # Add SSL configuration if enabled
        if settings.ELASTICSEARCH_USE_SSL:
            client_config["use_ssl"] = True
            client_config["verify_certs"] = settings.ELASTICSEARCH_VERIFY_CERTS
            # Use https URL
            es_url = f"https://{self.host}:{self.port}"
            client_config["hosts"] = [es_url]
        
        # Initialize Elasticsearch client
        self.client = Elasticsearch(**client_config)
        
        # Test connection
        try:
            info = self.client.info()
            logger.info(f"✅ Connected to Elasticsearch at {self.host}:{self.port}")
            logger.info(f"   Cluster: {info.get('cluster_name', 'unknown')}, Version: {info.get('version', {}).get('number', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Elasticsearch: {e}")
            raise
    
    def search(
        self,
        query: str,
        index_name: str,
        method_name: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search in Elasticsearch index (ASR or OCR)
        
        Args:
            query: Search query text
            index_name: Elasticsearch index name ('asr' or 'ocr')
            method_name: Method name for result ('asr' or 'ocr')
            top_k: Number of results to return (defaults to settings.DEFAULT_TOP_K)
            
        Returns:
            List of search results with IDs (frontend will map to keyframe_path)
        """
        # Use DEFAULT_TOP_K if top_k not provided
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K
        
        try:
            search_body = {
                "query": {
                    "match": {
                        "content": {
                            "query": query,
                            "fuzziness": "AUTO"
                        }
                    }
                },
                "size": top_k
            }
            
            response = self.client.search(index=index_name, body=search_body)
            
            results = []
            for hit in response.get("hits", {}).get("hits", []):
                result_id = hit["_id"]
                score = hit["_score"]
                content = hit["_source"].get("content", "")
                
                if method_name == "ocr":
                    keyframe_path = get_keyframe_path(result_id)
                else:
                    keyframe_path = get_scene_keyframe_path(result_id)

                results.append({
                    "id": result_id,
                    "score": float(score),
                    "content": content,
                    "method": method_name,
                    "keyframe_path": keyframe_path
                })
            
            logger.info(f"{method_name.upper()} search returned {len(results)} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"{method_name.upper()} search error: {e}")
            return []
    
    def search_asr(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search ASR transcripts in Elasticsearch"""
        return self.search(query, "asr", "asr", top_k)
    
    def search_ocr(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search OCR text in Elasticsearch"""
        return self.search(query, "ocr", "ocr", top_k)


# Singleton instance
_asr_ocr_search_instance: Optional[ASROCRSearch] = None


def get_asr_ocr_search() -> ASROCRSearch:
    """Get or create ASR/OCR search instance"""
    global _asr_ocr_search_instance
    if _asr_ocr_search_instance is None:
        _asr_ocr_search_instance = ASROCRSearch()
    return _asr_ocr_search_instance

