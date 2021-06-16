from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import worker_process_init, beat_init
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'switch.settings')

app = Celery('switch')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY') #4.0

#app.config_from_object('django.conf:settings')

app.autodiscover_tasks() #4.0

#app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


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
from kombu.common import Broadcast


app.conf.task_routes = {
		'secondary.channels.notify.tasks.update_credentials': {'queue': 'bulk_notification','exchange': 'bulk_notification','routing_key':'bulk_notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.get_delivery_status': {'queue': 'bulk_notification','exchange': 'bulk_notification','routing_key':'bulk_notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.send_bulk_notification': {'queue': 'bulk_notification','exchange': 'bulk_notification','routing_key':'bulk_notification','delivery_mode': 'transient'}, #Unknown

		'secondary.channels.notify.tasks.contact_outbound_bulk_logger': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'},
		'secondary.channels.notify.tasks.recipient_outbound_bulk_logger': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'},
		'secondary.channels.notify.tasks.send_contact_unsubscription': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.contact_unsubscription': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.send_contact_subscription': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.contact_subscription': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.send_outbound_sms_messages': {'queue': 'notification','exchange': 'notification','routing_key':'notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.bulk_send_outbound_sms_messages': {'queue': 'bulk_notification','exchange': 'bulk_notification','routing_key':'bulk_notification','delivery_mode': 'transient'}, 

		'secondary.channels.notify.tasks.bulk_send_outbound_batch': {'queue': 'bulk_spawned_outbound_notification','exchange': 'bulk_spawned_outbound_notification','routing_key':'bulk_spawned_outbound_notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.bulk_send_outbound': {'queue': 'bulk_spawned_outbound_notification','exchange': 'bulk_spawned_outbound_notification','routing_key':'bulk_spawned_outbound_notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.send_outbound_batch': {'queue': 'spawned_outbound_notification','exchange': 'spawned_outbound_notification','routing_key':'spawned_outbound_notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.send_outbound': {'queue': 'spawned_outbound_notification','exchange': 'spawned_outbound_notification','routing_key':'spawned_outbound_notification','delivery_mode': 'transient'}, 

		'secondary.channels.notify.tasks.bulk_send_outbound_messages': {'queue': 'bulk_spawned_outbound_notification','exchange': 'bulk_spawned_outbound_notification','routing_key':'bulk_spawned_outbound_notification','delivery_mode': 'transient'}, 
		'secondary.channels.notify.tasks.send_outbound_messages': {'queue': 'spawned_outbound_notification','exchange': 'spawned_outbound_notification','routing_key':'spawned_outbound_notification','delivery_mode': 'transient'}, 

		'secondary.channels.notify.tasks.send_outbound_email_messages': {'queue': 'bulk_notification','exchange': 'bulk_notification','routing_key':'bulk_notification','delivery_mode': 'transient'}, 

		'secondary.channels.dsc.tasks.pre_process_file_upload': {'queue': 'files','exchange': 'files','routing_key':'files','delivery_mode': 'transient'},
		'secondary.channels.dsc.tasks.process_file_upload': {'queue': 'files','exchange': 'files','routing_key':'files','delivery_mode': 'transient'},
		'secondary.channels.dsc.tasks.process_file_upload_activity': {'queue': 'files','exchange': 'files','routing_key':'files','delivery_mode': 'transient'},
		'secondary.channels.notify.tasks.add_bulk_contact': {'queue': 'files','exchange': 'files','routing_key':'files','delivery_mode': 'transient'},
		'secondary.channels.notify.tasks.add_gateway_bulk_contact': {'queue': 'files','exchange': 'files','routing_key':'files','delivery_mode': 'transient'},

		'secondary.finance.paygate.tasks.institution_notification': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.paygate.tasks.process_float_alert': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.paygate.tasks.float_alert': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.vbs.tasks.process_overdue_credit': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.paygate.tasks.process_incoming_poller': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.paygate.tasks.incoming_poller': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.erp.pos.tasks.process_settled_order': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.erp.pos.tasks.process_paid_order': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.paygate.tasks.send_paygate_outgoing': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},
		'secondary.finance.paygate.tasks.process_incoming_payments': {'queue': 'payments','exchange': 'payments','routing_key':'payments','delivery_mode': 'transient'},

		'secondary.channels.notify.tasks.service_call': {'queue': 'services','exchange': 'services','routing_key':'services','delivery_mode': 'transient'},
		'primary.core.bridge.tasks.background_service_call': {'queue': 'services','exchange': 'services','routing_key':'services','delivery_mode': 'transient'},
		'primary.core.bridge.tasks.process_background_service_call': {'queue': 'services','exchange': 'services','routing_key':'services','delivery_mode': 'transient'},
		'primary.core.bridge.tasks.process_background_service': {'queue': 'services','exchange': 'services','routing_key':'services','delivery_mode': 'transient'},

		'secondary.channels.dsc.tasks.process_push_request': {'queue': 'push_request','exchange': 'push_request','routing_key':'push_request','delivery_mode': 'transient'},

		'primary.core.bridge.tasks.service_call': {'queue': 'thirdparty','exchange': 'thirdparty','routing_key':'thirdparty','delivery_mode': 'transient'}, #To be updated to a new servicesnotifications queue in the future 
		'secondary.channels.notify.tasks.update_delivery_status': {'queue': 'thirdparty','exchange': 'thirdparty','routing_key':'thirdparty','delivery_mode': 'transient'}, #To be updated to a delivery notifications queue in the future 

		'secondary.finance.paygate.tasks.process_gateway_institution_notification': {'queue': 'products','exchange': 'products','routing_key':'products','delivery_mode': 'transient'}, #To be updated to a payments notifications queue in the future 
		'secondary.finance.paygate.tasks.process_institution_notification': {'queue': 'products','exchange': 'products','routing_key':'products','delivery_mode': 'transient'}, #To be updated to a payments notifications queue in the future 

		'thirdparty.bidfather.tasks.closed_bids_invoicing': {'queue': 'thirdparty','exchange': 'thirdparty','routing_key':'thirdparty','delivery_mode': 'transient'},
		'thirdparty.wahi.tasks.process_approved_loan': {'queue': 'thirdparty','exchange': 'thirdparty','routing_key':'thirdparty','delivery_mode': 'transient'},
		'products.crb.tasks.reference_activity_service_call': {'queue': 'products','exchange': 'products','routing_key':'products','delivery_mode': 'transient'},
		'products.crb.tasks.process_reference_activity': {'queue': 'products','exchange': 'products','routing_key':'products','delivery_mode': 'transient'},
		}


'''

'''


app.conf.task_queues = (
    Queue('celery', Exchange('celery'), routing_key='celery', delivery_mode=1),
    Queue('notification', Exchange('notification'), routing_key='notification', delivery_mode=1),
    Queue('bulk_spawned_outbound_notification', Exchange('bulk_spawned_outbound_notification'), routing_key='bulk_spawned_outbound_notification', delivery_mode=1),
    Queue('spawned_outbound_notification', Exchange('spawned_outbound_notification'), routing_key='spawned_outbound_notification', delivery_mode=1),
    Queue('bulk_notification', Exchange('bulk_notification'), routing_key='bulk_notification', delivery_mode=1),
    Queue('files', Exchange('files'), routing_key='files', delivery_mode=1),
    Queue('payments', Exchange('payments'), routing_key='payments', delivery_mode=1),
    Queue('services', Exchange('services'), routing_key='services', delivery_mode=1),
    Queue('push_request', Exchange('push_request'), routing_key='push_request', delivery_mode=1),
    Queue('thirdparty', Exchange('thirdparty'), routing_key='thirdparty', delivery_mode=1),
    Queue('products', Exchange('products'), routing_key='products', delivery_mode=1),
)

#app.conf.task_queues = ()

app.conf.broker_url = settings.CELERY_BROKER_URL
#app.conf.broker_url = "redis://192.168.137.22:6379/"
#app.conf.broker_url = "redis://localhost:6379/"
#app.conf.broker_url = "amqp://guest:guest@192.168.137.23:5672"
#app.conf.broker_url = "librabbitmq://guest:guest@192.168.137.23:5672"

app.conf.task_default_queue = 'celery'
app.conf.task_default_exchange_type = 'direct'
app.conf.task_default_routing_key = 'celery'
#app.conf.worker_pool='gevent' #Never use this option to select the eventlet or gevent pool. You must use the -P option to celery worker instead, to ensure the monkey patches are not applied too late, causing things to break in strange ways.


app.conf.task_protocol = 1
app.conf.delivery_mode = 1
app.conf.result_expires = 360

app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'
app.conf.task_serializer = 'json'
app.conf.accept_content = ['pickle', 'json', 'msgpack', 'yaml','application/x-python-serialize']
app.conf.enable_utc = True
app.conf.timezone = 'Africa/Nairobi'
app.conf.task_soft_time_limit = 60
app.conf.task_acks_late = False

app.conf.worker_prefetch_multiplier = 1
##app.conf.worker_prefetch_multiplier = 1
#app.conf.worker_prefetch_multiplier = 128
#app.conf.worker_disable_rate_limits = True
##app.conf.broker_pool_limit = 10000
app.conf.worker_send_task_events = True
app.conf.broker_connection_max_retries = None
#app.conf.broker_pool_limit = None
app.conf.broker_pool_limit = 1

app.conf.worker_concurrency = 50
app.conf.event_queue_expires = 60
app.conf.result_backend = None
app.conf.broker_connection_timeout = 30



app.conf.broker_heartbeat = None
##app.conf.broker_heartbeat = 0 #workaround for rabbitmq gevent issue "Connection Reset"
#app.conf.broker_heartbeat = 10
#app.conf.broker_heartbeat_checkrate = 2.0

#broker_transport_options = {'confirm_publish': True}

'''
#from librabbitmq import Connection

#conn = Connection(host="localhost", userid="guest", password="guest", virtual_host="/")

#channel = conn.channel()
#channel.exchange_declare(exchange, type, ...)
#channel.queue_declare(queue, ...)
#channel.queue_bind(queue, exchange, routing_key)

'''

