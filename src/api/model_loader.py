"""
Model Loader — Singleton utility
Loads trained models and data once at startup and exposes them globally.

Note: ContentBasedRecommender is rebuilt from raw data at startup (not loaded from pkl)
because the similarity matrix is ~728MB on disk. Rebuilding takes ~3s and uses ~300MB RAM.
"""

import logging
import joblib
import pandas as pd
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

MODELS_DIR    = PROJECT_ROOT / "models"
RAW_DATA_DIR  = PROJECT_ROOT / "data" / "raw" / "ml-latest"
PROC_DATA_DIR = PROJECT_ROOT / "data" / "processed"


class ModelStore:
    """Holds all loaded models and data as attributes."""

    def __init__(self):
        self.cb_model      = None
        self.cf_model      = None
        self.hybrid_model  = None
        self.movies_df     = None
        self.ratings_df    = None
        self.tags_df       = None
        self.rating_stats  = None   # pre-aggregated per-movie rating stats
        self.genres_list   = None   # list of unique genres
        self.genre_matrix  = None   # binary matrix of genres [n_movies, n_genres]
        self.is_loaded     = False

    def load(self):
        """Load everything. Called once at startup."""
        if self.is_loaded:
            return

        logger.info("🔄 Loading data and models...")

        # ── Data ──────────────────────────────────────────────────────────
        try:
            self.movies_df  = pd.read_csv(RAW_DATA_DIR / "movies.csv")
            self.ratings_df = pd.read_csv(RAW_DATA_DIR / "ratings.csv")
            tags_path = RAW_DATA_DIR / "tags.csv"
            self.tags_df = pd.read_csv(tags_path) if tags_path.exists() else None

            # Merge TMDB IDs so we can fetch posters later
            links_path = RAW_DATA_DIR / "links.csv"
            if links_path.exists():
                links_df = pd.read_csv(links_path)
                self.movies_df = self.movies_df.merge(
                    links_df[["movieId", "tmdbId"]], on="movieId", how="left"
                )
                logger.info(f"✅ Merged tmdbId for poster lookups")

            logger.info(f"✅ Loaded {len(self.movies_df):,} movies, {len(self.ratings_df):,} ratings")

            # ── Precompute Genre Matrix ──────────────────────────────────────
            logger.info("🔄 Precomputing genre matrix...")
            # 1. Get unique genres in a stable order
            all_genres = set()
            for g in self.movies_df["genres"].dropna():
                all_genres.update(g.split("|"))
            all_genres.discard("(no genres listed)")
            self.genres_list = sorted(all_genres)
            logger.info(f"✅ Found {len(self.genres_list)} unique genres")

            # 2. Build binary mapping (n_movies, n_genres)
            # This is much faster for dot-product scoring than string operations per request
            import numpy as np
            genre_to_idx = {g: i for i, g in enumerate(self.genres_list)}
            self.genre_matrix = np.zeros((len(self.movies_df), len(self.genres_list)), dtype=np.float32)

            for i, genres_str in enumerate(self.movies_df["genres"]):
                if pd.isna(genres_str):
                    continue
                for g in genres_str.split("|"):
                    if g in genre_to_idx:
                        self.genre_matrix[i, genre_to_idx[g]] = 1.0

            logger.info("✅ Genre matrix ready")

            # Pre-aggregate per-movie rating stats so endpoints don't groupby on every request
            logger.info("🔄 Pre-aggregating rating stats...")
            self.rating_stats = self.ratings_df.groupby("movieId").agg(
                avg_rating=("rating", "mean"),
                num_ratings=("rating", "count"),
            ).reset_index()
            self.rating_stats["avg_rating"] = self.rating_stats["avg_rating"].round(2)
            logger.info(f"✅ Rating stats ready ({len(self.rating_stats):,} movies with ratings)")

        except FileNotFoundError as e:
            raise RuntimeError(f"Data files not found: {e}. Run ingestion first.")

        # ── Collaborative Filtering (small pkl, fast to load) ─────────────
        cf_path = MODELS_DIR / "collaborative_model.pkl"
        if cf_path.exists():
            self.cf_model = joblib.load(cf_path)
            logger.info("✅ Loaded collaborative_model.pkl")
        else:
            logger.warning("⚠️  collaborative_model.pkl not found — run train_models.py first")

        # ── Content-Based (rebuild from data — faster than loading 728MB pkl) ──
        logger.info("🔄 Building Content-Based model from data...")
        try:
            try:
                from src.models.content_based import ContentBasedRecommender
            except ImportError:
                from models.content_based import ContentBasedRecommender

            self.cb_model = ContentBasedRecommender()
            self.cb_model.fit(self.movies_df, tags_df=self.tags_df)
            logger.info("✅ Content-Based model ready")
        except Exception as e:
            logger.error(f"⚠️  Content-Based model failed to build: {e}")
            self.cb_model = None

        # ── Hybrid (wraps CB + CF, rebuild instead of loading 744MB pkl) ──
        if self.cb_model and self.cf_model:
            try:
                from src.models.hybrid import HybridRecommender
            except ImportError:
                from models.hybrid import HybridRecommender

            self.hybrid_model = HybridRecommender(self.cb_model, self.cf_model)
            self.hybrid_model.fit(self.ratings_df)
            logger.info("✅ Hybrid model ready")
        else:
            logger.warning("⚠️  Hybrid model skipped (CB or CF not available)")

        self.is_loaded = True
        logger.info("✅ All models ready.")


# Global singleton — imported by routers
store = ModelStore()
