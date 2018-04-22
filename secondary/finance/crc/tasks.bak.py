from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from crc.models import *
from django.db.models import Q
import hashlib, hmac, base64

import logging
lgr = logging.getLogger('secondary.finance.iic')
	

class Wrapper:
	def signature_check(self, payload):
		try:
			if 'signed_field_names' in payload.keys():
				SECRET_KEY = '080df2e12ca74a62a488a1aea2d05f7c7f138b1001234481b60b468cf664e4de2f759b40ea6541b39166c821382bbbd50cbea337c4ae4d55991412c235a008022ef8f925a7874eb19bd174964c5e8ed4af37913f1cee4f61b703eebdb3258d76dbaef09088414a0d9656266b8a8d55f2bc5a891bb30142f58113d9bf87339e30'

		                p = []
        		        for key in payload['signed_field_names'].split(','):
					if key in payload.keys():
						k = '%s=%s' % (key,payload[key])
					else:
						k = '%s=' % (key)
					p.append(k)
				p1 = ','.join(p)
				lgr.info("Hash String: %s" % p1)
				a = hmac.new( SECRET_KEY, p1, hashlib.sha256)
				signature = base64.b64encode(a.digest())
			payload['signature'] = signature
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Check Signature: %s" % e)
		return payload


class System(Wrapper):
	def register_token(self, payload, node_info):
		try:
			req_signature = payload['signature']
			payload = self.signature_check(payload)
			if base64.b64decode(req_signature) == base64.b64decode(payload['signature']):
				transaction = Transaction.objects.get(id=payload['req_transaction_uuid'])
				user = transaction.user
				processor = Processor.objects.get(name='bbk_mipay_7298516_kes')
				card_type = CardType.objects.filter(processor__currency__code=payload['req_currency'],processor=processor,reference=payload['req_card_type'])
				card_record = CardRecord.objects.filter(status__name='ACTIVE',card_number=payload['req_card_number'],card_expiry_date=payload['req_card_expiry_date'],card_type=card_type[0])
				status = CardRecordStatus.objects.get(name='ACTIVE')
				if len(card_record)>0:
					card_record = card_record[0]
					card_record.user=user;card_record.status =status;card_record.bill_to_forename=payload['req_bill_to_forename'];
					card_record.bill_to_surname=payload['req_bill_to_surname'];card_record.bill_to_email=payload['req_bill_to_email'];
					card_record.bill_to_address_line1=payload['req_bill_to_address_line1'];card_record.bill_to_address_city=payload['req_bill_to_address_city'];
					card_record.bill_to_address_country=payload['req_bill_to_address_country'];
					card_record.bill_to_address_postal_code=payload['req_bill_to_address_postal_code'];card_record.card_number=payload['req_card_number'];
					card_record.card_type=card_type[0];card_record.card_expiry_date=payload['req_card_expiry_date'];card_record.payment_token=payload['payment_token'];
					card_record.processor=processor;	
				else:
					card_record = CardRecord(user=user,status =status,bill_to_forename=payload['req_bill_to_forename'],
						bill_to_surname=payload['req_bill_to_surname'],bill_to_email=payload['req_bill_to_email'],\
						bill_to_address_line1=payload['req_bill_to_address_line1'],bill_to_address_city=payload['req_bill_to_address_city'],\
						bill_to_address_country=payload['req_bill_to_address_country'],\
						bill_to_address_postal_code=payload['req_bill_to_address_postal_code'],card_number=payload['req_card_number'],\
						card_type=card_type[0],card_expiry_date=payload['req_card_expiry_date'],payment_token=payload['payment_token'],\
						processor=processor)
				if 'req_bill_to_phone' in payload.keys():
					card_record.bill_to_phone = payload['req_bill_to_phone']
				if 'req_bill_to_address_state' in payload.keys():
					card_record.bill_to_address_state= payload['req_bill_to_address_state']

				card_record.save()
				payload['response'] = "Token Registered"
				payload['response_status'] = '00'
			else:
				lgr.info("Request Signature: %s Signature: %s" % (str(req_signature)[:100], str(payload['signature'])[:100]))
				payload['response_status'] = '15'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error Registering Token: %s" % e)
		return payload

	def process_cybersource_details(self, payload, node_info):
		try:
			payload['access_key'] = 'ecfcf5f2877738c19368f5fae98346b4'
			payload['locale'] = 'en'
			payload['profile_id'] = '28A2B9DC-5F48-470A-9D56-983AFE5CBB43'
			if 'payment_method' in payload.keys():
				payment_method = PaymentMethod.objects.get(id=payload['payment_method'])
				payload['currency'] = payment_method.processor.currency.code
				if payment_method.name == 'card':
					payload['trigger'] = 'CARD'

			payload['amount'] = '38'
			payload['unsigned_field_names'] = 'card_type,card_number,card_expiry_date,bill_to_forename,bill_to_surname,bill_to_email,bill_to_phone,bill_to_address_line1,bill_to_address_city,bill_to_address_state,bill_to_address_country,bill_to_address_postal_code'
			payload['signed_field_names'] = 'access_key,profile_id,transaction_uuid,signed_field_names,unsigned_field_names,signed_date_time,locale,transaction_type,reference_number,amount,currency,payment_method'
			payload['transaction_uuid'] = payload['bridge__transaction_id']
			payload['signed_date_time'] = payload['transaction_timestamp']
			payload['transaction_type'] = 'sale,create_payment_token'
			payload['reference_number'] = 'MPY*12453'
			payload['payment_method'] = 'card'
			payload = self.signature_check(payload)
			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				payload['response'] = 'Details Processed Succesfully'
			lgr.info('Final Payload: %s' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error Processing Cybersource Details: %s" % e)
		return payload

class Registration(System):
	pass

class Trade(System):
	pass

class Payments(System):
	pass


lgr = get_task_logger(__name__)
#Celery Tasks Here
