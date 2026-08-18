"""RAG Service Adapter."""

import logging
from typing import Dict, Optional, Any
import httpx

from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class RagServiceAdapter:
    """Adapter for communicating with the RAG Service."""
    
    def __init__(self, base_url: str = "http://rag-service:8001"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }
        
    async def ingest_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Ingest content from a URL via the RAG service.
        
        Args:
            url: The URL to ingest
            
        Returns:
            Dictionary containing document_id, title, summary, etc.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/url",
                    json={"url": url, "generate_summary": True},
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"RAG Service error: {response.text}")
                    return None
                    
                return response.json()
                
        except Exception as e:
            logger.error(f"Failed to call RAG service: {e}")
            return None

    async def check_health(self) -> bool:
        """Check if RAG service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/stats")
                return response.status_code == 200
        except Exception:
            return False
