"""
TMDB Poster Service
Fetches movie poster URLs from The Movie Database (TMDB) API with a local
JSON cache to minimise API calls.

Usage:
    poster = TMDBPosterService()
    url = poster.get_poster_url(tmdb_id=862)  # e.g. Toy Story
"""

import os
import json
import logging
import requests
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"  # 342px wide posters
TMDB_API_BASE = "https://api.themoviedb.org/3"

PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_FILE = PROJECT_ROOT / "data" / "processed" / "poster_cache.json"


class TMDBPosterService:
    """Fetches and caches TMDB poster URLs."""

    def __init__(self):
        self.api_key = os.environ.get("TMDB_API_KEY", "")
        self._cache: Dict[str, Optional[str]] = {}
        self._load_cache()

    def _load_cache(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self._cache = json.load(f)
                logger.info(f"📷 Loaded {len(self._cache):,} cached poster URLs")
            except (json.JSONDecodeError, IOError):
                self._cache = {}

    def _save_cache(self):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f)
        except IOError:
            pass

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_poster_url(self, tmdb_id, title: str = None) -> Optional[str]:
        """Get a poster URL for a TMDB movie ID.  Returns None on failure.
        If direct ID lookup fails and title is provided, falls back to search."""
        if not tmdb_id or not self.api_key:
            return None

        key = str(int(tmdb_id))

        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Fetch from TMDB API by ID
        try:
            resp = requests.get(
                f"{TMDB_API_BASE}/movie/{key}",
                params={"api_key": self.api_key},
                timeout=3,
            )
            if resp.status_code == 200:
                data = resp.json()
                poster_path = data.get("poster_path")
                url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None
                if url:
                    self._cache[key] = url
                    if len(self._cache) % 50 == 0:
                        self._save_cache()
                    return url
        except Exception:
            pass

        # Fallback: search by title if ID lookup failed
        if title:
            url = self._search_poster_by_title(title)
            if url:
                self._cache[key] = url
                return url

        # Don't cache None — allow future retries
        return None

    def _search_poster_by_title(self, title: str) -> Optional[str]:
        """Search TMDB by movie title and return the first poster URL found."""
        try:
            # Strip year from title like "Planet Earth (2006)"
            import re
            clean = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            # Also handle "Movie, The" -> "The Movie"
            if ', The' in clean:
                clean = 'The ' + clean.replace(', The', '')

            resp = requests.get(
                f"{TMDB_API_BASE}/search/movie",
                params={"api_key": self.api_key, "query": clean},
                timeout=3,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results[:3]:
                    poster_path = r.get("poster_path")
                    if poster_path:
                        return f"{TMDB_IMAGE_BASE}{poster_path}"
        except Exception:
            pass
        return None

    def get_poster_urls_batch(self, tmdb_ids: list, titles: Dict[str, str] = None) -> Dict[str, Optional[str]]:
        """Get poster URLs for multiple TMDB IDs.  Cached IDs are returned
        immediately; uncached ones are fetched (sequentially).
        titles: optional mapping of str(tmdb_id) -> movie title for search fallback."""
        results = {}
        to_fetch = []

        for tid in tmdb_ids:
            if tid is None or (isinstance(tid, float) and str(tid) == 'nan'):
                continue
            key = str(int(tid))
            if key in self._cache:
                results[key] = self._cache[key]
            else:
                to_fetch.append(key)

        # Fetch uncached (limit to avoid slowing API responses)
        titles = titles or {}
        for key in to_fetch[:30]:
            title = titles.get(key)
            url = self.get_poster_url(int(key), title=title)
            results[key] = url

        # Save after a batch
        if to_fetch:
            self._save_cache()

        return results


# Global singleton
poster_service = TMDBPosterService()
