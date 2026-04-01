"""
Feature Engineering Module for StreamLens
Implements genre encoding, TF-IDF for tags, and context features
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType, IntegerType
from pyspark.ml.feature import (
    StringIndexer, OneHotEncoder, VectorAssembler,
    CountVectorizer, IDF, Tokenizer, StopWordsRemover
)
from pyspark.ml import Pipeline
import numpy as np


class FeatureEngineer:
    """Feature engineering for movie recommendation system"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        
    def create_genre_features(self, movies_df: DataFrame):
        """
        Create one-hot encoded features for genres
        Uses multi-label binarization for movies with multiple genres
        
        Args:
            movies_df: Movies DataFrame with 'genres_array' column
        
        Returns:
            DataFrame with genre feature columns
        """
        print("\n🎭 Creating genre features...")
        
        # Get all unique genres
        all_genres = movies_df.select(F.explode('genres_array').alias('genre')).distinct()
        genres_list = [row['genre'] for row in all_genres.collect()]
        genres_list = sorted([g for g in genres_list if g != '(no genres listed)'])
        
        print(f"   Found {len(genres_list)} unique genres")
        
        # Create binary column for each genre
        for genre in genres_list:
            col_name = f"genre_{genre.lower().replace('-', '_')}"
            movies_df = movies_df.withColumn(
                col_name,
                F.when(F.array_contains('genres_array', genre), 1).otherwise(0)
            )
        
        print(f"✅ Created {len(genres_list)} genre feature columns")
        
        return movies_df, genres_list
    
    def create_tag_features(self, tags_df: DataFrame, movies_df: DataFrame):
        """
        Create TF-IDF features from movie tags
        
        Args:
            tags_df: Tags DataFrame
            movies_df: Movies DataFrame
        
        Returns:
            DataFrame with tag TF-IDF features
        """
        print("\n🏷️  Creating tag-based features...")
        
        # Aggregate tags per movie
        movie_tags = tags_df.groupBy('movieId').agg(
            F.collect_list('tag').alias('tags_list'),
            F.count('tag').alias('num_tags')
        )
        
        # Join with movies
        movies_with_tags = movies_df.join(movie_tags, on='movieId', how='left')
        
        # Handle movies without tags
        movies_with_tags = movies_with_tags.fillna({'num_tags': 0})
        movies_with_tags = movies_with_tags.withColumn(
            'tags_list',
            F.when(F.col('tags_list').isNull(), F.array()).otherwise(F.col('tags_list'))
        )
        
        # Concatenate all tags into text
        movies_with_tags = movies_with_tags.withColumn(
            'tags_text',
            F.concat_ws(' ', 'tags_list')
        )
        
        print(f"✅ Aggregated tags for movies")
        
        return movies_with_tags
    
    def create_temporal_context_features(self, ratings_df: DataFrame):
        """
        Create context features based on time of rating
        
        Args:
            ratings_df: Ratings DataFrame with datetime column
        
        Returns:
            DataFrame with temporal context features
        """
        print("\n⏰ Creating temporal context features...")
        
        # Hour of day features (already have time_of_day)
        
        # Weekend vs weekday
        ratings_df = ratings_df.withColumn(
            'is_weekend',
            F.when((F.col('day_of_week') == 1) | (F.col('day_of_week') == 7), 1).otherwise(0)
        )
        
        # Season (assuming Northern Hemisphere)
        ratings_df = ratings_df.withColumn(
            'season',
            F.when(F.col('month').isin([12, 1, 2]), 'winter')
             .when(F.col('month').isin([3, 4, 5]), 'spring')
             .when(F.col('month').isin([6, 7, 8]), 'summer')
             .otherwise('fall')
        )
        
        print(f"✅ Created temporal context features")
        
        return ratings_df
    
    def create_user_genre_preferences(self, ratings_df: DataFrame, movies_df: DataFrame, genre_columns: list):
        """
        Create user profile based on genre preferences
        
        Args:
            ratings_df: Ratings DataFrame
            movies_df: Movies DataFrame with genre features
            genre_columns: List of genre column names
        
        Returns:
            DataFrame with user genre preferences
        """
        print("\n👤 Creating user genre preference profiles...")
        
        # Join ratings with movies to get genres
        ratings_with_genres = ratings_df.join(
            movies_df.select(['movieId'] + genre_columns),
            on='movieId'
        )
        
        # Calculate weighted genre scores per user
        # Weight by rating (higher ratings = stronger preference)
        user_genre_prefs = ratings_with_genres.groupBy('userId').agg(
            *[F.sum(F.col(genre_col) * F.col('rating')).alias(f'pref_{genre_col}') 
              for genre_col in genre_columns]
        )
        
        print(f"✅ Created user genre preference profiles")
        
        return user_genre_prefs
    
    def create_age_group_feature(self, movies_df: DataFrame):
        """
        Create age group categorization based on movie year
        Used for age-appropriate recommendations
        
        Args:
            movies_df: Movies DataFrame with year column
        
        Returns:
            DataFrame with age_group column
        """
        print("\n🎂 Creating age group features...")
        
        movies_df = movies_df.withColumn(
            'decade',
            (F.floor(F.col('year') / 10) * 10).cast('int')
        )
        
        movies_df = movies_df.withColumn(
            'era',
            F.when(F.col('year') < 1970, 'classic')
             .when((F.col('year') >= 1970) & (F.col('year') < 1990), 'vintage')
             .when((F.col('year') >= 1990) & (F.col('year') < 2010), 'modern')
             .otherwise('contemporary')
        )
        
        print(f"✅ Created age group and era features")
        
        return movies_df
    
    def create_popularity_features(self, ratings_df: DataFrame):
        """
        Create popularity and trending features
        
        Args:
            ratings_df: Ratings DataFrame
        
        Returns:
            DataFrame with popularity features
        """
        print("\n📊 Creating popularity features...")
        
        # Overall popularity
        popularity = ratings_df.groupBy('movieId').agg(
            F.count('rating').alias('popularity_score'),
            F.mean('rating').alias('quality_score')
        )
        
        # Recent popularity (last year of data)
        max_timestamp = ratings_df.agg(F.max('timestamp')).collect()[0][0]
        one_year_ago = max_timestamp - (365 * 24 * 60 * 60)  # 1 year in seconds
        
        recent_popularity = ratings_df.filter(F.col('timestamp') > one_year_ago).groupBy('movieId').agg(
            F.count('rating').alias('recent_popularity'),
            F.mean('rating').alias('recent_quality')
        )
        
        # Combine popularity features
        popularity_features = popularity.join(recent_popularity, on='movieId', how='left')
        popularity_features = popularity_features.fillna({'recent_popularity': 0, 'recent_quality': 0.0})
        
        # Calculate trending score (recent popularity / overall popularity)
        popularity_features = popularity_features.withColumn(
            'trending_score',
            F.when(F.col('popularity_score') > 0, 
                   F.col('recent_popularity') / F.col('popularity_score'))
             .otherwise(0.0)
        )
        
        print(f"✅ Created popularity and trending features")
        
        return popularity_features
    
    def normalize_features(self, df: DataFrame, feature_cols: list):
        """
        Min-max normalization for numerical features
        
        Args:
            df: DataFrame
            feature_cols: List of columns to normalize
        
        Returns:
            DataFrame with normalized features
        """
        print(f"\n📐 Normalizing {len(feature_cols)} features...")
        
        for col_name in feature_cols:
            # Get min and max
            min_max = df.agg(
                F.min(col_name).alias('min'),
                F.max(col_name).alias('max')
            ).collect()[0]
            
            min_val = min_max['min']
            max_val = min_max['max']
            
            if max_val > min_val:
                df = df.withColumn(
                    f"{col_name}_normalized",
                    (F.col(col_name) - min_val) / (max_val - min_val)
                )
            else:
                df = df.withColumn(f"{col_name}_normalized", F.lit(0.0))
        
        print(f"✅ Features normalized")
        
        return df


