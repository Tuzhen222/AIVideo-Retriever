"""
Qwen3-Embedding-8B text embedding client - calls remote embedding API
"""
import requests
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class QwenClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.EMBEDDING_SERVER_QWEN
        if not self.base_url:
            raise ValueError("EMBEDDING_SERVER_QWEN must be set in environment variables")

        self.base_url = self.base_url.rstrip("/")
        self.timeout = 60  

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
                url = f"{self.base_url}/embedding/qwen/text"
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
