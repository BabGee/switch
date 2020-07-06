from __future__ import absolute_import

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError, DatabaseError
import pytz, time, json, pycurl, os, random, string
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import base64, re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Q, F
#import urllib, urllib2
from django.db import transaction
from xml.sax.saxutils import escape, unescape
from django.utils.encoding import smart_text
from django.db.models import Count, Sum, Max, Min, Avg
from secondary.channels.notify.models import *
from secondary.erp.pos.models import *
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers
from primary.core.upc.tasks import Wrappers as UPCWrappers

from primary.core.bridge import tasks as bridgetasks

import numpy as np
import pandas as pd
from primary.core.administration.views import WebService
from .models import *

import logging
lgr = logging.getLogger('secondary.finance.paygate')

from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from switch.celery import single_instance_task

class Wrappers:
	def validate_url(self, url):
		val = URLValidator()
		try:
			val(url)
			return True
		except ValidationError as e:
			lgr.info("URL Validation Error: %s" % e)
			return False

	def post_request(self, payload, node):
		try:
			if self.validate_url(node):
				jdata = json.dumps(payload)
				#response = urllib2.urlopen(node, jdata, timeout = timeout)
				#jdata = response.read()
				#payload = json.loads(jdata)
				c = pycurl.Curl()
				#Timeout after 10 seconds
				c.setopt(pycurl.CONNECTTIMEOUT, 30)
				c.setopt(pycurl.TIMEOUT, 30)
				c.setopt(pycurl.NOSIGNAL, 1)
				c.setopt(pycurl.URL, str(node) )
				c.setopt(pycurl.POST, 1)
				header=['Content-Type: application/json; charset=utf-8','Content-Length: '+str(len(jdata))]
				c.setopt(pycurl.HTTPHEADER, header)
				c.setopt(pycurl.POSTFIELDS, str(jdata))
				import StringIO
				b = StringIO.StringIO()
				c.setopt(pycurl.WRITEFUNCTION, b.write)
				c.perform()
				response = b.getvalue()

				payload = json.loads(response)
		except Exception as e:
			lgr.info("Error Posting Request: %s" % e)
			payload['response_status'] = '96'

		return payload

	def endpoint_payload(self, payload):
		new_payload, transaction = {}, None
		for k, v in payload.items():
			key = k.lower()
			if 'credentials' not in key and \
			 'validate_pin' not in key and 'access_level' not in key and \
			 'sec_hash' not in key and 'ip_address' not in key and \
			 key != 'service' and key != 'lat' and key != 'lng' and \
			 key != 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and \
			 key != 'gpid' and key != 'sec' and key != 'response':
				new_payload[str(k)] = str(v)


		return new_payload



	def response_payload(self, payload):
		#lgr.info('Response Payload: %s' % payload)
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
		except Exception as e: 
			pass
			#lgr.info('Error on Response Payload: %s' % e)
		return payload



	def transaction_payload(self, payload, responseType='pickle'):
		new_payload, transaction, count = {}, None, 1
		for k, v in payload.items():
			try:
				value = json.loads(v)
				if isinstance(value, list) or isinstance(value, dict):continue
			except: pass
			key = k.lower()
			if 'card' not in key and 'credentials' not in key and 'new_pin' not in key and \
			 'validate_pin' not in key and 'password' not in key and 'confirm_password' not in key and \
			 'pin' not in key and 'access_level' not in key and \
			 'response_status' not in key and 'sec_hash' not in key and 'ip_address' not in key and \
			 key != 'service' and key != 'lat' and key != 'lng' and \
			 key != 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and 'transaction_timestamp' not in key and \
			 'action_id' not in key and 'bridge__transaction_id' not in key and \
			 'merchant_data' not in key and 'signedpares' not in key and \
			 key != 'gpid' and key != 'sec' and \
			 key not in ['vpc_securehash','currency','amount'] and 'balance' not in key and \
			 'institution_id' not in key and key != 'response' and key != 'input' and 'url' not in key and \
			 'availablefund' not in key and key != 'repeat_bridge_transaction' and key != 'transaction_auth':
				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:40]
				else:
					break
				count = count+1

		if responseType=='json':
			return json.dumps(new_payload)
		else:
			return new_payload

