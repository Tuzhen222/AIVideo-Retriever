import requests
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class BigGClient:    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.EMBEDDING_SERVER_MULTIMODAL
        if not self.base_url:
            raise ValueError("EMBEDDING_SERVER_MULTIMODAL must be set in environment variables")
        self.base_url = self.base_url.rstrip("/")
        self.timeout = 60
        self._batch_available = None  # Cache batch endpoint availability

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
                url = f"{self.base_url}/embedding/bigg/text/batch"
                data = {"texts": texts}
                response = requests.post(url, json=data, timeout=self.timeout)
                
                if response.status_code == 200:
                    self._batch_available = True
                    result = response.json()
                    embeddings = [np.array(emb, dtype=np.float32) for emb in result["embeddings"]]
                    return np.vstack(embeddings) if embeddings else np.array([])
                else:
                    self._batch_available = False
                    logger.info(f"[BIGG] Batch endpoint not available, using individual calls")
            except Exception as e:
                self._batch_available = False
                logger.info(f"[BIGG] Batch endpoint not available: {e}")
        
        # Use batch endpoint if available
        elif self._batch_available:
            try:
                url = f"{self.base_url}/embedding/bigg/text/batch"
                data = {"texts": texts}
                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                embeddings = [np.array(emb, dtype=np.float32) for emb in result["embeddings"]]
                return np.vstack(embeddings) if embeddings else np.array([])
            except Exception as e:
                logger.error(f"[BIGG] Batch request failed: {e}, falling back")

        # Fallback: individual requests
        embeddings = []
        for text in texts:
            try:
                url = f"{self.base_url}/embedding/bigg/text"
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
