from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'switch.settings')

app = Celery('switch')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


from django.core.cache import cache
import functools

def single_instance_task(timeout):
    def task_exc(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            lock_id = "celery-single-instance-" + func.__name__
            acquire_lock = lambda: cache.add(lock_id, "true", timeout)
            release_lock = lambda: cache.delete(lock_id)
            if acquire_lock():
                try:
                    func(*args, **kwargs)
                finally:
                    release_lock()
        return wrapper
    return task_exc

from kombu import Exchange, Queue

app.conf.task_routes = {
		'notify.tasks.send_bulk_sms': {'queue': 'commandline1','routing_key':'commandline1'}, 
		'notify.tasks.send_outbound_sms_messages': {'queue': 'messages','routing_key':'messages'}, 
		'notify.tasks.send_outbound': {'queue': 'messages1','routing_key':'messages1'}, 
		'notify.tasks.send_outbound_email_messages': {'queue': 'messages2','routing_key':'messages2'}, 
		'dsc.tasks.process_file_upload_activity': {'queue': 'files','routing_key':'files'},
		'notify.tasks.add_bulk_contact': {'queue': 'commandline','routing_key':'commandline'},
		'notify.tasks.add_gateway_bulk_contact': {'queue': 'commandline1','routing_key':'commandline1'},
		'paygate.tasks.send_paygate_outgoing': {'queue': 'payments','routing_key':'payments'},
		'paygate.tasks.process_incoming_payments': {'queue': 'payments','routing_key':'payments'},
		'dsc.tasks.process_file_upload': {'queue': 'files','routing_key':'files'},
		'notify.tasks.service_call': {'queue': 'services','routing_key':'services'},
		'dsc.tasks.process_push_notification': {'queue': 'push_notification','routing_key':'push_notification'},
		}


app.conf.task_queues = (
    Queue('celery', Exchange('celery'), routing_key='celery', delivery_mode=1),
    Queue('commandline', Exchange('commandline'), routing_key='commandline', delivery_mode=1),
    Queue('commandline1', Exchange('commandline1'), routing_key='commandline1', delivery_mode=1),
    Queue('messages', Exchange('messages'), routing_key='messages', delivery_mode=1),
    Queue('messages1', Exchange('messages1'), routing_key='messages1', delivery_mode=1),
    Queue('messages2', Exchange('messages2'), routing_key='messages2', delivery_mode=1),
    Queue('files', Exchange('files'), routing_key='files', delivery_mode=1),
    Queue('payments', Exchange('payments'), routing_key='payments', delivery_mode=1),
    Queue('services', Exchange('services'), routing_key='services', delivery_mode=1),
    Queue('push_notification', Exchange('push_notification'), routing_key='push_notification', delivery_mode=1),

)

app.conf.task_default_queue = 'celery'
app.conf.task_default_exchange_type = 'celery'
app.conf.task_default_routing_key = 'celery'