class System(Wrappers):
	def payment_details(self, payload, node_info):
		try:
			if 'ext_first_name' in payload.keys(): payload['first_name'] = payload['ext_first_name']
			if 'ext_middle_name' in payload.keys(): payload['middle_name'] = payload['ext_middle_name']
			if 'ext_last_name' in payload.keys(): payload['last_name'] = payload['ext_last_name']

			payload['response_status'] = '00'
			payload['response'] = 'Captrued Payment Details'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Payment Details: %s" % e)
		return payload


	def float_to_amount(self, payload, node_info):
		try:
			if 'float_amount' in payload.keys():
				payload['amount'] = payload['float_amount']
				payload['response_status'] = '00'
				payload['response'] = 'Amount Captured'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No float amount to capture'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Float to Amount: %s" % e)
		return payload


	def amount_to_float(self, payload, node_info):
		try:
			if 'amount' in payload.keys():
				payload['float_amount'] = payload['amount']
				payload['response_status'] = '00'
				payload['response'] = 'Float Amount Captured'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No amount to capture'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Amount to Float: %s" % e)
		return payload


	@transaction.atomic
	def payment_notification(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			reference = payload['reference'].strip() if 'reference' in payload.keys() else ""

			institution_incoming_service = None
			lgr.info('Payment Notification')

			#capture remittance
			remittance_product = RemittanceProduct.objects.filter(Q(service__name=payload['SERVICE']),\
						Q(remittance__gateway=gateway_profile.gateway)|Q(remittance__gateway=None))

			lgr.info('Payment Notification: Remittance Product: %s' % remittance_product)

			if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
				remittance_product = remittance_product.filter(currency__code=payload['currency'])

			lgr.info('Payment Notification: Remittance Product: %s' % remittance_product)

			if 'payment_method' in payload.keys() and payload['payment_method'] not in ["",None]:
				remittance_product = remittance_product.filter(payment_method__name=payload['payment_method'])

			lgr.info('Payment Notification: Remittance Product: %s' % remittance_product)

			if 'ext_service_id' in payload.keys():
				remittance_product = remittance_product.filter(remittance__ext_service_id=payload['ext_service_id'])

			lgr.info('Payment Notification: Remittance Product: %s' % remittance_product)

			if 'ext_product_id' in payload.keys():
				remittance_product = remittance_product.filter(ext_product_id=payload['ext_product_id'])

			if remittance_product.exists():
				product = remittance_product.first()
				######### Institution Incoming Service ###############
				keyword = reference[:4] #Add Regex to Keyword in future
				lgr.info('Keyword: %s' % keyword)
				institution_incoming_service_list = InstitutionIncomingService.objects.filter(Q(remittance_product=product)|Q(remittance_product=None),\
									Q(keyword__iexact=keyword)|Q(keyword__in=[''])|Q(keyword__iexact=reference)|Q(keyword__isnull=True))

				if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
					amount = Decimal(payload['amount'])
					institution_incoming_service_list = institution_incoming_service_list.filter(Q(min_amount__gte=amount)|Q(min_amount__isnull=True),\
															Q(max_amount__lte=amount)|Q(max_amount__isnull=True))

				purchase_order = PurchaseOrder.objects.filter(reference__iexact=reference, status__name='UNPAID', expiry__gte=timezone.now())
				lgr.info('Order: %s' % purchase_order)
				if institution_incoming_service_list.exists() and institution_incoming_service_list.count() == 1:
					lgr.info('Keyword Found')
					institution_incoming_service = institution_incoming_service_list[0]
				elif institution_incoming_service_list.exists() and institution_incoming_service_list.count() > 1:
					lgr.info('Multi Keyword Found') #Take the one with an empty keyword
					institution_incoming_service_list = institution_incoming_service_list.filter(Q(keyword__in=[''])|Q(keyword__isnull=True))
					institution_incoming_service = institution_incoming_service_list[0] if institution_incoming_service_list.exists() else None

				#Execute Order Options
				lgr.info('Institution Service: %s' % institution_incoming_service)
				if institution_incoming_service and institution_incoming_service.process_order == True:
					lgr.info('Process Order True')
					if purchase_order.exists():pass #process_order=True - Only Process where order exists
					else: institution_incoming_service = None
				elif institution_incoming_service and institution_incoming_service.process_order == False:
					lgr.info('Process Order False') #DO NOT PROCESS with incoming service if order exists in POS
					if purchase_order.exists(): institution_incoming_service = None
					else: pass #process_order=False - Only Process where order DOES NOT exist
				else: pass #process all

				######### Institution Incoming Service ###############


				# Capture remittance product institution

				if 'institution_id' not in payload.keys() and product.institution:
					payload['institution_id'] = product.institution.id

				#institution_notification = InstitutionNotification.objects.filter(remittance_product=product)
				
				try: institution_notification = product.institutionnotification
				except: institution_notification = None

				try: gateway_institution_notification = product.gatewayinstitutionnotification
				except: gateway_institution_notification = None

				#log paygate incoming
				response_status = ResponseStatus.objects.get(response='DEFAULT')
				state = IncomingState.objects.get(name="CREATED")

				ext_inbound_id = payload['ext_inbound_id'] if 'ext_inbound_id' in payload.keys() else payload['bridge__transaction_id']


				last_incoming  = Incoming.objects.select_for_update().filter(remittance_product=product).order_by('-id')
				if len(last_incoming): last_incoming.filter(id=last_incoming[:1][0].id).update(updated=True)

				f_incoming = last_incoming.filter(ext_inbound_id=ext_inbound_id)
				if len(f_incoming):
					payload['response_status'] = '94'
					payload['response'] = 'External Inbound ID Exists'
				else:
					incoming = Incoming(remittance_product=product,reference=reference,\
						request=self.transaction_payload(payload),channel=Channel.objects.get(id=payload['chid']),\
						response_status=response_status, ext_inbound_id=ext_inbound_id,state=state)
					if 'ext_first_name' in payload.keys() and payload['ext_first_name'] not in ["",None]: incoming.ext_first_name = payload['ext_first_name']
					if 'ext_middle_name' in payload.keys() and payload['ext_middle_name'] not in ["",None]: incoming.ext_middle_name = payload['ext_middle_name']
					if 'ext_last_name' in payload.keys() and payload['ext_last_name'] not in ["",None]: incoming.ext_last_name = payload['ext_last_name']
					if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
						incoming.currency = Currency.objects.get(code=payload['currency'])
					if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
						incoming.amount = Decimal(payload['amount'])
					if 'charge' in payload.keys() and payload['charge'] not in ["",None]:
						incoming.charge = Decimal(payload['charge'])

					if product.institution:
						incoming.institution = product.institution
					if institution_incoming_service is not None:
						incoming.institution_incoming_service = institution_incoming_service
					if institution_notification:
						incoming.institution_notification = institution_notification


					msisdn = UPCWrappers().get_msisdn(payload)
					if msisdn is not None:
						try:msisdn = MSISDN.objects.get(phone_number=msisdn)
						except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();
						incoming.msisdn = msisdn

					incoming.save()

					if gateway_institution_notification:
						process_gateway_institution_notification.delay(gateway_institution_notification.id, payload)

					if product.credit_account: payload['trigger'] = 'credit_account%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					if product.notification: payload['trigger'] = 'notification%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

					payload['paygate_incoming_id'] = incoming.id
					payload['response_status'] = '00'
					payload['response'] = 'Payment Received'
			else:
					payload['response_status'] = '25'
					payload['response'] = 'Remittance Product Not Found'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Payment Notification: %s" % e)
		return payload


	def remit_confirmation(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			p = payload['paygate_outgoing_id'].split('-')
			try: paygate_outgoing_id =  int(p[len(p)-1])
			except: paygate_outgoing_id = 0

			outgoing = Outgoing.objects.filter(id=paygate_outgoing_id,response_status__response='09')

			if outgoing.exists():
				o = outgoing[0]
				params=payload.copy()
				try:params.update(json.loads(o.message))
				except:pass
				o.message = self.transaction_payload(params,'json')
				if 'request_status' in payload.keys():
					o.response_status = ResponseStatus.objects.get(response=payload['request_status'])
				else:
					o.response_status = ResponseStatus.objects.get(response='00')

				o.state = OutgoingState.objects.get(name='DELIVERED')

				if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in ["",None]:
					o.ext_outbound_id = payload['ext_outbound_id']
				elif 'bridge__transaction_id' in payload.keys():
					o.ext_outbound_id = payload['bridge__transaction_id']

				o.save()
				payload['response_status'] = '00'
				payload['response'] = 'Remit Confirmed'

			else:

				payload['response_status'] = '25'
				payload['response'] = 'No Remit Request Found'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Remit Confirmation: %s" % e)
		return payload


	def remit(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			try:
				remittance_product = RemittanceProduct.objects.filter(Q(service__name=payload['SERVICE']),\
							Q(remittance__gateway=gateway_profile.gateway)|Q(remittance__gateway=None))

				if 'currency' in payload.keys():
					remittance_product = remittance_product.filter(Q(currency__code=payload['currency'])|Q(currency=None))

				if 'payment_method' in payload.keys():
					remittance_product = remittance_product.filter(Q(payment_method__name=payload['payment_method'])\
								|Q(payment_method=None))

				if 'ext_service_id' in payload.keys():
					remittance_product = remittance_product.filter(remittance__ext_service_id=payload['ext_service_id'])

				if 'product_type_id' in payload.keys():
					remittance_product = remittance_product.filter(Q(product_type__id=payload['product_type_id'])\
								|Q(product_type=None))

				if 'product_item_id' in payload.keys():
					product_item = ProductItem.objects.get(id=payload['product_item_id'])
					remittance_product = remittance_product.filter(Q(product_type=product_item.product_type)\
								|Q(product_type=None))

				if 'ext_product_id' in payload.keys():
					remittance_product = remittance_product.filter(ext_product_id=payload['ext_product_id'])

				if remittance_product.exists():

					product = remittance_product.first()
					#Forex Currency
					'''
					if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
						currency = Currency.objects.get(code=payload['currency'])
						if currency != remittance_product[0].remittance.institution_till.till_currency:
							till_currency = remittance_product[0].remittance.institution_till.till_currency
							payload['currency'] = till_currency.code
							forex = Forex.objects.filter(base_currency=currency, quote_currency=till_currency)
							if forex.exists():
								if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
									amount = Decimal(payload['amount'])*forex[0].exchange_rate
									payload['amount'] = amount.quantize(Decimal('.01'), rounding=ROUND_DOWN) 
								else:
									payload['amount'] = Decimal(0)
							else:
								payload['amount'] = Decimal(0)
							lgr.info('Forex Calculate amount to %s|from: %s| %s' % (currency, till_currency, payload['amount']) )
					'''
					#log outgoing
					response_status = ResponseStatus.objects.get(response='DEFAULT')
					state = OutgoingState.objects.get(name="CREATED")


					if 'institution_id' not in payload.keys() and product.institution:
						payload['institution_id'] = product.institution.id

					
					try: institution_notification = product.institutionnotification
					except: institution_notification = None

					reference = payload['bridge__transaction_id'] if 'reference' not in payload.keys() else payload['reference']
					
					outgoing = Outgoing(remittance_product=product,reference=reference,\
							request=self.transaction_payload(payload),\
							response_status=response_status, sends=0, state=state)

					if institution_notification:
						outgoing.institution_notification = institution_notification

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

					outgoing.scheduled_send = scheduled_send

					if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in ["",None]:
						outgoing.ext_outbound_id = payload['ext_outbound_id']
					elif 'bridge__transaction_id' in payload.keys():
						outgoing.ext_outbound_id = payload['bridge__transaction_id']

					if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
						outgoing.currency = Currency.objects.get(code=payload['currency'])
					if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
						outgoing.amount = Decimal(payload['amount'])
					if 'charge' in payload.keys() and payload['charge'] not in ["",None]:
						outgoing.charge = Decimal(payload['charge'])

					outgoing.save()
					payload['paygate_outgoing_id'] = outgoing.id
					payload['sends'] = outgoing.sends

					if product.realtime and product.remittance.status.name == 'ACTIVE': #Process realtime & Active remittance 
						lgr.info("Active Realtime Remit")
						params = payload.copy()
						node = product.endpoint.url
						params['account_id'] = product.endpoint.account_id
						params['username'] = product.endpoint.username
						params['password'] = product.endpoint.password

						if product.endpoint.request:
							#try:params.update(json.loads(remittance_product[0].endpoint.request))
							try:params.update(product.endpoint.request)
							except:pass

						params = self.endpoint_payload(params)

						lgr.info('Endpoint: %s' % node)
						outgoing.sends = outgoing.sends+1
						params = WebService().post_request(params, node)

						if 'response' in params.keys(): outgoing.message = str(self.response_payload(params['response']))[:3839]
						if 'ext_outbound_id' in params.keys(): 
							payload['ext_outbound_id'] = params['ext_outbound_id']
							outgoing.ext_outbound_id = payload['ext_outbound_id']
							outgoing.save()
						if 'ext_inbound_id' in params.keys(): payload['ext_inbound_id'] = params['ext_inbound_id']

						if 'response' in params.keys(): payload['remit_response'] = params['response']
						if 'response_status' in params.keys() and params['response_status'] not in [None,""]:
							try:outgoing.response_status = ResponseStatus.objects.get(response=str(params['response_status']))
							except:params['response_status']='06';outgoing.response_status = ResponseStatus.objects.get(response='06')
							if params['response_status'] == '00':
								outgoing.state = OutgoingState.objects.get(name='DELIVERED')	
								if product.show_message:
									payload['response'] = params['response']
								else:
									payload['response'] = 'Remittance Submitted'
							else:
								#if product.fail_continues:
								#	payload['trigger'] = 'fail_continues%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
								#	params['response_status'] = '00'
								#else:
								outgoing.state = OutgoingState.objects.get(name='SENT')
								if 'response' in params.keys() and product.show_message:
									payload['response'] = params['response']
								else:
									payload['response'] = 'Remittance Failed'

							payload['response_status'] = params['response_status']
						else:
							outgoing.state = OutgoingState.objects.get(name='FAILED')
							#if product.fail_continues:
							#	payload['trigger'] = 'fail_continues%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
							#	outgoing.response_status = ResponseStatus.objects.get(response='00')
							#	payload['response_status'] = '00'
							#else:
							outgoing.response_status = ResponseStatus.objects.get(response='06')
							payload['response_status'] = '06'

						outgoing.save()	
					else:
						payload['response'] = 'Remittance Submitted'
						payload['response_status'] = '00'
				else:
					payload['response'] = 'Remittance product not found'
					payload['response_status'] = '92'

			except ProductItem.DoesNotExist:
				lgr.info("ProdutItem Does not Exist")
				payload['response_status'] = '25'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Remittance: %s" % e)
		return payload

	@transaction.atomic
	def credit_float(self, payload, node_info):
		try:
			lgr.info("Add Float: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])

			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)


			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = FloatManager.objects.select_for_update().filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-id')

				if 'institution_id' in payload.keys():
					#float_balance = float_balance.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					float_balance = float_balance.filter(Q(institution__id=payload['institution_id']))
				else:
					float_balance = float_balance.filter(institution=None)

				# Crediting Requires the institution_id to be expilicitly specified in the payload
				institution = Institution.objects.get(id=payload['institution_id'])
				gateway = gateway_profile.gateway

				charge = Decimal(0)
				charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
						max_amount__gt=Decimal(payload['float_amount']),credit=False),\
						Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None))) #Credit Float reverses debits and adds charges


				if 'product_item_id' in payload.keys():
					product_item = ProductItem.objects.get(id=payload['product_item_id'])
					charge_list = charge_list.filter(product_type=product_item.product_type)
				elif 'float_product_type_id' in payload.keys():
					charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])
				elif 'product_type_id' in payload.keys():
					charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
				elif 'product_type' in payload.keys():
					charge_list = charge_list.filter(product_type__name=payload['product_type'])
				else:
					charge_list = charge_list.filter(product_type=None)


				if 'institution_id' in payload.keys():
					charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
				else:
					charge_list = charge_list.filter(institution=None)

				for c in charge_list:
					if c.is_percentage:
						charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
					else:
						charge = charge+c.charge_value


				if float_balance.exists():
					#Last Balance Check
					float_balance.filter(id=float_balance[:1][0].id).update(updated=True)
					balance_bf = Decimal(float_balance[0].balance_bf) + (Decimal(payload['float_amount']) - charge)
				else:
					balance_bf = (Decimal(payload['float_amount']) - charge)

				lgr.info("New Balance Brought Forward: %s" % balance_bf)

				float_record = FloatManager(credit=True,\
					float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
					charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
					balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
					float_type=float_type[0], gateway=gateway)

				float_record.institution = institution
				
				if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
					float_record.ext_outbound_id = payload['ext_outbound_id']
				elif 'bridge__transaction_id' in payload.keys():
					float_record.ext_outbound_id = payload['bridge__transaction_id']

				float_record.save()

				payload['response'] = 'Float Credited with: %s balance: %s' % (payload['float_amount'], balance_bf)
				payload['response_status'] = '00'
			
			elif Decimal(payload['float_amount']) <= 0:
				payload['response'] = 'No float amount to Credit'
				payload['response_status'] = '00'

			#except DatabaseError as e:
			#transaction.set_rollback(True)

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Crediting Float: %s" % e)
		return payload

	@transaction.atomic
	def credit_agent_float(self, payload, node_info):
		try:
			lgr.info("Add Float: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])

			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)


			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = AgentFloatManager.objects.select_for_update().filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-id')

				if 'agent_id' in payload.keys():
					float_balance = float_balance.filter(Q(agent__id=payload['agent_id'])|Q(agent=None))
				else:
					float_balance = float_balance.filter(agent_id=None)

				# Crediting Requires the agent_id to be expilicitly specified in the payload
				agent = Agent.objects.get(id=payload['agent_id'])
				gateway = gateway_profile.gateway

				charge = Decimal(0)
				charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
						max_amount__gt=Decimal(payload['float_amount']),credit=False),\
						Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None))) #Credit Float reverses debits and adds charges


				if 'product_item_id' in payload.keys():
					product_item = ProductItem.objects.get(id=payload['product_item_id'])
					charge_list = charge_list.filter(product_type=product_item.product_type)
				elif 'float_product_type_id' in payload.keys():
					charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])
				elif 'product_type_id' in payload.keys():
					charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
				elif 'product_type' in payload.keys():
					charge_list = charge_list.filter(product_type__name=payload['product_type'])
				else:
					charge_list = charge_list.filter(product_type=None)


				if 'institution_id' in payload.keys():
					charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
				else:
					charge_list = charge_list.filter(institution=None)

				for c in charge_list:
					if c.is_percentage:
						charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
					else:
						charge = charge+c.charge_value


				if float_balance.exists():
					#Last Balance Check
					float_balance.filter(id=float_balance[:1][0].id).update(updated=True)
					balance_bf = Decimal(float_balance[0].balance_bf) + (Decimal(payload['float_amount']) - charge)
				else:
					balance_bf = (Decimal(payload['float_amount']) - charge)

				lgr.info("New Balance Brought Forward: %s" % balance_bf)

				float_record = AgentFloatManager(credit=True,\
					float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
					charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
					balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
					float_type=float_type[0], gateway=gateway)

				float_record.agent = agent
				
				if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
					float_record.ext_outbound_id = payload['ext_outbound_id']
				elif 'bridge__transaction_id' in payload.keys():
					float_record.ext_outbound_id = payload['bridge__transaction_id']

				float_record.save()

				payload['response'] = 'Float Credited with: %s balance: %s' % (payload['float_amount'], balance_bf)
				payload['response_status'] = '00'
			
			elif Decimal(payload['float_amount']) <= 0:
				payload['response'] = 'No float amount to Credit'
				payload['response_status'] = '00'

			#except DatabaseError as e:
			#transaction.set_rollback(True)

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Crediting Float: %s" % e)
		return payload


	@transaction.atomic
	def reverse_debit_float(self, payload, node_info):
		try:
			lgr.info("Credit Float: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])

			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)


			if len(float_type) and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = FloatManager.objects.select_for_update().filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-id')


				if 'institution_id' in payload.keys():
					#float_balance = float_balance.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					float_balance = float_balance.filter(Q(institution__id=payload['institution_id']))
				else:
					float_balance = float_balance.filter(institution=None)

				if len(float_balance):
					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None))) #Credit Float reverses debits and adds charges


					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
					elif 'float_product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])
					elif 'product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
					elif 'product_type' in payload.keys():
						charge_list = charge_list.filter(product_type__name=payload['product_type'])
					else:
						charge_list = charge_list.filter(product_type=None)
	

					if 'institution_id' in payload.keys():
						charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					else:
						charge_list = charge_list.filter(institution=None)


					for c in charge_list:
						if c.is_percentage:
							charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
						else:
							charge = charge+c.charge_value

					balance_bf = Decimal(float_balance[0].balance_bf) + (Decimal(payload['float_amount']) + charge) #Credit Float reverses debits and adds charges
					lgr.info("Balance Brought Forward: %s" % balance_bf)

					institution = float_balance[0].institution
					gateway = float_balance[0].gateway


					#Last Balance Check
					float_balance.filter(id=float_balance[:1][0].id).update(updated=True)

					float_record = FloatManager(credit=True,\
						float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
						charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
						balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
						float_type=float_type[0], gateway=gateway)

					if institution:
						float_record.institution = institution

					if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
						float_record.ext_outbound_id = payload['ext_outbound_id']
					elif 'bridge__transaction_id' in payload.keys():
						float_record.ext_outbound_id = payload['bridge__transaction_id']

					float_record.save()
					#check last entry balance_bf
					#Create a debit entry with float_amount entry and deducted balance_bf
					payload['response'] = 'Float Credited with: %s balance: %s' % (payload['float_amount'], balance_bf)
					payload['response_status'] = '00'
				else:
					payload['response'] = 'No float amount to Reverse'
					payload['response_status'] = '00'

			elif Decimal(payload['float_amount']) <= 0:
				payload['response'] = 'No float amount to reverse debit'
				payload['response_status'] = '00'
			#except DatabaseError as e:
			#transaction.set_rollback(True)

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Crediting Float: %s" % e)
		return payload

	def check_float(self, payload, node_info):
		#service to user verify_institution to avoid institutions using other institutions float
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			lgr.info('Float Type: %s' % float_type)
			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			lgr.info('Float Type: %s' % float_type)
			lgr.info('Payload: %s' % payload)
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])
			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)
			lgr.info('Float Type: %s' % float_type)
			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				if 'institution_id' in payload.keys():
					#float_balance = FloatManager.objects.filter(Q(float_type=float_type[0],gateway=gateway_profile.gateway), Q(institution__id=payload['institution_id'])|Q(institution=None)).order_by('-id')
					float_balance = FloatManager.objects.filter(Q(float_type=float_type[0],gateway=gateway_profile.gateway), Q(institution__id=payload['institution_id'])).order_by('-id')
				else:
					float_balance = FloatManager.objects.filter(float_type=float_type[0],gateway=gateway_profile.gateway, institution=None).order_by('-id')

				lgr.info('Float Balance: %s' % float_balance)
				#check float exists
				if float_balance.exists() and Decimal(float_balance[0].balance_bf) >= Decimal(payload['float_amount']):
					lgr.info('Float Exists')
					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None)))

					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
					elif 'float_product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])

					elif 'product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
					elif 'product_type' in payload.keys():
						charge_list = charge_list.filter(product_type__name=payload['product_type'])
					else:
						charge_list = charge_list.filter(product_type=None)
	
					if 'institution_id' in payload.keys():
						charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					else:
						charge_list = charge_list.filter(institution=None)


					for c in charge_list:
						if c.is_percentage:
							charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
						else:
							charge = charge+c.charge_value		

					balance_bf = Decimal(float_balance[0].balance_bf) - (Decimal(payload['float_amount']) + charge)
					if balance_bf >= Decimal(0):
						payload['response'] = '%s Float Balance: %s' % (float_type[0].name, balance_bf)
						payload['response_status'] = '00'
					else:
						payload['response'] = '%s Float Balance: %s' % (float_type[0].name, balance_bf)
						lgr.info("Not enough Float")
						payload['response_status'] = '51'
				else:
					payload['response'] = '%s Float Balance: No Float' % (float_type[0].name)
					lgr.info("No Float")
					payload['response_status'] = '51'
			elif Decimal(payload['float_amount']) <= Decimal(0):
				payload['response'] = 'No float amount to debit'
				payload['response_status'] = '00'
			else:
				lgr.info("No Float")
				payload['response_status'] = '51'
		except Exception as e:
			payload['response'] = 'Error %s' % e
			payload['response_status'] = '96'
			lgr.info("Error on Checking Float: %s" % e)
		return payload

	@transaction.atomic
	def debit_float(self, payload, node_info):
		#service to user verify_institution to avoid institutions using other institutions float
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			#lgr.info('Float Type: %s' % float_type)
			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			#lgr.info('Float Type: %s' % float_type)
			#lgr.info('Payload: %s' % payload)
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])
			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)
			#lgr.info('Float Type: %s' % float_type)
			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				#float_balance = FloatManager.objects.select_for_update(of=('self',),nowait=True).filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-date_created')
				'''
				float_balance = FloatManager.objects.select_for_update(nowait=True).filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-date_created')
				if 'institution_id' in payload.keys():
					float_balance = float_balance.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
				else:
					float_balance = float_balance.filter(institution=None)
				'''

				if 'institution_id' in payload.keys():
					#float_balance = FloatManager.objects.select_for_update().filter(Q(float_type=float_type[0],gateway=gateway_profile.gateway), Q(institution__id=payload['institution_id'])|Q(institution=None)).order_by('-id')
					float_balance = FloatManager.objects.select_for_update().filter(Q(float_type=float_type[0],gateway=gateway_profile.gateway), Q(institution__id=payload['institution_id'])).order_by('-id')
				else:
					float_balance = FloatManager.objects.select_for_update().filter(float_type=float_type[0],gateway=gateway_profile.gateway, institution=None).order_by('-id')

				#lgr.info('Float Balance: %s' % float_balance)
				#check float exists
				if float_balance.exists() and Decimal(float_balance[0].balance_bf) >= Decimal(payload['float_amount']):
					#lgr.info('Float Exists')
					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None)))

					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
					elif 'float_product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])

					elif 'product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
					elif 'product_type' in payload.keys():
						charge_list = charge_list.filter(product_type__name=payload['product_type'])
					else:
						charge_list = charge_list.filter(product_type=None)
	
					if 'institution_id' in payload.keys():
						charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					else:
						charge_list = charge_list.filter(institution=None)


					for c in charge_list:
						if c.is_percentage:
							charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
						else:
							charge = charge+c.charge_value		

					balance_bf = Decimal(float_balance[0].balance_bf) - (Decimal(payload['float_amount']) + charge)
					if balance_bf >= Decimal(0):
						institution = float_balance[0].institution
						gateway = float_balance[0].gateway

						#Last Balance Check
						float_balance.filter(id=float_balance[:1][0].id).update(updated=True)
						#float_balance.filter(updated=False).update(updated=True)

						float_record = FloatManager(credit=False,\
							float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
							charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
							balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
							float_type=float_type[0], gateway=gateway)

						if institution:
							float_record.institution = institution

						if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
							float_record.ext_outbound_id = payload['ext_outbound_id']
						elif 'bridge__transaction_id' in payload.keys():
							float_record.ext_outbound_id = payload['bridge__transaction_id']
						float_record.save()
						#check last entry balance_bf
						#Create a debit entry with float amount entry and deducted balance_bf
						payload['response'] = 'Float Debited with: %s balance: %s' % (payload['float_amount'], balance_bf)
						payload['response_status'] = '00'
					else:
						lgr.info("Not enough Float")
						payload['response_status'] = '51'
				else:
					lgr.info("No Float")
					payload['response_status'] = '51'
			elif Decimal(payload['float_amount']) <= Decimal(0):
				payload['response'] = 'No float amount to debit'
				payload['response_status'] = '00'
			else:
				lgr.info("No Float")
				payload['response_status'] = '51'

			##except DatabaseError as e:
			##transaction.set_rollback(True)
		except Exception as e:
			payload['response'] = 'Error %s' % e
			payload['response_status'] = '96'
			lgr.info("Error on Debiting Float: %s" % e)
		return payload


	@transaction.atomic
	def reverse_debit_agent_float(self, payload, node_info):
		try:
			lgr.info("Credit Float: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])

			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)


			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = AgentFloatManager.objects.select_for_update().filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-id')


				if 'agent_id' in payload.keys():
					float_balance = float_balance.filter(Q(agent__id=payload['agent_id'])|Q(agent=None))
				else:
					float_balance = float_balance.filter(agent=None)

				if float_balance.exists():
					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None))) #Credit Float reverses debits and adds charges


					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
					elif 'float_product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])
					elif 'product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
					elif 'product_type' in payload.keys():
						charge_list = charge_list.filter(product_type__name=payload['product_type'])
					else:
						charge_list = charge_list.filter(product_type=None)
	

					if 'institution_id' in payload.keys():
						charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					else:
						charge_list = charge_list.filter(institution=None)


					for c in charge_list:
						if c.is_percentage:
							charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
						else:
							charge = charge+c.charge_value

					balance_bf = Decimal(float_balance[0].balance_bf) + (Decimal(payload['float_amount']) + charge) #Credit Float reverses debits and adds charges
					lgr.info("Balance Brought Forward: %s" % balance_bf)

					agent = float_balance[0].agent
					gateway = float_balance[0].gateway


					#Last Balance Check
					float_balance.filter(id=float_balance[:1][0].id).update(updated=True)

					float_record = AgentFloatManager(credit=True,\
						float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
						charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
						balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
						float_type=float_type[0], gateway=gateway)

					if agent:
						float_record.agent = agent

					if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
						float_record.ext_outbound_id = payload['ext_outbound_id']
					elif 'bridge__transaction_id' in payload.keys():
						float_record.ext_outbound_id = payload['bridge__transaction_id']

					float_record.save()
					#check last entry balance_bf
					#Create a debit entry with float_amount entry and deducted balance_bf
					payload['response'] = 'Float Credited with: %s balance: %s' % (payload['float_amount'], balance_bf)
					payload['response_status'] = '00'
				else:
					payload['response'] = 'No float amount to Reverse'
					payload['response_status'] = '00'

			elif Decimal(payload['float_amount']) <= 0:
				payload['response'] = 'No float amount to reverse debit'
				payload['response_status'] = '00'
			#except DatabaseError as e:
			#transaction.set_rollback(True)

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Crediting Float: %s" % e)
		return payload

	@transaction.atomic
	def debit_agent_float(self, payload, node_info):
		#service to user verify_institution to avoid institutions using other institutions float
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			float_type = FloatType.objects.filter(Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))

			if 'payment_method' in payload.keys():
				float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			lgr.info('Float Type: %s' % float_type)
			if 'institution_id' in payload.keys():
				float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				float_type = float_type.filter(institution=None)

			lgr.info('Float Type: %s' % float_type)
			lgr.info('Payload: %s' % payload)
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				float_type = float_type.filter(product_type=product_item.product_type)
			elif 'float_product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['float_product_type_id'])
			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)
			lgr.info('Float Type: %s' % float_type)
			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = AgentFloatManager.objects.select_for_update().filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-id')

				if 'agent_id' in payload.keys():
					float_balance = float_balance.filter(Q(agent__id=payload['agent_id'])|Q(agent=None))
				else:
					float_balance = float_balance.filter(agent=None)
				lgr.info('Float Balance: %s' % float_balance)
				#check float exists
				if float_balance.exists() and Decimal(float_balance[0].balance_bf) >= Decimal(payload['float_amount']):

					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lte=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None)))

					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
					elif 'float_product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['float_product_type_id'])

					elif 'product_type_id' in payload.keys():
						charge_list = charge_list.filter(product_type__id=payload['product_type_id'])
					elif 'product_type' in payload.keys():
						charge_list = charge_list.filter(product_type__name=payload['product_type'])
					else:
						charge_list = charge_list.filter(product_type=None)
	
					if 'institution_id' in payload.keys():
						charge_list = charge_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
					else:
						charge_list = charge_list.filter(institution=None)


					for c in charge_list:
						if c.is_percentage:
							charge = charge + ((c.charge_value/100)*Decimal(payload['float_amount']))
						else:
							charge = charge+c.charge_value		

					balance_bf = Decimal(float_balance[0].balance_bf) - (Decimal(payload['float_amount']) + charge)
					if balance_bf >= Decimal(0):
						agent = float_balance[0].agent
						gateway = float_balance[0].gateway

						#Last Balance Check
						float_balance.filter(id=float_balance[:1][0].id).update(updated=True)

						float_record = AgentFloatManager(credit=False,\
							float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
							charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
							balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
							float_type=float_type[0], gateway=gateway)

						if agent:
							float_record.agent = agent

						if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
							float_record.ext_outbound_id = payload['ext_outbound_id']
						elif 'bridge__transaction_id' in payload.keys():
							float_record.ext_outbound_id = payload['bridge__transaction_id']
						float_record.save()
						#check last entry balance_bf
						#Create a debit entry with float amount entry and deducted balance_bf
						payload['response'] = 'Float Debited with: %s balance: %s' % (payload['float_amount'], balance_bf)
						payload['response_status'] = '00'
					else:
						lgr.info("Not enough Float")
						payload['response_status'] = '51'
				else:
					lgr.info("No Float")
					payload['response_status'] = '51'
			elif Decimal(payload['float_amount']) <= Decimal(0):
				payload['response'] = 'No float amount to debit'
				payload['response_status'] = '00'
			else:
				lgr.info("No Float")
				payload['response_status'] = '51'

			#except DatabaseError as e:
			#transaction.set_rollback(True)
		except Exception as e:
			payload['response'] = 'Error %s' % e
			payload['response_status'] = '96'
			lgr.info("Error on Debiting Float: %s" % e)
		return payload


	def contact_group_debit_float(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			def check(float_type, payload):
				#Wherever tills match, currencies match
				#Only Institutions can use float. A profile with institution rights can disburse float hence institution=gateway_profile.institution
				float_balance = FloatManager.objects.filter(float_type=float_type,gateway=gateway_profile.gateway).order_by('-id')

				if 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					float_balance = float_balance.filter(institution=institution)
				else:
					float_balance = float_balance.filter(institution=None)

				#check float exists
				if float_balance.exists() and Decimal(float_balance[0].balance_bf) >= Decimal(payload['float_amount']):
		       			payload['response_status'] = '00'

				elif int(payload['float_amount']) == 0:
		       			payload['response_status'] = '00'

				else:
					lgr.info("No Float")
					payload['response_status'] = '51'

				return payload

			contact_group_list = ContactGroup.objects.filter(id__in=[a for a in payload['contact_group'].split(',') if a],\
							institution=gateway_profile.institution,\
							gateway=gateway_profile.gateway)

			lgr.info('Contact Group List: %s' % contact_group_list)
			contact = Contact.objects.filter(subscribed=True,status__name='ACTIVE',\
							contact_group__in=[c for c in contact_group_list],\
							product__notification__code__institution=gateway_profile.institution,\
							product__notification__code__gateway=gateway_profile.gateway).select_related('product')

			lgr.info('Contact: %s' % contact)
			contact_product_list = contact.values('product__id','product__unit_credit_charge').annotate(product_count=Count('product__id'))

			lgr.info('Contact Group List: %s' % contact_group_list)
			#Get Amount

			float_exists = True
			for contact_product in contact_product_list:
				contact_list_count = contact.filter(product__id=contact_product['product__id']).distinct('gateway_profile__msisdn__phone_number').count()

				lgr.info('Contact List Count: %s' % contact_list_count)
				message = payload['message'].strip()
				message = unescape(message)
				message = smart_text(message)
				message = escape(message)
				chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
				messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
				messages_count = len(messages)
				payload['float_amount'] = Decimal(contact_list_count * contact_product['product__unit_credit_charge'] * messages_count)

				notification_product = NotificationProduct.objects.get(id=contact_product['product__id'])

				float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
						Q(float_product_type__institution_till=notification_product.notification.institution_till),\
						Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))


				if 'payment_method' in payload.keys():
					float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))


				if 'institution_id' in payload.keys():
					float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))


				payload = check(float_type[0], payload)

				if 'response_status' in payload.keys() and payload['response_status'] != '00':
					float_exists = False
					break


			if float_exists:
				response = ''
				for contact_product in contact_product_list:
					contact_list_count = contact.filter(product__id=contact_product['product__id']).distinct('gateway_profile__msisdn__phone_number').count()

					message = payload['message'].strip()
					message = unescape(message)
					message = smart_text(message)
					message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					messages_count = len(messages)

					notification_product = NotificationProduct.objects.get(id=contact_product['product__id'])

					#Wherever tills match, currencies match
					float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
							Q(service__name=payload['SERVICE'])|Q(service=None),\
							Q(gateway=gateway_profile.gateway)|Q(gateway=None))


					#payload['product_type_id'] = notification_product.notification.product_type.id

					payload['float_amount'] = Decimal(contact_list_count * contact_product['product__unit_credit_charge'] * messages_count)

					if notification_product.notification.code.institution:
						payload['institution_id'] = notification_product.notification.code.institution.id
					else:
						if 'institution_id' in payload.keys(): del payload['institution_id'] #User gateway Float if exists, if not, fail

					payload['float_product_type_id'] = notification_product.notification.product_type.id
					payload = self.debit_float(payload, node_info)
					response = '%s | %s' % (response,payload['response'])

				payload['response'] = response

		except Exception as e:
			payload['response'] = 'Error %s' % e
			payload['response_status'] = '96'
			lgr.info("Error on Debiting Float: %s" % e)
		return payload



	def notification_debit_float(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			def check(float_type, payload):
				#Wherever tills match, currencies match
				#Only Institutions can use float. A profile with institution rights can disburse float hence institution=gateway_profile.institution
				float_balance = FloatManager.objects.filter(float_type=float_type,gateway=gateway_profile.gateway).order_by('-id')

				if 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					float_balance = float_balance.filter(institution=institution)
				else:
					float_balance = float_balance.filter(institution=None)

				#check float exists
				if float_balance.exists() and Decimal(float_balance[0].balance_bf) >= Decimal(payload['float_amount']):
		       			payload['response_status'] = '00'

				elif int(payload['float_amount']) == 0:
		       			payload['response_status'] = '00'

				else:
					lgr.info("No Float")
					payload['response_status'] = '51'

				return payload



			notification_product_list = NotificationProduct.objects.filter(id__in=[a for a in payload['notification_product'].split(',') if a],\
							notification__code__institution=gateway_profile.institution,\
							notification__code__gateway=gateway_profile.gateway)

			#check Float Exists loop
			float_exists = True
			for notification_product in notification_product_list:

				contact_list_count = Contact.objects.filter(product=notification_product,subscribed=True,status__name='ACTIVE').count()
				message = payload['message'].strip()
				message = unescape(message)
				message = smart_text(message)
				message = escape(message)
				chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
				messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
				messages_count = len(messages)

				payload['float_amount'] = Decimal(contact_list_count * notification_product.unit_credit_charge * messages_count)
				float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
						Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))


				if 'payment_method' in payload.keys():
					float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))


				if 'institution_id' in payload.keys():
					float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))


				payload = check(float_type[0], payload)

				if 'response_status' in payload.keys() and payload['response_status'] != '00':
					float_exists = False
					break


			if float_exists:
				response = ''
				#debit Float Exists loop
				for notification_product in notification_product_list:

					contact_list_count = Contact.objects.filter(product=notification_product,subscribed=True,status__name='ACTIVE').count()
					message = payload['message'].strip()
					message = unescape(message)
					message = smart_text(message)
					message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					messages_count = len(messages)

					#Wherever tills match, currencies match
					float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
							Q(service__name=payload['SERVICE'])|Q(service=None),\
							Q(gateway=gateway_profile.gateway)|Q(gateway=None))


					#payload['product_type_id'] = notification_product.notification.product_type.id

					payload['float_amount'] = Decimal(contact_list_count * notification_product.unit_credit_charge * messages_count)

					if notification_product.notification.code.institution:
						payload['institution_id'] = notification_product.notification.code.institution.id
					else:
						if 'institution_id' in payload.keys(): del payload['institution_id'] #User gateway Float if exists, if not, fail

					payload['float_product_type_id'] = notification_product.notification.product_type.id
					payload = self.debit_float(payload, node_info)
					response = '%s | %s' % (response,payload['response'])

				payload['response'] = response

		except Exception as e:
			payload['response'] = 'Error %s' % e
			payload['response_status'] = '96'
			lgr.info("Error on Debiting Float: %s" % e)
		return payload

	def debit_batch_float(self, payload, node_info):
		try:
			#lgr.info('Payload: %s' % payload)
			notifications = json.loads(payload['notifications_object'])
			if notifications:
				for key, value in notifications.items():
					params = payload.copy()
					params['float_product_type_id'] = value['float_product_type_id']
					params['float_amount'] = value['float_amount']
					if 'institution_id' in value.keys(): params['institution_id'] = value['institution_id']
					params = self.debit_float(params, node_info)
					payload['response_status'] = params['response_status']
					if payload['response_status'] == '00':
						payload['response'] = params['response']
					else: break
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No Batch Notification to debit'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Debit Batch Float: %s" % e)
		return payload


	def check_batch_float(self, payload, node_info):
		try:
			#lgr.info('Payload: %s' % payload)
			notifications = json.loads(payload['notifications_object'])
			if notifications:
				response = None
				for key, value in notifications.items():
					params = payload.copy()
					params['float_product_type_id'] = value['float_product_type_id']
					params['float_amount'] = value['float_amount']
					if 'institution_id' in value.keys(): params['institution_id'] = value['institution_id']
					params = self.check_float(params, node_info)
					payload['response_status'] = params['response_status']
					if 'response' in params.keys():
						response = '%s | %s' % (params['response'], response if response else '')
						payload['response'] = response

					if not payload['response_status'] == '00': break #Stop service when no float
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No Batch Float to debit'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Check Batch Float: %s" % e)
		return payload


	def log_payment(self, payload, node_info):
		try:
			payload['response'] = 'Payment Logged'
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Payment Log: %s" % e)
		return payload

	def reverse_log_payment(self, payload, node_info):
		try:
			payload['response'] = 'Reversed Payment Logged'
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Reversing Payment Log: %s" % e)
		return payload

	def remit_charges(self, payload, node_info):
		try:
			payload['response'] = 'Remit Charges %s' % payload['amount']
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Remit Charges: %s" % e)
		return payload

