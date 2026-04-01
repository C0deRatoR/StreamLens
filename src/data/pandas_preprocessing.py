"""
Alternative Preprocessing using Pandas
For systems where Spark/Java is not available yet
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from sklearn.preprocessing import MultiLabelBinarizer, MinMaxScaler
from datetime import datetime


class PandasPreprocessor:
    """Preprocess MovieLens data using Pandas (alternative to Spark)"""
    
    def __init__(self, data_path="data/raw/ml-latest/"):
        self.data_path = Path(data_path)
        self.output_path = Path("data/processed")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
    def load_data(self):
        """Load all MovieLens datasets"""
        print("📊 Loading datasets...")
        
        self.movies = pd.read_csv(self.data_path / "movies.csv")
        self.ratings = pd.read_csv(self.data_path / "ratings.csv")
        self.tags = pd.read_csv(self.data_path / "tags.csv")
        self.links = pd.read_csv(self.data_path / "links.csv")
        
        print(f"✅ Loaded {len(self.movies)} movies")
        print(f"✅ Loaded {len(self.ratings)} ratings")
        print(f"✅ Loaded {len(self.tags)} tags")
        print(f"✅ Loaded {len(self.links)} links")
        
    def preprocess_movies(self):
        """Preprocess movies dataset"""
        print("\n🔧 Preprocessing movies...")
        
        # Extract year from title
        self.movies['year'] = self.movies['title'].str.extract(r'\((\d{4})\)$')[0].astype('float')
        
        # Clean title
        self.movies['clean_title'] = self.movies['title'].str.replace(r'\s*\(\d{4}\)\s*$', '', regex=True)
        
        # Split genres into list
        self.movies['genres_list'] = self.movies['genres'].str.split('|')
        
        # Number of genres
        self.movies['num_genres'] = self.movies['genres_list'].apply(len)
        
        # Decade and era
        self.movies['decade'] = (self.movies['year'] // 10 * 10).astype('Int64')
        self.movies['era'] = pd.cut(
            self.movies['year'],
            bins=[0, 1970, 1990, 2010, 2030],
            labels=['classic', 'vintage', 'modern', 'contemporary']
        )
        
        print(f"✅ Movies preprocessed")
        
    def preprocess_ratings(self):
        """Preprocess ratings dataset"""
        print("\n🔧 Preprocessing ratings...")
        
        # Convert timestamp to datetime
        self.ratings['datetime'] = pd.to_datetime(self.ratings['timestamp'], unit='s')
        
        # Extract temporal features
        self.ratings['year'] = self.ratings['datetime'].dt.year
        self.ratings['month'] = self.ratings['datetime'].dt.month
        self.ratings['day'] = self.ratings['datetime'].dt.day
        self.ratings['hour'] = self.ratings['datetime'].dt.hour
        self.ratings['day_of_week'] = self.ratings['datetime'].dt.dayofweek
        
        # Time of day context
        def get_time_of_day(hour):
            if 6 <= hour < 12:
                return 'morning'
            elif 12 <= hour < 18:
                return 'afternoon'
            elif 18 <= hour < 22:
                return 'evening'
            else:
                return 'night'
        
        self.ratings['time_of_day'] = self.ratings['hour'].apply(get_time_of_day)
        
        # Weekend
        self.ratings['is_weekend'] = (self.ratings['day_of_week'] >= 5).astype(int)
        
        # Season
        def get_season(month):
            if month in [12, 1, 2]:
                return 'winter'
            elif month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            else:
                return 'fall'
        
        self.ratings['season'] = self.ratings['month'].apply(get_season)
        
        print(f"✅ Ratings preprocessed")
        
    def create_genre_features(self):
        """Create one-hot encoded genre features"""
        print("\n🎭 Creating genre features...")
        
        # Get all unique genres
        all_genres = set()
        for genres in self.movies['genres_list']:
            all_genres.update(genres)
        all_genres.discard('(no genres listed)')
        all_genres = sorted(list(all_genres))
        
        # Create binary columns for each genre
        for genre in all_genres:
            col_name = f"genre_{genre.lower().replace('-', '_')}"
            self.movies[col_name] = self.movies['genres_list'].apply(
                lambda x: 1 if genre in x else 0
            )
        
        self.genre_columns = [f"genre_{g.lower().replace('-', '_')}" for g in all_genres]
        
        print(f"✅ Created {len(self.genre_columns)} genre features")
        
        return all_genres
        
    def aggregate_movie_stats(self):
        """Aggregate rating statistics for each movie"""
        print("\n📈 Aggregating movie statistics...")
        
        movie_stats = self.ratings.groupby('movieId').agg({
            'rating': ['count', 'mean', 'std', 'min', 'max']
        }).round(3)
        
        movie_stats.columns = ['num_ratings', 'avg_rating', 'std_rating', 'min_rating', 'max_rating']
        movie_stats = movie_stats.reset_index()
        
        # Merge with movies
        self.movies = self.movies.merge(movie_stats, on='movieId', how='left')
        self.movies.fillna({
            'num_ratings': 0,
            'avg_rating': 0.0,
            'std_rating': 0.0
        }, inplace=True)
        
        print(f"✅ Movie statistics computed")
        
    def aggregate_user_stats(self):
        """Aggregate rating statistics for each user"""
        print("\n📈 Aggregating user statistics...")
        
        self.user_stats = self.ratings.groupby('userId').agg({
            'rating': ['count', 'mean', 'std', 'min', 'max']
        }).round(3)
        
        self.user_stats.columns = ['num_ratings', 'avg_rating', 'std_rating', 'min_rating', 'max_rating']
        self.user_stats = self.user_stats.reset_index()
        
        print(f"✅ User statistics computed")
        
    def create_popularity_features(self):
        """Create popularity and trending features"""
        print("\n📊 Creating popularity features...")
        
        # Get max timestamp
        max_timestamp = self.ratings['timestamp'].max()
        one_year_ago = max_timestamp - (365 * 24 * 60 * 60)
        
        recent_ratings = self.ratings[self.ratings['timestamp'] > one_year_ago]
        
        recent_stats = recent_ratings.groupby('movieId').agg({
            'rating': ['count', 'mean']
        })
        recent_stats.columns = ['recent_popularity', 'recent_quality']
        recent_stats = recent_stats.reset_index()
        
        # Merge
        self.movies = self.movies.merge(recent_stats, on='movieId', how='left')
        self.movies.fillna({
            'recent_popularity': 0,
            'recent_quality': 0.0
        }, inplace=True)
        
        # Trending score
        self.movies['trending_score'] = np.where(
            self.movies['num_ratings'] > 0,
            self.movies['recent_popularity'] / self.movies['num_ratings'],
            0.0
        )
        
        print(f"✅ Popularity features created")
        
    def create_user_genre_preferences(self, genre_columns):
        """Create user genre preference profiles"""
        print("\n👤 Creating user genre preferences...")
        
        # Merge ratings with genre features
        ratings_with_genres = self.ratings.merge(
            self.movies[['movieId'] + genre_columns],
            on='movieId'
        )
        
        # Calculate weighted genre preferences (rating * genre_indicator)
        user_prefs = {}
        for genre_col in genre_columns:
            user_prefs[f'pref_{genre_col}'] = (
                ratings_with_genres.groupby('userId')
                .apply(lambda x: (x[genre_col] * x['rating']).sum())
            )
        
        self.user_genre_prefs = pd.DataFrame(user_prefs).reset_index()
        
        print(f"✅ User genre preferences created")
        
    def save_processed_data(self):
        """Save all processed data"""
        print("\n💾 Saving processed data...")
        
        # Save CSVs
        self.movies.to_csv(self.output_path / "movies_processed.csv", index=False)
        self.ratings.to_csv(self.output_path / "ratings_processed.csv", index=False)
        self.user_stats.to_csv(self.output_path / "user_stats.csv", index=False)
        self.user_genre_prefs.to_csv(self.output_path / "user_genre_prefs.csv", index=False)
        
        # Save metadata
        metadata = {
            'num_movies': len(self.movies),
            'num_ratings': len(self.ratings),
            'num_users': self.ratings['userId'].nunique(),
            'genre_columns': self.genre_columns,
            'processing_date': datetime.now().isoformat()
        }
        
        with open(self.output_path / "preprocessing_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ All data saved to {self.output_path}")
        
    def run_pipeline(self):
        """Run the complete preprocessing pipeline"""
        print("=" * 60)
        print("StreamLens - Pandas Preprocessing Pipeline")
        print("=" * 60)
        
        self.load_data()
        self.preprocess_movies()
        self.preprocess_ratings()
        genres = self.create_genre_features()
        self.aggregate_movie_stats()
        self.aggregate_user_stats()
        self.create_popularity_features()
        self.create_user_genre_preferences(self.genre_columns)
        self.save_processed_data()
        
        print("\n" + "=" * 60)
        print("✅ Preprocessing Complete!")
        print("=" * 60)
        print(f"\nProcessed files saved to: {self.output_path}")
        print(f"  - movies_processed.csv: {len(self.movies)} rows")
        print(f"  - ratings_processed.csv: {len(self.ratings)} rows")
        print(f"  - user_stats.csv: {len(self.user_stats)} rows")
        print(f"  - user_genre_prefs.csv: {len(self.user_genre_prefs)} rows")


if __name__ == "__main__":
    preprocessor = PandasPreprocessor()
    preprocessor.run_pipeline()
