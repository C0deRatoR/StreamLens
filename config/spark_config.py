"""
Spark Configuration for StreamLens
"""

from pyspark import SparkConf

def get_spark_config(app_name="StreamLens", local_mode=True):
    """
    Get Spark configuration for the application.
    
    Args:
        app_name: Name of the Spark application
        local_mode: If True, run in local mode. If False, configure for cluster.
    
    Returns:
        SparkConf object
    """
    conf = SparkConf()
    conf.setAppName(app_name)
    
    if local_mode:
        # Local mode configuration for development
        conf.setMaster("local[*]")  # Use all available cores
        conf.set("spark.driver.memory", "4g")
        conf.set("spark.executor.memory", "4g")
    else:
        # Cluster mode configuration (adjust based on your cluster)
        conf.setMaster("spark://your-master:7077")
        conf.set("spark.driver.memory", "8g")
        conf.set("spark.executor.memory", "8g")
        conf.set("spark.executor.instances", "4")
    
    # Common configurations
    conf.set("spark.sql.shuffle.partitions", "200")
    conf.set("spark.default.parallelism", "100")
    conf.set("spark.sql.adaptive.enabled", "true")
    conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    # Serialization
    conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    
    # UI and logging
    conf.set("spark.ui.showConsoleProgress", "true")
    conf.set("spark.eventLog.enabled", "false")
    
    return conf


# Quick access configurations
LOCAL_CONFIG = get_spark_config(local_mode=True)
CLUSTER_CONFIG = get_spark_config(local_mode=False)