class Payments(System):
	pass

class Trade(System):
	pass




@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_gateway_institution_notification(notification, payload):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		gateway_institution_notification = GatewayInstitutionNotification.objects.get(id=notification)
		lgr.info('Started Processing Gateway Institution Notification: %s | %s' % (gateway_institution_notification, payload))
		notification_key_list = gateway_institution_notification.notification_service.notification_key.all().values_list('key', flat=True)
		entry_keys = list(set(payload.keys()).intersection(set(list(notification_key_list))))

		params = gateway_institution_notification.notification_service.request if isinstance(gateway_institution_notification.notification_service.request, dict) else {}

		for entry in entry_keys:
			params[entry] = payload[entry]


		bridgetasks.background_service_call.delay(gateway_institution_notification.notification_service.service.name,
							gateway_institution_notification.gateway_profile.id, 
							params)

		lgr.info('Logged Gateway Institution Notification: %s | %s' % (gateway_institution_notification, params))
	except Exception as e:
		lgr.info('Error on Process Gateway Institution Notification: %s' % e)



@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_institution_notification(incoming):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		i = Incoming.objects.get(id=incoming)
		payload = {}
		lgr.info("Non-realtime Remit")
		if i.request not in [None, ""]:
			try:payload.update(i.request)
			except Exception as e: lgr.info('Failed to update Request: %s' % e)

		node = i.institution_notification.url

		payload['amount'] = str(i.amount)
		payload['reference'] = i.reference
		if i.currency is not None:
			payload['currency'] = i.currency.code

		payload['account_id'] = i.institution_notification.account_id
		payload['username'] = i.institution_notification.username
		payload['password'] = i.institution_notification.password
		payload['paygate_outgoing_id'] = i.id
		if i.inst_num_tries:
			payload['sends'] = i.inst_num_tries+1
			i.inst_num_tries=i.inst_num_tries+1
		else:
			i.inst_num_tries=1
			payload['sends'] = 1

		if i.institution_notification.request:
			try:payload.update(i.institution_notification.request)
			except:pass


		params = {}
		if i.institution_notification.allowed_notification_key not in [None,""]:
			allowed_notification_key = i.institution_notification.allowed_notification_key.split(',')
			for a in allowed_notification_key:
				if a in payload.keys(): params[a] = payload[a]


		payload = WebService().post_request(params, node)

		i.inst_notified = True
		if 'response' in payload.keys(): i.message = str(Wrappers().response_payload(payload['response']))[:128]; payload['response'] = payload['response']
		else: payload['response'] = 'Remit Submitted'
		if 'response_status' in payload.keys() and payload['response_status'] not in [None,""]:
			try:i.response_status = ResponseStatus.objects.get(response=str(payload['response_status']))
			except:payload['response_status'] = '06'; i.response_status = ResponseStatus.objects.get(response='06')
			if payload['response_status'] == '00':
				i.state = IncomingState.objects.get(name='PROCESSED')
				payload['response_status'] = '00'
			else:
				i.state = IncomingState.objects.get(name='PROCESSED')
				payload['response_status'] = payload['response_status']
		else:
			i.state = IncomingState.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='06')
			payload['response_status'] = '06'
		i.save()

	except Exception as e:
		lgr.info('Error on Process Institution Notification: %s' % e)


