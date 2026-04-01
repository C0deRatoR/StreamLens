"""
Model Evaluation Module
Evaluates recommender models using standard metrics:
  - RMSE, MAE (rating prediction accuracy)
  - Precision@K, Recall@K, NDCG@K (ranking quality)
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from src.models.content_based import ContentBasedRecommender
    from src.models.collaborative_filtering import CollaborativeRecommender
    from src.models.hybrid import HybridRecommender
except ImportError:
    from content_based import ContentBasedRecommender
    from collaborative_filtering import CollaborativeRecommender
    from hybrid import HybridRecommender


# ─────────────────────────────────────────────
# Metric Functions
# ─────────────────────────────────────────────

def rmse(y_true, y_pred):
    """Root Mean Squared Error"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred):
    """Mean Absolute Error"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return float(np.mean(np.abs(y_true - y_pred)))


def precision_at_k(recommended_ids, relevant_ids, k):
    """Fraction of top-K recommendations that are relevant"""
    if k == 0:
        return 0.0
    top_k = recommended_ids[:k]
    hits = len(set(top_k) & set(relevant_ids))
    return hits / k


def recall_at_k(recommended_ids, relevant_ids, k):
    """Fraction of relevant items found in top-K recommendations"""
    if not relevant_ids:
        return 0.0
    top_k = recommended_ids[:k]
    hits = len(set(top_k) & set(relevant_ids))
    return hits / len(relevant_ids)


def ndcg_at_k(recommended_ids, relevant_ids, k):
    """Normalized Discounted Cumulative Gain at K"""
    top_k = recommended_ids[:k]
    relevant_set = set(relevant_ids)

    dcg = 0.0
    for i, item_id in enumerate(top_k):
        if item_id in relevant_set:
            dcg += 1.0 / np.log2(i + 2)  # log2(rank+1), rank is 1-indexed

    # Ideal DCG: all relevant items at the top
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(ideal_hits))

    return dcg / idcg if idcg > 0 else 0.0


# ─────────────────────────────────────────────
# Evaluator Class
# ─────────────────────────────────────────────

class ModelEvaluator:
    def __init__(self, k=10, relevance_threshold=4.0, test_size=0.2, random_state=42):
        """
        Args:
            k: Number of recommendations to evaluate (Precision@K, Recall@K, NDCG@K)
            relevance_threshold: Minimum rating to consider a movie "relevant"
            test_size: Fraction of data to use for testing
            random_state: Random seed for reproducibility
        """
        self.k = k
        self.relevance_threshold = relevance_threshold
        self.test_size = test_size
        self.random_state = random_state

    def split_data(self, ratings_df):
        """Split ratings into train and test sets"""
        train_df, test_df = train_test_split(
            ratings_df,
            test_size=self.test_size,
            random_state=self.random_state
        )
        return train_df.reset_index(drop=True), test_df.reset_index(drop=True)

    def evaluate_cf_ratings(self, cf_model, test_df):
        """
        Evaluate CF model on rating prediction (RMSE, MAE).
        Uses the reconstructed user-item matrix to predict ratings.
        """
        y_true = []
        y_pred = []

        from sklearn.decomposition import TruncatedSVD
        # Only works for SVD-based CF (not ALS implicit)
        if not hasattr(cf_model.model, 'components_'):
            return None, None  # ALS doesn't predict explicit ratings

        for _, row in test_df.iterrows():
            user_id = row['userId']
            movie_id = row['movieId']
            actual_rating = row['rating']

            if user_id not in cf_model.user_map or movie_id not in cf_model.item_map:
                continue

            user_idx = cf_model.user_map[user_id]
            item_idx = cf_model.item_map[movie_id]

            user_vec = cf_model.user_item_matrix[user_idx]
            user_factors = cf_model.model.transform(user_vec)
            scores = np.dot(user_factors, cf_model.model.components_).flatten()
            predicted_rating = scores[item_idx]

            # Clip to valid rating range [0.5, 5.0]
            predicted_rating = np.clip(predicted_rating, 0.5, 5.0)

            y_true.append(actual_rating)
            y_pred.append(predicted_rating)

        if not y_true:
            return None, None

        return rmse(y_true, y_pred), mae(y_true, y_pred)

    def evaluate_ranking(self, model_name, recommend_fn, test_df, train_df):
        """
        Evaluate a model on ranking metrics (Precision@K, Recall@K, NDCG@K).

        Args:
            model_name: Name of the model (for logging)
            recommend_fn: Callable(user_id, top_k) -> list of movie IDs
            test_df: Test ratings DataFrame
            train_df: Train ratings DataFrame (to exclude already-seen items)
        """
        precisions, recalls, ndcgs = [], [], []

        # Get users who appear in both train and test
        test_users = test_df['userId'].unique()
        train_users = set(train_df['userId'].unique())
        eval_users = [u for u in test_users if u in train_users]

        print(f"   Evaluating {model_name} on {len(eval_users)} users...")

        for user_id in eval_users:
            # Ground truth: movies rated >= threshold in test set
            user_test = test_df[test_df['userId'] == user_id]
            relevant_ids = user_test[
                user_test['rating'] >= self.relevance_threshold
            ]['movieId'].tolist()

            if not relevant_ids:
                continue

            # Get recommendations
            try:
                recs = recommend_fn(user_id, top_k=self.k)
                if isinstance(recs, pd.DataFrame):
                    if recs.empty:
                        rec_ids = []
                    elif 'movieId' in recs.columns:
                        rec_ids = recs['movieId'].tolist()
                    else:
                        rec_ids = []
                elif isinstance(recs, list):
                    rec_ids = recs
                else:
                    rec_ids = []
            except Exception:
                rec_ids = []

            precisions.append(precision_at_k(rec_ids, relevant_ids, self.k))
            recalls.append(recall_at_k(rec_ids, relevant_ids, self.k))
            ndcgs.append(ndcg_at_k(rec_ids, relevant_ids, self.k))

        return {
            f'Precision@{self.k}': np.mean(precisions) if precisions else 0.0,
            f'Recall@{self.k}': np.mean(recalls) if recalls else 0.0,
            f'NDCG@{self.k}': np.mean(ndcgs) if ndcgs else 0.0,
        }

    def run(self, movies_df, ratings_df, tags_df=None):
        """
        Full evaluation pipeline: train all models, evaluate, print results.

        Args:
            movies_df: Movies DataFrame
            ratings_df: Ratings DataFrame
            tags_df: Optional tags DataFrame
        
        Returns:
            results_df: DataFrame with metrics for each model
        """
        print("\n" + "=" * 60)
        print("StreamLens - Model Evaluation")
        print("=" * 60)

        # 1. Split data
        print(f"\n📊 Splitting data (train={1-self.test_size:.0%} / test={self.test_size:.0%})...")
        train_df, test_df = self.split_data(ratings_df)
        print(f"   Train: {len(train_df):,} ratings | Test: {len(test_df):,} ratings")

        results = {}

        # ── 2. Content-Based ──────────────────────────────────────
        print("\n🧠 Training & Evaluating Content-Based Model...")
        cb_model = ContentBasedRecommender()
        cb_model.fit(movies_df, tags_df=tags_df)

        def cb_recommend(user_id, top_k):
            user_history = train_df[train_df['userId'] == user_id]
            if user_history.empty:
                return []
            # Use the user's top-rated movie as the seed
            fav_movie_id = user_history.sort_values('rating', ascending=False).iloc[0]['movieId']
            try:
                recs = cb_model.recommend(movie_id=fav_movie_id, top_k=top_k)
                return recs['movieId'].tolist()
            except ValueError:
                return []

        cb_ranking = self.evaluate_ranking('Content-Based', cb_recommend, test_df, train_df)
        results['Content-Based'] = {**cb_ranking, 'RMSE': '-', 'MAE': '-'}

        # ── 3. Collaborative Filtering ────────────────────────────
        print("\n🤝 Training & Evaluating Collaborative Filtering Model...")
        cf_model = CollaborativeRecommender(n_factors=50)
        cf_model.fit(train_df)

        cf_rmse, cf_mae = self.evaluate_cf_ratings(cf_model, test_df)

        def cf_recommend(user_id, top_k):
            recs = cf_model.recommend(user_id, top_k=top_k)
            if isinstance(recs, pd.DataFrame) and not recs.empty:
                return recs['movieId'].tolist()
            return []

        cf_ranking = self.evaluate_ranking('Collaborative Filtering', cf_recommend, test_df, train_df)
        results['Collaborative Filtering'] = {
            **cf_ranking,
            'RMSE': f'{cf_rmse:.4f}' if cf_rmse is not None else '-',
            'MAE':  f'{cf_mae:.4f}'  if cf_mae  is not None else '-',
        }

        # ── 4. Hybrid ─────────────────────────────────────────────
        print("\n🧬 Training & Evaluating Hybrid Model...")
        hybrid_model = HybridRecommender(cb_model, cf_model)
        hybrid_model.fit(train_df)

        def hybrid_recommend(user_id, top_k):
            recs = hybrid_model.recommend(user_id, top_k=top_k)
            if isinstance(recs, pd.DataFrame) and not recs.empty and 'movieId' in recs.columns:
                return recs['movieId'].tolist()
            return []

        hybrid_ranking = self.evaluate_ranking('Hybrid', hybrid_recommend, test_df, train_df)
        results['Hybrid'] = {**hybrid_ranking, 'RMSE': '-', 'MAE': '-'}

        # ── 5. Print Results ──────────────────────────────────────
        print("\n" + "=" * 60)
        print("📊 Evaluation Results")
        print("=" * 60)

        results_df = pd.DataFrame(results).T
        # Reorder columns
        col_order = ['RMSE', 'MAE', f'Precision@{self.k}', f'Recall@{self.k}', f'NDCG@{self.k}']
        results_df = results_df[[c for c in col_order if c in results_df.columns]]

        # Format float columns
        for col in results_df.columns:
            results_df[col] = results_df[col].apply(
                lambda x: f'{float(x):.4f}' if isinstance(x, float) else x
            )

        print(results_df.to_string())
        print("=" * 60)

        return results_df


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

def main():
    DATA_PATH = Path('data/raw/ml-latest')
    PROCESSED_PATH = Path('data/processed')

    print("📊 Loading data...")
    try:
        movies_df = pd.read_csv(DATA_PATH / 'movies.csv')
        ratings_df = pd.read_csv(DATA_PATH / 'ratings.csv')

        tags_path = DATA_PATH / 'tags.csv'
        tags_df = pd.read_csv(tags_path) if tags_path.exists() else None
    except FileNotFoundError as e:
        print(f"❌ Data not found: {e}")
        print("   Please run data ingestion first: python src/data/ingestion.py")
        return

    print(f"✅ Loaded {len(movies_df):,} movies and {len(ratings_df):,} ratings")

    evaluator = ModelEvaluator(k=10, relevance_threshold=4.0)
    results = evaluator.run(movies_df, ratings_df, tags_df=tags_df)

    # Save results
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    results.to_csv(PROCESSED_PATH / 'evaluation_results.csv')
    print(f"\n💾 Results saved to {PROCESSED_PATH / 'evaluation_results.csv'}")


if __name__ == '__main__':
    main()
