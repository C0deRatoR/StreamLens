"""
Recommendations Router
Endpoints for getting movie recommendations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from src.api.model_loader import store
from src.api.tmdb import poster_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# ── Context → Genre boost mapping ─────────────────────────────────────────

CONTEXT_GENRE_BOOSTS: Dict[str, Dict[str, List[str]]] = {
    "time_of_day": {
        "morning":    ["Animation", "Comedy", "Children", "Musical", "Fantasy"],
        "afternoon":  ["Adventure", "Action", "Documentary", "Sci-Fi"],
        "evening":    ["Drama", "Thriller", "Romance", "Mystery", "Crime"],
        "late_night": ["Horror", "Thriller", "Sci-Fi", "Crime", "Film-Noir"],
    },
    "social": {
        "alone":   ["Drama", "Documentary", "Thriller", "Horror", "Mystery"],
        "friends": ["Comedy", "Action", "Adventure", "Sci-Fi", "Fantasy"],
        "date":    ["Romance", "Comedy", "Drama", "Musical"],
        "family":  ["Animation", "Comedy", "Adventure", "Children", "Fantasy"],
    },
    "mood": {
        "adventurous": ["Adventure", "Action", "Sci-Fi", "Fantasy", "Western"],
        "relaxed":     ["Comedy", "Animation", "Musical", "Romance"],
        "intense":     ["Thriller", "Horror", "Crime", "Mystery", "War"],
        "thoughtful":  ["Drama", "Documentary", "Film-Noir", "War"],
    },
}


# ── Pydantic models ───────────────────────────────────────────────────────

class ContextInfo(BaseModel):
    time_of_day: Optional[str] = None
    social: Optional[str] = None
    mood: Optional[str] = None

class RatedMovie(BaseModel):
    movieId: int
    rating: float = Field(ge=0.5, le=5.0)

class PersonalizedRequest(BaseModel):
    preferred_genres: List[str] = []
    age_group: Optional[str] = None
    context: Optional[ContextInfo] = None
    rated_movies: List[RatedMovie] = []
    top_k: int = Field(12, ge=1, le=50)


def _format_movie_list(df: pd.DataFrame, score_col: str = None) -> List[dict]:
    """Convert a recommendations DataFrame to a clean list of dicts."""
    if df is None or df.empty:
        return []
    result = []
    tmdb_ids = []
    for _, row in df.iterrows():
        item = {
            "movieId": int(row["movieId"]),
            "title":   str(row["title"]) if "title" in row.index else "Unknown",
            "genres":  str(row["genres"]) if "genres" in row.index else "",
        }
        if score_col and score_col in row.index:
            item["score"] = round(float(row[score_col]), 4)
        # Include rating stats when available
        if "avg_rating" in row.index and row["avg_rating"]:
            item["avg_rating"] = round(float(row["avg_rating"]), 2)
        if "num_ratings" in row.index and row["num_ratings"]:
            item["num_ratings"] = int(row["num_ratings"])
        # TMDB ID for poster lookup
        tmdb_id = row.get("tmdbId")
        if tmdb_id and pd.notna(tmdb_id):
            item["tmdbId"] = int(tmdb_id)
            tmdb_ids.append(tmdb_id)
        result.append(item)

    # Batch-fetch poster URLs
    if tmdb_ids and poster_service.is_available:
        posters = poster_service.get_poster_urls_batch(tmdb_ids)
        for item in result:
            tid = item.get("tmdbId")
            if tid:
                item["poster_url"] = posters.get(str(tid))

    return result


@router.get("/user/{user_id}", summary="Hybrid recommendations for a user")
def recommend_for_user(
    user_id: int,
    top_k: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    mode: str = Query("hybrid", enum=["hybrid", "cf", "cb"], description="Recommendation mode"),
):
    """
    Get personalised movie recommendations for a given user ID.
    - **hybrid**: Weighted combination of CF + Content-Based (default)
    - **cf**: Collaborative Filtering only
    - **cb**: Content-Based only (uses user's top-rated movie as seed)
    """
    if not store.is_loaded:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")

    try:
        if mode == "hybrid":
            if store.hybrid_model is None:
                raise HTTPException(status_code=503, detail="Hybrid model not available.")
            recs = store.hybrid_model.recommend(user_id, top_k=top_k)
            return {"user_id": user_id, "mode": mode, "recommendations": _format_movie_list(recs, "hybrid_score")}

        elif mode == "cf":
            if store.cf_model is None:
                raise HTTPException(status_code=503, detail="CF model not available.")
            recs = store.cf_model.recommend(user_id, top_k=top_k)
            return {"user_id": user_id, "mode": mode, "recommendations": _format_movie_list(recs, "score")}

        elif mode == "cb":
            if store.cb_model is None:
                raise HTTPException(status_code=503, detail="CB model not available.")
            if store.ratings_df is None:
                raise HTTPException(status_code=503, detail="Ratings data not loaded.")
            user_history = store.ratings_df[store.ratings_df["userId"] == user_id]
            if user_history.empty:
                raise HTTPException(status_code=404, detail=f"No history found for user {user_id}.")
            fav_movie_id = user_history.sort_values("rating", ascending=False).iloc[0]["movieId"]
            recs = store.cb_model.recommend(movie_id=int(fav_movie_id), top_k=top_k)
            return {"user_id": user_id, "mode": mode, "seed_movie_id": int(fav_movie_id), "recommendations": _format_movie_list(recs, "similarity_score")}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movie/{movie_id}", summary="Content-based similar movies")
def recommend_similar_movies(
    movie_id: int,
    top_k: int = Query(10, ge=1, le=50),
):
    """Get movies similar to a given movie using Content-Based Filtering."""
    if not store.is_loaded:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")
    if store.cb_model is None:
        raise HTTPException(status_code=503, detail="Content-Based model not available.")

    try:
        recs = store.cb_model.recommend(movie_id=movie_id, top_k=top_k)
        return {"movie_id": movie_id, "recommendations": _format_movie_list(recs, "similarity_score")}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top", summary="Top popular movies")
def top_movies(
    top_k: int = Query(20, ge=1, le=100),
    min_ratings: int = Query(50, ge=1, description="Minimum number of ratings"),
    sort_by: str = Query("popularity", enum=["popularity", "rating"]),
):
    """
    Get the most popular or highest-rated movies.
    - **popularity**: sorted by number of ratings
    - **rating**: sorted by average rating (with min_ratings filter)
    """
    if store.ratings_df is None or store.movies_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded.")

    if store.rating_stats is None:
        raise HTTPException(status_code=503, detail="Rating data not loaded.")

    stats = store.rating_stats[store.rating_stats["num_ratings"] >= min_ratings].copy()
    cols = ["movieId", "title", "genres"]
    if "tmdbId" in store.movies_df.columns:
        cols.append("tmdbId")
    stats = stats.merge(store.movies_df[cols], on="movieId", how="left")

    if sort_by == "popularity":
        stats = stats.sort_values("num_ratings", ascending=False)
    else:
        stats = stats.sort_values("avg_rating", ascending=False)

    top = stats.head(top_k)
    result = []
    for _, row in top.iterrows():
        result.append({
            "movieId":     int(row["movieId"]),
            "title":       str(row["title"]),
            "genres":      str(row["genres"]),
            "num_ratings": int(row["num_ratings"]),
            "avg_rating":  round(float(row["avg_rating"]), 2),
        })
    return {"sort_by": sort_by, "movies": result}


# ── Personalised (profile + context + ratings) ───────────────────────────

@router.post("/personalized", summary="Context-aware personalised recommendations")
def personalized_recommendations(req: PersonalizedRequest):
    """
    Generate recommendations based on a user profile, viewing context, and
    any movies the user has already rated — *no pre-existing userId required*.
    """
    if not store.is_loaded:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")

    movies_df = store.movies_df
    if movies_df is None:
        raise HTTPException(status_code=503, detail="Movie data not loaded.")

    # 1. Build genre affinity weights
    if store.genres_list is None or store.genre_matrix is None:
        raise HTTPException(status_code=503, detail="Genre data not precomputed.")

    # Vector of weights [n_genres]
    genre_weights = np.zeros(len(store.genres_list), dtype=np.float32)
    genre_to_idx = {g: i for i, g in enumerate(store.genres_list)}

    # Base boost from preferred genres
    for g in req.preferred_genres:
        if g in genre_to_idx:
            genre_weights[genre_to_idx[g]] += 3.0

    # Context boosts
    if req.context:
        for dimension, value in [
            ("time_of_day", req.context.time_of_day),
            ("social", req.context.social),
            ("mood", req.context.mood),
        ]:
            if value and dimension in CONTEXT_GENRE_BOOSTS:
                boosted = CONTEXT_GENRE_BOOSTS[dimension].get(value, [])
                for g in boosted:
                    if g in genre_to_idx:
                        genre_weights[genre_to_idx[g]] += 1.5

    # 2. Score every movie by genre affinity via dot product
    # (n_movies x n_genres) @ (n_genres x 1) -> (n_movies x 1)
    genre_scores = store.genre_matrix @ genre_weights

    # Average the score by number of genres per movie to match original logic
    # Precompute this in model_loader would be even better, but let's do it here for now
    genres_per_movie = store.genre_matrix.sum(axis=1)
    genres_per_movie[genres_per_movie == 0] = 1.0 # avoid div by zero
    genre_scores = genre_scores / genres_per_movie

    cols = ["movieId", "title", "genres"]
    if "tmdbId" in movies_df.columns:
        cols.append("tmdbId")
    scored = movies_df[cols].copy()
    scored["genre_score"] = genre_scores

    # 2b. Rating boost from global average ratings
    if store.rating_stats is not None:
        rating_stats = store.rating_stats.copy()
        # Filter out movies with very few ratings to avoid noise
        rating_stats = rating_stats[rating_stats["num_ratings"] >= 5]
        # Normalise avg_rating to [0, 1]
        r_min = rating_stats["avg_rating"].min()
        r_max = rating_stats["avg_rating"].max()
        if r_max > r_min:
            rating_stats["rating_norm"] = (rating_stats["avg_rating"] - r_min) / (r_max - r_min)
        else:
            rating_stats["rating_norm"] = 1.0
        # Scale to match genre_score range with a tuneable weight
        max_gs = scored["genre_score"].max()
        rating_weight = 0.4
        rating_stats["rating_boost"] = rating_stats["rating_norm"] * max_gs * rating_weight
        scored = scored.merge(
            rating_stats[["movieId", "avg_rating", "num_ratings", "rating_boost"]],
            on="movieId", how="left",
        )
        scored["rating_boost"] = scored["rating_boost"].fillna(0.0)
        scored["avg_rating"]  = scored["avg_rating"].fillna(0.0)
        scored["num_ratings"] = scored["num_ratings"].fillna(0).astype(int)
    else:
        scored["rating_boost"] = 0.0
        scored["avg_rating"]  = 0.0
        scored["num_ratings"] = 0

    rated_ids = {r.movieId: r.rating for r in req.rated_movies}
    cb_boost = np.zeros(len(movies_df), dtype=np.float32)

    if rated_ids and store.cb_model is not None and store.cb_model.is_fitted:
        # Get indices of rated movies
        # We can optimize this by pre-mapping movieId to index in store
        for mid, rating in rated_ids.items():
            matches = movies_df[movies_df["movieId"] == mid].index
            if len(matches) == 0:
                continue
            idx = matches[0]
            sims = store.cb_model.get_similarities(idx)
            # Weight by user rating normalised to [0,1]
            weight = rating / 5.0
            cb_boost += sims.astype(np.float32) * weight

        # Normalise cb_boost to [0, max_genre_score]
        max_gs = scored["genre_score"].max()
        max_cb = cb_boost.max()
        if max_cb > 0 and max_gs > 0:
            cb_boost = cb_boost / max_cb * max_gs

    scored["cb_boost"] = cb_boost

    # 4. Combined score (genre affinity + CB similarity + global rating boost)
    scored["score"] = scored["genre_score"] + scored["cb_boost"] + scored["rating_boost"]

    # Remove already-rated movies from results
    scored = scored[~scored["movieId"].isin(rated_ids.keys())]

    # Sort and pick top_k
    top = scored.sort_values("score", ascending=False).head(req.top_k)

    # Normalise final score to [0, 1]
    max_score = top["score"].max()
    if max_score > 0:
        top = top.copy()
        top["score"] = top["score"] / max_score

    return {
        "context": req.context.model_dump() if req.context else None,
        "recommendations": _format_movie_list(top, "score"),
    }