@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def institution_notification():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		lgr.info('Notification 1')

		orig_incoming = Incoming.objects.select_for_update().filter(Q(state__name='CREATED'),Q(inst_notified=False),~Q(institution_notification=None))

		lgr.info('Notification 1.1: %s' % orig_incoming)
		incoming = list(orig_incoming.values_list('id',flat=True)[:100])

		lgr.info('Notification 1.2: %s' % incoming)
		processing = orig_incoming.filter(id__in=incoming).update(state=IncomingState.objects.get(name='PROCESSING'))
		for ic in incoming:
			lgr.info('Notification 2: %s' % ic)
			process_institution_notification.delay(ic)
			lgr.info('Notification 2.1: %s' % ic)
	except Exception as e:
		lgr.info('Error on Institution Notification: %s' % e)


@app.task(ignore_result=True)
@transaction.atomic
def send_payment(outgoing):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		i = Outgoing.objects.get(id=outgoing)
		payload = {}
		lgr.info("Non-realtime Remit")
		if i.request:
			try:payload.update(i.request)
			except Exception as e: lgr.info('Failed to update Request: %s' % e)

		node = i.remittance_product.endpoint.url

		payload['amount'] = str(i.amount)
		payload['reference'] = i.reference
		if i.currency is not None:
			payload['currency'] = i.currency.code

		payload['account_id'] = i.remittance_product.endpoint.account_id
		payload['username'] = i.remittance_product.endpoint.username
		payload['password'] = i.remittance_product.endpoint.password
		payload['paygate_outgoing_id'] = i.id
		payload['sends'] = i.sends

		profile_tz = pytz.timezone('Africa/Nairobi')

		payload['transaction_timestamp'] = profile_tz.normalize(i.date_modified.astimezone(profile_tz)).isoformat()

		if i.remittance_product.endpoint.request:
			#try:payload.update(json.loads(i.remittance_product.endpoint.request))
			try:payload.update(i.remittance_product.endpoint.request)
			except:pass

		payload = WebService().post_request(payload, node)

		if 'response' in payload.keys(): i.message = str(Wrappers().response_payload(payload['response']))[:3839]; payload['response'] = payload['response']
		else: payload['response'] = 'Remit Submitted'
		if 'response_status' in payload.keys() and payload['response_status'] not in [None,""]:
			try:i.response_status = ResponseStatus.objects.get(response=str(payload['response_status']))
			except:payload['response_status'] = '06'; i.response_status = ResponseStatus.objects.get(response='06')
			if payload['response_status'] == '00':
				i.state = OutgoingState.objects.get(name='DELIVERED')
				payload['response_status'] = '00'
			else:
				i.state = OutgoingState.objects.get(name='SENT')
				payload['response_status'] = payload['response_status']
		else:
			i.state = OutgoingState.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='06')
			payload['response_status'] = '06'
		i.save()
	except Exception as e:
		lgr.info('Error Sending Payment: %s' % e)


