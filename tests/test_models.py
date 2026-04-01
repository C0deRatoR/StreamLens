"""
Unit tests for StreamLens recommender models.
Validates core functionality and regression checks for bug fixes.
"""

import pandas as pd
import numpy as np
import pytest
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.content_based import ContentBasedRecommender
from src.models.collaborative_filtering import CollaborativeRecommender
from src.models.hybrid import HybridRecommender


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def movies_df():
    return pd.DataFrame({
        'movieId': [1, 2, 3, 4, 5],
        'title': ['Toy Story', 'Jumanji', 'Grumpier Old Men', 'Waiting to Exhale', 'Father of the Bride Part II'],
        'genres': ['Adventure|Animation|Children|Comedy|Fantasy',
                   'Adventure|Children|Fantasy',
                   'Comedy|Romance',
                   'Comedy|Drama|Romance',
                   'Comedy'],
    })


@pytest.fixture
def ratings_df():
    return pd.DataFrame({
        'userId':  [1, 1, 1, 2, 2, 2, 3, 3],
        'movieId': [1, 2, 3, 1, 2, 4, 3, 5],
        'rating':  [5.0, 4.0, 3.0, 5.0, 5.0, 2.0, 4.0, 3.5],
    })


@pytest.fixture
def tags_df():
    return pd.DataFrame({
        'userId':  [1, 1, 2],
        'movieId': [1, 2, 1],
        'tag':     ['fun', 'adventure', 'pixar'],
    })


@pytest.fixture
def cb_model(movies_df, tags_df):
    model = ContentBasedRecommender()
    model.fit(movies_df, tags_df=tags_df)
    return model


@pytest.fixture
def cf_model(ratings_df):
    model = CollaborativeRecommender(method='svd', n_factors=5)
    model.fit(ratings_df)
    return model


# ── Content-Based Tests ───────────────────────────────────────────────────

class TestContentBasedRecommender:
    def test_fit_creates_similarity_matrix(self, cb_model):
        assert cb_model.similarity_matrix is not None
        assert cb_model.similarity_matrix.shape == (5, 5)

    def test_recommend_by_title(self, cb_model):
        recs = cb_model.recommend(movie_title='Toy Story', top_k=3)
        assert isinstance(recs, pd.DataFrame)
        assert len(recs) == 3
        assert 'similarity_score' in recs.columns
        assert 'movieId' in recs.columns
        assert 'title' in recs.columns

    def test_recommend_by_id(self, cb_model):
        recs = cb_model.recommend(movie_id=1, top_k=2)
        assert isinstance(recs, pd.DataFrame)
        assert len(recs) == 2

    def test_recommend_unknown_title_raises(self, cb_model):
        with pytest.raises(ValueError, match="not found"):
            cb_model.recommend(movie_title='Nonexistent Movie')

    def test_recommend_unknown_id_raises(self, cb_model):
        with pytest.raises(ValueError, match="not found"):
            cb_model.recommend(movie_id=9999)

    def test_genres_pipe_replaced_literally(self, cb_model):
        """Regression: B1 — pipe should be replaced literally, not as regex OR."""
        genres_str = cb_model.movies_df['genres_str'].iloc[0]
        assert '|' not in genres_str
        # Should have actual genre words, not single chars (which regex OR would produce)
        assert 'Adventure' in genres_str


# ── Collaborative Filtering Tests ─────────────────────────────────────────

class TestCollaborativeRecommender:
    def test_fit_creates_matrix(self, cf_model):
        assert cf_model.user_item_matrix is not None
        assert cf_model.user_item_matrix.shape == (3, 5)  # 3 users, 5 movies

    def test_recommend_returns_dataframe(self, cf_model):
        recs = cf_model.recommend(user_id=1, top_k=2)
        assert isinstance(recs, pd.DataFrame)
        assert 'movieId' in recs.columns
        assert 'score' in recs.columns

    def test_cold_start_returns_empty_dataframe(self, cf_model):
        """Regression: B3 — cold-start should return empty DataFrame, not list."""
        recs = cf_model.recommend(user_id=9999, top_k=5)
        assert isinstance(recs, pd.DataFrame)
        assert recs.empty
        assert 'movieId' in recs.columns


# ── Hybrid Tests ──────────────────────────────────────────────────────────

class TestHybridRecommender:
    def test_recommend_includes_genres(self, cb_model, cf_model, ratings_df):
        """Regression: B4 — hybrid output must include genres column."""
        hybrid = HybridRecommender(cb_model, cf_model)
        hybrid.fit(ratings_df)
        recs = hybrid.recommend(user_id=1, top_k=3)
        assert isinstance(recs, pd.DataFrame)
        if not recs.empty:
            assert 'genres' in recs.columns
            assert 'title' in recs.columns

    def test_recommend_returns_dataframe_for_unknown_user(self, cb_model, cf_model, ratings_df):
        """Hybrid should handle cold-start gracefully."""
        hybrid = HybridRecommender(cb_model, cf_model)
        hybrid.fit(ratings_df)
        recs = hybrid.recommend(user_id=9999, top_k=3)
        assert isinstance(recs, pd.DataFrame)
