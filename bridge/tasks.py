from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
import base64, re

from bridge.models import *

import logging
lgr = logging.getLogger('bridge')

class Wrappers:
	@app.task(filter=task_method, ignore_result=True)
	def service_call(self, service, gateway_profile, payload):
		lgr = get_task_logger(__name__)
		from api.views import ServiceCall
		try:
			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

class System(Wrappers):
	def check_transaction_auth(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if 'bridge__transaction_id' in payload.keys():
				transaction_list = Transaction.objects.filter(Q(id=payload['bridge__transaction_id']),\
						~Q(next_command=None), Q(next_command__access_level=gateway_profile.access_level),\
						Q(current_command__access_level__hierarchy__gt=gateway_profile.access_level.hierarchy))
				if len(transaction_list)>0:
					payload['response'] = 'Operator Transaction found'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'Transaction not found'
					payload['response_status'] = '25'
			else:
				payload['response'] = 'Transaction Authorizations Only'
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Institution Details: %s" % e)

		return payload


class Trade(System):
	pass

class Payments(System):
	pass



@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_pending_transactions():
	from celery.utils.log import get_task_logger
        lgr = get_task_logger(__name__)
        transactions = Transaction.objects.select_for_update().filter(id__in=[318123])

        for t in transactions:
                try:
			t.transaction_status = TransactionStatus.objects.get(name='PENDING')
			t.save()
			payload = {}
			payload['repeat_bridge_transaction'] = str(t.id)
			payload['gateway_host'] = '127.0.0.1'
			Wrappers().service_call.delay(t.service, t.gateway_profile, payload)

			lgr.info("Transaction Processed")
                except Exception, e:
			t.transaction_status = TransactionStatus.objects.get(name='FAILED')
			t.save()

                        lgr.info('Error processing file upload: %s | %s' % (u,e))