@app.task(ignore_result=True)
@transaction.atomic
def send_payment_deprecated(payload,node):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	payload = json.loads(payload)
	i = Outgoing.objects.get(id=payload['id'])
	try:
		if i.state.name != 'PROCESSING':
			i.sends = i.sends+1
			i.state = OutgoingState.objects.get(name='PROCESSING')
			i.save()

		params = WebService().post_request(payload, node)

		if 'response' in params.keys(): i.message = str(params['response'])[:3839]; payload['response'] = params['response']
		else: payload['response'] = 'Remit Submitted'
		if 'response_status' in params.keys() and params['response_status'] not in [None,""]:
			try:i.response_status = ResponseStatus.objects.get(response=str(params['response_status']))
			except:params['response_status'] = '06'; i.response_status = ResponseStatus.objects.get(response='06')
			if params['response_status'] == '00':
				i.state = OutgoingState.objects.get(name='DELIVERED')
				payload['response_status'] = '00'
			else:
				i.state = OutgoingState.objects.get(name='SENT')
				payload['response_status'] = params['response_status']
		else:
			i.state = OutgoingState.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='06')
			payload['response_status'] = '06'
		i.save()
	except Exception as e:
		lgr.info('Error Sending Payment: %s' % e)


@app.task(ignore_result=True)
def service_call(payload):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		payload = json.loads(payload)
		payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))
		service = Service.objects.get(id=payload['service_id'])
		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)
		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception as e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload




