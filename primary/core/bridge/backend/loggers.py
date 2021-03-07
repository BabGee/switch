from primary.core.bridge.models import *
from primary.core.bridge.backend.wrappers import Wrappers
import json
from django.utils.formats import date_format
from django.utils import timezone
from datetime import datetime
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.contrib.gis.geos import Point
from django.contrib.gis.geoip2 import GeoIP2
import logging
lgr = logging.getLogger('primary.core.bridge')


class Loggers:
	response_params = {}
	def transaction_payload(self, payload):
		new_payload, trans, count = {}, None, 1
		for k, v in payload.items():
			key = k.lower()
			if 'card' not in key and 'credentials' not in key and 'new_pin' not in key and \
			 'validate_pin' not in key and 'password' not in key and 'confirm_password' not in key and \
			 'pin' not in key and 'access_level' not in key and \
			 'response_status' not in key and 'sec_hash' not in key and 'ip_address' not in key and \
			 'service' not in key and key != 'lat' and key != 'lng' and \
			 key != 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and 'transaction_timestamp' not in key and \
			 'action_id' not in key and 'bridge__transaction_id' not in key and \
			 'merchant_data' not in key and 'signedpares' not in key and \
			 key != 'gpid' and key != 'sec' and  key != 'fingerprint' and key != 'user_agent' and\
			 key not in ['vpc_securehash','currency','amount'] and \
			 'institution_id' not in key and key != 'response' and key != 'input':
				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:500]
				else:
					break
				count = count+1

		return json.dumps(new_payload)

	def log_transaction(self, service_id, gateway_profile_id, payload):
		try:
			service = Service.objects.get(id=service_id)
			gateway_profile = GatewayProfile.objects.get(id=gateway_profile_id)
			channel = Channel.objects.get(id=int(payload['chid']))
			currency_code = payload['currency'] if 'currency' in payload.keys() and payload['currency']!='' else None
			currency = Currency.objects.get(code=currency_code) if currency_code is not None  else None
			amount = payload['amount'] if 'amount' in payload.keys() and payload['amount']!='' else None
			charges = payload['charges'] if 'charges' in payload.keys() and payload['charges']!='' else None
			raise_charges = payload['raise_charges'] if 'raise_charges' in payload.keys() and payload['raise_charges']!='' else None
			transaction_status = TransactionStatus.objects.get(name='CREATED')
			response_status = ResponseStatus.objects.get(response='DEFAULT')

			#ip_address MUST exist in payload. Identification of the originating IP is compulsory in all requests
			#Create co-ordinates if dont exist
			lng = payload['lng'] if 'lng' in payload.keys() else 0.0
			lat = payload['lat'] if 'lat' in payload.keys() else 0.0
			trans_point = Point(float(lng), float(lat))
			g = GeoIP2()

			msisdn = None
			if "msisdn" in payload.keys():
				msisdn = str(payload['msisdn']).strip()
				if len(msisdn) >= 9 and msisdn[:1] == '+':
					msisdn = str(msisdn)
				elif len(msisdn) >= 7 and len(msisdn) <=10 and msisdn[:1] == '0':
					country_list = Country.objects.filter(mpoly__intersects=trans_point)
					ip_point = g.geos(str(payload['ip_address']))
					if country_list.exists() and country_list[0].ccode:
						msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
					elif ip_point:
						country_list = Country.objects.filter(mpoly__intersects=ip_point)
						if country_list.exists() and country_list[0].ccode:
							msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
						else:
							msisdn = None
					else:
						msisdn = '+254%s' % msisdn[1:]
				elif len(msisdn) >=10  and msisdn[:1] != '0' and msisdn[:1] != '+':
					msisdn = '+%s' % msisdn #clean msisdn for lookup
				else:
					msisdn = None


			trans = Transaction(gateway_profile= gateway_profile,service = service, channel=channel, gateway=gateway_profile.gateway,\
					request = self.transaction_payload(payload),currency = currency,\
					amount = amount, charges = charges, raise_charges = raise_charges, \
					transaction_status = transaction_status, response_status = response_status,\
					ip_address = payload['ip_address'],geometry = trans_point)

			if msisdn is not None:
				try:msisdn = MSISDN.objects.get(phone_number=msisdn)
				except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();
				trans.msisdn = msisdn

			if 'institution_id' in payload.keys():
				trans.institution = Institution.objects.get(id=payload['institution_id'])

			if 'fingerprint' in payload.keys():
				trans.fingerprint = payload['fingerprint']

			if 'csrf_token' in payload.keys():
				trans.token = payload['csrf_token']
			elif 'csrfmiddlewaretoken' in payload.keys():
				trans.token = payload['csrfmiddlewaretoken']
			elif 'token' in payload.keys():
				trans.token = payload['token']
			if 'user_agent' in payload.keys():
				trans.user_agent = payload['user_agent']


			results = trans.save()

			self.response_params['response_status'] = '00'
			self.response_params['trans'] = trans
		except Exception as e:
			lgr.info('\n\n\n\n\n\t-----------------------------Error Logging Transaction: %s' % e)
			self.response_params['response_status'] = '96'
		return self.response_params

	def update_transaction(self, trans, payload, response):
		try:
			response_tree,count = {}, 1
			#Always Trim response to managable Items
			if 'response' in response.keys():
				for key, value in response['response'].items():
					key = key.lower()
					if key not in ['get_interface','get_section','login','get_institution_details','get_gateway_details','session']:
						key = str(key[:30])
						if count <= 20:
							response_tree[key] = str(value)[:100]
						else:
							break
						count = count+1
			lgr.info('Response Tree on Update: %s' % response_tree)
			trans.response_status = ResponseStatus.objects.get(response=str(response['response_status']))	
			trans.transaction_status = TransactionStatus.objects.get(name='PROCESSED')
			trans.overall_status = ResponseStatus.objects.get(response=str(response['overall_status']))	
			trans.response = json.dumps(response_tree)
			trans.save()
			response = True
		except Exception as e:
			response = False				 
			lgr.info('Error Updating Transaction: %s' % e)				
		return response


