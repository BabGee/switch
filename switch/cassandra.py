from cassandra.cqlengine import connection
from cassandra.cqlengine.connection import (
    cluster as cql_cluster, session as cql_session)

connection.setup(['cassandra-0-service'], "notify")

app = session