@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_incoming_poller(ic):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:

		lgr.info('Poller 3')
		ip = IncomingPoller.objects.get(id=ic)

		#API Request
		#params = json.loads(ip.remittance_product.endpoint.request)
		params = ip.remittance_product.endpoint.request

		try:params.update(ip.request)
		except Exception as e: lgr.info('Failed to update Request: %s' % e)

		params['account_id'] = ip.remittance_product.endpoint.account_id
		params['username'] = ip.remittance_product.endpoint.username
		params['password'] = ip.remittance_product.endpoint.password

		node = ip.remittance_product.endpoint.url

		lgr.info('Poller 4')
		params = WebService().post_request(params, node)
		if 'response_status' in params.keys() and params['response_status'] =='00':

			lgr.info('Poller 5')
			#Background Request
			service = ip.service

			if 'rows' in params['response'].keys() and params['response']['rows']:
				for i in range(len(params['response']['rows'])):
					payload = {}
					for j in range(len(params['response']['cols'])):
						key = params['response']['cols'][j]['label'].lower().replace(" ", "_").replace("/", "_")
						payload[key] = params['response']['rows'][i][j]

					lgr.info('Payload: %s' % payload)
					if Incoming.objects.filter(remittance_product__remittance=ip.remittance_product.remittance, ext_inbound_id=payload['ext_inbound_id']).exists(): pass
					else:
						payload['chid'] = 2
						payload['ip_address'] = '127.0.0.1'
						payload['gateway_host'] = ip.gateway.default_host.all()[0].host

						lgr.info('Service: %s | Payload: %s' % (service, payload))
						gateway_profile = GatewayProfile.objects.get(gateway=ip.gateway,user__username='System@User', status__name='ACTIVATED',user__is_active=True)

						bridgetasks.background_service_call.delay(service.name, gateway_profile.id, payload)

			elif 'data' in params['response'].keys() and params['response']['data']:
				df = pd.DataFrame(params['response']['data'])
				for index, row in df.iterrows():
					lgr.info('Row: %s|%s' % (index,row))

					payload = dict(row)

					remittance_product = RemittanceProduct.objects.filter(remittance=ip.remittance_product.remittance, currency__code=payload['currency'],\
									payment_method__name=payload['payment_method'],	remittance__ext_service_id=payload['ext_service_id'],\
									ext_product_id=payload['ext_product_id'])
					if remittance_product.exists():
						lgr.info('Payload: %s|%s' % (payload,remittance_product[0]))
						if Incoming.objects.filter(remittance_product=remittance_product[0], ext_inbound_id=payload['ext_inbound_id']).exists(): pass
						else:
							payload['chid'] = 2
							payload['ip_address'] = '127.0.0.1'
							payload['gateway_host'] = ip.gateway.default_host.all()[0].host

							lgr.info('Service: %s | Payload: %s' % (service, payload))
							gateway_profile = GatewayProfile.objects.get(gateway=ip.gateway,user__username='System@User', status__name='ACTIVATED',user__is_active=True)

							bridgetasks.background_service_call.delay(service.name, gateway_profile.id, payload)
					else: lgr.info('Remittance Product does not exist: %s' % payload)

			else: lgr.info('Incoming Poller (No Data): %s' % params)

		else: lgr.info('Incoming Poller Request failed: %s' % params)

		ip.status = IncomingPollerStatus.objects.get(name='PROCESSED')
		if ip.frequency.run_every > 0: ip.next_run = timezone.now() + timezone.timedelta(seconds=ip.frequency.run_every)
		ip.save()

	except Exception as e:
		lgr.info('Error processing incoming_poller: %s ' % e)

