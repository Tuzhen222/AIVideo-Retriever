import requests
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings
from app.services.gemini.url_manager import URLManager

logger = logging.getLogger(__name__)


class BigGClient:    
    def __init__(self, base_url: str = None):
        if base_url:
            self.base_url = base_url.rstrip("/")
            self.url_manager = None
        else:
            if not settings.EMBEDDING_SERVER_MULTIMODAL:
                raise ValueError("EMBEDDING_SERVER_MULTIMODAL must be set in environment variables")
            
            # Use URL manager for load balancing
            self.url_manager = URLManager(settings.EMBEDDING_SERVER_MULTIMODAL)
            self.base_url = None  # Will be set per request
        
        self.timeout = 60
        self._batch_available = None  # Cache batch endpoint availability
    
    def _get_base_url(self) -> str:
        """Get base URL with load balancing"""
        if self.base_url:
            return self.base_url
        if self.url_manager:
            url = self.url_manager.get_next_url()
            logger.debug(f"[BIGG] Using server: {url}")
            return url.rstrip("/")
        raise ValueError("No base URL available")

    def extract_text_embedding(
        self,
        texts: Union[str, List[str]]
    ) -> np.ndarray:
        """
        Extract text embeddings from CLIP bigG model.
        Optimized: sends all texts in one batch request if server supports it.
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        # Try batch endpoint first (only if not already checked)
        if self._batch_available is None:
            try:
                base_url = self._get_base_url()
                url = f"{base_url}/embedding/bigg/text/batch"
                data = {"texts": texts}
                response = requests.post(url, json=data, timeout=self.timeout)
                
                if response.status_code == 200:
                    self._batch_available = True
                    result = response.json()
                    embeddings = [np.array(emb, dtype=np.float32) for emb in result["embeddings"]]
                    logger.info(f"[BIGG] Batch endpoint available, processed {len(texts)} texts")
                    return np.vstack(embeddings) if embeddings else np.array([])
                else:
                    self._batch_available = False
                    logger.info(f"[BIGG] Batch endpoint not available (status {response.status_code}), using individual calls")
            except requests.exceptions.HTTPError as e:
                if "404" in str(e):
                    self._batch_available = False
                    logger.info(f"[BIGG] Batch endpoint not supported by server, using individual calls")
                else:
                    self._batch_available = False
                    logger.warning(f"[BIGG] Batch endpoint error: {e}, using individual calls")
            except Exception as e:
                self._batch_available = False
                logger.info(f"[BIGG] Batch endpoint unavailable: {e}, using individual calls")
        
        # Use batch endpoint if available
        elif self._batch_available:
            try:
                base_url = self._get_base_url()
                url = f"{base_url}/embedding/bigg/text/batch"
                data = {"texts": texts}
                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                embeddings = [np.array(emb, dtype=np.float32) for emb in result["embeddings"]]
                return np.vstack(embeddings) if embeddings else np.array([])
            except Exception as e:
                logger.warning(f"[BIGG] Batch request failed: {e}, falling back to individual calls")
                self._batch_available = False

        # Fallback: individual requests
        embeddings = []
        for text in texts:
            try:
                base_url = self._get_base_url()
                url = f"{base_url}/embedding/bigg/text"
                data = {"text": text}

                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()

                result = response.json()
                emb = np.array(result["embedding"], dtype=np.float32)
                embeddings.append(emb)

            except Exception as e:
                logger.error(f"Error extracting CLIP bigG text embedding: {e}")
                return np.array([])

        return np.vstack(embeddings) if embeddings else np.array([])
