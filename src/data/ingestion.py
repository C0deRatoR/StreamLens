"""
StreamLens Data Ingestion Module
Handles downloading and initial loading of datasets
"""

import os
import requests
import zipfile
from pathlib import Path
from typing import Optional
import pandas as pd
from loguru import logger


class DataIngestion:
    """Handle data downloading and initial loading"""
    
    def __init__(self, raw_data_path: str = "./data/raw"):
        self.raw_data_path = Path(raw_data_path)
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        
    def download_movielens(self, version: str = "ml-25m") -> Path:
        """
        Download MovieLens dataset
        
        Args:
            version: ml-25m (25 million) or ml-latest-small
        
        Returns:
            Path to extracted dataset
        """
        logger.info(f"Downloading MovieLens {version} dataset...")
        
        # MovieLens download URLs
        urls = {
            "ml-25m": "https://files.grouplens.org/datasets/movielens/ml-25m.zip",
            "ml-latest": "https://files.grouplens.org/datasets/movielens/ml-latest.zip",
            "ml-latest-small": "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
            "ml-1m": "https://files.grouplens.org/datasets/movielens/ml-1m.zip"
        }
        
        if version not in urls:
            raise ValueError(f"Version {version} not supported. Choose from {list(urls.keys())}")
        
        zip_path = self.raw_data_path / f"{version}.zip"
        extract_path = self.raw_data_path / version
        
        # Download if not exists
        if not zip_path.exists():
            logger.info(f"Downloading from {urls[version]}")
            response = requests.get(urls[version], stream=True)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.success(f"Downloaded to {zip_path}")
        else:
            logger.info(f"Dataset already downloaded at {zip_path}")
        
        # Extract if not exists
        if not extract_path.exists():
            logger.info(f"Extracting to {extract_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.raw_data_path)
            logger.success(f"Extracted to {extract_path}")
        else:
            logger.info(f"Dataset already extracted at {extract_path}")
        
        return extract_path
    
    def load_movielens_data(self, version: str = "ml-25m") -> dict:
        """
        Load MovieLens data into pandas DataFrames
        
        Returns:
            Dictionary with DataFrames: movies, ratings, tags, links
        """
        data_path = self.raw_data_path / version
        
        logger.info(f"Loading MovieLens data from {data_path}")
        
        data = {}
        
        # Load movies
        movies_path = data_path / "movies.csv"
        if movies_path.exists():
            data['movies'] = pd.read_csv(movies_path)
            logger.info(f"Loaded {len(data['movies'])} movies")
        
        # Load ratings
        ratings_path = data_path / "ratings.csv"
        if ratings_path.exists():
            data['ratings'] = pd.read_csv(ratings_path)
            logger.info(f"Loaded {len(data['ratings'])} ratings")
        
        # Load tags
        tags_path = data_path / "tags.csv"
        if tags_path.exists():
            data['tags'] = pd.read_csv(tags_path)
            logger.info(f"Loaded {len(data['tags'])} tags")
        
        # Load links (to IMDB and TMDB)
        links_path = data_path / "links.csv"
        if links_path.exists():
            data['links'] = pd.read_csv(links_path)
            logger.info(f"Loaded {len(data['links'])} links")
        
        return data
    
    def download_tmdb_kaggle(self, kaggle_path: Optional[str] = None):
        """
        Instructions for downloading TMDB dataset from Kaggle
        
        Note: This requires manual download or Kaggle API setup
        """
        logger.info("""
        To download TMDB dataset from Kaggle:
        
        1. Install Kaggle CLI: pip install kaggle
        2. Set up API credentials: https://www.kaggle.com/docs/api
        3. Download dataset:
           kaggle datasets download -d tmdb/tmdb-movie-metadata
        4. Extract to data/raw/tmdb/
        
        Or download manually from:
        https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata
        """)
        
        if kaggle_path:
            logger.info(f"Expected Kaggle dataset at: {kaggle_path}")


if __name__ == "__main__":
    # Example usage
    ingestion = DataIngestion()
    
    # Download and load MovieLens
    ingestion.download_movielens(version="ml-latest")
    data = ingestion.load_movielens_data(version="ml-latest")
    
    # Show basic info
    for name, df in data.items():
        print(f"\n{name.upper()}:")
        print(df.head())
        print(f"Shape: {df.shape}")
