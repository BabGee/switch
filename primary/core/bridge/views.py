from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task


from primary.core.bridge.models import *
from primary.core.bridge.backend.loggers import Loggers
from primary.core.bridge.backend.wrappers import Wrappers
import simplejson as json
from django.utils.formats import date_format
from django.utils import timezone
from datetime import datetime, timedelta
import pytz,  time
from django.utils.formats import get_format
from django.db.models import Q

import logging
lgr = logging.getLogger('primary.core.bridge')


def transact(gateway_profile, trans, service, payload, response_tree):

	transaction_object = trans['trans']
	profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
	timestamp = profile_tz.normalize(transaction_object.date_modified.astimezone(profile_tz)).isoformat()
	if 'response_status' in trans.keys() and trans['response_status'] == '00':

		payload['bridge__transaction_id'] = transaction_object.id

		#payload['transaction_timestamp'] = transaction.date_created.isoformat()
		#payload['transaction_timestamp'] = transaction.date_created.strftime("%Y-%m-%dT%H:%M:%SZ")
		#payload['transaction_timestamp'] = profile_tz.normalize(transaction.date_modified.astimezone(profile_tz)).strftime("%Y-%m-%dT%H:%M:%SZ")
		payload['transaction_timestamp'] = timestamp 

		response_tree = ServiceProcessor().action_exec(service, gateway_profile, payload, transaction_object) 
		if Loggers().update_transaction(transaction_object, payload, response_tree) is False:
			lgr.critical('Transaction Update Failed')
			response_tree['response_status'] = '96'
		else:
			lgr.info("Transaction Succesfully Updated")
	elif 'response_status' in trans.keys() and trans['response_status'] != '00':
		response_tree['response_status'] = trans['response_status']
		lgr.info("Transaction Wasn't Succesfully Processed")
		response_status = Wrappers().process_responsestatus(response_tree['response_status'], payload)
	else:
		response_tree['response_status'] = '96'
		lgr.info("No Response Status in Response Tree")
		response_status = Wrappers().process_responsestatus(response_tree['response_status'],payload)

	response_tree['timestamp'] = timestamp
	response_tree['transaction_reference'] = transaction_object.id
	return response_tree

@app.task(ignore_result=True)
def background_transact(gateway_profile_id, transaction_id, service_id, payload, response_tree):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:

		trans = {}
		trans['response_status'] = '00'
		t = Transaction.objects.get(id=transaction_id)
		trans['trans'] = t
		lgr.info("Transaction: %s" % trans)

		lgr.info("Request: %s" % t.request)
		new_payload = json.loads(t.request).copy()
		new_payload['chid'] = t.channel.id
		new_payload['ip_address'] = t.ip_address

		if t.amount:
			new_payload['amount'] = t.amount
		if t.currency:
			new_payload['currency'] = t.currency.code

		if t.institution:
			new_payload['institution_id'] = t.institution.id
		new_payload.update(payload)
		lgr.info('New Payload: %s' % new_payload)

		gateway_profile = GatewayProfile.objects.using('read').get(id=gateway_profile_id)
		service = Service.objects.using('read').get(id=service_id)
		response_tree = transact(gateway_profile, trans, service, new_payload, response_tree)
	except Exception as e:
		lgr.info('Error on BackgroundService Call: %s' % e)

	return response_tree


