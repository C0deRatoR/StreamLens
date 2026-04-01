"""
Model Training Pipeline
Trains, evaluates, and saves recommender models.
"""

import pandas as pd
import numpy as np
import os
import joblib
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from src.models.content_based import ContentBasedRecommender
    from src.models.collaborative_filtering import CollaborativeRecommender
    from src.models.hybrid import HybridRecommender
    from src.models.evaluate import ModelEvaluator
except ImportError as e:
    print(f"Error importing models: {e}")
    # Fallback for direct execution
    from content_based import ContentBasedRecommender
    from collaborative_filtering import CollaborativeRecommender
    from hybrid import HybridRecommender
    from evaluate import ModelEvaluator

def train_and_save():
    print("=" * 60)
    print("StreamLens - Model Training Pipeline")
    print("=" * 60)
    
    # Paths
    DATA_PATH = Path('data/processed')
    MODELS_PATH = Path('models')
    MODELS_PATH.mkdir(exist_ok=True)
    
    # 1. Load Data
    print("\n📊 Loading processed data...")
    RAW_PATH = Path('data/raw/ml-latest')
    try:
        # Try processed first, fall back to raw
        if (DATA_PATH / 'movies_processed.csv').exists():
            movies_df = pd.read_csv(DATA_PATH / 'movies_processed.csv')
            ratings_df = pd.read_csv(DATA_PATH / 'ratings_processed.csv')
        else:
            print("⚠️ Processed data not found, loading from raw...")
            movies_df = pd.read_csv(RAW_PATH / 'movies.csv')
            ratings_df = pd.read_csv(RAW_PATH / 'ratings.csv')
        
        # Load tags for better content-based features
        tags_path = RAW_PATH / 'tags.csv'
        if tags_path.exists():
            tags_df = pd.read_csv(tags_path)
            print(f"✅ Loaded {len(tags_df)} tags")
        else:
            print("⚠️ Tags file not found, skipping tags.")
            tags_df = None
            
    except FileNotFoundError as e:
        print(f"❌ Data not found: {e}")
        return
        
    print(f"✅ Loaded {len(movies_df)} movies and {len(ratings_df)} ratings")
    
    # 2. Train Content-Based Model
    print("\n🧠 Training Content-Based Model...")
    cb_model = ContentBasedRecommender()
    cb_model.fit(movies_df, tags_df=tags_df)
    
    # Save parameters/artifacts if needed, but we'll save the whole object
    joblib.dump(cb_model, MODELS_PATH / 'content_based_model.pkl')
    print("✅ Content-Based Model saved")
    
    # 3. Train Collaborative Filtering Model
    print("\n🤝 Training Collaborative Filtering Model...")
    cf_model = CollaborativeRecommender(n_factors=50)
    cf_model.fit(ratings_df)
    
    joblib.dump(cf_model, MODELS_PATH / 'collaborative_model.pkl')
    print("✅ Collaborative Model saved")
    
    # 4. Initialize Hybrid Model
    print("\n🧬 Initializing Hybrid Model...")
    hybrid_model = HybridRecommender(cb_model, cf_model)
    # Hybrid doesn't need 'fit' in this implementation (it uses the fitted sub-models)
    # But it needs ratings_df for user history lookup
    hybrid_model.fit(ratings_df) 
    
    # We save the wrapper (or just re-init it in API using loaded sub-models)
    # Saving it is convenient
    joblib.dump(hybrid_model, MODELS_PATH / 'hybrid_model.pkl')
    print("✅ Hybrid Model saved")
    
    # 5. Evaluation / Demo
    print("\n" + "=" * 60)
    print("🚀 Model Evaluation Demo")
    print("=" * 60)
    
    # Pick a random user
    sample_user = ratings_df['userId'].sample(1).iloc[0]
    print(f"\nExample Recommendations for User ID: {sample_user}")
    
    # Show user history
    user_history = ratings_df[ratings_df['userId'] == sample_user].sort_values('rating', ascending=False).head(5)
    history_titles = user_history.merge(movies_df, on='movieId')['title'].tolist()
    print(f"User likes: {history_titles}")
    
    print("\n--- Content-Based (based on first liked movie) ---")
    if user_history.empty:
        print("No history.")
    else:
        fav_movie_id = user_history.iloc[0]['movieId']
        fav_movie_title = movies_df[movies_df['movieId'] == fav_movie_id]['title'].values[0]
        print(f"Because you liked '{fav_movie_title}':")
        print(cb_model.recommend(movie_id=fav_movie_id, top_k=3)[['title', 'similarity_score']])
        
    print("\n--- Collaborative Filtering ---")
    print(cf_model.recommend(sample_user, top_k=3))
    
    print("\n--- Hybrid Recommender ---")
    hybrid_recs = hybrid_model.recommend(sample_user, top_k=5)
    print(hybrid_recs[['title', 'hybrid_score']] if not hybrid_recs.empty else "No recommendations")

    # 6. Evaluate all models
    print("\n" + "=" * 60)
    print("📊 Running Model Evaluation...")
    print("=" * 60)
    evaluator = ModelEvaluator(k=10, relevance_threshold=4.0)
    eval_results = evaluator.run(movies_df, ratings_df, tags_df=tags_df)
    
    # Save evaluation results
    eval_results.to_csv(DATA_PATH / 'evaluation_results.csv')
    print(f"\n💾 Evaluation results saved to {DATA_PATH / 'evaluation_results.csv'}")

if __name__ == "__main__":
    train_and_save()
