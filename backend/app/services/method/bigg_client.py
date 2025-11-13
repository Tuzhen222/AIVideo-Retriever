"""
CLIP ViT-bigG embedding client - calls remote embedding API
"""
import requests
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class BigGClient:    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.EMBEDDING_SERVER_URL
        if not self.base_url:
            raise ValueError("EMBEDDING_SERVER_URL must be set in environment variables")
        self.base_url = self.base_url.rstrip('/')
        self.timeout = 60  # seconds
    
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
                # Call API
                url = f"{self.base_url}/embedding/bigg/text"
                data = {"text": text}
                
                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                embedding = np.array(result['embedding'], dtype=np.float32)
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error extracting CLIP bigG text embedding: {e}")
                # Fallback to 1024-dim zero vector (common for CLIP variants)
                embeddings.append(np.zeros(1024, dtype=np.float32))
        
        if not embeddings:
            return np.array([])
        
        return np.vstack(embeddings)


