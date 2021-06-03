#import pyspark
#import socket
#
#from pyspark.sql import SparkSession
#
#sock_name = socket.gethostname()
#host = socket.gethostbyname(sock_name)
#
#conf = pyspark.SparkConf()\
#        .setAll([
#            ('spark.executor.memory', '1g'), 
#            ('spark.executor.cores', '1'), 
#            ('spark.driver.host', host),
#            ("spark.shuffle.service.enabled", "false"),
#            ("spark.dynamicAllocation.enabled", "false"),
#            ('spark.cores.max', '1'), 
#            ('spark.driver.memory','1g'),
#            ("spark.cassandra.connection.host", "cassandra-0-service"),
#            ])
#
#app = SparkSession.builder\
#                .master("spark://spark-master:7077")\
#                .config("spark.jars.packages", 
#                        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.1,com.datastax.spark:spark-cassandra-connector_2.12:3.0.1")\
#                .config(conf=conf)\
#		.config("spark.ui.port", 4040) \
#                .appName('switch-spark')\
#                .getOrCreate()
#


app = None