def main():
    """Test feature engineering pipeline"""
    from preprocessing import SparkDataPreprocessor
    
    print("=" * 60)
    print("StreamLens - Feature Engineering Pipeline")
    print("=" * 60)
    
    # Initialize preprocessor
    preprocessor = SparkDataPreprocessor("StreamLens_FeatureEngineering")
    
    try:
        # Load data
        data = preprocessor.load_data()
        
        # Preprocess
        movies_processed = preprocessor.preprocess_movies(data['movies'])
        ratings_processed = preprocessor.preprocess_ratings(data['ratings'])
        
        # Initialize feature engineer
        fe = FeatureEngineer(preprocessor.spark)
        
        # Create features
        movies_with_genres, genre_list = fe.create_genre_features(movies_processed)
        movies_with_tags = fe.create_tag_features(data['tags'], movies_with_genres)
        movies_with_age = fe.create_age_group_feature(movies_with_tags)
        
        ratings_with_context = fe.create_temporal_context_features(ratings_processed)
        
        genre_cols = [f"genre_{g.lower().replace('-', '_')}" for g in genre_list]
        user_genre_prefs = fe.create_user_genre_preferences(
            ratings_with_context, movies_with_genres, genre_cols
        )
        
        popularity_features = fe.create_popularity_features(ratings_with_context)
        
        # Combine all features
        movies_final = movies_with_age.join(popularity_features, on='movieId', how='left')
        
        print("\n" + "=" * 60)
        print("Preview of final feature set:")
        print("=" * 60)
        movies_final.select(
            'movieId', 'title', 'year', 'era', 'num_genres',
            'popularity_score', 'quality_score', 'trending_score'
        ).show(10, truncate=False)
        
        # Save engineered features
        preprocessor.save_processed_data({
            'movies_features': movies_final,
            'ratings_features': ratings_with_context,
            'user_genre_preferences': user_genre_prefs
        }, output_path="../data/processed/features/")
        
        print("\n✅ Feature Engineering Complete!")
        
    finally:
        preprocessor.stop()


if __name__ == "__main__":
    main()
