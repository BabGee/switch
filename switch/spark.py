import pyspark
import socket

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *


sock_name = socket.gethostname()
host = socket.gethostbyname(sock_name)

conf = pyspark.SparkConf()\
        .setAll([
            ('spark.driver.host', host),
            ("spark.cassandra.connection.host", "cassandra-0-service"),
            ])


#.config("spark.jars.packages", 
#        "")\
#"org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1,com.datastax.spark:spark-cassandra-connector_2.12:3.0.1,io.delta:delta-core_2.12:1.0.0")\
#                .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")\
#                .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")\

app = SparkSession.builder\
                .master("spark://spark-master:7077")\
                .config("spark.jars.packages", 
                        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.1,com.datastax.spark:spark-cassandra-connector_2.12:3.0.1")\
                .config(conf=conf)\
                .appName('switch-faust')\
                .getOrCreate()
