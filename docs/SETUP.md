# StreamLens Setup Guide

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Java 8 or 11** - Required for Apache Spark
- **Git** - [Download](https://git-scm.com/downloads)
- **PostgreSQL** - [Download](https://www.postgresql.org/download/)

## Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd StreamLens
```

## Step 2: Create Virtual Environment

**On Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

## Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install all required packages including:
- Apache Spark (PySpark)
- FastAPI
- Pandas, NumPy, Scikit-learn
- Surprise, LightFM (recommendation libraries)
- Visualization tools (Matplotlib, Seaborn, Plotly)

## Step 4: Verify Java Installation (for Spark)

Apache Spark requires Java 8 or 11. Verify your installation:

```bash
java -version
```

**If Java is not installed:**

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install openjdk-11-jdk
```

**macOS:**
```bash
brew install openjdk@11
```

**Windows:**
Download from [Oracle](https://www.oracle.com/java/technologies/downloads/) or [Adoptium](https://adoptium.net/)

## Step 5: Verify Spark Installation

```bash
python -c "from pyspark.sql import SparkSession; spark = SparkSession.builder.appName('test').master('local[1]').getOrCreate(); print('Spark version:', spark.version); spark.stop()"
```

You should see the Spark version printed (e.g., "Spark version: 3.5.0")

## Step 6: Download NLTK Data (for text processing)

```bash
python -m nltk.downloader punkt stopwords
```

## Step 7: Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your configuration:

```bash
# Example .env configuration
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/streamlens
TMDB_API_KEY=your_api_key_here
```

**Get TMDB API Key:**
1. Sign up at https://www.themoviedb.org/
2. Go to Settings → API
3. Request an API key (free)

## Step 8: Set Up PostgreSQL Database

**Create database:**
```bash
createdb streamlens
```

Or using SQL:
```sql
CREATE DATABASE streamlens;
```

## Step 9: Download Datasets

### MovieLens Dataset

You can use the built-in data ingestion script:

```bash
python src/data/ingestion.py
```

Or download manually:
- **Small version (for testing)**: https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
- **25M version (for production)**: https://files.grouplens.org/datasets/movielens/ml-25m.zip

Extract to `data/raw/ml-latest-small/` or `data/raw/ml-25m/`

### TMDB Dataset from Kaggle

**Option 1: Kaggle CLI**
```bash
pip install kaggle
# Configure Kaggle API credentials (see https://www.kaggle.com/docs/api)
kaggle datasets download -d tmdb/tmdb-movie-metadata
unzip tmdb-movie-metadata.zip -d data/raw/tmdb/
```

**Option 2: Manual Download**
1. Visit https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata
2. Download the dataset
3. Extract to `data/raw/tmdb/`

## Step 10: Verify Installation

Run the test script to verify everything is working:

```bash
python -c "
import pandas as pd
import numpy as np
from pyspark.sql import SparkSession
import sklearn
import surprise
import fastapi
print('✓ All core libraries imported successfully!')
print(f'✓ Pandas: {pd.__version__}')
print(f'✓ NumPy: {np.__version__}')
print(f'✓ Scikit-learn: {sklearn.__version__}')
print('✓ Setup complete!')
"
```

## Step 11: Run Jupyter Notebook (Optional)

```bash
jupyter notebook
```

This will open Jupyter in your browser for exploratory data analysis.

## Troubleshooting

### Issue: "JAVA_HOME is not set"

**Linux/Mac:**
```bash
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
```

Add to `~/.bashrc` or `~/.zshrc` to make permanent.

**Windows:**
1. Find Java installation path (e.g., `C:\Program Files\Java\jdk-11`)
2. Set environment variable: `JAVA_HOME=C:\Program Files\Java\jdk-11`
3. Add `%JAVA_HOME%\bin` to PATH

### Issue: "psycopg2 failed to install"

**Linux:**
```bash
sudo apt-get install libpq-dev python3-dev
pip install psycopg2-binary
```

**Mac:**
```bash
brew install postgresql
pip install psycopg2-binary
```

### Issue: Spark fails to start

1. Check Java version: `java -version` (should be 8 or 11)
2. Check JAVA_HOME: `echo $JAVA_HOME`
3. Try smaller memory allocation in `config/spark_config.py`

### Issue: Dataset download fails

- Check internet connection
- Try downloading manually from the provided URLs
- For MovieLens, mirrors are available at https://grouplens.org/datasets/movielens/

## Next Steps

Once setup is complete:

1. **Explore the data**: Open `notebooks/01_data_exploration.ipynb`
2. **Read the documentation**: Check `docs/` folder
3. **Start developing**: Follow the implementation phases in the project overview

## Development Workflow

Always work on feature branches:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
# Make changes
git add .
git commit -m "Description of changes"
git push origin feature/your-feature-name
```

## Getting Help

- Check `README.md` for project overview
- See `docs/` for detailed documentation
- Contact your team members or instructor

---

**Setup Complete! 🎉**

You're ready to start building StreamLens!
