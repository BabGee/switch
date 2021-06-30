import os, sys
import faust
# make sure the gevent event loop is used as early as possible.
os.environ.setdefault('FAUST_LOOP', 'eventlet')

# set the default Django settings module for the 'faust' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'switch.settings')

# set for models to run on async
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

#app = faust.App('django-switch', autodiscover=False, origin='faustapp')
app = faust.App('switch-faust', topic_partitions=4, autodiscover=True, origin='switch')
#app = faust.App('switch-faust', topic_partitions=4, autodiscover=True)

@app.on_configured.connect
def configure_from_settings(app, conf, **kwargs):
    from django.conf import settings
    conf.broker = settings.FAUST_BROKER_URL
    conf.store = settings.FAUST_STORE_URL

