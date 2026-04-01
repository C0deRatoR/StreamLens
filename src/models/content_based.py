"""
Content-Based Recommender System
Uses TF-IDF Vectorization on movie genres and tags to find similar movies.

Similarity is computed **on-demand** (one row at a time) rather than
precomputing the full N×N matrix — this keeps memory usage practical even
for datasets with 80k+ movies.
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

class ContentBasedRecommender:
    def __init__(self):
        self.tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None          # sparse TF-IDF matrix (stored)
        self.similarity_matrix = None     # kept for tiny datasets / tests
        self.movies_df = None
        self.indices = None
        self._n_movies = 0

    def fit(self, movies_df, tags_df=None):
        """
        Fit the model by building the TF-IDF matrix.

        For small datasets (< 15 000 movies) the full cosine-similarity
        matrix is still precomputed for speed.  For larger datasets only
        the sparse TF-IDF matrix is stored and similarities are computed
        per-query to avoid huge memory allocation.
        """
        self.movies_df = movies_df.copy()

        # 1. Genres (replace pipe with space)
        self.movies_df['genres_str'] = self.movies_df['genres'].str.replace('|', ' ', regex=False)

        # 2. Tags (if provided)
        if tags_df is not None:
            movie_tags = tags_df.groupby('movieId')['tag'].apply(
                lambda x: ' '.join(x.dropna().astype(str))
            ).reset_index()
            self.movies_df = self.movies_df.merge(movie_tags, on='movieId', how='left')
            self.movies_df['tag'] = self.movies_df['tag'].fillna('')
            self.movies_df['content'] = self.movies_df['genres_str'] + ' ' + self.movies_df['tag']
        else:
            self.movies_df['content'] = self.movies_df['genres_str']

        print("Constructing TF-IDF matrix...")
        self.tfidf_matrix = self.tfidf.fit_transform(self.movies_df['content'])
        self._n_movies = self.tfidf_matrix.shape[0]
        print(f"TF-IDF Matrix Shape: {self.tfidf_matrix.shape}")

        # Only precompute the dense similarity matrix for small datasets
        if self._n_movies < 15_000:
            print("Calculating cosine similarity (small dataset — precomputing)...")
            self.similarity_matrix = linear_kernel(self.tfidf_matrix, self.tfidf_matrix)
        else:
            print(f"ℹ️  Large dataset ({self._n_movies:,} movies) — similarity computed on-demand")
            self.similarity_matrix = None  # will use get_similarities() instead

        # Reverse map: title → row index
        self.indices = pd.Series(
            self.movies_df.index, index=self.movies_df['title']
        ).drop_duplicates()

        print("✅ Content-Based Model trained successfully")

    # ── On-demand similarity ──────────────────────────────────────────────

    def get_similarities(self, idx):
        """Return a 1-D array of cosine similarities between movie at *idx*
        and every other movie.  Uses the precomputed matrix when available,
        otherwise computes a single row on the fly (fast & low-memory)."""
        if self.similarity_matrix is not None:
            return self.similarity_matrix[idx]
        # Compute one row: (1 × D) @ (D × N) → (1 × N)
        row = linear_kernel(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        return row

    @property
    def is_fitted(self):
        """True when the model has been fitted (TF-IDF matrix available)."""
        return self.tfidf_matrix is not None

    # ── Recommend ──────────────────────────────────────────────────────────

    def recommend(self, movie_title=None, movie_id=None, top_k=10):
        """
        Get recommendations based on a movie.

        Args:
            movie_title: Title of the movie to find similarities for
            movie_id:    ID of the movie (alternative to title)
            top_k:       Number of recommendations to return

        Returns:
            DataFrame with recommended movies and similarity scores
        """
        if not self.is_fitted:
            raise ValueError("Model has not been fitted yet. Call fit() first.")

        idx = None

        if movie_title:
            if movie_title not in self.indices:
                raise ValueError(f"Movie '{movie_title}' not found in dataset")
            idx = self.indices[movie_title]
        elif movie_id:
            movie_matches = self.movies_df[self.movies_df['movieId'] == movie_id].index
            if len(movie_matches) == 0:
                raise ValueError(f"Movie ID {movie_id} not found in dataset")
            idx = movie_matches[0]
        else:
            raise ValueError("Either movie_title or movie_id must be provided")

        # On-demand similarity for this one movie
        sims = self.get_similarities(idx)
        sim_scores = list(enumerate(sims))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:top_k+1]

        movie_indices = [i[0] for i in sim_scores]

        result = self.movies_df.iloc[movie_indices][['movieId', 'title', 'genres']].copy()
        result['similarity_score'] = [i[1] for i in sim_scores]
        return result


if __name__ == "__main__":
    print("Testing ContentBasedRecommender...")

    movies_data = {
        'movieId': [1, 2, 3, 4, 5],
        'title': ['Toy Story', 'Jumanji', 'Grumpier Old Men', 'Waiting to Exhale', 'Father of the Bride Part II'],
        'genres': ['Adventure|Animation|Children|Comedy|Fantasy', 'Adventure|Children|Fantasy', 'Comedy|Romance', 'Comedy|Drama|Romance', 'Comedy']
    }
    movies_df = pd.DataFrame(movies_data)

    recommender = ContentBasedRecommender()
    recommender.fit(movies_df)

    print("\nRecommendations for 'Toy Story':")
    print(recommender.recommend(movie_title='Toy Story', top_k=3))
