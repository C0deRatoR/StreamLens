"""
StreamLens FastAPI Application
Main entry point — loads models on startup and mounts all routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os
from pathlib import Path

# Load .env file so TMDB_API_KEY and other secrets are available
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.api.model_loader import store
from src.api.routers import recommendations, movies


# ── Lifespan: load models once at startup ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()
    yield
    # (cleanup on shutdown if needed)


# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="StreamLens Recommender API",
    description=(
        "Context-aware movie recommendation system powered by "
        "Content-Based Filtering, Collaborative Filtering, and a Hybrid model."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for local development (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(recommendations.router)
app.include_router(movies.router)


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "StreamLens Recommender API",
        "status": "running",
        "models_loaded": store.is_loaded,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "models": {
            "content_based":   store.cb_model is not None,
            "collaborative":   store.cf_model is not None,
            "hybrid":          store.hybrid_model is not None,
        },
        "data": {
            "movies":  store.movies_df is not None,
            "ratings": store.ratings_df is not None,
        },
    }
