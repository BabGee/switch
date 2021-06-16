from cassandra.cqlengine import connection
from cassandra.cqlengine.connection import session

connection.setup(['cassandra-0-service'], "notify")

app = session
