"""
BLIP2 embedding client - calls remote embedding API
"""
import requests
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class BLIP2Client:    
    def __init__(self, base_url: str = None):

        self.base_url = base_url or settings.EMBEDDING_SERVER_URL
        if not self.base_url:
            raise ValueError("EMBEDDING_SERVER_URL must be set in environment variables")
        # Remove trailing slash
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
                url = f"{self.base_url}/embedding/blip2/text"
                data = {"text": text}
                
                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                embedding = np.array(result['embedding'], dtype=np.float32)
                
                # Check embedding dimension
                # Note: Collection blip2 expects 1408 dimensions, but API may return 2048
                # If dimension mismatch, we need to handle it
                if embedding.shape[0] == 2048:
                    # Resize from 2048 to 1408 by taking first 1408 dimensions
                    # This is a workaround - ideally the API should return 1408
                    logger.warning(f"BLIP2 embedding has 2048 dimensions, resizing to 1408 for Qdrant collection")
                    embedding = embedding[:1408]
                elif embedding.shape[0] != 1408:
                    logger.warning(f"BLIP2 embedding has unexpected dimension: {embedding.shape[0]}, expected 1408")
                
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error extracting BLIP2 text embedding: {e}")
                # Return zero embedding with expected dimension for Qdrant collection
                # Collection blip2 expects 1408 dimensions
                embeddings.append(np.zeros(1408, dtype=np.float32))
        
        if not embeddings:
            return np.array([])
        
        return np.vstack(embeddings)

