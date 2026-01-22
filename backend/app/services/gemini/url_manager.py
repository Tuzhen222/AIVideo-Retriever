"""
URL Manager for load balancing between multiple embedding server URLs.
Similar to APIKeyManager but for server URLs.
"""
import threading
from typing import List, Optional


class URLManager:
    """Thread-safe URL rotation manager"""
    
    def __init__(self, urls: List[str]):
        """
        Initialize with list of URLs.
        
        Args:
            urls: List of server URLs (comma-separated string will be parsed)
        """
        if isinstance(urls, str):
            # Parse comma-separated string
            self.urls = [url.strip() for url in urls.split(",") if url.strip()]
        else:
            self.urls = urls if isinstance(urls, list) else []
        
        if not self.urls:
            raise ValueError("At least one URL must be provided")
        
        self._index = 0
        self._lock = threading.Lock()
    
    def get_next_url(self) -> str:
        """
        Get next URL in round-robin fashion.
        Thread-safe.
        
        Returns:
            Next URL
        """
        with self._lock:
            url = self.urls[self._index]
            self._index = (self._index + 1) % len(self.urls)
            return url
    
    def get_all_urls(self) -> List[str]:
        """Get all available URLs"""
        return self.urls.copy()
    
    def __len__(self):
        """Number of URLs"""
        return len(self.urls)
