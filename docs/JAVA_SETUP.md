# Java Installation and Setup Guide for Apache Spark

This guide will help you install Java (required for Apache Spark) on your system.

## Quick Installation

### For Arch Linux / Manjaro
```bash
# Install OpenJDK 11 (recommended for Spark)
sudo pacman -S jre11-openjdk

# Set JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
export PATH=$JAVA_HOME/bin:$PATH

# Make it permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk' >> ~/.zshrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

### For Ubuntu/Debian
```bash
# Install OpenJDK 11
sudo apt update
sudo apt install openjdk-11-jdk

# Set JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# Make it permanent
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### For macOS
```bash
# Install using Homebrew
brew install openjdk@11

# Set JAVA_HOME
export JAVA_HOME=/usr/local/opt/openjdk@11
export PATH=$JAVA_HOME/bin:$PATH

# Make it permanent
echo 'export JAVA_HOME=/usr/local/opt/openjdk@11' >> ~/.zshrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

## Verification

After installation, verify Java is working:

```bash
java -version
echo $JAVA_HOME
```

You should see output like:
```
openjdk version "11.0.x"
/usr/lib/jvm/java-11-openjdk
```

## Test Spark

Once Java is installed, test Spark:

```bash
cd /home/k0der/Atlas/Projects/StreamLens
source venv/bin/activate
python -c "from pyspark.sql import SparkSession; spark = SparkSession.builder.appName('test').master('local[*]').getOrCreate(); print('✅ Spark Version:', spark.version); spark.stop()"
```

## Run Preprocessing

After Java setup, run the preprocessing pipeline:

```bash
# Activate virtual environment
source venv/bin/activate

# Run preprocessing
python src/data/preprocessing.py

# Run feature engineering
python src/data/feature_engineering.py
```

## Troubleshooting

### Issue: "JAVA_HOME is not set"
```bash
# Find Java installation
which java
# or
readlink -f $(which java)

# Set JAVA_HOME to the directory containing bin/java
export JAVA_HOME=/path/to/java/home
```

### Issue: Spark fails with memory errors
Reduce memory allocation in `config/spark_config.py`:
```python
conf.set("spark.driver.memory", "2g")  # Reduce from 4g
conf.set("spark.executor.memory", "2g")
```

### Issue: Permission denied
```bash
# Make scripts executable
chmod +x src/data/preprocessing.py
chmod +x src/data/feature_engineering.py
```
