"""
Collaborative Filtering Recommender System
Uses Matrix Factorization to recommend items based on user-item interactions.
"""

import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

# Try to import implicit, fallback to None if not available
try:
    import implicit
    IMPLICIT_AVAILABLE = True
except ImportError:
    IMPLICIT_AVAILABLE = False
    print("⚠️ 'implicit' library not found. Falling back to SVD.")

class CollaborativeRecommender:
    def __init__(self, method='als', n_factors=50, regularization=0.01):
        self.method = method
        self.n_factors = n_factors
        self.regularization = regularization
        self.model = None
        self.user_item_matrix = None
        self.user_map = None
        self.item_map = None
        self.reverse_user_map = None
        self.reverse_item_map = None
        
    def fit(self, ratings_df):
        """
        Fit the model on ratings data
        
        Args:
            ratings_df: DataFrame with 'userId', 'movieId', 'rating'
        """
        # Create mappings for user and item IDs to matrix indices
        unique_users = ratings_df['userId'].unique()
        unique_items = ratings_df['movieId'].unique()
        
        self.user_map = {user_id: index for index, user_id in enumerate(unique_users)}
        self.reverse_user_map = {index: user_id for user_id, index in self.user_map.items()}
        
        self.item_map = {item_id: index for index, item_id in enumerate(unique_items)}
        self.reverse_item_map = {index: item_id for item_id, index in self.item_map.items()}
        
        # Create sparse matrix
        # Rows: Users, Cols: Items
        rows = [self.user_map[u] for u in ratings_df['userId']]
        cols = [self.item_map[i] for i in ratings_df['movieId']]
        data = ratings_df['rating'].tolist()
        
        self.user_item_matrix = csr_matrix((data, (rows, cols)), 
                                         shape=(len(unique_users), len(unique_items)))
        
        print(f"User-Item Matrix Shape: {self.user_item_matrix.shape}")
        
        if IMPLICIT_AVAILABLE and self.method == 'als':
            print("Training ALS model using 'implicit'...")
            # Implicit expects Item-User matrix for training usually? 
            # In newer versions (0.6+), fit takes (user_items) if using implicit.cpu.als?
            # Let's check common pattern. Usually fit(user_item_matrix)
            
            self.model = implicit.als.AlternatingLeastSquares(
                factors=self.n_factors,
                regularization=self.regularization,
                iterations=15
            )
            # Adapt to implicit version if needed, but assuming standard 0.7+
            # fit() expects user_items usually.
            self.model.fit(self.user_item_matrix)
            
        else:
            print("Training TruncatedSVD model...")
            self.model = TruncatedSVD(n_components=self.n_factors, random_state=42)
            self.model.fit(self.user_item_matrix)
            
        print("✅ Collaborative Filtering Model trained successfully")
        
    def recommend(self, user_id, top_k=10):
        """
        Get recommendations for a user
        """
        if user_id not in self.user_map:
            print(f"⚠️ User {user_id} not found in training data (Cold Start).")
            return pd.DataFrame(columns=['movieId', 'score'])
            
        user_idx = self.user_map[user_id]
        
        recommendations = []
        
        if IMPLICIT_AVAILABLE and self.method == 'als':
            # recommend() takes user_id (index) and user_item_matrix
            # returns tuple (item_indices, scores)
            item_indices, scores = self.model.recommend(
                user_idx, 
                self.user_item_matrix[user_idx], 
                N=top_k
            )
            
            for idx, score in zip(item_indices, scores):
                recommendations.append({
                    'movieId': self.reverse_item_map[idx],
                    'score': float(score)
                })
                
        else:
            # SVD Inference
            # Reconstruct user vector
            user_vec = self.user_item_matrix[user_idx]
            
            # Predict all item scores
            # user_vec (1, n_items) * V_t.T (n_items, n_factors) ? 
            # transform returns (1, n_factors)
            user_factors = self.model.transform(user_vec)
            
            # scores = user_factors * components (n_factors, n_items)
            scores = np.dot(user_factors, self.model.components_).flatten()
            
            # Sort scores
            # Get indices of top_k
            # Exclude items already rated? Implicit does this automatically. SVD doesn't.
            
            already_rated = set(self.user_item_matrix[user_idx].indices)
            
            # Filter and sort
            top_indices = np.argsort(scores)[::-1]
            
            count = 0
            for idx in top_indices:
                if idx not in already_rated:
                    recommendations.append({
                        'movieId': self.reverse_item_map[idx],
                        'score': float(scores[idx])
                    })
                    count += 1
                    if count >= top_k:
                        break
                        
        return pd.DataFrame(recommendations)

if __name__ == "__main__":
    # Test
    print("Testing CollaborativeRecommender...")
    
    ratings_data = {
        'userId': [1, 1, 1, 2, 2, 3],
        'movieId': [1, 2, 3, 1, 2, 1],
        'rating': [5, 4, 3, 5, 5, 2] # 3 users, 3 items
    }
    ratings_df = pd.DataFrame(ratings_data)
    
    cf = CollaborativeRecommender(method='als')
    cf.fit(ratings_df)
    
    print("\nRecommendations for User 1:")
    print(cf.recommend(user_id=1, top_k=2))