@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def incoming_poller():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
	try:
		lgr.info('Poller 1')

		orig_incoming_poller = IncomingPoller.objects.select_for_update().filter(Q(status__name='PROCESSED')|Q(status__name='PROCESSING',\
										 date_modified__gte=timezone.now()-timezone.timedelta(minutes=600),frequency__run_every=0),\
										 Q(next_run__lte=timezone.now())|Q(frequency__run_every=0))

		lgr.info('Poller 1.1: %s' % orig_incoming_poller)
		incoming = list(orig_incoming_poller.values_list('id',flat=True)[:100])

		lgr.info('Poller 1.2: %s' % incoming)
		processing = orig_incoming_poller.filter(id__in=incoming).update(status=IncomingPollerStatus.objects.get(name='PROCESSING'), date_modified=timezone.now())
		for ic in incoming:
			lgr.info('Poller 2: %s' % ic)
			process_incoming_poller.delay(ic)
			lgr.info('Poller 2.1: %s' % ic)
	except Exception as e:
		lgr.info('Error on Incoming Poller: %s' % e)



@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_paygate_outgoing():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
	try:
		orig_outgoing = Outgoing.objects.select_for_update().filter(Q(scheduled_send__lte=timezone.now()),\
					Q(Q(remittance_product__realtime=False),Q(state__name='CREATED'))|Q(state__name='RESEND'),\
					~Q(response_status__action__in=['0']),\
					~Q(remittance_product__endpoint=None),Q(remittance_product__remittance__status__name='ACTIVE'))

		outgoing = list(orig_outgoing.values_list('id',flat=True)[:100])
		processing = orig_outgoing.filter(id__in=outgoing).update(state=OutgoingState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)
		for og in outgoing:
			send_payment.delay(og)
	except Exception as e:
		lgr.info('Error on Send Paygate Outgoing: %s' % e)



