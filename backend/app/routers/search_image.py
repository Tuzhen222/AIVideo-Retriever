"""
Image-based search endpoint
Search for similar images using CLIP image embeddings
"""
import time
import os
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.logger.logger import app_logger as logger
from app.services.vector_db.qdrant_client import get_qdrant_client
from app.utils.mapping import get_keyframe_path

router = APIRouter()


class ImageSearchRequest(BaseModel):
    """Request for image search using keyframe path"""
    keyframe_path: str
    top_k: Optional[int] = 200


class ImageSearchResponse(BaseModel):
    """Response for image search"""
    results: List[Dict[str, Any]]
    total: int
    query_image: str
    method: str = "clip-image"
    search_time_ms: float


async def get_image_embedding(image_path: str) -> List[float]:
    """
    Get CLIP image embedding from model server
    Args:
        image_path: Path to image file (e.g., "/keyframes/L01_V001/123.webp")
    Returns:
        embedding: List of floats (CLIP image embedding)
    """
    # Convert URL path to file system path
    # Frontend sends: "/keyframes/L01_V001/123.webp"
    # Need to convert to: "backend/app/data/keyframe/L01_V001/123.webp"
    
    if image_path.startswith("/keyframes/"):
        # Remove "/keyframes/" prefix and add proper data directory path
        relative_path = image_path.replace("/keyframes/", "")
        full_path = os.path.join(settings.BASE_DIR, "app", "data", "keyframes", relative_path)
    elif image_path.startswith("backend/app/data/keyframe/"):
        # Already in mapping format
        full_path = os.path.join(settings.BASE_DIR, image_path.replace("backend/", ""))
    else:
        # Try as relative path
        full_path = os.path.join(settings.BASE_DIR, "app", "data", image_path.lstrip("/"))
    
    logger.info(f"[IMAGE_SEARCH] Converted path: {image_path} -> {full_path}")
    
    if not os.path.exists(full_path):
        logger.error(f"[IMAGE_SEARCH] Image not found: {full_path}")
        raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")
    
    # Call model server to get embedding
    model_server_url = getattr(settings, "EMBEDDING_SERVER_MULTIMODAL", "http://localhost:7000")
    endpoint = f"{model_server_url}/embedding/clip/image"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(full_path, "rb") as f:
                files = {"file": (os.path.basename(full_path), f, "image/webp")}
                response = await client.post(endpoint, files=files)
                response.raise_for_status()
                
                data = response.json()
                embedding = data["embedding"]
                logger.info(f"[IMAGE_SEARCH] Got embedding dimension: {len(embedding)}")
                return embedding
                
    except httpx.HTTPError as e:
        logger.error(f"[IMAGE_SEARCH] Failed to get embedding from model server: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image embedding: {str(e)}")
    except Exception as e:
        logger.error(f"[IMAGE_SEARCH] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@router.post("/search/by-image", response_model=ImageSearchResponse)
async def search_by_image(request: ImageSearchRequest):
    """
    Search for similar images using CLIP image embedding
    
    Args:
        request: ImageSearchRequest with keyframe_path and top_k
        
    Returns:
        ImageSearchResponse with similar images
    """
    start_time = time.time()
    
    logger.info(f"[IMAGE_SEARCH] Searching for similar images to: {request.keyframe_path}")
    
    try:
        # 1. Get image embedding from model server
        embedding = await get_image_embedding(request.keyframe_path)
        
        # 2. Search in Qdrant CLIP collection
        qdrant = get_qdrant_client()
        collection_name = "clip"  # CLIP image-text collection
        
        search_results = qdrant.search(
            collection_name=collection_name,
            query_vector=embedding,
            top_k=request.top_k
        )
        
        # 3. Format results (search_results is already formatted by wrapper)
        results = []
        for i, hit in enumerate(search_results):
            payload = hit.get("payload", {})
            result_id = hit.get("id", "")
            
            # Get keyframe_path from mapping using ID (same as text search)
            keyframe_path = get_keyframe_path(result_id)
            
            if i < 3:  # Log first 3 results for debugging
                logger.info(f"[IMAGE_SEARCH] Result #{i}: ID={result_id}, Path={keyframe_path}, Score={hit.get('score', 0)}")
            
            results.append({
                "id": result_id,
                "keyframe_path": keyframe_path,
                "score": float(hit.get("score", 0)),
                "video": payload.get("video", ""),
                "frame_idx": payload.get("frame_idx"),
            })
        
        search_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[IMAGE_SEARCH] Found {len(results)} similar images in {search_time_ms:.2f}ms")
        if results:
            logger.info(f"[IMAGE_SEARCH] First result sample: {results[0]}")
        
        return ImageSearchResponse(
            results=results,
            total=len(results),
            query_image=request.keyframe_path,
            method="clip-image",
            search_time_ms=search_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[IMAGE_SEARCH] Error during search: {e}")
        raise HTTPException(status_code=500, detail=f"Image search failed: {str(e)}")


@router.post("/search/by-image-upload", response_model=ImageSearchResponse)
async def search_by_image_upload(
    file: UploadFile = File(...),
    top_k: int = 200
):
    """
    Search for similar images by uploading an image file
    
    Args:
        file: Image file upload
        top_k: Number of results to return
        
    Returns:
        ImageSearchResponse with similar images
    """
    start_time = time.time()
    
    logger.info(f"[IMAGE_SEARCH] Uploaded image: {file.filename}")
    
    try:
        # 1. Get embedding directly from uploaded file
        model_server_url = getattr(settings, "MODEL_SERVER_URL", "http://localhost:7000")
        endpoint = f"{model_server_url}/embedding/clip/image"
        
        # Read file content
        contents = await file.read()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (file.filename, contents, file.content_type)}
            response = await client.post(endpoint, files=files)
            response.raise_for_status()
            
            data = response.json()
            embedding = data["embedding"]
            logger.info(f"[IMAGE_SEARCH] Got embedding dimension: {len(embedding)}")
        
        # 2. Search in Qdrant
        qdrant = get_qdrant_client()
        collection_name = "clip"
        
        search_results = qdrant.search(
            collection_name=collection_name,
            query_vector=embedding,
            top_k=top_k
        )
        
        # 3. Format results (search_results is already formatted by wrapper)
        results = []
        for hit in search_results:
            payload = hit.get("payload", {})
            result_id = hit.get("id", "")
            
            # Get keyframe_path from mapping using ID (same as text search)
            keyframe_path = get_keyframe_path(result_id)
            
            results.append({
                "id": result_id,
                "keyframe_path": keyframe_path,
                "score": float(hit.get("score", 0)),
                "video": payload.get("video", ""),
                "frame_idx": payload.get("frame_idx"),
            })
        
        search_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[IMAGE_SEARCH] Found {len(results)} similar images in {search_time_ms:.2f}ms")
        
        return ImageSearchResponse(
            results=results,
            total=len(results),
            query_image=file.filename,
            method="clip-image",
            search_time_ms=search_time_ms
        )
        
    except httpx.HTTPError as e:
        logger.error(f"[IMAGE_SEARCH] Model server error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image embedding: {str(e)}")
    except Exception as e:
        logger.error(f"[IMAGE_SEARCH] Error during search: {e}")
        raise HTTPException(status_code=500, detail=f"Image search failed: {str(e)}")
