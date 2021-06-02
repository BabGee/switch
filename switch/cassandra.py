import cassandra

from cassandra.cluster import Cluster
cluster = Cluster(['cassandra-0-service'])

app = cluster.connect()

