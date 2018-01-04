from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q, F
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

from .models import *

import logging
lgr = logging.getLogger('bridge')

class Wrappers:
	@app.task(ignore_result=True)
	def service_call(self, service, gateway_profile, payload):
		lgr = get_task_logger(__name__)
		from primary.core.api.views import ServiceCall
		try:
			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

	def response_payload(self, payload):

		lgr.info('Response Payload: %s' % payload)
		try:
			payload = payload if isinstance(payload, dict)  else json.loads(payload)
			new_payload, transaction, count = {}, None, 1
			for k, v in dict(payload).items():
				key = k.lower()
				if 'photo' not in key and 'fingerprint' not in key and 'signature' not in key and \
				'institution_id' not in key and 'gateway_id' not in key and 'response_status' not in key and \
				'username' not in key and 'product_item' not in key and 'bridge__transaction_id' not in key and \
				'currency' not in key and 'action_id' not in key:
					if count <= 30:
						new_payload[str(k)[:30] ] = str(v)[:40]
					else:
						break
					count = count+1

			payload = json.dumps(new_payload)
		except Exception, e:

			lgr.info('Error on Response Payload: %s' % e)
		return payload


	def transaction_payload(self, payload):
		new_payload, transaction, count = {}, None, 1
		for k, v in payload.items():
			key = k.lower()
			if 'card' not in key and 'credentials' not in key and 'new_pin' not in key and \
			 'validate_pin' not in key and 'password' not in key and 'confirm_password' not in key and \
			 'pin' not in key and 'access_level' not in key and \
			 'response_status' not in key and 'sec_hash' not in key and 'ip_address' not in key and \
			 'service' not in key and key <> 'lat' and key <> 'lng' and \
			 key <> 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and 'transaction_timestamp' not in key and \
			 'action_id' not in key and 'bridge__transaction_id' not in key and \
			 'merchant_data' not in key and 'signedpares' not in key and \
			 key <> 'gpid' and key <> 'sec' and  key <> 'fingerprint' and \
			 key not in ['ext_product_id','vpc_securehash','currency','amount'] and \
			 'institution_id' not in key and key <> 'response' and key <> 'input':
				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:500]
				else:
					break
				count = count+1

		return json.dumps(new_payload)




class System(Wrappers):
	def background_service(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			background_service = BackgroundService.objects.filter(trigger_service__name=payload['SERVICE'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			if background_service.exists():
				status = TransactionStatus.objects.get(name='CREATED')
				response_status = ResponseStatus.objects.get(response='DEFAULT')

				channel = Channel.objects.get(id=int(payload['chid']))
				currency_code = payload['currency'] if 'currency' in payload.keys() and payload['currency']!='' else None
				currency = Currency.objects.get(code=currency_code) if currency_code is not None  else None
				amount = payload['amount'] if 'amount' in payload.keys() and payload['amount']!='' else None
				charges = payload['charges'] if 'charges' in payload.keys() and payload['charges']!='' else None



				activity = BackgroundServiceActivity(background_service=background_service[0], status=status, \
						gateway_profile=session_gateway_profile,request=self.transaction_payload(payload),\
						channel=channel, response_status=response_status, currency = currency,\
						amount = amount, charges = charges, gateway=session_gateway_profile.gateway,\
						sends=0)

				activity.transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None

				if 'scheduled_send' in payload.keys() and payload['scheduled_send'] not in ["",None]:
					try:date_obj = datetime.strptime(payload["scheduled_send"], '%d/%m/%Y %I:%M %p')
					except: date_obj = None
					if date_obj is not None:		
						profile_tz = pytz.timezone(gateway_profile.profile.timezone)
						scheduled_send = pytz.timezone(gateway_profile.profile.timezone).localize(date_obj)
						lgr.info("Send Scheduled: %s" % scheduled_send)
					else:
						scheduled_send = timezone.now()+timezone.timedelta(seconds=1)
				else:
					scheduled_send = timezone.now()+timezone.timedelta(seconds=1)

				activity.scheduled_send = scheduled_send

				if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in ["",None]:
					activity.ext_outbound_id = payload['ext_outbound_id']

				if 'institution_id' in payload.keys():
					activity.institution = Institution.objects.get(id=payload['institution_id'])

				activity.save()

				payload['response'] = "Activity Logged. Wait to Process"
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '21'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Background Service: %s" % e)
		return payload


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

'''
@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_pending_transactions():
	from celery.utils.log import get_task_logger
        lgr = get_task_logger(__name__)
        transactions = Transaction.objects.select_for_update().filter(id__in=[123])

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
'''


@app.task(ignore_result=True)
def background_service_call(background):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		i = BackgroundServiceActivity.objects.get(id=background)

		payload = json.loads(i.background_service.details)
		try:payload.update(json.loads(i.request))
		except:pass
		payload['chid'] = i.channel.id
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = '127.0.0.1'
		if i.institution:
			payload['institution_id'] = i.institution.id
		if i.currency:
			payload['currency'] = i.currency.code
		if i.amount:
			payload['amount'] = i.amount

		service = i.background_service.activity_service
		gateway_profile = i.gateway_profile

		payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)

		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)

		i.transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None
		i.current_command = ServiceCommand.objects.get(id=payload['action_id']) if 'action_id' in payload.keys() else None

		if 'last_response' in payload.keys():i.message = Wrappers().response_payload(payload['last_response'])[:3839]
		if 'response_status' in payload.keys():
			i.status = TransactionStatus.objects.get(name='PROCESSED')
			i.response_status = ResponseStatus.objects.get(response=payload['response_status'])
		else:
			payload['response_status'] = '20'
			i.status = TransactionStatus.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='20')

		#Set for failed retries in every 6 hours within 24 hours
		if payload['response_status'] <> '00':
			if i.background_service.cut_off_command and i.current_command and i.current_command.level > i.background_service.cut_off_command.level:
				pass
			elif  i.sends > 3:
				pass
			else:
				i.status = TransactionStatus.objects.get(name='CREATED')
				i.response_status = ResponseStatus.objects.get(response='DEFAULT')
				i.scheduled_send = timezone.now()+timezone.timedelta(hours=6)
				i.sends = i.sends + 1

		i.save()

	except Exception, e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_background_service():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		orig_background = BackgroundServiceActivity.objects.select_for_update().filter(response_status__response='DEFAULT',\
					status__name='CREATED', date_modified__lte=timezone.now()-timezone.timedelta(seconds=2),\
					scheduled_send__lte=timezone.now())
		background = list(orig_background.values_list('id',flat=True)[:250])

		processing = orig_background.filter(id__in=background).update(status=TransactionStatus.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)
		for bg in background:
			background_service_call.delay(bg)
	except Exception, e:
		lgr.info('Error on Processing Background Service: %s' % e)

