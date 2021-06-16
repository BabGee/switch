from __future__ import absolute_import, unicode_literals
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app
from .faust import app as faust_app
from .kafka import app as kafka_app
from .spark import app as spark_app
#from .cassandra import app as cassandra_app

__all__ = ('celery_app','faust_app', 'kafka_app', 'spark_app',)
#__all__ = ('celery_app','faust_app', 'kafka_app', 'spark_app','cassandra_app',)
