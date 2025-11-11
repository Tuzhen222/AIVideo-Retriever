"""
CLIP embedding client - calls remote embedding API
"""
import requests
import numpy as np
from PIL import Image
from typing import List, Union
import io
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class CLIPClient:
    def __init__(self, base_url: str = None):

        self.base_url = base_url or settings.EMBEDDING_SERVER_URL
        if not self.base_url:
            raise ValueError("EMBEDDING_SERVER_URL must be set in environment variables")
        self.base_url = self.base_url.rstrip('/')
        self.timeout = 60  
    
    def extract_image_embedding(
        self,
        images: Union[List[Image.Image], Image.Image]
    ) -> np.ndarray:
        if isinstance(images, Image.Image):
            images = [images]
        
        if not images:
            return np.array([])
        
        embeddings = []
        for img in images:
            try:
                # Convert PIL Image to bytes
                img_bytes = io.BytesIO()
                img_rgb = img.convert("RGB")
                img_rgb.save(img_bytes, format='JPEG')
                img_bytes.seek(0)
                
                # Call API
                url = f"{self.base_url}/embedding/clip/image"
                files = {'file': ('image.jpg', img_bytes, 'image/jpeg')}
                
                response = requests.post(url, files=files, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                embedding = np.array(result['embedding'], dtype=np.float32)
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error extracting CLIP image embedding: {e}")
                embeddings.append(np.zeros(1024, dtype=np.float32))
        
        if not embeddings:
            return np.array([])
        
        return np.vstack(embeddings)
    
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
                url = f"{self.base_url}/embedding/clip/text"
                data = {"text": text}
                
                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                embedding = np.array(result['embedding'], dtype=np.float32)
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error extracting CLIP text embedding: {e}")
                # Return zero embedding with expected dimension
                embeddings.append(np.zeros(1024, dtype=np.float32))
        
        if not embeddings:
            return np.array([])
        
        return np.vstack(embeddings)



