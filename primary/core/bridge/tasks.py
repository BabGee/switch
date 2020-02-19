from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task, group, chain
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

import simplejson as json
from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q, F
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string
from decimal import Decimal, ROUND_DOWN
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
lgr = logging.getLogger('primary.core.bridge')

class Wrappers:
	def response_payload(self, payload):

		lgr.info('Response Payload: %s' % payload)
		try:
			payload = payload if isinstance(payload, dict)  else json.loads(payload, parse_float=Decimal)
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

			payload = json.dumps(new_payload) if isinstance(new_payload, dict) else payload
		except Exception as e:

			lgr.info('Error on Response Payload: %s' % e)
		return payload


	def approval_activity_payload(self, payload):
		new_payload, transaction, count = {}, None, 1

		exempt_keys = ['card','credentials','new_pin','validate_pin','confirm_password','password','pin',\
					   'access_level','response_status','sec_hash','ip_address','service' ,'lat','lng',\
					   'chid','session','session_id','csrf_token','csrfmiddlewaretoken' , 'gateway_host' ,'gateway_profile' ,\
					   'transaction_timestamp' ,'action_id' , 'bridge__transaction_id','merchant_data', 'signedpares',\
					   'gpid','sec','fingerprint','vpc_securehash',\
					   'institution_id','response','input','trigger','send_minutes_period','send_hours_period',\
					   'send_days_period','send_years_period','token','repeat_bridge_transaction','transaction_auth']

		for k, v in payload.items():
			try:
				value = json.loads(v, parse_float=Decimal)
				if isinstance(value, list) or isinstance(value, dict):continue
			except: pass
			key = k.lower()
			if key not in exempt_keys:
				if count <= 100:
					new_payload[str(k)[:30] ] = str(v)[:500]
				else:
					break
				count = count+1

		return new_payload


	def background_activity_payload(self, payload):
		new_payload, transaction, count = {}, None, 1

		exempt_keys = ['card','credentials','new_pin','validate_pin','confirm_password','password','pin',\
					   'access_level','response_status','sec_hash','ip_address','service' ,'lat','lng',\
					   'chid','session','session_id','csrf_token','csrfmiddlewaretoken' , 'gateway_host' ,'gateway_profile' ,\
					   'transaction_timestamp' ,'action_id' , 'bridge__transaction_id','merchant_data', 'signedpares',\
					   'gpid','sec','fingerprint','vpc_securehash','currency','amount',\
					   'institution_id','response','input','trigger','send_minutes_period','send_hours_period',\
					   'send_days_period','send_years_period','token','repeat_bridge_transaction','transaction_auth']

		for k, v in payload.items():
			try:
				value = json.loads(v, parse_float=Decimal)
				if isinstance(value, list) or isinstance(value, dict):continue
			except: pass
			key = k.lower()
			if key not in exempt_keys:
				if count <= 100:
					new_payload[str(k)[:30] ] = str(v)[:500]
				else:
					break
				count = count+1

		return new_payload



	def service_call(self, service, gateway_profile, payload):
		lgr = get_task_logger(__name__)
		from primary.core.api.views import ServiceCall
		try:
			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

	def background_service_call(self, service, gateway_profile, payload, details={}):
		try:
			status = TransactionStatus.objects.get(name='CREATED')
			response_status = ResponseStatus.objects.get(response='DEFAULT')

			channel = Channel.objects.get(id=int(payload['chid']))
			currency_code = payload['currency'] if 'currency' in payload.keys() and payload['currency']!='' else None
			currency = Currency.objects.get(code=currency_code) if currency_code is not None  else None
			amount = payload['amount'] if 'amount' in payload.keys() and payload['amount']!='' else None
			charges = payload['charges'] if 'charges' in payload.keys() and payload['charges']!='' else None
			request = self.background_activity_payload(payload)
			lgr.info('Request: %s' % request)
			if details: #details can be used to inject triggers
				try: request.update(details) #Triggers removed in previous call
				except Exception as e: lgr.info('Error on Updating Details: %s' % e)

			lgr.info('Request: %s' % request)
			activity = BackgroundServiceActivity(service=service, status=status,\
					gateway_profile=gateway_profile,request=request,\
					channel=channel, response_status=response_status, currency = currency,\
					amount = amount, charges = charges, gateway=gateway_profile.gateway,\
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
			elif 'send_minutes_period' in payload.keys():
				scheduled_send = timezone.now()+timezone.timedelta(minutes=(int(payload['send_minutes_period'])))
			elif 'send_hours_period' in payload.keys():
				scheduled_send = timezone.now()+timezone.timedelta(hours=(int(payload['send_hours_period'])))
			elif 'send_days_period' in payload.keys():
				scheduled_send = timezone.now()+timezone.timedelta(days=(int(payload['send_days_period'])))
			elif 'send_years_period' in payload.keys():
				scheduled_send = timezone.now()+timezone.timedelta(days=(365*int(payload['send_years_period'])))
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Background Service Call: %s" % e)
		return payload


class System(Wrappers):
	def background_service(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			background_service = BackgroundService.objects.filter(Q(trigger_service__name=payload['SERVICE']),\
										Q(gateway=gateway_profile.gateway)|Q(gateway=None))
			if 'institution_id' in payload.keys():
				background_service = background_service.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))

			#Check if trigger Exists
			if 'trigger' in payload.keys():
				triggers = str(payload['trigger'].strip()).split(',')
				lgr.info('BackgroundService Triggers: %s' % triggers)
				trigger_list = Trigger.objects.filter(name__in=triggers)
				background_service = background_service.filter(Q(trigger__in=trigger_list)|Q(trigger=None)).distinct()
				#Eliminate none matching trigger list
				for i in background_service:
					if i.trigger.all().exists():
						if i.trigger.all().count() == trigger_list.count():
							if False in [i.trigger.filter(id=t.id).exists() for t in trigger_list.all()]:
								lgr.info('Non Matching: %s' % i)
								background_service = background_service.filter(~Q(id=i.id))
						else:
							lgr.info('Non Matching: %s' % i)
							background_service = background_service.filter(~Q(id=i.id))
			else:
				background_service = background_service.filter(Q(trigger=None))

			if background_service.exists():
				service = background_service[0].service
				details = json.loads(background_service[0].details)
				payload = self.background_service_call(service, session_gateway_profile, payload, details)
			else:
				#all are successes
				payload['response'] = 'No Activity Service Found'
				payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Background Service: %s" % e)
		return payload


	def reject_activity(self, payload, node_info):
		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		try:
			activities = ApprovalActivity.objects.filter(pk=payload['approval_activity_pk'])

			if activities.exists():
				activity = activities[0]

				activity_status = ApprovalActivityStatus.objects.get(name='REJECTED')
				activity.status = activity_status
				activity.approver_gateway_profile = gateway_profile

				activity.save()

				payload['response'] = 'Activity Rejected'
				payload['response_status'] = '00'

			else:
				payload['response_status'] = '25'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Background Service Call: %s" % e)
		return payload


	def approve_activity(self, payload, node_info):
		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		try:
			activity = ApprovalActivity.objects.get(pk=payload['approval_activity_pk'])

			if gateway_profile.role == activity.approval.approver:
				# activity = activities[0]

				activity_status = ApprovalActivityStatus.objects.get(name='APPROVED')
				activity.status = activity_status
				activity.approver_gateway_profile = gateway_profile

				activity.save()
				payload.update(activity.request)

				payload = self.background_service_call(activity.approval.service, activity.affected_gateway_profile, payload)
			else:
				payload['response'] = 'You are not allowed to approve this activity'
				payload['response_status'] = '25'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Background Service Call: %s" % e)
		return payload

	def approval_service(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			approvals = Approval.objects.filter(Q(trigger_service__name=payload['SERVICE']),\
										Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'institution_id' in payload.keys():
				approvals = approvals.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))

			#Check if trigger Exists
			if 'trigger' in payload.keys():
				triggers = str(payload['trigger'].strip()).split(',')
				lgr.info('BackgroundService Triggers: %s' % triggers)
				trigger_list = Trigger.objects.filter(name__in=triggers)
				approvals = approvals.filter(Q(trigger__in=trigger_list)|Q(trigger=None)).distinct()
				#Eliminate none matching trigger list
				for i in approvals:
					if i.trigger.all().exists():
						if i.trigger.all().count() == trigger_list.count():
							if False in [i.trigger.filter(id=t.id).exists() for t in trigger_list.all()]:
								lgr.info('Non Matching: %s' % i)
								approvals = approvals.filter(~Q(id=i.id))
						else:
							lgr.info('Non Matching: %s' % i)
							approvals = approvals.filter(~Q(id=i.id))
			else:
				approvals = approvals.filter(Q(trigger=None))

			if approvals.exists():
				approval = approvals[0]

				if gateway_profile.role != approval.requestor:
					payload['response'] = "You Are Not Authorised to initiate this Approval Request."
					payload['response_status'] = '63'

					return payload

				# check if pending approvals exists
				if approval.pending_count:
					#Pending Related Added to ensure that related services are restricted (Mostly for multiple actions within the same row)
					pending_approvals = ApprovalActivity.objects.filter(Q(status__name='CREATED'),\
									Q(affected_gateway_profile=session_gateway_profile),Q(approval=approval)\
									|Q(approval__pending_related_service__name=payload['SERVICE']))

					if approval.approval_identifier not in ['',None]:
						pending_approvals = pending_approvals.filter(identifier=payload[approval.approval_identifier.strip()])

					pending_approvals_count = pending_approvals.count()
					if pending_approvals_count == approval.pending_count:
						# enough pending approvals created
						payload['response'] = "There is already Pending approvals for this service"
						payload['response_status'] = '94'

						return payload

					elif pending_approvals_count > approval.pending_count:
						# extra pending approvals exist
						# Backward compatibility, delete extra pending, oldest first
						extra_pending_approvals = pending_approvals.order_by('date_created')[:pending_approvals_count-approval.pending_count].values_list("id", flat=True)
						ApprovalActivity.objects.filter(pk__in=list(extra_pending_approvals)).delete()

						payload['response'] = "There is already Pending approvals for this service"
						payload['response_status'] = '94'

						return payload

				status = ApprovalActivityStatus.objects.get(name='CREATED')
				channel = Channel.objects.get(id=int(payload['chid']))
				response_status = ResponseStatus.objects.get(response='DEFAULT')

				request = payload.copy()
				request = self.approval_activity_payload(request)
				try: request.update(json.loads(approval.details)) #Triggers removed in previous call so no need to append
				except: pass

				activity = ApprovalActivity()
				activity.status=status
				activity.requestor_gateway_profile = gateway_profile
				activity.affected_gateway_profile = session_gateway_profile
				activity.request=request
				activity.channel=channel
				activity.gateway=gateway_profile.gateway
				activity.approval=approval
				activity.response_status = response_status
				if approval.approval_identifier not in ['',None]:
					activity.identifier = payload[approval.approval_identifier.strip()]

				if 'institution_id' in payload.keys():
					activity.institution = Institution.objects.get(id=payload['institution_id'])

				activity.save()

				payload['response'] = "Activity Logged. Wait to Process"

			else:
				payload['response'] = 'No Activity Service Found'
			#all are successes
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.error("Error on Background Service: %s" % e, exc_info=True)
		return payload
	def reset_background_service_activity(self,payload,node_info):
		try:
			status = TransactionStatus.objects.get(name='CREATED')
			response_status = ResponseStatus.objects.get(response='DEFAULT')
			
			BackgroundServiceActivity.objects.filter(id=payload['background_service_activity_id']).update(response_status=response_status,status=status)

			payload['response'] = "Activity reset, Waitting to process"
			payload['response_status'] = '00'


		except Exception as e:
			payload['response_status'] = '96'
			lgr.error("Error reseting background service activity",exc_info=True)
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
		except Exception as e:
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

