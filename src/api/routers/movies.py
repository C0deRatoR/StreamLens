"""
Movies Router
Endpoints for browsing and searching movies.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from src.api.model_loader import store
from src.api.tmdb import poster_service

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/genres", summary="List all unique genres")
def list_genres():
    """Return a sorted list of every unique genre in the catalogue."""
    if store.movies_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded.")

    all_genres = set()
    for g in store.movies_df["genres"].dropna():
        for genre in g.split("|"):
            genre = genre.strip()
            if genre and genre != "(no genres listed)":
                all_genres.add(genre)

    return {"genres": sorted(all_genres)}


@router.get("/search", summary="Search movies by title")
def search_movies(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search for movies by partial title match (case-insensitive)."""
    if store.movies_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded.")

    mask = store.movies_df["title"].str.contains(q, case=False, na=False, regex=False)
    results = store.movies_df[mask].head(limit)

    cols = ["movieId", "title", "genres"]
    if "tmdbId" in results.columns:
        cols.append("tmdbId")
    movies_list = results[cols].to_dict(orient="records")

    # Split genres into arrays
    for m in movies_list:
        g = m.get("genres", "")
        m["genres"] = [x.strip() for x in str(g).split("|") if x.strip() and x.strip() != "(no genres listed)"]

    # Fetch poster URLs
    if poster_service.is_available:
        tmdb_ids = [m["tmdbId"] for m in movies_list if m.get("tmdbId") and str(m["tmdbId"]) != 'nan']
        if tmdb_ids:
            title_map = {str(int(m["tmdbId"])): m.get("title", "") for m in movies_list if m.get("tmdbId") and str(m["tmdbId"]) != 'nan'}
            posters = poster_service.get_poster_urls_batch(tmdb_ids, titles=title_map)
            for m in movies_list:
                tid = m.get("tmdbId")
                if tid and str(tid) != 'nan':
                    m["tmdbId"] = int(tid)
                    m["poster_url"] = posters.get(str(int(tid)))

    return {
        "query": q,
        "count": len(results),
        "movies": movies_list,
    }


@router.get("/{movie_id}", summary="Get movie details")
def get_movie(movie_id: int):
    """Get details for a specific movie by ID."""
    if store.movies_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded.")

    row = store.movies_df[store.movies_df["movieId"] == movie_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found.")

    movie = row.iloc[0]

    # Compute rating stats if ratings are loaded
    stats = {}
    if store.ratings_df is not None:
        movie_ratings = store.ratings_df[store.ratings_df["movieId"] == movie_id]["rating"]
        if not movie_ratings.empty:
            stats = {
                "num_ratings": int(len(movie_ratings)),
                "avg_rating":  round(float(movie_ratings.mean()), 2),
                "min_rating":  float(movie_ratings.min()),
                "max_rating":  float(movie_ratings.max()),
            }

    result = {
        "movieId": int(movie["movieId"]),
        "title":   str(movie["title"]),
        "genres":  [g.strip() for g in str(movie["genres"]).split("|") if g.strip() and g.strip() != "(no genres listed)"],
        **stats,
    }

    # Poster URL
    tmdb_id = movie.get("tmdbId")
    if tmdb_id and str(tmdb_id) != 'nan':
        result["tmdbId"] = int(tmdb_id)
        if poster_service.is_available:
            result["poster_url"] = poster_service.get_poster_url(int(tmdb_id), title=str(movie["title"]))

    return result
