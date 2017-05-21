from __future__ import absolute_import

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import pytz, time, json, pycurl
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Q
import operator
import urllib, urllib2
from django.db import transaction
from xml.sax.saxutils import escape, unescape
from django.utils.encoding import smart_str, smart_unicode
from django.db.models import Count, Sum, Max, Min, Avg

from paygate.models import *
from notify.models import *
from pos.models import *

import logging
lgr = logging.getLogger('paygate')

from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from switch.celery import single_instance_task

class Wrappers:
	@app.task(filter=task_method, ignore_result=True)
	def service_call(self, service, gateway_profile, payload):
		from celery.utils.log import get_task_logger
		lgr = get_task_logger(__name__)
		from api.views import ServiceCall
		try:
			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

	def validate_url(self, url):
		val = URLValidator()
		try:
			val(url)
			return True
		except ValidationError, e:
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
		except Exception, e:
			lgr.info("Error Posting Request: %s" % e)
                        payload['response_status'] = '96'

		return payload

	@app.task(filter=task_method, ignore_result=True)
	def send_payment(self, i, payload,node):
		from celery.utils.log import get_task_logger
		lgr = get_task_logger(__name__)
		try:

			if i.state.name <> 'PROCESSING':
				i.sends = i.sends+1
				i.state = OutgoingState.objects.get(name='PROCESSING')
				i.save()

			params = self.post_request(payload, node)


			if 'response' in params.keys(): i.message = str(params['response'])[:1919]; payload['response'] = params['response']
			else: payload['response'] = 'Remit Submitted'
			if 'response_status' in params.keys() and params['response_status'] not in [None,""]:
				try:i.response_status = ResponseStatus.objects.get(response=str(params['response_status']))
				except:i.response_status = ResponseStatus.objects.get(response='06')
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
		except Exception, e:
			lgr.info('Error Sending Payment: %s' % e)


	def endpoint_payload(self, payload):
		new_payload, transaction = {}, None
		for k, v in payload.items():
			key = k.lower()
			if 'credentials' not in key and \
			 'validate_pin' not in key and 'access_level' not in key and \
			 'sec_hash' not in key and 'ip_address' not in key and \
			 'service' not in key and key <> 'lat' and key <> 'lng' and \
			 key <> 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and \
			 key <> 'gpid' and key <> 'sec' and key <> 'response':
				new_payload[str(k)] = str(v)


		return new_payload



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
			 key <> 'gpid' and key <> 'sec' and \
			 key not in ['ext_product_id','vpc_securehash','ext_inbound_id','currency','amount'] and \
			 'institution_id' not in key and key <> 'response' and key <> 'input'  and 'url' not in key and \
			 'availablefund' not in key:
				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:40]
				else:
					break
				count = count+1


		return json.dumps(new_payload)