'''
def process_pending_transactions(id_list):
	#from celery.utils.log import get_task_logger
	#lgr = get_task_logger(__name__)
	#transactions = Transaction.objects.select_for_update().filter(id__in=id_list)
	transactions = Transaction.objects.filter(id__in=id_list)

	transactions.update(transaction_status = TransactionStatus.objects.get(name='PENDING'))
	payload = {}
	payload['repeat_bridge_transaction'] = ','.join(map(str, transactions.values_list('id', flat=True)))
	payload['gateway_host'] = '127.0.0.1'
	Wrappers().service_call(Service.objects.get(name='BOOTSTRAP'), GatewayProfile.objects.get(id=1), payload)

	lgr.info("Transaction Processed")


@app.task(ignore_result=True)
def service_call(service_name, gateway_profile_id, payload):
	try:
		lgr.info('Received Service Task: %s' % service_name)
		service = Service.objects.get(name=service_name)
		gateway_profile = GatewayProfile.objects.get(id=gateway_profile_id)
		Wrappers().service_call(service, gateway_profile, payload)
	except Exception as e:
		lgr.info('Error on Service Call: %s' % e)


@app.task(ignore_result=True)
def background_service_call(service_name, gateway_profile_id, payload):
	try:
		lgr.info('Received BG Task: %s' % service_name)
		service = Service.objects.get(name=service_name)
		gateway_profile = GatewayProfile.objects.get(id=gateway_profile_id)
		Wrappers().background_service_call(service, gateway_profile, payload)
	except Exception as e:
		lgr.info('Error on BackgroundService Call: %s' % e)


@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
def process_background_service_call(background):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		i = BackgroundServiceActivity.objects.get(id=background)
		#Always copy json field as it updates back on save if you don't e.g. float/Decimal type on amount below
		payload = i.request.copy()

		lgr.info('\n\n\n\n\t########\Pre-Request: %s\n\n' % payload)
		payload['chid'] = i.channel.id
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = '127.0.0.1'
		if i.institution:
			payload['institution_id'] = i.institution.id
		if i.currency:
			payload['currency'] = i.currency.code
		if i.amount:
			#payload['amount'] = float(i.amount)
			payload['amount'] = i.amount

		service = i.service
		gateway_profile = i.gateway_profile

		if i.service.retry and i.sends > i.service.retry.max_retry:
			payload['trigger'] = 'last_send%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

		payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))

		lgr.info('\n\n\n\n\t########\Request: %s\n\n' % payload)
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)

		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)

		i.transaction_reference = '%s,%s' % (i.transaction_reference, payload['transaction_reference']) if 'transaction_reference' in payload.keys() else i.transaction_reference
		i.current_command = ServiceCommand.objects.get(id=payload['action_id']) if 'action_id' in payload.keys() else None

		#if 'last_response' in payload.keys():i.message = Wrappers().response_payload(payload['last_response'])[:3839]
		if 'last_response' in payload.keys():i.message = str(payload['last_response'])[:3839]

		if 'response_status' in payload.keys():
			i.status = TransactionStatus.objects.get(name='PROCESSED')
			i.response_status = ResponseStatus.objects.get(response=payload['response_status'])
		else:
			payload['response_status'] = '20'
			i.status = TransactionStatus.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='20')

		#Set for failed retries in every 6 hours within 24 hours
		if payload['response_status'] != '00':
			if i.service.retry:
				#Update Service Cut-off to service from BG service
				try: servicecutoff = i.service.servicecutoff #Not working
				except ServiceCutOff.DoesNotExist: servicecutoff = None
				if servicecutoff and servicecutoff.cut_off_command and i.current_command and i.current_command.level > servicecutoff.cut_off_command.level:
					pass
				elif  i.sends > i.service.retry.max_retry:
					pass
				else:
					i.status = TransactionStatus.objects.get(name='CREATED')
					i.response_status = ResponseStatus.objects.get(response='DEFAULT')
					retry_in = (i.service.retry.max_retry_hours)/(i.service.retry.max_retry)
					i.scheduled_send = timezone.now()+timezone.timedelta(hours=float(retry_in))

		i.save()

	except Exception as e:
		lgr.info('Unable to make service call: %s' % e)


@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
@transaction.atomic
@single_instance_task(60*10)
def process_background_service():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		orig_background = BackgroundServiceActivity.objects.select_for_update().filter(response_status__response='DEFAULT',\
					status__name='CREATED', date_modified__lte=timezone.now()-timezone.timedelta(seconds=2),\
					scheduled_send__lte=timezone.now())
		background = list(orig_background.values_list('id',flat=True)[:100])

		processing = orig_background.filter(id__in=background).update(status=TransactionStatus.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)
		tasks = []
		for bg in background:
			tasks.append(process_background_service_call.s(bg))

		chunks, chunk_size = len(tasks), 100
		bg_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]

	except Exception as e:
		lgr.info('Error on Processing Background Service: %s' % e)

