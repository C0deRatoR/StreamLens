"""
Hybrid Recommender System
Combines Content-Based and Collaborative Filtering recommendations.
"""

import pandas as pd
import numpy as np

class HybridRecommender:
    def __init__(self, cb_model, cf_model, cb_weight=0.3, cf_weight=0.7):
        """
        Args:
            cb_model: Trained ContentBasedRecommender
            cf_model: Trained CollaborativeRecommender
            cb_weight: Weight for content-based scores
            cf_weight: Weight for collaborative filtering scores
        """
        self.cb_model = cb_model
        self.cf_model = cf_model
        self.cb_weight = cb_weight
        self.cf_weight = cf_weight
        self.ratings_df = None
        
    def fit(self, ratings_df):
        """
        Store ratings for user history retrieval
        """
        self.ratings_df = ratings_df
        
    def normalize_scores(self, scores):
        """Normalize scores to 0-1 range"""
        if not scores:
            return {}
        
        min_score = min(scores.values())
        max_score = max(scores.values())
        
        if max_score == min_score:
            return {k: 1.0 for k in scores}
            
        return {k: (v - min_score) / (max_score - min_score) for k, v in scores.items()}
        
    def recommend(self, user_id, top_k=10):
        """
        Get hybrid recommendations
        """
        # 1. Get CF Recommendations
        try:
            cf_recs_df = self.cf_model.recommend(user_id, top_k=top_k * 2) # Get more to allow filtering/reranking
            cf_scores = dict(zip(cf_recs_df['movieId'], cf_recs_df['score'])) if not cf_recs_df.empty else {}
        except Exception as e:
            print(f"CF Error: {e}")
            cf_scores = {}
            
        # 2. Get Content-Based Recommendations
        # Based on user's high-rated movies
        cb_scores = {}
        
        if self.ratings_df is not None:
            user_history = self.ratings_df[self.ratings_df['userId'] == user_id]
            
            # Get top 3 rated movies by this user
            top_user_movies = user_history.sort_values('rating', ascending=False).head(3)['movieId'].tolist()
            
            if top_user_movies:
                # Find similar movies for each
                for movie_id in top_user_movies:
                    try:
                        # We need CB model to support recommendation by ID
                        # Assuming my CB implementation supports it (it does)
                        recs = self.cb_model.recommend(movie_id=movie_id, top_k=5)
                        for _, row in recs.iterrows():
                            mid = row['movieId']
                            score = row['similarity_score']
                            # Accumulate scores (if recommended by multiple favorites, it's better)
                            cb_scores[mid] = cb_scores.get(mid, 0) + score
                    except ValueError:
                        continue
        
        # 3. Combine Scores
        # Normalize both
        cf_norm = self.normalize_scores(cf_scores)
        cb_norm = self.normalize_scores(cb_scores)
        
        # Get all unique movies
        all_movies = set(cf_norm.keys()) | set(cb_norm.keys())
        
        final_scores = []
        for mid in all_movies:
            s_cf = cf_norm.get(mid, 0)
            s_cb = cb_norm.get(mid, 0)
            
            # Simple weighted average
            final_score = (s_cf * self.cf_weight) + (s_cb * self.cb_weight)
            final_scores.append({'movieId': mid, 'hybrid_score': final_score})
            
        # Sort and return
        final_scores = sorted(final_scores, key=lambda x: x['hybrid_score'], reverse=True)[:top_k]
        
        # Format as DataFrame
        if not final_scores:
            return pd.DataFrame(columns=['movieId', 'hybrid_score', 'title'])
            
        result_df = pd.DataFrame(final_scores)
        
        # Add titles if possible (using CB model's data)
        if hasattr(self.cb_model, 'movies_df') and self.cb_model.movies_df is not None:
            result_df = result_df.merge(self.cb_model.movies_df[['movieId', 'title', 'genres']], on='movieId', how='left')
            
        return result_df

if __name__ == "__main__":
    print("Hybrid Recommender Module")
