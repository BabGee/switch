from __future__ import absolute_import
import csv

import logging
lgr = logging.getLogger('secondary.channels.notify')

from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from switch.celery import single_instance_task

from notify.models import *

class Wrappers:
	@app.task(filter=task_method, ignore_result=True)
	def service_call(self, service, gateway_profile, payload):
		lgr = get_task_logger(__name__)
		from api.views import ServiceCall
		try:
			payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
def run():
	with open('/var/www/html/eagle_africa.csv', 'rb') as f:
	    reader = csv.reader(f)
	    your_list = map(tuple, reader)

	for c in your_list:
		service = 'SEND SMS'
		payload = {}
		payload['chid'] = '5'
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = '127.0.0.1'

		if c[0] not in ['',None] and '+' not in c[0]:
			payload['MSISDN'] = '+%s' % c[0].strip()
		elif c[0] not in ['',None]:
			payload['MSISDN'] = '%s' % c[0].strip()

		if c[1] not in ['',None]:
			payload['FULL NAMES'] = c[1].strip()
		if c[5] not in ['',None]:
			payload['message'] = c[5].strip()[:160]

		gateway_profile = GatewayProfile.objects.get(id=223057)
		try:Wrappers().service_call.delay(service, gateway_profile, payload)
		except Exception, e: lgr.info('Error on Service Call: %s' % e)

		lgr.info('Send Bulk SMS Payload: %s' % payload)
		break

