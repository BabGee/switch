from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'switch.settings')

app = Celery('switch')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')


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
		'secondary.channels.notify.tasks.send_bulk_sms': {'queue': 'commandline1','routing_key':'commandline1'}, 
		'secondary.channels.notify.tasks.send_outbound_sms_messages': {'queue': 'sms','routing_key':'sms'}, 
		'secondary.channels.notify.tasks.send_outbound': {'queue': 'spawned_sms','routing_key':'spawned_sms'}, 
		'secondary.channels.notify.tasks.send_outbound_email_messages': {'queue': 'email','routing_key':'email'}, 
		'secondary.channels.dsc.tasks.process_file_upload_activity': {'queue': 'files','routing_key':'files'},
		'secondary.channels.notify.tasks.add_bulk_contact': {'queue': 'commandline','routing_key':'commandline'},
		'secondary.channels.notify.tasks.add_gateway_bulk_contact': {'queue': 'commandline1','routing_key':'commandline1'},
		'secondary.finance.paygate.tasks.send_paygate_outgoing': {'queue': 'payments','routing_key':'payments'},
		'secondary.finance.paygate.tasks.process_incoming_payments': {'queue': 'payments','routing_key':'payments'},
		'secondary.channels.dsc.tasks.process_file_upload': {'queue': 'files','routing_key':'files'},
		'secondary.channels.notify.tasks.service_call': {'queue': 'services','routing_key':'services'},
		'primary.core.bridge.tasks.background_service_call': {'queue': 'services','routing_key':'services'},
		'primary.core.bridge.tasks.process_background_service_call': {'queue': 'services','routing_key':'services'},
		'primary.core.bridge.tasks.process_background_service': {'queue': 'services','routing_key':'services'},
		'secondary.finance.crb.tasks.reference_activity_service_call': {'queue': 'services','routing_key':'services'},
		'secondary.finance.crb.tasks.process_reference_activity': {'queue': 'commandline','routing_key':'commandline'},
		'secondary.channels.dsc.tasks.process_push_request': {'queue': 'push_request','routing_key':'push_request'},
		}


app.conf.task_queues = (
    Queue('celery', Exchange('celery'), routing_key='celery', delivery_mode=1),
    Queue('commandline', Exchange('commandline'), routing_key='commandline', delivery_mode=1),
    Queue('commandline1', Exchange('commandline1'), routing_key='commandline1', delivery_mode=1),
    Queue('sms', Exchange('sms'), routing_key='sms', delivery_mode=1),
    Queue('spawned_sms', Exchange('spawned_sms'), routing_key='spawned_sms', delivery_mode=1),
    Queue('email', Exchange('email'), routing_key='email', delivery_mode=1),
    Queue('files', Exchange('files'), routing_key='files', delivery_mode=1),
    Queue('payments', Exchange('payments'), routing_key='payments', delivery_mode=1),
    Queue('services', Exchange('services'), routing_key='services', delivery_mode=1),
    Queue('push_request', Exchange('push_request'), routing_key='push_request', delivery_mode=1),

)

app.conf.task_default_queue = 'celery'
app.conf.task_default_exchange_type = 'celery'
app.conf.task_default_routing_key = 'celery'
