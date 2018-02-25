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
lgr = logging.getLogger('bridge')

class ServiceProcessor:
	def action_reverse(self, commands, gateway_profile, payload, transaction, reverse_response_tree, level):
		response = 'No Response'
		#Reverse any action below the command (Less Than) not (Less Than or Equal)
		commands = commands.filter(~Q(reverse_function__isnull=True),~Q(reverse_function__iexact=''), level__lt=level,\
				 status__name='ENABLED').order_by('-level')
		lgr.info('Got Reversal Commands:%s' % commands)

		#do reverse
		#for item in reversed(commands):
		for item in commands:
			lgr.info('Got Reversal Items: %s' % item)
			status = item.status
			node_system = item.node_system
			payload = Wrappers().create_payload(item, gateway_profile, payload)

			lgr.info('Reverse Payload: '%s) % payload
			try:

				#Check if triggerable action
				if item.trigger.all().exists():
					#Check if trigger Exists
					if 'trigger' in payload.keys():
						triggers = str(payload['trigger'].strip()).split(',')
						lgr.info('Reverse Command Triggers: %s' % triggers)
						trigger_list = Trigger.objects.filter(name__in=triggers)
						#Ensure matches all existing triggers for action
						if False in [trigger_list.filter(id=t.id).exists() for t in item.trigger.all()]:
							item = None
						else:
							pass #Trigger matches
					else:
						item = None #No trigger, so, no action for a triggerable action
				else:
					pass #Not a triggerable action

				if item:
					if node_system.node_status.name == 'LOCAL API'  and item.reverse_function <> 'no_reverse':
						payload = Wrappers().call_api(item, item.reverse_function, payload)
					elif node_system.node_status.name == 'EXT API'  and item.reverse_function <> 'no_reverse':	
						payload_ext = Wrappers().call_ext_api(item, item.reverse_function, payload)
						if 'response_status' in payload_ext.keys():
							payload['response_status'] = str(payload_ext['response_status'])
						if 'response' in payload_ext.keys():
							payload['response'] = str(payload_ext['response'])
						if 'ext_transaction_id' in payload_ext.keys():
							payload['ext_transaction_id'] = str(payload_ext['ext_transaction_id'])

					elif node_system.node_status.name == 'LOCAL' and item.reverse_function <> 'no_reverse':
						payload = Wrappers().call_local(item, item.reverse_function, payload)
					elif node_system.node_status.name == 'BLANK' and item.reverse_function <> 'no_reverse':
						pass
					elif item.reverse_function == 'no_reverse':
						break

					if payload['response_status'] <> '00':
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
				else:
					#No action
					continue
			except Exception, e:
				reverse_response_tree['response_status'] = '96'
				lgr.info("Error: %s" % e)

			lgr.info('Command Function: %s Response: %s' % (item.reverse_function, str(response)[:100]))
			reverse_response_tree['response'][item.reverse_function] = response

		return reverse_response_tree

	def action_exec(self, service, gateway_profile, payload, transaction):
		response = 'No Response'
		response_tree = {'response':{}}
		level = None
		reverse = False
		lgr.info('Action Exec Started: %s' % service)
		all_commands = ServiceCommand.objects.filter(Q(service=service),Q(gateway=gateway_profile.gateway)|Q(gateway=None),\
								Q(channel__id=payload['chid'])|Q(channel=None)).order_by('level')
		if 'payment_method' in payload.keys():
			all_commands = all_commands.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))
		else:
			all_commands = all_commands.filter(payment_method=None)
		#To handle multi level authorization
		commands = all_commands.filter(Q(access_level=None) |Q(access_level=gateway_profile.access_level),Q(status__name='ENABLED'))
		#do request
		count = 1
		for item in commands:
			payload['action_id'] = item.id
			count = count+1

			lgr.info('Got Items: %s' % item)
			status = item.status
			node_system = item.node_system
			payload = Wrappers().create_payload(item, gateway_profile, payload)

			lgr.info('Payload: '%s) % payload
			try:

				#Check if triggerable action
				if item.trigger.all().exists():
					#Check if trigger Exists
					if 'trigger' in payload.keys():
						triggers = str(payload['trigger'].strip()).split(',')
						lgr.info('Command Triggers: %s' % triggers)
						trigger_list = Trigger.objects.filter(name__in=triggers)
						#Ensure matches all existing triggers for action
						if False in [trigger_list.filter(id=t.id).exists() for t in item.trigger.all()]:
							item = None
						else:
							pass #Trigger matches
					else:
						item = None #No trigger, so, no action for a triggerable action
				else:
					pass #Not a triggerable action

				if item:
					#process action
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
						pass
					elif node_system.node_status.name == 'LOCAL':	
						payload = Wrappers().call_local(item, item.command_function, payload)
					if payload['response_status'] <> '00':
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
						if transaction is not None:
							transaction.current_command = item
							all_commands = all_commands.filter(level__gt=item.level)
							if len(all_commands)>0:
								transaction.next_command = all_commands[0]
							else:
								transaction.next_command = None
						response = item.response if item.response not in [None,''] else payload['response'] 
					if item.command_function in response_tree['response'].keys():
						response_tree['response'][item.command_function+str(item.level)] = response
					else:
						response_tree['response'][item.command_function] = response

				else:
					#No action
					continue
			except Exception, e:
				response_tree['response_status'] = '96'
				lgr.critical("Error: %s" % e)

			lgr.info('Command Function: %s Response: %s' % (item.command_function, str(response)[:100]))
			response_tree['response'][item.command_function] = response

		#!Important to decide whether service success/failure
		response_tree['action_id'] = payload['action_id'] if 'action_id' in payload.keys() else 0
		response_tree['response_status'] = payload['response_status']
		response_tree['overall_status']	= payload['response_status']
		if payload['response_status'] <> 00:
			response_tree['last_response'] = service.failed_last_response if service.failed_last_response not in [None,''] else response
		else:
			response_tree['last_response'] = service.success_last_response if service.success_last_response not in [None,''] else response

		if reverse:
			lgr.info('Service Script Processing Reversal')
			reverse_payload = payload.copy()
			reverse_response_tree = response_tree.copy()
			reverse_response_tree = self.action_reverse(commands, gateway_profile, reverse_payload, transaction, reverse_response_tree, level)
			response_tree['overall_status'] = reverse_response_tree['response_status']

		return response_tree


	def do_process(self, service, gateway_profile, payload):	

		transaction = {}
		response_tree = {'response':{}, 'response_status':'06'}

		try:
			lgr.info('Service: %s, Service Status: %s, Access Level: %s' % (service.name, service.status.name, service.access_level_list()))
			def transact(transaction, service, payload):
				if 'response_status' in transaction.keys() and transaction['response_status'] == '00':
					transaction = transaction['transaction']
					payload['bridge__transaction_id'] = transaction.id

					profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
					#payload['transaction_timestamp'] = transaction.date_created.isoformat()
					#payload['transaction_timestamp'] = transaction.date_created.strftime("%Y-%m-%dT%H:%M:%SZ")
					#payload['transaction_timestamp'] = profile_tz.normalize(transaction.date_modified.astimezone(profile_tz)).strftime("%Y-%m-%dT%H:%M:%SZ")
					payload['transaction_timestamp'] = profile_tz.normalize(transaction.date_modified.astimezone(profile_tz)).isoformat()

					response_tree = self.action_exec(service, gateway_profile, payload, transaction) 
					if Loggers().update_transaction(transaction, payload, response_tree) is False:
						lgr.critical('Transaction Update Failed')
						response_tree['response_status'] = '96'
					else:
						lgr.info("Transaction Succesfully Updated")
				elif 'response_status' in transaction.keys() and transaction['response_status'] <> '00':
					response_tree['response_status'] = transaction['response_status']
					lgr.info("Transaction Wasn't Succesfully Processed")
					response_status = Wrappers().process_responsestatus(response_tree['response_status'], payload)
				else:
					response_tree['response_status'] = '96'
					lgr.info("No Response Status in Response Tree")
					response_status = Wrappers().process_responsestatus(response_tree['response_status'],payload)

				return response_tree

			if 'transaction_auth' in payload.keys() and payload['transaction_auth'] not in [None,'']:
				transaction_list = Transaction.objects.filter(Q(id__in=str(payload['transaction_auth']).split(",")),\
						~Q(next_command=None),Q(next_command__access_level=gateway_profile.access_level)).\
						prefetch_related('service','institution')
				lgr.info("Auth Transaction List: %s" % transaction_list)
				for t in transaction_list:
					transaction = {}
					transaction['response_status'] = '00'
					transaction['transaction'] = t
					lgr.info("Transaction: %s" % transaction)
					if t.request not in [None,'']:
						lgr.info("Request: %s" % t.request)
						new_payload = json.loads(t.request).copy()
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
						payload = new_payload.copy()

					response_tree = transact(transaction, t.service, payload)
			elif 'repeat_bridge_transaction' in payload.keys() and payload['repeat_bridge_transaction'] not in [None,'']:
				transaction_list = Transaction.objects.filter(id__in=str(payload['repeat_bridge_transaction']).split(","))
				lgr.info("Repeat Transaction List: %s" % transaction_list)
				for t in transaction_list:
					transaction = {}
					transaction['response_status'] = '00'
					transaction['transaction'] = t
					lgr.info("Transaction: %s" % transaction)
					if t.request not in [None,'']:
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
						payload = new_payload.copy()
					response_tree = transact(transaction, t.service, payload)

			else:
				if service.status.name == 'ENABLED':
					transaction = Loggers().log_transaction(service, gateway_profile, payload)
					response_tree = transact(transaction, service, payload)

				elif service.status.name == 'POLLER':
					response_tree = self.action_exec(service, gateway_profile, payload, None) 
				else:
					lgr.info('Service not Enabled')
					response_tree['response_status'] = '05'

		except Exception, e:
			response_tree['response_status'] = '96'
			lgr.critical("Error Processing Service: %s" % e)

		return response_tree
