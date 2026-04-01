# StreamLens — Context-Aware Movie Recommendation System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikit-learn&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

A hybrid recommendation engine that suggests movies based on user preferences, ratings, and contextual factors like mood, time of day, and social setting — with movie posters powered by TMDB.

## 🎯 Project Overview

**Academic Project**: 4th Semester College Project  
**Timeline**: 8 weeks  
**Dataset**: MovieLens ml-latest (86k movies, 33M ratings, 330k users)

> **Note**: The raw dataset (~1.3 GB) and trained model files (~820 MB) are not included in this repository. See [Quick Start](#-quick-start) for instructions on downloading the data and training the models from scratch.

## 🚀 Features

- **Context-Aware Recommendations** — incorporates mood, time of day, and social setting
- **Hybrid Recommendation Engine** — Content-Based (TF-IDF) + Collaborative Filtering (SVD)
- **Vectorized Genre Scoring** — precomputed genre matrix + NumPy dot products for fast recommendations
- **Rating-Aware Scoring** — blends global movie ratings into personalised picks
- **Movie Posters** — TMDB integration with local JSON caching
- **Interactive Web Interface** — Streamlit frontend with dark UI and sidebar navigation
- **Big Data Processing** — Apache Spark pipeline (with Pandas fallback)
- **Data Visualisation** — EDA charts (genre distribution, rating trends, top movies)

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.9+ |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Streamlit |
| **ML** | scikit-learn (TF-IDF, SVD), implicit (ALS) |
| **Data** | pandas, NumPy, PySpark (optional) |
| **Posters** | TMDB API |
| **Visualisation** | Matplotlib, Seaborn |

## 📂 Project Structure

```
StreamLens/
├── config/                        # Configuration
│   └── spark_config.py           # Spark session helper
├── data/                          # Datasets (gitignored — see Quick Start)
│   ├── raw/ml-latest/            # MovieLens raw CSVs (~1.3 GB, not committed)
│   ├── processed/                # Preprocessed data + poster cache
│   └── external/                 # External API data
├── src/                           # Source code
│   ├── data/                     # Data pipeline
│   │   ├── ingestion.py          # Download MovieLens dataset
│   │   ├── preprocessing.py      # Spark-based preprocessing
│   │   ├── pandas_preprocessing.py  # Pandas-based preprocessing
│   │   ├── feature_engineering.py   # Spark feature engineering
│   │   └── run_eda.py            # Generate EDA visualisations
│   ├── models/                   # Recommendation models
│   │   ├── content_based.py      # TF-IDF + cosine similarity
│   │   ├── collaborative_filtering.py  # SVD / ALS
│   │   ├── hybrid.py             # Weighted CB + CF blend
│   │   ├── evaluate.py           # RMSE, Precision@K, NDCG@K
│   │   └── train_models.py       # Training pipeline
│   └── api/                      # FastAPI backend
│       ├── main.py               # App entry point (auto-loads .env)
│       ├── model_loader.py       # Singleton model store + genre matrix
│       ├── tmdb.py               # TMDB poster service with JSON cache
│       └── routers/
│           ├── movies.py         # Browse / search endpoints
│           └── recommendations.py  # Recommendation endpoints
├── frontend/                      # Streamlit web app
│   └── app.py                    # UI (profile, For You, Browse, Rate)
├── models/                        # Trained model files (.pkl — gitignored)
├── tests/                         # Unit tests (pytest)
│   ├── test_api.py
│   └── test_models.py
├── visualizations/eda/            # Generated EDA charts
├── notebooks/                     # Jupyter exploration notebooks
├── docs/                          # Documentation
│   ├── SETUP.md                  # Detailed setup walkthrough
│   ├── JAVA_SETUP.md             # Java setup for Apache Spark
│   └── recommendation_system_report.md  # Academic evaluation report
├── requirements.txt
├── setup.py                       # pip install -e . support
├── .env.example                   # Template — copy to .env and fill in keys
├── LICENSE
└── README.md
```

## 🔧 Quick Start

### 1. Setup

```bash
git clone <repository-url>
cd StreamLens
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Download & Process Data

```bash
python src/data/ingestion.py
python src/data/pandas_preprocessing.py
python src/data/run_eda.py
```

### 3. Train Models

```bash
python src/models/train_models.py
```

> ⚠️ Training the content-based model on the full MovieLens dataset requires ~8 GB RAM and ~30 minutes. The resulting `.pkl` files (~820 MB total) are not committed to this repo.

### 4. Configure TMDB (for movie posters)

```bash
cp .env.example .env
# Edit .env → set TMDB_API_KEY (free at themoviedb.org)
```

The API server auto-loads `.env` at startup — no `export` commands needed.

### 5. Run

```bash
# Terminal 1 — API server
source venv/bin/activate
python -m uvicorn src.api.main:app --port 8000 --reload

# Terminal 2 — Frontend
source venv/bin/activate
streamlit run frontend/app.py
```

API docs: `http://localhost:8000/docs`  
Frontend: `http://localhost:8501`

## 🧪 Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## ⚡ Performance

The personalized recommendation endpoint uses a **precomputed binary genre matrix** (built once at startup) and **NumPy dot products** to score all 86k movies in milliseconds. Response time targets:

| Operation | Time |
|-----------|------|
| Cold start (model loading) | ~60s |
| Personalized recs (no ratings) | ~0.08s |
| Personalized recs (10 rated movies) | ~0.25s |

## 📊 Evaluation Metrics

- **RMSE / MAE** — Rating prediction accuracy
- **Precision@K** — Relevant items in top K
- **Recall@K** — Coverage of relevant items
- **NDCG@K** — Ranking quality

## 📚 Documentation

- [PROJECT_DOCS.md](PROJECT_DOCS.md) — Complete technical documentation
- [docs/SETUP.md](docs/SETUP.md) — Detailed setup guide
- [docs/JAVA_SETUP.md](docs/JAVA_SETUP.md) — Java setup for Spark
- [docs/recommendation_system_report.md](docs/recommendation_system_report.md) — Academic evaluation report

## 🙏 Acknowledgments

- [MovieLens](https://grouplens.org/datasets/movielens/) dataset by GroupLens Research
- [TMDB](https://www.themoviedb.org/) for movie posters and metadata
- Apache Spark community

## 📄 License

This project is licensed under the [MIT License](LICENSE).