@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_paygate_outgoing_deprecated():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) one hour ago | Send all non realtime created and resends all, realtime and non-relatime
	outgoing = Outgoing.objects.select_for_update().filter(Q(scheduled_send__lte=timezone.now()),\
				Q(Q(remittance_product__realtime=False),Q(state__name='CREATED'))|Q(state__name='RESEND'),\
				~Q(response_status__action__in=['0']),\
				~Q(remittance_product__endpoint=None),Q(remittance_product__remittance__status__name='ACTIVE'))[:100]

	for i in outgoing:
		try:
			i.sends = i.sends+1
			i.state = OutgoingState.objects.get(name='PROCESSING')
			i.save()

			payload = {}
			lgr.info("Non-realtime Remit")
			if i.request:
				try:payload.update(i.request)
				except Exception as e: lgr.info('Failed to update Request: %s' % e)

			params = payload.copy()
			node = i.remittance_product.endpoint.url

			params['amount'] = str(i.amount)
			params['reference'] = i.reference
			if i.currency is not None:
				params['currency'] = i.currency.code

			params['account_id'] = i.remittance_product.endpoint.account_id
			params['username'] = i.remittance_product.endpoint.username
			params['password'] = i.remittance_product.endpoint.password
			params['paygate_outgoing_id'] = i.id
			params['sends'] = i.sends

			profile_tz = pytz.timezone('Africa/Nairobi')

			params['transaction_timestamp'] = profile_tz.normalize(i.date_modified.astimezone(profile_tz)).isoformat()

			if i.remittance_product.endpoint.request:
				#try:params.update(json.loads(i.remittance_product.endpoint.request))
				try:params.update(i.remittance_product.endpoint.request)
				except:pass


			lgr.info('Endpoint: %s' % node)
			params['id'] = i.id

			params = json.dumps(params, cls=DjangoJSONEncoder)
			send_payment_deprecated.delay(params, node)

		except Exception as e:
			lgr.info('Error sending paygate outgoing item: %s | %s' % (i,e))




@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_incoming_payments():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	incoming = Incoming.objects.select_for_update().filter(Q(processed=False),~Q(institution_incoming_service=None),Q( date_modified__lte=timezone.now()-timezone.timedelta(seconds=2) ))[:10]

	for c in incoming:
		try:
			c.processed = True
			c.save()
			lgr.info('Captured Incoming: %s' % c)
			payload = c.request

			try:payload.update(json.loads(c.institution_incoming_service.details))
			except Exception as e: lgr.info('Error on Details: %s' % e)

			service = c.institution_incoming_service.service

			payload['paygate_incoming_id'] = c.id
			#payload['service_id'] = service.id

			#Product Item not on all Incoming Services
			if c.institution_incoming_service.product_item:
				payload['product_item_id'] = c.institution_incoming_service.product_item.id
				payload['institution_id'] = c.institution_incoming_service.product_item.institution.id

			#Back to Incoming Log
			payload['currency'] = c.currency.code
			payload['amount'] = c.amount
			payload['reference'] = c.reference
			payload['chid'] = c.channel.id
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = c.institution_incoming_service.gateway.default_host.all()[0].host


			lgr.info('Service: %s | Payload: %s' % (service, payload))
			if service is None:
				lgr.info('No Service to process for product: %s' % c.product_type)
			else:
				gateway_profile_list = GatewayProfile.objects.filter(gateway=c.institution_incoming_service.gateway,user__username='System@User', status__name__in=['ACTIVATED'])
				if len(gateway_profile_list) > 0 and gateway_profile_list[0].user.is_active:
					#payload['gateway_profile_id'] = gateway_profile_list[0].id
	    				#payload = json.dumps(payload, cls=DjangoJSONEncoder)

					bridgetasks.background_service_call.delay(service.name, gateway_profile_list[0].id, payload)
					'''
					try:service_call(payload)
					except Exception as e: lgr.info('Error on Service Call: %s' % e)
					'''
		except Exception as e:
			lgr.info('Error processing paid order item: %s | %s' % (c,e))


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_float_alert(fai):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:

		lgr.info('Float Alert 3')
		fa = FloatAlert.objects.get(id=fai)

		'''
		float_manager = FloatManager(float_type=fa.float_type, gateway=fa.gateway)
		if fa.insitution is not None:
			float_manager = float_manager.filter(institution=fa.institution)

		#Process_float_manager_alert
		#float_manager_last_debit = 


		lgr.info('\n\n\n\n\t-----------------Do Float Alert Work\n\n\n\n\n\n')

		payload = json.loads(fa.request)	

		service = fa.service

		payload['institution_id'] = c.institution_incoming_service.product_item.institution.id
		payload['currency'] = c.currency.code
		payload['amount'] = c.amount
		payload['reference'] = c.reference
		payload['chid'] = c.channel.id
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = c.institution_incoming_service.gateway.default_host.all()[0].host


		lgr.info('Service: %s | Payload: %s' % (service, payload))
		if service is None:
			lgr.info('No Service to process for product: %s' % c.product_type)
		else:
			gateway_profile_list = GatewayProfile.objects.filter(gateway=c.institution_incoming_service.gateway,user__username='System@User', status__name__in=['ACTIVATED'])
			if len(gateway_profile_list) > 0 and gateway_profile_list[0].user.is_active:
				bridgetasks.background_service_call.delay(service.name, gateway_profile_list[0].id, payload)
		'''

		fa.status = FloatAlertStatus.objects.get(name='PROCESSED')
		fa.next_run = timezone.now() + timezone.timedelta(seconds=fa.frequency.run_every)
		fa.save()
	except Exception as e:
		lgr.info('Error processing incoming_poller: %s ' % e)


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def float_alert():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
	try:
		lgr.info('Float Alert 1')

		orig_float_alert = FloatAlert.objects.select_for_update().filter(Q(status__name='PROCESSED'),Q(next_run__lte=timezone.now()))

		lgr.info('Float Alert 1.1: %s' % orig_float_alert)
		float_alert = list(orig_float_alert.values_list('id',flat=True)[:100])

		lgr.info('Float Alert 1.2: %s' % float_alert)
		processing = orig_float_alert.filter(id__in=float_alert).update(status=FloatAlertStatus.objects.get(name='PROCESSING'), date_modified=timezone.now())
		for fai in float_alert:
			lgr.info('Float Alert 2: %s' % fai)
			process_float_alert.delay(fai)
			lgr.info('Float Alert 2.1: %s' % fai)
	except Exception as e:
		lgr.info('Error on Float Alert: %s' % e)




