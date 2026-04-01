
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import os
from pathlib import Path

# Set visualization style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)

def ensure_dir(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)

def run_eda():
    print("=" * 60)
    print("StreamLens - Exploratory Data Analysis Support Script")
    print("=" * 60)

    # Define paths
    DATA_PATH = 'data/raw/ml-latest/'
    PROCESSED_PATH = 'data/processed/'
    VIS_PATH = 'visualizations/eda/'
    
    ensure_dir(PROCESSED_PATH)
    ensure_dir(VIS_PATH)

    print("📊 Loading datasets...")
    try:
        movies = pd.read_csv(os.path.join(DATA_PATH, 'movies.csv'))
        ratings = pd.read_csv(os.path.join(DATA_PATH, 'ratings.csv'))
        tags = pd.read_csv(os.path.join(DATA_PATH, 'tags.csv'))
        links = pd.read_csv(os.path.join(DATA_PATH, 'links.csv'))
    except FileNotFoundError as e:
        print(f"❌ Error loading data: {e}")
        return

    print(f"✅ Loaded {len(movies)} movies")
    print(f"✅ Loaded {len(ratings)} ratings")
    
    # Preprocessing for EDA
    ratings['datetime'] = pd.to_datetime(ratings['timestamp'], unit='s')
    ratings['year'] = ratings['datetime'].dt.year
    
    # 1. Rating Distribution
    print("📈 Generating Rating Distribution plot...")
    plt.figure(figsize=(10, 6))
    sns.countplot(data=ratings, x='rating', palette='viridis')
    plt.title('Distribution of Movie Ratings', fontsize=16, fontweight='bold')
    plt.xlabel('Rating', fontsize=12)
    plt.ylabel('Count', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_PATH, 'rating_distribution.png'))
    plt.close()

    # 2. Ratings over time
    print("📈 Generating Ratings Over Time plot...")
    ratings_over_time = ratings.groupby('year').size()
    plt.figure(figsize=(12, 6))
    ratings_over_time.plot(kind='bar', color='steelblue')
    plt.title('Number of Ratings per Year', fontsize=16, fontweight='bold')
    plt.xlabel('Year', fontsize=12)
    plt.ylabel('Number of Ratings', fontsize=12)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_PATH, 'ratings_over_time.png'))
    plt.close()

    # 3. Top 20 Most Rated Movies
    print("📈 Generating Top 20 Movies plot...")
    movie_rating_counts = ratings.groupby('movieId').size().reset_index(name='num_ratings')
    top_movies = movie_rating_counts.nlargest(20, 'num_ratings')
    top_movies = top_movies.merge(movies[['movieId', 'title']], on='movieId')
    
    plt.figure(figsize=(12, 8))
    sns.barplot(data=top_movies, y='title', x='num_ratings', palette='rocket')
    plt.title('Top 20 Most Rated Movies', fontsize=16, fontweight='bold')
    plt.xlabel('Number of Ratings', fontsize=12)
    plt.ylabel('Movie Title', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_PATH, 'top_20_movies.png'))
    plt.close()

    # 4. Top 20 Highest Rated Movies (min 50 ratings)
    print("📈 Generating Top 20 Highest Rated Movies plot...")
    # Calculate avg rating and count
    movie_stats = ratings.groupby('movieId').agg({'rating': ['mean', 'count']})
    movie_stats.columns = ['avg_rating', 'num_ratings']
    
    # Filter for movies with significant number of ratings (e.g., > 50)
    # Using a threshold to avoid 1-rating 5-star movies
    min_ratings = 50
    popular_movies = movie_stats[movie_stats['num_ratings'] >= min_ratings]
    
    top_rated = popular_movies.nlargest(20, 'avg_rating').reset_index()
    top_rated = top_rated.merge(movies[['movieId', 'title']], on='movieId')
    
    plt.figure(figsize=(12, 8))
    sns.barplot(data=top_rated, y='title', x='avg_rating', palette='coolwarm')
    plt.title(f'Top 20 Highest Rated Movies (min {min_ratings} ratings)', fontsize=16, fontweight='bold')
    plt.xlabel('Average Rating', fontsize=12)
    plt.ylabel('Movie Title', fontsize=12)
    plt.xlim(3, 5)  # Focus on the top range
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_PATH, 'top_20_highest_rated.png'))
    plt.close()
    
    # 5. Genre Analysis
    print("📈 Generating Genre Analysis plot...")
    all_genres = []
    for genres_str in movies['genres']:
        if pd.notna(genres_str):
            all_genres.extend(genres_str.split('|'))
    genre_counts = pd.Series(all_genres).value_counts()
    
    plt.figure(figsize=(12, 8))
    genre_counts.head(20).plot(kind='barh', color='teal')
    plt.title('Top 20 Movie Genres', fontsize=16, fontweight='bold')
    plt.xlabel('Number of Movies', fontsize=12)
    plt.ylabel('Genre', fontsize=12)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_PATH, 'genre_distribution.png'))
    plt.close()

    # Save summary stats
    print("💾 Saving summary statistics...")
    num_users = ratings['userId'].nunique()
    num_movies = ratings['movieId'].nunique()
    num_ratings = len(ratings)
    
    summary = {
        'num_users': int(num_users),
        'num_movies': int(num_movies),
        'num_ratings': int(num_ratings),
        'avg_rating': float(ratings['rating'].mean()),
        'sparsity': float((1 - num_ratings / (num_users * num_movies)) * 100),
        'top_genres': genre_counts.head(10).to_dict(),
        'date_range': f"{ratings['datetime'].min()} to {ratings['datetime'].max()}"
    }
    
    with open(os.path.join(PROCESSED_PATH, 'eda_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2, default=str)
        
    print(f"✅ EDA Complete! Visualizations saved to {VIS_PATH}")

if __name__ == "__main__":
    run_eda()
