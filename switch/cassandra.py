from cassandra.cqlengine import connection
from cassandra.cqlengine.connection import session
from cassandra.cqlengine import connection
from cassandra.cqlengine.connection import (
    cluster as cql_cluster, session as cql_session)

def cassandra_init(**kwargs):
	""" Initialize a clean Cassandra connection. """
	if cql_cluster is not None:
		cql_cluster.shutdown()
	if cql_session is not None:
		cql_session.shutdown()
	#connection.setup()
	connection.setup(['cassandra-0-service'], "notify")

