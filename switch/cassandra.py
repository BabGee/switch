import cassandra

from cassandra.cluster import Cluster
cluster = Cluster(['cassandra-0-service'])

session = cluster.connect()
session = _cassandra
session.set_keyspace('notify')
app = session