class ServiceProcessor:
	def action_reverse(self, commands, gateway_profile, payload, trans, reverse_response_tree, level):
		response = 'No Response'
		#Reverse any action below the command (Less Than) not (Less Than or Equal)
		commands = commands.filter(~Q(reverse_function__isnull=True),~Q(reverse_function__iexact=''), level__lt=level,\
				 status__name='ENABLED').order_by('-level').select_related()
		lgr.info('Got Reversal Commands:%s' % commands)

		#do reverse
		#for item in reversed(commands):
		for item in commands:
			lgr.info('Got Reversal Items: %s' % item)
			status = item.status
			node_system = item.node_system
			payload = Wrappers().create_payload(item, gateway_profile, payload)
			try:

				#Check if triggerable action
				if item.trigger.all().exists():
					#Check if trigger Exists
					if 'trigger' in payload.keys():
						triggers = str(payload['trigger'].strip()).split(',')
						trigger_list = Trigger.objects.using('read').filter(name__in=triggers).select_related()

						lgr.info('Reverse Command Triggers: %s' % trigger_list)
						#Ensure matches all existing triggers for action
						if item.trigger.all().count() == trigger_list.count():
							if False in [item.trigger.filter(id=t.id).exists() for t in trigger_list.all()]:
								lgr.info('Non Matching: %s' % item)
								continue # Do not process command
						else:
							lgr.info('Non Matching: %s' % item)
							continue
					else:
						lgr.info('No Trigger in Payload so skip: %s' % item)
						continue

				if node_system.node_status.name == 'LOCAL API'  and item.reverse_function != 'no_reverse':
					payload = Wrappers().call_api(item, item.reverse_function, payload)
				elif node_system.node_status.name == 'EXT API'  and item.reverse_function != 'no_reverse':	
					payload_ext = Wrappers().call_ext_api(item, item.reverse_function, payload)
					if 'response_status' in payload_ext.keys():
						payload['response_status'] = str(payload_ext['response_status'])
					if 'response' in payload_ext.keys():
						payload['response'] = str(payload_ext['response'])
					if 'ext_transaction_id' in payload_ext.keys():
						payload['ext_transaction_id'] = str(payload_ext['ext_transaction_id'])

				elif node_system.node_status.name == 'LOCAL' and item.reverse_function != 'no_reverse':
					payload = Wrappers().call_local(item, item.reverse_function, payload)
				elif node_system.node_status.name == 'BLANK' and item.reverse_function != 'no_reverse':
					payload['response_status'] = '00' #In future, add colum for blank response_status to allow injection of required response_status
				elif item.reverse_function == 'no_reverse':
					payload['response_status'] = '00' #No reverse is a service command hence success, but shouldn't affect transacting response status. (affects only overall_status)
					break

				if payload['response_status'] != '00' and payload['response_status'] not in [rs.response for rs in item.success_response_status.all()]:
					response_status = Wrappers().process_responsestatus(payload['response_status'],payload)
					response = response_status['response']
					lgr.info('Failed response status. check if to reverse: %s' % response_status['reverse'])						
					reverse_response_tree['response'][item.reverse_function] = response
					break
				else:
					response = item.response if item.response not in [None,''] else payload['response'] 
				reverse_response_tree['response_status'] = payload['response_status']
				lgr.info('Captured Response: %s' % str(response)[:100])
				reverse_response_tree['response'][item.reverse_function] = response
			except Exception as e:
				reverse_response_tree['response_status'] = '96'
				lgr.info("Error: %s" % e)

			lgr.info('Command Function: %s Response: %s' % (item.reverse_function, str(response)[:100]))
			reverse_response_tree['response'][item.reverse_function] = response

		return reverse_response_tree

	def action_exec(self, service, gateway_profile, payload, trans):
		response = 'No Response'
		response_tree = {'response':{}}
		level = None
		reverse = False
		lgr.info('Action Exec Started: %s' % service)
		all_commands = ServiceCommand.objects.using('read').filter(Q(service=service),Q(gateway=gateway_profile.gateway)|Q(gateway=None),\
								Q(channel__id=payload['chid'])|Q(channel=None)).order_by('level').select_related()
		if 'payment_method' in payload.keys():
			all_commands = all_commands.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None)).select_related()
		else:
			all_commands = all_commands.filter(payment_method=None).select_related()
		#To handle multi level authorization
		commands = all_commands.filter(Q(access_level=None) |Q(access_level=gateway_profile.access_level),Q(status__name='ENABLED')).select_related().using('read')
		#do request
		count = 1
		for item in commands:
			payload['action_id'] = item.id
			count = count+1

			lgr.info('Got Items: %s' % item)
			status = item.status
			node_system = item.node_system
			try:
				lgr.info("if item.trigger.all(): %s" % item.trigger.all())
				#Check if triggerable action
				if item.trigger.all().exists():
					#Check if trigger Exists
					if 'trigger' in payload.keys():
						lgr.info("payload['trigger'] : %s"%payload['trigger'])
						triggers = str(payload['trigger'].strip()).split(',')
						trigger_list = Trigger.objects.using('read').filter(name__in=triggers).select_related()

						lgr.info('Command Triggers: %s' % trigger_list)
						#Ensure matches all existing triggers for action
						if item.trigger.all().count() == trigger_list.count():
							if False in [item.trigger.filter(id=t.id).exists() for t in trigger_list.all()]:
								lgr.info('Non Matching: %s' % item)
								continue # Do not process command
						else:
							lgr.info('Non Matching: %s' % item)
							continue

					else:
						continue

				#process action
				payload = Wrappers().create_payload(item, gateway_profile, payload)
				lgr.info('#process action \n %s \n' % payload)
				if node_system.node_status.name == 'LOCAL API':
					payload = Wrappers().call_api(item, item.command_function, payload)
				elif node_system.node_status.name == 'EXT API':	
					payload_ext = Wrappers().call_ext_api(item, item.command_function, payload)
					if 'response_status' in payload_ext.keys():
						payload['response_status'] = str(payload_ext['response_status'])
					if 'response' in payload_ext.keys():
						payload['response'] = str(payload_ext['response'])
					if 'ext_transaction_id' in payload_ext.keys():
						payload['ext_transaction_id'] = str(payload_ext['ext_transaction_id'])
				elif node_system.node_status.name == 'BLANK':	
					payload['response_status'] = '00' #In future, add colum for blank response_status to allow injection of required response_status
				elif node_system.node_status.name == 'LOCAL':	
					payload = Wrappers().call_local(item, item.command_function, payload)
				if payload['response_status'] != '00' and payload['response_status'] not in [rs.response for rs in item.success_response_status.all()]:
					response_status = Wrappers().process_responsestatus(payload['response_status'], payload)
					response = response_status['response']
					lgr.info('Failed response status. check if to reverse: %s' % response_status['reverse'])						
					if response_status['reverse'] and item.reverse_function not in ['no_reverse']:
						lgr.info('This definitely has to be reversed surely: %s' % item.level)
						reverse=True
						level=item.level
					if item.command_function in response_tree['response'].keys():
						response_tree['response'][item.command_function+str(item.level)] = response
					else:
						response_tree['response'][item.command_function] = response
					break
				else:
					#Log command to transaction
					if trans is not None:
						trans.current_command = ServiceCommand.objects.using('default').get(id=item.id)
						all_commands = all_commands.using('default').filter(level__gt=item.level).select_related()
						if len(all_commands)>0:
							trans.next_command = all_commands[0]
						else:
							trans.next_command = None
					response = item.response if item.response not in [None,''] else payload['response'] 
				if item.command_function in response_tree['response'].keys():
					response_tree['response'][item.command_function+str(item.level)] = response
				else:
					response_tree['response'][item.command_function] = response
			except Exception as e:
				response_tree['response_status'] = '96'
				lgr.critical("Error: %s" % e)

			lgr.info('Command Function: %s Response: %s' % (item.command_function, str(response)[:100]))
			response_tree['response'][item.command_function] = response

		#!Important to decide whether service success/failure
		response_tree['action_id'] = payload['action_id'] if 'action_id' in payload.keys() else 0
		response_tree['response_status'] = payload['response_status']
		response_tree['overall_status']	= payload['response_status']
		last_response = '' if isinstance(response, dict) else response

		if service.last_response not in [None, '']:
			status_last_response = None
			for service_last_response in service.last_response.split('|'):
				service_last_response = service_last_response.replace('%%', '|')  # Escape percentage character
				try:
					key, value = service_last_response.split('%')
				except:
					continue
				if payload['response_status'] == key.strip():
					status_last_response = value.replace('|', '%').strip()
					break

			response_tree['last_response'] = status_last_response if status_last_response else last_response


		elif payload['response_status'] != '00':
			response_tree['last_response'] = service.failed_last_response if service.failed_last_response not in [None,''] else last_response
		else:
			response_tree['last_response'] = service.success_last_response if service.success_last_response not in [None,''] else last_response

		if service.allowed_response_key not in [None,""]:
			allowed_response_keys = service.allowed_response_key.split(',')
			for a in allowed_response_keys:
				if a in payload.keys(): response_tree[a] = payload[a]

		if reverse:
			lgr.info('Service Script Processing Reversal')
			reverse_payload = payload.copy()
			reverse_response_tree = response_tree.copy()
			reverse_response_tree = self.action_reverse(commands, gateway_profile, reverse_payload, trans, reverse_response_tree, level)
			response_tree['overall_status'] = reverse_response_tree['response_status']

		return response_tree


	def do_process(self, service, gateway_profile, payload):	

		lgr.info('Started Do Process')
		trans = {}
		response_tree = {'response':{}, 'response_status':'06'}

		try:
			lgr.info('Service: %s, Service Status: %s, Access Level: %s' % (service.name, service.status.name, service.access_level_list()))

			if 'transaction_auth' in payload.keys() and payload['transaction_auth'] not in [None,'']:
				transaction_list = Transaction.objects.using('read').filter(Q(id__in=str(payload['transaction_auth']).split(",")),\
						~Q(next_command=None),Q(next_command__access_level=gateway_profile.access_level)).\
						select_related('service','institution')
				lgr.info("Auth Transaction List: %s" % transaction_list)
				del payload['transaction_auth']
				for t in transaction_list:
					try:
						background_transact.delay(gateway_profile.id, t.id, t.service.id, payload, response_tree)
						lgr.info('Transaction Auth: %s' % t)
					except Exception as e:
						lgr.info('Error On Background Transact')

				response_tree['response_status'] = '00'
				response_tree['response'] = 'Auth Transaction Captured'

			elif 'repeat_bridge_transaction' in payload.keys() and payload['repeat_bridge_transaction'] not in [None,'']:
				transaction_list = Transaction.objects.using('read').filter(id__in=str(payload['repeat_bridge_transaction']).split(",")).select_related()
				lgr.info("Repeat Transaction List: %s" % transaction_list)
				del payload['repeat_bridge_transaction']
				for t in transaction_list:
					try:
						background_transact.delay(t.gateway_profile.id, t.id, t.service.id, payload, response_tree)
						lgr.info('Repeat Bridge Transaction: %s' % t)
					except Exception as e:
						lgr.info('Error On Background Transact')
				response_tree['response_status'] = '00'
				response_tree['response'] = 'Auth Transaction Captured'
			else:
				if service.status.name == 'ENABLED':

					trans = Loggers().log_transaction(service.id, gateway_profile.id, payload)
					response_tree = transact(gateway_profile, trans, service, payload, response_tree)

				elif service.status.name == 'POLLER':

					lgr.info('Got Poller')
					response_tree = self.action_exec(service, gateway_profile, payload, None) 
				else:
					lgr.info('Service not Enabled')
					response_tree['response_status'] = '05'

		except Exception as e:
			response_tree['response_status'] = '96'
			lgr.critical("Error Processing Service: %s" % e)

		return response_tree
