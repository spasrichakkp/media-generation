"""
URL Scraper - Fetch and parse content from URLs
"""

import logging
from typing import Dict, Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class UrlScraper:
    """Scraper for fetching and parsing URL content."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "MediaGenerationBot/1.0 (Internal RAG System)"
        }

    async def scrape(self, url: str) -> Optional[Dict]:
        """
        Fetch and parse content from a URL.

        Args:
            url: The URL to scrape

        Returns:
            Dictionary containing content and metadata, or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator="\n")
                
                # Clean text (remove excessive whitespace)
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = "\n".join(chunk for chunk in chunks if chunk)
                
                title = soup.title.string if soup.title else url
                
                return {
                    "content": clean_text,
                    "type": "url",
                    "metadata": {
                        "source": url,
                        "title": title,
                        "content_type": response.headers.get("content-type", "text/html")
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None
