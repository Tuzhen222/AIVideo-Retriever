"""
Qwen3-Embedding-8B text embedding client - calls remote embedding API
"""
import requests
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings
from app.services.gemini.url_manager import URLManager

logger = logging.getLogger(__name__)


class QwenClient:
    def __init__(self, base_url: str = None):
        if base_url:
            self.base_url = base_url.rstrip("/")
            self.url_manager = None
        else:
            if not settings.EMBEDDING_SERVER_QWEN:
                raise ValueError("EMBEDDING_SERVER_QWEN must be set in environment variables")
            
            # Use URL manager for load balancing
            self.url_manager = URLManager(settings.EMBEDDING_SERVER_QWEN)
            self.base_url = None  # Will be set per request
        
        self.timeout = 60
    
    def _get_base_url(self) -> str:
        """Get base URL with load balancing"""
        if self.base_url:
            return self.base_url
        if self.url_manager:
            url = self.url_manager.get_next_url()
            logger.debug(f"[QWEN] Using server: {url}")
            return url.rstrip("/")
        raise ValueError("No base URL available")  

    def extract_text_embedding(
        self,
        texts: Union[str, List[str]]
    ) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        embeddings = []

        for text in texts:
            try:
                base_url = self._get_base_url()
                url = f"{base_url}/embedding/qwen/text"
                data = {"text": text}

                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()

                result = response.json()
                emb = np.array(result["embedding"], dtype=np.float32)

                embeddings.append(emb)

            except Exception as e:
                logger.error(f"Error extracting Qwen text embedding: {e}")
                return np.array([])

        return np.vstack(embeddings) if embeddings else np.array([])
