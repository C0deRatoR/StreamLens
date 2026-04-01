# StreamLens — Complete Project Documentation

> **Context-Aware Movie Recommendation System**
> A hybrid recommendation engine that blends user preferences, contextual signals (mood, time, social setting), content similarity, collaborative filtering, and global movie ratings to deliver personalised movie suggestions.

---

## Table of Contents

1. [How It All Works — End to End](#how-it-all-works--end-to-end)
2. [Architecture Overview](#architecture-overview)
3. [Complete Folder & File Reference](#complete-folder--file-reference)
4. [The Recommendation Engine — In Depth](#the-recommendation-engine--in-depth)
5. [How to Run the Project](#how-to-run-the-project)

---

## How It All Works — End to End

StreamLens follows a classic **data → preprocess → train → serve → display** pipeline. Here is every step, in order:

### Step 1 — Data Ingestion

The raw data comes from the **MovieLens "ml-latest"** dataset (≈33M ratings, ≈86k movies, ≈1.1M tags, ≈330k users). The ingestion script (`src/data/ingestion.py`) downloads and extracts the zip from the [GroupLens website](https://files.grouplens.org/datasets/movielens/) into `data/raw/ml-latest/`.

**Raw CSV files loaded:**

| File | Contents |
|------|----------|
| `movies.csv` | `movieId`, `title`, `genres` (pipe-separated) |
| `ratings.csv` | `userId`, `movieId`, `rating` (0.5–5.0), `timestamp` |
| `tags.csv` | `userId`, `movieId`, `tag`, `timestamp` |
| `links.csv` | `movieId`, `imdbId`, `tmdbId` (external links) |

### Step 2 — Preprocessing & EDA

Two preprocessing paths exist (Spark and Pandas) — the **Pandas path** (`src/data/pandas_preprocessing.py`) is the primary one used:

1. **Load** all four CSV files.
2. **Clean movies**: extract release year from titles, split genres into arrays, create one-hot genre columns.
3. **Clean ratings**: convert Unix timestamps to datetime, extract temporal features (hour, day of week, month, season, time-of-day).
4. **Aggregate movie stats**: per-movie average rating, rating count, rating variance, popularity score.
5. **Aggregate user stats**: per-user average rating, count, standard deviation.
6. **Create popularity features**: Bayesian average rating (weighted by global mean), trending scores.
7. **User genre preferences**: for each user, compute weighted genre preference based on their rating history.
8. **Save** processed CSVs to `data/processed/`.

The **EDA script** (`src/data/run_eda.py`) generates 5 visualisation plots saved to `visualizations/eda/`:

- Rating distribution histogram
- Ratings over time (bar chart by year)
- Top 20 most-rated movies
- Top 20 highest-rated movies (min 50 ratings)
- Genre distribution

An `eda_summary.json` is also generated with overall dataset statistics (number of users, movies, sparsity, etc.).

### Step 3 — Model Training

The training pipeline (`src/models/train_models.py`) trains three models:

#### 3a. Content-Based Filtering (CB)

- **How it works**: TF-IDF vectorisation on each movie's combined genre string + user tags → stores the **sparse TF-IDF matrix** and computes cosine similarity **on demand** (one row at a time). For small datasets (<15k movies) the full similarity matrix is precomputed; for large datasets like ml-latest (86k movies) it is computed per-query to avoid the ~56 GiB memory cost of a dense N×N matrix.
- **Input**: movie genres and optional tags.
- **Output**: for any given movie, returns the most similar movies ranked by cosine similarity.
- **Key file**: `src/models/content_based.py`

#### 3b. Collaborative Filtering (CF)

- **How it works**: Constructs a user-item rating matrix → decomposes it using Truncated SVD (or ALS via the `implicit` library if available) → predicts unseen ratings.
- **Input**: user–movie–rating triples.
- **Output**: for any given user, returns movies they haven't seen ranked by predicted rating.
- **Key file**: `src/models/collaborative_filtering.py`

#### 3c. Hybrid Recommender

- **How it works**: Combines CB and CF with configurable weights (default: 30% CB, 70% CF). For a given user, it gets CF recommendations + CB recommendations based on the user's top-rated movies, normalises both score sets to [0, 1], and computes a weighted average.
- **Key file**: `src/models/hybrid.py`

#### 3d. Evaluation

- **Metrics**: RMSE, MAE (rating accuracy), Precision@K, Recall@K, NDCG@K (ranking quality).
- **Method**: Train/test split (80/20), evaluate all three models, save results to `data/processed/evaluation_results.csv`.
- **Key file**: `src/models/evaluate.py`

After training, models are serialised to `models/` as `.pkl` files using `joblib`. Only `collaborative_model.pkl` (≈5MB) is actually loaded from disk — the CB and Hybrid models are rebuilt from raw data at API startup (faster than loading the ≈729MB+ pkl files).

### Step 4 — API Server (FastAPI)

The API (`src/api/main.py`) starts a FastAPI server that:

1. **On startup** (`model_loader.py`): loads raw data + `links.csv` (for TMDB IDs), pre-aggregates per-movie rating stats (so endpoints don't groupby 33M rows per request), **precomputes a binary genre matrix** (n_movies × n_genres, stored as NumPy float32 array), rebuilds the CB model from scratch (sparse TF-IDF matrix), loads the CF model from pkl, constructs the Hybrid model.
2. **Poster service** (`tmdb.py`): fetches movie poster URLs from the TMDB API with a local JSON cache (`data/processed/poster_cache.json`). Posters are batch-fetched and cached — subsequent requests are instant.
3. **Exposes endpoints** via two routers (all movie responses include `poster_url` when a TMDB API key is configured):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/movies/genres` | GET | List all unique genres |
| `/movies/search?q=...` | GET | Search movies by title (with poster URLs) |
| `/movies/{id}` | GET | Movie details with rating stats and poster |
| `/recommendations/user/{id}` | GET | Hybrid/CF/CB recommendations for a known user |
| `/recommendations/movie/{id}` | GET | Content-similar movies |
| `/recommendations/top` | GET | Top movies by popularity or rating |
| `/recommendations/personalized` | POST | **Main endpoint** — context-aware personalised picks |
| `/health` | GET | API and model health status |

### Step 5 — Personalised Recommendation Scoring (the core algorithm)

When a user hits **`POST /recommendations/personalized`**, the system scores every movie in the database using three components:

```
final_score = genre_score + cb_boost + rating_boost
```

| Component | What it measures | How it's calculated |
|-----------|-----------------|---------------------|
| **genre_score** | "Matches your taste" | Genre weights are built into a vector and scored via a **matrix-vector dot product** (`genre_matrix @ weight_vector`) over the precomputed binary genre matrix — scoring all 86k movies in milliseconds without any Python loops. |
| **cb_boost** | "Similar to what you liked" | For each movie the user has rated, the TF-IDF cosine similarity to every other movie is computed. Results are accumulated as a NumPy array (not Pandas series) to avoid indexing overhead. The boost is normalised to match the genre_score range. |
| **rating_boost** | "Actually highly rated" | Aggregates global average rating from all users (min 5 reviews to filter noise). The avg rating is normalised to [0, 1] and scaled to 40% of the genre_score range — so quality influences ranking without overpowering personal taste. |

Already-rated movies are excluded. The top-K results are normalised to [0, 1] and returned to the frontend.

### Step 6 — Frontend (Streamlit)

The Streamlit app (`frontend/app.py`) provides three pages:

1. **🎯 For You** — Profile setup (name, age, preferred genres, context), then personalised recommendations with **movie poster images**, match-score bars, star ratings, and "Show More" pagination.
2. **🔍 Browse** — Search movies by title, view details with posters, rate inline.
3. **⭐ Rate Movies** — Rate movies to influence future recommendations.

Movie cards display TMDB poster images (with a gradient placeholder fallback when no poster is available). Results default to 10 per page with a "Show More" button to load 10 more at a time.

On first visit, users set up their profile (genres, mood, time, social setting). Context can be adjusted anytime from the sidebar.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                     │
│              (frontend/app.py, port 8501)                │
│  Profile Setup │ For You │ Browse │ Rate Movies          │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (JSON)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                        │
│               (src/api/main.py, port 8000)               │
│                                                           │
│  ┌─────────────┐  ┌──────────────────────┐               │
│  │   Movies     │  │  Recommendations     │               │
│  │   Router     │  │  Router              │               │
│  │             │  │                      │               │
│  │ /genres     │  │ /personalized (POST) │               │
│  │ /search     │  │ /user/{id}           │               │
│  │ /{movie_id} │  │ /movie/{id}          │               │
│  │             │  │ /top                 │               │
│  └─────────────┘  └──────────────────────┘               │
│                                                           │
│  ┌───────────────────────────────────────────┐           │
│  │            MODEL STORE (Singleton)         │           │
│  │  • CB Model  (sparse TF-IDF, on-demand)    │           │
│  │  • CF Model  (loaded from pkl)             │           │
│  │  • Hybrid    (wraps CB + CF)               │           │
│  │  • rating_stats (pre-aggregated)           │           │
│  │  • movies_df + tmdbId, ratings_df, tags_df │           │
│  └───────────────────────────────────────────┘           │
│                                                           │
│  ┌───────────────────────────────────────────┐           │
│  │        TMDB POSTER SERVICE (Cache)         │           │
│  │  • Fetches poster URLs from TMDB API       │           │
│  │  • Caches to poster_cache.json             │           │
│  └───────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                             │
│                                                           │
│  data/raw/ml-latest/         ←  MovieLens dataset         │
│  data/processed/             ←  Preprocessed CSVs         │
│  models/                     ←  Trained model pkl files    │
│  visualizations/eda/         ←  EDA charts (PNG)          │
└─────────────────────────────────────────────────────────┘
```

---

## Complete Folder & File Reference

### Root Directory

| File | Purpose |
|------|---------|
| `README.md` | Project overview, tech stack, setup instructions, team info |
| `requirements.txt` | All Python dependencies |
| `setup.py` | Package configuration for `pip install -e .` |
| `.env.example` | Template for environment variables (DB, API keys, Spark config) |
| `.gitignore` | Excludes venv, data, **pycache**, models, etc. |

---

### `config/` — Configuration

| File | Purpose |
|------|---------|
| `spark_config.py` | Apache Spark configuration helper. Provides `get_spark_config()` for local or cluster mode with memory, parallelism, and serialisation settings. Used by the Spark-based preprocessing pipeline. |

---

### `data/` — Datasets

| Path | Purpose |
|------|---------|
| `data/raw/ml-latest/` | **Raw MovieLens data** — `movies.csv`, `ratings.csv`, `tags.csv`, `links.csv`, `genome-scores.csv`, `genome-tags.csv`, `README.txt` |
| `data/processed/` | **Preprocessed outputs** — `movies_processed.csv`, `ratings_processed.csv`, `user_stats.csv`, `user_genre_prefs.csv`, `eda_summary.json`, `evaluation_results.csv`, `preprocessing_metadata.json`, `poster_cache.json` |
| `data/external/` | Placeholder for external API data (e.g. TMDB). Currently empty (`.gitkeep`). |

---

### `src/data/` — Data Processing Scripts

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package init marker |
| `ingestion.py` | 146 | **Data downloader.** `DataIngestion` class downloads MovieLens zip from GroupLens, extracts it, and loads CSVs into Pandas DataFrames. Also has TMDB/Kaggle download instructions. |
| `preprocessing.py` | 267 | **Spark-based preprocessing.** `SparkDataPreprocessor` loads data into PySpark, extracts year from titles, parses genres, converts timestamps, aggregates movie/user stats, saves to Parquet. Requires Java + PySpark. |
| `pandas_preprocessing.py` | 272 | **Pandas-based preprocessing** (primary fallback). `PandasPreprocessor` does the same pipeline without Spark: load → clean movies → clean ratings → one-hot genres → aggregate stats → popularity features → user genre preferences → save CSVs. |
| `feature_engineering.py` | 329 | **Spark feature engineering.** `FeatureEngineer` creates genre one-hot features, TF-IDF tag features, temporal context features, user genre profiles, movie age groups, popularity/trending features, and normalisation. Requires PySpark. |
| `run_eda.py` | 152 | **EDA visualisation script.** Generates 5 matplotlib/seaborn plots (rating distribution, ratings over time, top 20 most-rated, top 20 highest-rated, genre distribution) and saves `eda_summary.json`. |

---

### `src/models/` — Recommendation Models

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package init marker |
| `content_based.py` | 140 | **Content-Based Recommender.** `ContentBasedRecommender` builds a sparse TF-IDF matrix from movie genres + tags. For small datasets (<15k) precomputes a full cosine similarity matrix; for large datasets stores only the sparse TF-IDF matrix and computes similarity **on demand** via `get_similarities(idx)` — one row at a time using `linear_kernel`. |
| `collaborative_filtering.py` | 159 | **Collaborative Filtering.** `CollaborativeRecommender` constructs a sparse user-item matrix, trains either ALS (via `implicit`) or TruncatedSVD (sklearn fallback), and recommends unseen movies for a user by predicted score. Handles cold-start gracefully (returns empty DataFrame). |
| `hybrid.py` | 114 | **Hybrid Recommender.** `HybridRecommender` wraps CB + CF models. For a user, it gets CF recommendations and CB recommendations (seeded by the user's top-3 rated movies), normalises both to [0, 1], and returns a weighted combination (default: 30% CB + 70% CF). |
| `evaluate.py` | 336 | **Model Evaluator.** `ModelEvaluator` runs train/test split, evaluates all three models on RMSE, MAE, Precision@K, Recall@K, and NDCG@K. Prints comparison table and returns results as a DataFrame. |
| `train_models.py` | 139 | **Training Pipeline.** `train_and_save()` loads data, trains CB, CF, and Hybrid models, saves them as `.pkl` files via `joblib`, runs a demo recommendation for a random user, and runs the full evaluation pipeline. Entry point: `python src/models/train_models.py`. |

---

### `models/` — Serialised Model Files

| File | Size | Purpose |
|------|------|---------|
| `collaborative_model.pkl` | ≈5 MB | Trained CF model (SVD or ALS). **Loaded from disk** by the API at startup. |

> **Note:** `content_based_model.pkl` and `hybrid_model.pkl` were previously stored here (~729MB and ~744MB) but have been removed — the API rebuilds them from raw data in ≈3 seconds, which is faster than loading the massive pkl files.

---

### `src/api/` — FastAPI Backend

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package init marker |
| `main.py` | 86 | **FastAPI app entry point.** Loads `.env` file automatically at startup (no `export` needed). Configures CORS, mounts routers, loads models on startup via `lifespan`, exposes `/` and `/health` endpoints. Start with: `python -m uvicorn src.api.main:app --port 8000` |
| `model_loader.py` | 140 | **Model Store singleton.** `ModelStore.load()` reads raw CSVs, merges `tmdbId` from `links.csv`, pre-aggregates per-movie rating stats, **precomputes a binary genre matrix** `(n_movies × n_genres)` for vectorized scoring, loads `collaborative_model.pkl`, rebuilds sparse CB model from data + tags, wraps both in a Hybrid model. All routers access `store` globally. |
| `tmdb.py` | 115 | **TMDB Poster Service.** Fetches movie poster URLs from the TMDB API (requires `TMDB_API_KEY` in `.env` — auto-loaded). Caches poster paths locally to `data/processed/poster_cache.json`. Supports single and batch lookups with fetch limits to avoid blocking API responses. |

### `src/api/routers/` — API Route Handlers

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package init marker |
| `movies.py` | 95 | **Movie browsing endpoints.** `GET /movies/genres` (list all genres), `GET /movies/search?q=` (title search with poster URLs), `GET /movies/{id}` (detail with rating stats and poster). |
| `recommendations.py` | 350 | **Recommendation endpoints.** `GET /recommendations/user/{id}` (hybrid/CF/CB for known users). `GET /recommendations/movie/{id}` (similar movies). `GET /recommendations/top` (popular/highest-rated with filters, uses pre-aggregated stats). `POST /recommendations/personalized` (context-aware endpoint — uses vectorized genre dot product + NumPy CB boost accumulation + rating boost). All responses include `poster_url` when TMDB is configured. |

---

### `frontend/` — Streamlit Web App

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 990 | **Full Streamlit frontend.** Includes custom CSS (dark theme, glassmorphism, Inter font), profile setup flow, three pages (For You, Browse, Rate Movies), context controls (time/mood/social), movie cards with **TMDB poster images** (gradient placeholder fallback), genre badges, match-score bars, star ratings, and "Show More" pagination. Communicates with the FastAPI backend via HTTP. |

---

### `tests/` — Unit Tests

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 0 | Package init marker |
| `test_api.py` | — | **API integration tests.** Tests for the `/health` and `/movies` endpoints. Run with: `pytest tests/ -v` |
| `test_models.py` | 143 | **Model unit tests.** Tests for CB (fit, recommend by title/ID, error handling, genre pipe regression), CF (fit, recommend, cold-start returns empty DataFrame), and Hybrid (includes genres, handles unknown users). Run with: `pytest tests/ -v` |

---

### `notebooks/` — Jupyter Notebooks

| File | Purpose |
|------|---------|
| `01_data_exploration.ipynb` | Interactive data exploration notebook for EDA, visualisations, and data understanding. |

---

### `visualizations/eda/` — Generated Charts

| File | Purpose |
|------|---------|
| `rating_distribution.png` | Histogram of all rating values (0.5–5.0) |
| `ratings_over_time.png` | Bar chart of ratings count per year |
| `top_20_movies.png` | Top 20 most-rated movies |
| `top_20_highest_rated.png` | Top 20 highest-rated movies (min 50 ratings) |
| `genre_distribution.png` | Horizontal bar chart of genre frequency |

---

### `docs/` — Setup Documentation

| File | Purpose |
|------|---------|
| `SETUP.md` | Full setup guide — prerequisites, venv, pip install, Java/Spark verify, env vars, PostgreSQL, dataset download, troubleshooting |
| `JAVA_SETUP.md` | Java installation guide specifically for Spark (Arch, Ubuntu, macOS) |

---

## The Recommendation Engine — In Depth

### Content-Based Filtering — How TF-IDF + On-Demand Similarity Works

1. For each movie, a **content string** is constructed: genres (pipe → space) + user-generated tags.
   - Example: `"Adventure Animation Children Comedy Fantasy fun pixar"`
2. A **TF-IDF vectoriser** converts every movie's content string into a sparse vector where each dimension represents a term. TF-IDF weighs terms by frequency in the document vs. rarity across all documents — rare but descriptive terms get higher weight.
3. The resulting **sparse TF-IDF matrix** (86k × 52k) is stored. For small datasets (<15k movies) the full cosine similarity matrix is precomputed; for large datasets similarity is computed **on demand**: `linear_kernel(tfidf_matrix[idx], tfidf_matrix)` computes one row at a time (~50KB, instant).
4. To recommend: compute the similarity row for the seed movie, sort by similarity, return the top-K most similar movies (excluding itself).

### Collaborative Filtering — How SVD Works

1. A **user-item matrix** is constructed: rows = users, columns = movies, values = ratings. This matrix is extremely sparse (>98% empty for MovieLens).
2. **Truncated SVD** (or ALS via `implicit`) factorises this into low-rank matrices:
   - `User ≈ U × Σ` (user factors)
   - `Items ≈ V^T` (item factors)
3. To predict a rating: multiply the user's factor vector by the item's factor vector.
4. To recommend: predict scores for all unseen items for a user, sort by predicted score, return top-K.
5. **Cold-start handling**: if a user doesn't exist in the training data, an empty DataFrame is returned.

### Hybrid Recommender — How Blending Works

1. Get CF recommendations (top-K×2 to allow headroom).
2. Get CB recommendations: for the user's top 3 highest-rated movies, find 5 similar movies each; accumulate similarity scores (movies recommended by multiple favourites score higher).
3. Normalise both score sets to [0, 1] (min-max).
4. Compute weighted average: `final = 0.7 × CF + 0.3 × CB`.
5. Sort by final score, return top-K.

### Personalised Scoring — The Full Formula

The `POST /recommendations/personalized` endpoint scores every movie in the database:

```
final_score = genre_score + cb_boost + rating_boost
```

**genre_score** — Genre affinities are computed from:

- User's preferred genres: +3.0 per genre
- Context boosts: +1.5 per genre that matches the current time, mood, or social setting

Context → Genre mapping examples:

| Context | Boosted Genres |
|---------|---------------|
| Evening | Drama, Thriller, Romance, Mystery, Crime |
| Late Night | Horror, Thriller, Sci-Fi, Crime, Film-Noir |
| With Friends | Comedy, Action, Adventure, Sci-Fi, Fantasy |
| Date Night | Romance, Comedy, Drama, Musical |
| Adventurous Mood | Adventure, Action, Sci-Fi, Fantasy, Western |

A movie's genre_score = (sum of genre weights for its genres) / (number of genres).

**cb_boost** — For each movie the user has rated:

- Look up its row in the TF-IDF similarity matrix
- Multiply all similarities by `user_rating / 5.0` (higher-rated movies influence more)
- Accumulate across all rated movies
- Normalise to [0, max_genre_score]

**rating_boost** — Global quality signal:

- Aggregate `avg_rating` per movie from all users
- Filter: only movies with ≥5 ratings (avoids noise from obscure 5-star 1-review movies)
- Normalise avg_rating to [0, 1] via min-max
- Scale: `rating_boost = normalised_rating × max_genre_score × 0.4`
- The 0.4 weight means quality contributes ~40% as much as a perfect genre match

Finally:

- Already-rated movies are excluded
- Top-K results are normalised to [0, 1]
- Response includes `score`, `avg_rating`, `num_ratings`, and `poster_url` per movie

> **Performance note**: Rating stats are pre-aggregated at startup and the rating boost uses the cached `store.rating_stats` — no groupby on 33M rows per request. Genre scoring uses a precomputed binary matrix and NumPy dot product — no per-row Python loops. The full `/personalized` endpoint responds in ~0.08s (no ratings) to ~0.25s (10+ rated movies) on the 86k movie dataset.

---

## How to Run the Project

### 1. Initial Setup

```bash
cd StreamLens
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Download & Process Data

```bash
python src/data/ingestion.py                # Download MovieLens
python src/data/pandas_preprocessing.py     # Preprocess (Pandas)
python src/data/run_eda.py                  # Generate EDA plots
```

### 3. Train Models

```bash
python src/models/train_models.py
```

This trains Content-Based, Collaborative, and Hybrid models, saves pkl files to `models/`, and runs evaluation.

### 4. Configure TMDB Posters (optional)

```bash
cp .env.example .env
# Edit .env → set TMDB_API_KEY (free at themoviedb.org/signup)
```

### 5. Start the API

```bash
source venv/bin/activate
python -m uvicorn src.api.main:app --port 8000 --reload
```

API docs available at: `http://localhost:8000/docs`

> **Note:** The API server automatically loads `.env` at startup. No `export $(cat .env | xargs)` command is needed.

### 6. Start the Frontend

```bash
streamlit run frontend/app.py
```

Opens at: `http://localhost:8501`

### 7. Run Tests

```bash
python -m pytest tests/ -v
```
