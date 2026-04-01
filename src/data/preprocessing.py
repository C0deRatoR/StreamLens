"""
Spark Data Preprocessing Module
Handles loading, cleaning, and transforming MovieLens data using PySpark
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.spark_config import get_spark_config


class SparkDataPreprocessor:
    """Preprocess MovieLens data using Apache Spark"""
    
    def __init__(self, app_name="StreamLens_Preprocessing"):
        """Initialize Spark session with configuration"""
        conf = get_spark_config(app_name=app_name, local_mode=True)
        self.spark = SparkSession.builder.config(conf=conf).getOrCreate()
        print(f"✅ Spark Session initialized: {self.spark.version}")
        print(f"   Master: {self.spark.sparkContext.master}")
    
    def load_data(self, data_path="../data/raw/ml-latest/"):
        """
        Load MovieLens datasets into Spark DataFrames
        
        Args:
            data_path: Path to MovieLens data directory
        
        Returns:
            Dictionary of Spark DataFrames
        """
        print(f"\n📊 Loading data from {data_path}")
        
        # Load movies
        movies_df = self.spark.read.csv(
            f"{data_path}/movies.csv",
            header=True,
            inferSchema=True
        )
        print(f"✅ Loaded {movies_df.count()} movies")
        
        # Load ratings
        ratings_df = self.spark.read.csv(
            f"{data_path}/ratings.csv",
            header=True,
            inferSchema=True
        )
        print(f"✅ Loaded {ratings_df.count()} ratings")
        
        # Load tags
        tags_df = self.spark.read.csv(
            f"{data_path}/tags.csv",
            header=True,
            inferSchema=True
        )
        print(f"✅ Loaded {tags_df.count()} tags")
        
        # Load links
        links_df = self.spark.read.csv(
            f"{data_path}/links.csv",
            header=True,
            inferSchema=True
        )
        print(f"✅ Loaded {links_df.count()} links")
        
        return {
            'movies': movies_df,
            'ratings': ratings_df,
            'tags': tags_df,
            'links': links_df
        }
    
    def preprocess_movies(self, movies_df):
        """
        Preprocess movies DataFrame
        - Extract year from title
        - Parse genres into array
        - Clean title
        """
        print("\n🔧 Preprocessing movies...")
        
        # Extract year from title (e.g., "Toy Story (1995)" -> 1995)
        movies_df = movies_df.withColumn(
            'year',
            F.regexp_extract('title', r'\((\d{4})\)', 1).cast('int')
        )
        
        # Clean title (remove year)
        movies_df = movies_df.withColumn(
            'clean_title',
            F.regexp_replace('title', r'\s*\(\d{4}\)\s*$', '')
        )
        
        # Split genres into array
        movies_df = movies_df.withColumn(
            'genres_array',
            F.split('genres', r'\|')
        )
        
        # Add number of genres
        movies_df = movies_df.withColumn(
            'num_genres',
            F.size('genres_array')
        )
        
        print(f"✅ Movies preprocessed")
        movies_df.show(5, truncate=False)
        
        return movies_df
    
    def preprocess_ratings(self, ratings_df):
        """
        Preprocess ratings DataFrame
        - Convert timestamp to datetime
        - Extract temporal features
        """
        print("\n🔧 Preprocessing ratings...")
        
        # Convert timestamp to datetime
        ratings_df = ratings_df.withColumn(
            'datetime',
            F.from_unixtime('timestamp')
        )
        
        # Extract temporal features
        ratings_df = ratings_df.withColumn('year', F.year('datetime'))
        ratings_df = ratings_df.withColumn('month', F.month('datetime'))
        ratings_df = ratings_df.withColumn('day', F.dayofmonth('datetime'))
        ratings_df = ratings_df.withColumn('hour', F.hour('datetime'))
        ratings_df = ratings_df.withColumn('day_of_week', F.dayofweek('datetime'))
        
        # Time of day context (Morning, Afternoon, Evening, Night)
        ratings_df = ratings_df.withColumn(
            'time_of_day',
            F.when((F.col('hour') >= 6) & (F.col('hour') < 12), 'morning')
             .when((F.col('hour') >= 12) & (F.col('hour') < 18), 'afternoon')
             .when((F.col('hour') >= 18) & (F.col('hour') < 22), 'evening')
             .otherwise('night')
        )
        
        print(f"✅ Ratings preprocessed")
        ratings_df.show(5)
        
        return ratings_df
    
    def aggregate_movie_stats(self, ratings_df, movies_df):
        """
        Aggregate rating statistics for each movie
        """
        print("\n📈 Aggregating movie statistics...")
        
        movie_stats = ratings_df.groupBy('movieId').agg(
            F.count('rating').alias('num_ratings'),
            F.mean('rating').alias('avg_rating'),
            F.stddev('rating').alias('std_rating'),
            F.min('rating').alias('min_rating'),
            F.max('rating').alias('max_rating')
        )
        
        # Join with movies
        movies_with_stats = movies_df.join(movie_stats, on='movieId', how='left')
        
        # Fill nulls for movies without ratings
        movies_with_stats = movies_with_stats.fillna({
            'num_ratings': 0,
            'avg_rating': 0.0,
            'std_rating': 0.0
        })
        
        print(f"✅ Movie statistics computed")
        movies_with_stats.select(
            'movieId', 'title', 'num_ratings', 'avg_rating'
        ).orderBy(F.desc('num_ratings')).show(10)
        
        return movies_with_stats
    
    def aggregate_user_stats(self, ratings_df):
        """
        Aggregate rating statistics for each user
        """
        print("\n📈 Aggregating user statistics...")
        
        user_stats = ratings_df.groupBy('userId').agg(
            F.count('rating').alias('num_ratings'),
            F.mean('rating').alias('avg_rating'),
            F.stddev('rating').alias('std_rating'),
            F.min('rating').alias('min_rating'),
            F.max('rating').alias('max_rating')
        )
        
        print(f"✅ User statistics computed")
        user_stats.orderBy(F.desc('num_ratings')).show(10)
        
        return user_stats
    
    def save_processed_data(self, dataframes, output_path="../data/processed/"):
        """
        Save processed DataFrames to Parquet format
        
        Args:
            dataframes: Dictionary of DataFrames to save
            output_path: Output directory path
        """
        print(f"\n💾 Saving processed data to {output_path}")
        
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        for name, df in dataframes.items():
            output_file = f"{output_path}/{name}.parquet"
            df.write.mode('overwrite').parquet(output_file)
            print(f"✅ Saved {name} to {output_file}")
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("\n✅ Spark session stopped")


def main():
    """Main preprocessing pipeline"""
    print("=" * 60)
    print("StreamLens - Spark Data Preprocessing Pipeline")
    print("=" * 60)
    
    # Initialize preprocessor
    preprocessor = SparkDataPreprocessor()
    
    try:
        # Load data
        data = preprocessor.load_data()
        
        # Preprocess movies
        movies_processed = preprocessor.preprocess_movies(data['movies'])
        
        # Preprocess ratings
        ratings_processed = preprocessor.preprocess_ratings(data['ratings'])
        
        # Aggregate statistics
        movies_with_stats = preprocessor.aggregate_movie_stats(
            ratings_processed, movies_processed
        )
        user_stats = preprocessor.aggregate_user_stats(ratings_processed)
        
        # Save processed data
        preprocessor.save_processed_data({
            'movies': movies_with_stats,
            'ratings': ratings_processed,
            'tags': data['tags'],
            'user_stats': user_stats
        })
        
        print("\n" + "=" * 60)
        print("✅ Preprocessing Complete!")
        print("=" * 60)
        
    finally:
        # Stop Spark session
        preprocessor.stop()


if __name__ == "__main__":
    main()