class System(Wrappers):
        def amount_to_float(self, payload, node_info):
                try:
			if 'amount' in payload.keys():
				payload['float_amount'] = payload['amount']

				payload['response_status'] = '00'
				payload['response'] = 'Float Amount Captured'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No amount to capture'
                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Remittance: %s" % e)
                return payload

        def payment_notification(self, payload, node_info):
                try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			reference = payload['reference'].strip() if 'reference' in payload.keys() else ""
			reference_list = reference.split("-")
			institution_incoming_service, till, institution = None, None, None
			if len(reference_list)==3:
				till_id = reference_list[0]
				till = InstitutionTill.objects.get(id=till_id)

				#order, institution does not need a service as purchase order items have services
				business_number = reference_list[1] #is unique in UPC
				institution = Institution.objects.get(business_number__iexact=business_number)
				invoice_id = reference_list[2] #Used in purchase order
			else:
				if reference not in ['', None]:
					try:
						institution_incoming_service = InstitutionIncomingService.objects.get(keyword__iexact=reference)
					except InstitutionIncomingService.DoesNotExist: pass


			#capture remittance
			remittance_product = RemittanceProduct.objects.filter(Q(service__name=payload['SERVICE']),\
						Q(remittance__gateway=gateway_profile.gateway)|Q(remittance__gateway=None))

			if till is not None:
				remittance_product = remittance_product.filter(remittance__institution_till=till)

			if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
				remittance_product = remittance_product.filter(currency__code=payload['currency'])

			if 'payment_method' in payload.keys() and payload['payment_method'] not in ["",None]:
				remittance_product = remittance_product.filter(payment_method__name=payload['payment_method'])

			if 'ext_service_id' in payload.keys():
				remittance_product = remittance_product.filter(remittance__ext_service_id=payload['ext_service_id'])

			if 'ext_product_id' in payload.keys():
				remittance_product = remittance_product.filter(ext_product_id=payload['ext_product_id'])

			lgr.info('Remit: remittance_product: %s' % remittance_product)
			if len(remittance_product)>0:
				#log paygate incoming
				response_status = ResponseStatus.objects.get(response='DEFAULT')
				state = IncomingState.objects.get(name="CREATED")

				f_incoming = Incoming.objects.filter(remittance_product=remittance_product[0],ext_inbound_id=payload['ext_inbound_id'])

				if len(f_incoming)>0:
					payload['response_status'] = '94'
					payload['response'] = 'External Inbound ID Exists'

				else:
					incoming = Incoming(remittance_product=remittance_product[0],reference=reference,\
						request=self.transaction_payload(payload),channel=Channel.objects.get(id=payload['chid']),\
						response_status=response_status, ext_inbound_id=payload['ext_inbound_id'],state=state)
					if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
						incoming.currency = Currency.objects.get(code=payload['currency'])
					if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
						incoming.amount = Decimal(payload['amount'])
					if 'charge' in payload.keys() and payload['charge'] not in ["",None]:
						incoming.charge = Decimal(payload['charge'])
					if institution_incoming_service is not None:
						incoming.institution_incoming_service = institution_incoming_service
					if institution is not None:
						incoming.institution = institution
					incoming.save()

					payload['response_status'] = '00'
					payload['response'] = 'Payment Received'
                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Payment Notification: %s" % e)
                return payload


        def remit_confirmation(self, payload, node_info):
                try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			p = payload['paygate_outgoing_id'].split('-')
			paygate_outgoing_id =  p[len(p)-1]

			outgoing = Outgoing.objects.filter(id=paygate_outgoing_id,response_status__response='09')

			if outgoing.exists():
				o = outgoing[0]
				params=payload.copy()
				try:params.update(json.loads(o.message))
				except:pass
				o.message = self.transaction_payload(params)
				o.response_status = ResponseStatus.objects.get(response='00')
				o.state = OutgoingState.objects.get(name='DELIVERED')
				o.save()
				payload['response_status'] = '00'
				payload['response'] = 'Remit Confirmed'

			else:

				payload['response_status'] = '25'
				payload['response'] = 'No Remit Request Found'

                except Exception, e:
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
					remittance_product = remittance_product.filter(currency__code=payload['currency'])

				if 'payment_method' in payload.keys():
					remittance_product = remittance_product.filter(payment_method__name=payload['payment_method'])

				if 'ext_service_id' in payload.keys():
					remittance_product = remittance_product.filter(remittance__ext_service_id=payload['ext_service_id'])

				if 'product_type_id' in payload.keys():
					remittance_product = remittance_product.filter(product_type__id=payload['product_type_id'],\
								remittance__institution_till__in=product_item.institution_till.all())

				if 'product_item_id' in payload.keys():
					product_item = ProductItem.objects.get(id=payload['product_item_id'])
					remittance_product = remittance_product.filter(product_type=product_item.product_type,\
								remittance__institution_till__in=product_item.institution_till.all())

				if 'ext_product_id' in payload.keys():
					remittance_product = remittance_product.filter(ext_product_id=payload['ext_product_id'])

				if remittance_product.exists():
					#log outgoing
					response_status = ResponseStatus.objects.get(response='DEFAULT')
					state = OutgoingState.objects.get(name="CREATED")


					if 'institution_id' in payload.keys():
						institution = Institution.objects.get(id=payload['institution_id'])
					else:
						institution = None

					institution_notification = InstitutionNotification.objects.filter(institution=institution,remittance_product=remittance_product[0])

					reference = payload['bridge__transaction_id'] if 'reference' not in payload.keys() else payload['reference']
					
					outgoing = Outgoing(remittance_product=remittance_product[0],reference=reference,\
							request=self.transaction_payload(payload),\
							response_status=response_status, sends=0, state=state)

					if institution_notification.exists():
						outgoing.institution_notification = institution_notification[0]
					if institution is not None:
						outgoing.institution = institution

					if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
						outgoing.currency = Currency.objects.get(code=payload['currency'])
					if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
						outgoing.amount = Decimal(payload['amount'])
					if 'charge' in payload.keys() and payload['charge'] not in ["",None]:
						outgoing.charge = Decimal(payload['charge'])
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

					outgoing.save()
					if remittance_product[0].realtime and remittance_product[0].remittance.status.name == 'ACTIVE': #Process realtime & Active remittance 
						lgr.info("Active Realtime Remit")
						params = payload.copy()
						node = remittance_product[0].endpoint.url
						params['account_id'] = remittance_product[0].endpoint.account_id
						params['username'] = remittance_product[0].endpoint.username
						params['password'] = remittance_product[0].endpoint.password
						params['paygate_outgoing_id'] = outgoing.id
						if remittance_product[0].endpoint.request not in [None, ""]:
							try:params.update(json.loads(remittance_product[0].endpoint.request))
							except:pass

						params = self.endpoint_payload(params)

						lgr.info('Endpoint: %s' % node)
						lgr.info('Params: %s' % params)

						outgoing.sends = outgoing.sends+1
						params = self.post_request(params, node)
						if 'response' in params.keys(): outgoing.message = str(params['response'])[:1919]
						if 'response_status' in params.keys() and params['response_status'] not in [None,""]:
							try:outgoing.response_status = ResponseStatus.objects.get(response=str(params['response_status']))
							except:outgoing.response_status = ResponseStatus.objects.get(response='06')
							if params['response_status'] == '00':
								outgoing.state = OutgoingState.objects.get(name='DELIVERED')	
								if remittance_product[0].show_message:
									payload['response'] = params['response']
								else:
									payload['response'] = 'Remittance Submitted'
							else:
								outgoing.state = OutgoingState.objects.get(name='SENT')
								payload['response_status'] = params['response_status']
								if 'response' in params.keys() and remittance_product[0].show_message:
									payload['response'] = params['response']
								else:
									payload['response'] = 'Remittance Submitted'
						else:
							outgoing.state = OutgoingState.objects.get(name='FAILED')
							outgoing.response_status = ResponseStatus.objects.get(response='06')
							payload['response_status'] = '06'
					else:
						payload['response'] = 'Remittance Submitted'
						payload['response_status'] = '00'
					outgoing.save()	
				else:
					payload['response'] = 'Remittance product not found'
					payload['response_status'] = '92'

			except ProductItem.DoesNotExist:
				lgr.info("ProdutItem Does not Exist")
                        	payload['response_status'] = '25'

                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Remittance: %s" % e)
                return payload

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
			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)


			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = FloatManager.objects.filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-date_created')

				if 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					float_balance = float_balance.filter(institution=institution)
				else:
					float_balance = float_balance.filter(institution=None)

				if float_balance.exists():
					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lt=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None))) #Credit Float reverses debits and adds charges


					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
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

					float_record = FloatManager(credit=True,\
						float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
						charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
						balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
						float_type=float_type[0], gateway=float_balance[0].gateway)

					if float_balance[0].institution:
						float_record.institution = float_balance[0].institution

					if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
						float_record.ext_outbound_id = payload['ext_outbound_id']
					elif 'bridge__transaction_id' in payload.keys():
						float_record.ext_outbound_id = payload['bridge__transaction_id']

					float_record.save()

					#for i in float_balance[0].institution.all():
					#	float_record.institution.add(i) 

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
                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Crediting Float: %s" % e)
                return payload

        def debit_float(self, payload, node_info):
		#service to user verify_institution to avoid institutions using other institutions float
                try:
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
			elif 'product_type_id' in payload.keys():
				float_type = float_type.filter(product_type__id=payload['product_type_id'])
			elif 'product_type' in payload.keys():
				float_type = float_type.filter(product_type__name=payload['product_type'])
			else:
				float_type = float_type.filter(product_type=None)

			if float_type.exists() and Decimal(payload['float_amount']) > Decimal(0):
				float_balance = FloatManager.objects.filter(float_type=float_type[0],gateway=gateway_profile.gateway).order_by('-date_created')

				if 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					float_balance = float_balance.filter(institution=institution)
				else:
					float_balance = float_balance.filter(institution=None)

				#check float exists
				if float_balance.exists() and Decimal(float_balance[0].balance_bf) >= Decimal(payload['float_amount']):

					charge = Decimal(0)
					charge_list = FloatCharge.objects.filter(Q(float_type=float_type[0], min_amount__lt=Decimal(payload['float_amount']),\
							max_amount__gt=Decimal(payload['float_amount']),credit=False),\
							Q(Q(gateway=gateway_profile.gateway)|Q(gateway=None)))

					if 'product_item_id' in payload.keys():
						product_item = ProductItem.objects.get(id=payload['product_item_id'])
						charge_list = charge_list.filter(product_type=product_item.product_type)
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
						float_record = FloatManager(credit=False,\
							float_amount=Decimal(payload['float_amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
							charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
							balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN),\
							float_type=float_type[0], gateway=float_balance[0].gateway)

						if float_balance[0].institution:
							float_record.institution = float_balance[0].institution

						if 'ext_outbound_id' in payload.keys() and payload['ext_outbound_id'] not in [None,""]:
							float_record.ext_outbound_id = payload['ext_outbound_id']
						elif 'bridge__transaction_id' in payload.keys():
							float_record.ext_outbound_id = payload['bridge__transaction_id']
						float_record.save()

						#for i in float_balance[0].institution.all():
						#	float_record.institution.add(i) 

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

                except Exception, e:
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
				float_balance = FloatManager.objects.filter(float_type=float_type,gateway=gateway_profile.gateway).order_by('-date_created')

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
				message = smart_str(message)
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

				if 'response_status' in payload.keys() and payload['response_status'] <> '00':
					float_exists = False
					break


			if float_exists:
				response = ''
				for contact_product in contact_product_list:
					contact_list_count = contact.filter(product__id=contact_product['product__id']).distinct('gateway_profile__msisdn__phone_number').count()

					message = payload['message'].strip()
		        	        message = unescape(message)
					message = smart_str(message)
		                	message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					messages_count = len(messages)

					notification_product = NotificationProduct.objects.get(id=contact_product['product__id'])

					#Wherever tills match, currencies match
					float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
							Q(float_product_type__institution_till=notification_product.notification.institution_till),\
							Q(service__name=payload['SERVICE'])|Q(service=None),\
							Q(gateway=gateway_profile.gateway)|Q(gateway=None))


					#payload['product_type_id'] = notification_product.notification.product_type.id

 					payload['float_amount'] = Decimal(contact_list_count * contact_product['product__unit_credit_charge'] * messages_count)

					if notification_product.notification.code.institution:
						payload['institution_id'] = notification_product.notification.code.institution.id
					else:
						if 'institution_id' in payload.keys(): del payload['institution_id'] #User gateway Float if exists, if not, fail

					payload['product_type_id'] = notification_product.notification.product_type.id
					#payload['institution_till_id'] = notification_product.notification.institution_till.id
					payload = self.debit_float(payload, node_info)
					response = '%s | %s' % (response,payload['response'])

				payload['response'] = response

                except Exception, e:
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
				float_balance = FloatManager.objects.filter(float_type=float_type,gateway=gateway_profile.gateway).order_by('-date_created')

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
				message = smart_str(message)
	                	message = escape(message)
				chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
				messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
				messages_count = len(messages)

				payload['float_amount'] = Decimal(contact_list_count * notification_product.unit_credit_charge * messages_count)
				float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
						Q(float_product_type__institution_till=notification_product.notification.institution_till),\
						Q(service__name=payload['SERVICE'])|Q(service=None),\
						Q(gateway=gateway_profile.gateway)|Q(gateway=None))


				if 'payment_method' in payload.keys():
					float_type = float_type.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))


				if 'institution_id' in payload.keys():
					float_type = float_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))


				payload = check(float_type[0], payload)

				if 'response_status' in payload.keys() and payload['response_status'] <> '00':
					float_exists = False
					break


			if float_exists:
				response = ''
				#debit Float Exists loop
				for notification_product in notification_product_list:

					contact_list_count = Contact.objects.filter(product=notification_product,subscribed=True,status__name='ACTIVE').count()
					message = payload['message'].strip()
			                message = unescape(message)
					message = smart_str(message)
	                		message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					messages_count = len(messages)

					#Wherever tills match, currencies match
					float_type = FloatType.objects.filter(Q(product_type=notification_product.notification.product_type),\
							Q(float_product_type__institution_till=notification_product.notification.institution_till),\
							Q(service__name=payload['SERVICE'])|Q(service=None),\
							Q(gateway=gateway_profile.gateway)|Q(gateway=None))


					#payload['product_type_id'] = notification_product.notification.product_type.id

					payload['float_amount'] = Decimal(contact_list_count * notification_product.unit_credit_charge * messages_count)

					if notification_product.notification.code.institution:
						payload['institution_id'] = notification_product.notification.code.institution.id
					else:
						if 'institution_id' in payload.keys(): del payload['institution_id'] #User gateway Float if exists, if not, fail

					payload['product_type_id'] = notification_product.notification.product_type.id
					#payload['institution_till_id'] = notification_product.notification.institution_till.id
					payload = self.debit_float(payload, node_info)
					response = '%s | %s' % (response,payload['response'])

				payload['response'] = response

                except Exception, e:
			payload['response'] = 'Error %s' % e
                        payload['response_status'] = '96'
                        lgr.info("Error on Debiting Float: %s" % e)
                return payload

        def log_payment(self, payload, node_info):
                try:
                        payload['response'] = 'Payment Logged'
                        payload['response_status'] = '00'
                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Payment Log: %s" % e)
                return payload

        def reverse_log_payment(self, payload, node_info):
                try:
                        payload['response'] = 'Reversed Payment Logged'
                        payload['response_status'] = '00'
                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Reversing Payment Log: %s" % e)
                return payload


        def remit_charges(self, payload, node_info):
                try:
                        payload['response'] = 'Remit Charges %s' % payload['amount']
                        payload['response_status'] = '00'
                except Exception, e:
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
def send_paygate_outgoing():
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
			if i.request not in [None, ""]:
				try:payload.update(json.loads(i.request))
				except Exception, e: lgr.info('Failed to update Request: %s' % e)

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

			if i.remittance_product.endpoint.request not in [None, ""]:
				try:params.update(json.loads(i.remittance_product.endpoint.request))
				except:pass


			lgr.info('Endpoint: %s' % node)
			Wrappers().send_payment.delay(i, params, node)

		except Exception, e:
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
			payload = json.loads(c.request)	
			service = c.institution_incoming_service.service
			payload['product_item_id'] = c.institution_incoming_service.product_item.id
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
					gateway_profile = gateway_profile_list[0]

					try:Wrappers().service_call(service, gateway_profile, payload)
					except Exception, e: lgr.info('Error on Service Call: %s' % e)

		except Exception, e:
			lgr.info('Error processing paid order item: %s | %s' % (c,e))
