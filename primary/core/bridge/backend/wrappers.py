from primary.core.bridge.models import *
#from bridge.backend.local import *
from decimal import Decimal, ROUND_DOWN
import types, time, signal
import logging
import pytz, time, json, pycurl
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from primary.core.upc.tasks import Wrappers as UPCWrappers

lgr = logging.getLogger('primary.core.bridge')


class TimeoutError(Exception):
    pass

class timeout:
	def __init__(self, seconds=1, error_message='Timeout'):
		self.seconds = seconds
		self.error_message = error_message
	def handle_timeout(self, signum, frame):
		raise TimeoutError(self.error_message)
	def __enter__(self):
		signal.signal(signal.SIGALRM, self.handle_timeout)
		print (self.seconds)
		signal.alarm(self.seconds)
	def __exit__(self, type, value, traceback):
		signal.alarm(0)


class node:
	def __init__(self):
		self.log = None 
		self.url = None
		self.timeout = None
		self.key_file = None
		self.cert_file = None
		self.use_ssl = None
		self.username = None
		self.password = None
		self.api_key = None



class Wrappers:
	def validate_url(self, url):
		val = URLValidator()
		try:
			val(url)
			return True
		except ValidationError as e:
			lgr.info("URL Validation Error: %s" % e)
			return False

	def ext_payload(self, payload):
		new_payload, transaction, count = {}, None, 1
		for k, v in payload.items():
			key = k.lower()
			if 'card' not in key and 'credentials' not in key and 'new_pin' not in key and \
			 'validate_pin' not in key and 'password' not in key and 'confirm_password' not in key and \
			 'pin' not in key and 'access_level' not in key and \
			 'response_status' not in key and 'sec_hash' not in key and 'ip_address' not in key and \
			 key != 'lat' and key != 'lng' and \
			 key != 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and 'transaction_timestamp' not in key and \
			 'action_id' not in key and 'bridge__transaction_id' not in key and \
			 'merchant_data' not in key and 'signedpares' not in key and \
			 key != 'gpid' and key != 'sec' and \
			 key not in ['ext_product_id','vpc_securehash','service','accesspoint','access_point'] and \
			 'institution_id' not in key and key != 'response' and key != 'input':
				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:500]
				else:
					break
				count = count+1

		return new_payload

	def process_responsestatus(self,response_status, un_payload):
		payload = {}
		try:
			response_status = ResponseStatus.objects.using('read').get(response=str(response_status))
			if str(response_status.action) == '1':
				payload['reverse'] = True
			else:
				payload['reverse'] = False
			response = response_status.description
			if 'response' in un_payload.keys() and un_payload['response'] not in [None, ""]:
				payload['response'] = response+'. '+ un_payload['response']
			else:
				payload['response'] = response
		except ResponseStatus.DoesNotExist:
			payload['reverse'] = True			
		return payload

	def process_payment(self, payload):
		payment = {'charge': 0, "raise_charge": True}

		try:
			service_charge = ServiceCharge.objects.using('read').filter(enrolled_service =enrolled_service)

			payment['amount'] = Decimal(payload['amount']) if 'amount' in payload.keys() and payload['amount']!='' else Decimal(0)
			payment['currency'] = payload['currency'] if 'currency' in payload.keys() and payload['currency']!='' else 'USD'
			lgr.info("Payment : %s Service Charge: %s" % (payment, service_charge))
			for charge in service_charge:
				lgr.info("Charge: %s" % charge)
				if charge.is_percentage is False and (payment['currency'] != charge.currency.code):
					payment = {}
					break
				elif payment['amount'] > charge.max_amount or payment['amount']< charge.min_amount:
					payment = {}
					break
				else:
					if charge.is_percentage:
						payment['charge'] = payment['charge'] + ((charge.charge_value/100)*payment['amount'])
					else:
						payment['charge'] = payment['charge'] + charge.charge_value

			lgr.info("Finished Loop")

			payment['amount'], payment['charge'] = Decimal(payment['amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN), Decimal(payment['charge']).quantize(Decimal('.01'), rounding=ROUND_DOWN)
			lgr.info("Payment: %s" % payment)
		except Exception as e:
			payment = {}
			lgr.info('Payment Processing Failed: %s' % e)

		return payment

	def create_payload(self, item, gateway_profile, payload):
		lgr.info('Started Creating Payload')
		payload['SERVICE'] = item.service.name
		payload['gateway_id'] = gateway_profile.gateway.id
		payload['gateway_profile_id'] = gateway_profile.id

		if 'csrf_token' in payload.keys():
			payload['token'] = payload['csrf_token']
		elif 'csrfmiddlewaretoken' in payload.keys():
			payload['token'] = payload['csrfmiddlewaretoken']
		#if token in payload, then use existing token
	
		if 'msisdn' in payload.keys():
			msisdn = UPCWrappers().get_msisdn(payload)
			if msisdn is not None:
				payload['msisdn'] = msisdn
			else:
				del payload['msisdn']
		try: 
			details = json.loads(item.details)
			if isinstance(details,dict): 
				for k,v in details.items():
					if k == 'trigger':
						payload['trigger'] = '%s%s' % (details['trigger'],','+payload['trigger'] if 'trigger' in payload.keys() else '')
					else:
						payload[k] = v
		except Exception as e: lgr.info('Error on Add details: %s' % e)
		return payload

	def call_ext_api(self, item, function, payload):

		responseParams = {}
		lgr.info('processorFinal: We are now processing the transaction')

		try:
			node_info = {'url': item.node_system.URL,
				       	'timeout': item.node_system.timeout_time,
				       	'key_file': item.node_system.key_path,
				       	'cert_file': item.node_system.cert_path,
				       	'use_ssl': item.node_system.use_ssl,
					'username': item.node_system.username,
					'password': item.node_system.password,
					'api_key': item.node_system.api_key
				       }

			lgr.info('processorFinal: node_info %s' % node_info)
			node = '%s/%s' % (item.node_system.URL, function)
			lgr.info('Node: %s' % node)
			payload = self.ext_payload(payload)
			lgr.info('EXT Payload: %s' % payload)
			responseParams = self.post_request(payload, node)
		except Exception as e:
			responseParams['response_status'] = '96'
			lgr.info('processFinal: Error %s' % e);
		return  responseParams

		#(self, server, details, function, sub_node_handler):


	def call_api(self, item, function, payload):

		responseParams = {}
		lgr.info('processorFinal: We are now processing the transaction')

		try:
			node_info = {'url': item.node_system.URL,
				       	'timeout': item.node_system.timeout_time,
				       	'key_file': item.node_system.key_path,
				       	'cert_file': item.node_system.cert_path,
				       	'use_ssl': item.node_system.use_ssl,
					'username': item.node_system.username,
					'password': item.node_system.password,
					'api_key': item.node_system.api_key
				       }

			lgr.info('processorFinal: node_info %s' % node_info)
			node = '%s/%s' % (item.node_system.URL, function)
			lgr.info('Node: %s' % node)
			responseParams = self.post_request(payload, node)
		except Exception as e:
			responseParams['response_status'] = '96'
			lgr.info('processFinal: Error %s' % e);
		return  responseParams

		#(self, server, details, function, sub_node_handler):


	def call_local(self, item, function, payload):

		responseParams = {}
		lgr.info('processorFinal: We are now processing the transaction: %s' % item.command_function)
		try:	

			node_to_call = str(item.node_system.URL.lower())
			class_name = str(item.service.product.name.title())
			lgr.info("Node To Call: %s Class Name: %s" % (node_to_call, class_name))

			'''
			class_command = 'from '+node_to_call+'.tasks import '+class_name+' as c'
			lgr.info('Class Command: %s' % class_command)
			try:exec(class_command)
			except Exception as e: lgr.info('Error on Exec: %s' % e)

			lgr.info("Class: %s" % class_name)
			fn = c()
			
			'''

			import importlib
			module =  importlib.import_module(node_to_call+'.tasks')
			#module = __import__.import_module(node_to_call+'.tasks')
			lgr.info('Module: %s' % module)
			my_class = getattr(module, class_name)
			lgr.info('My Class: %s' % my_class)
			fn = my_class()
			lgr.info("Call Class: %s" % fn)

			func = getattr(fn, function)
			lgr.info("Run Func: %s TimeOut: %s" % (func, item.node_system.timeout_time))
			#lgr.info('Task Name: %s' % func.name)


			node_info = node()
			node_info.log = logging.getLogger(node_to_call)
			node_info.url = item.node_system.URL
			node_info.timeout = item.node_system.timeout_time
			node_info.key_file = item.node_system.key_path
			node_info.cert_file = item.node_system.cert_path
			node_info.use_ssl = item.node_system.use_ssl
			node_info.username = item.node_system.username
			node_info.password = item.node_system.password
			node_info.api_key = item.node_system.api_key


			#non celery use
			responseParams = func(payload, node_info)

		except Exception as e:
			responseParams['response_status'] = '96'
			lgr.info('processFinal: Error %s' % e);
		return  responseParams




