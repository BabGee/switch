from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
#from secondary.channels.vbs.models import *

from django.db.models import Q
import hashlib, hmac, base64, string, random
from decimal import Decimal
from datetime import datetime
import base64, re, crypt

from .models import *
import logging
lgr = logging.getLogger('secondary.finance.crc')
	
from keyczar import keyczar
location = '/opt/kz'
crypter = keyczar.Crypter.Read(location)

class Wrapper:
	mask_card = lambda self, q: "%s%s%s" % (q[:4],"".join(['*' for v in range(len(q)-8)]),q[len(q)-4:]) #Show's first 4 digits and used to preview card
	mask_pan = lambda self, q: "%s%s%s" % (q[:6],"".join(['*' for v in range(len(q)-10)]),q[len(q)-4:]) #Shows first 6 digits and used in search
	def cc_type(self,cc_number):
		import re
		AMEX_CC_RE = re.compile(r"^3[47][0-9]{13}$")
		VISA_CC_RE = re.compile(r"^4[0-9]{12}(?:[0-9]{3})?$")
		MASTERCARD_CC_RE = re.compile(r"^5[1-5][0-9]{14}$")
		DISCOVER_CC_RE = re.compile(r"^6(?:011|5[0-9]{2})[0-9]{12}$")
		DINERS_CC_RE = re.compile(r"^3[068][0-9]{12}$")
		JCB_CC_RE = re.compile(r"^3[013][13589][2678][0-9]{12}$")

		CC_MAP = {"003": AMEX_CC_RE, "001": VISA_CC_RE,
			     "002": MASTERCARD_CC_RE, "004": DISCOVER_CC_RE, "005": DINERS_CC_RE, "007": JCB_CC_RE}

		for type, regexp in CC_MAP.items():
			if regexp.match(str(cc_number)):
				return type
		return None


class System(Wrapper):
	def card_present_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if 'currency' not in payload.keys():
				payload['currency']= 'KES'
			if 'amount' in payload.keys():
				payload['amount']= Decimal(payload['amount'])
			else:
				payload['amount']= Decimal(0)

			if payload['entry_mode'] == 'contact':
				track_data = payload['card_track_data']
				track_data = track_data.replace('D','=')
				track_data = track_data.replace('F','?')
				track_data = ';%s'% track_data
				payload['card_track_data'] = track_data
			

			chars = string.digits
			rnd = random.SystemRandom()
			pin = ''.join(rnd.choice(chars) for i in range(0,4))

			payload['merchant_descriptor'] = 'MIPAY*%s' % pin
			payload['reference'] = 'REF%s' % pin

			payload['response_status'] = '00'
			payload['response'] = 'Card Present Details Captured'
		except Exception as e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Card Present Details: %s" % e)
		return payload


	def add_card_record(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			accountNumber = str(payload['card_accountnumber']).replace(' ','')
			pan = self.mask_pan(accountNumber)

			token = crypter.Encrypt(accountNumber)

			cvNumber = str(payload['card_cvnumber']) if 'card_cvnumber' in payload.keys() else ''

			cardType = str(self.cc_type(accountNumber))

			if 'card_expirationdate' in payload.keys():
				card_expirationDate = payload['card_expirationdate']

				expirationMonth = str(card_expirationDate.split('/')[0])
				expirationYear = str(card_expirationDate.split('/')[1])
			else:
				expirationMonth = str(payload['card_expirationmonth'])
				expirationYear = str(payload['card_expirationyear'])

			expiry_date = '20%s-%s-01' % (expirationYear,expirationMonth)
			expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()

			card_record_status = CardRecordStatus.objects.get(name='CREATED')
			card_type = CardType.objects.get(code=cardType)


			activation_currency = Currency.objects.get(code=payload['currency'])
			activation_amount = Decimal(payload['amount'])
			activation_pin = crypt.crypt(str(payload['activation_pin']), str(gateway_profile.id))


			card_record = CardRecord(status=card_record_status, card_number=self.mask_card(accountNumber), card_type=card_type,\
						card_expiry_date=expiry_date, token=token, gateway_profile=gateway_profile,\
						pan=pan, activation_currency=activation_currency, activation_amount=activation_amount,\
						activation_pin=activation_pin)

			if CardRecord.objects.filter(gateway_profile=gateway_profile,status__name='ACTIVE').exists() == False:
				card_record.is_default = True

			card_record.save()

			payload['pan'] = card_record.pan

			payload['response_status'] = '00'
			payload['response'] = 'Card Added'
		except Exception as e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Add Card Record: %s" % e)
		return payload

	def card_verification_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			accountNumber = str(payload['card_accountnumber']).replace(' ','')

			pan = self.mask_pan(accountNumber)
			card_record = CardRecord.objects.filter(pan=pan,status__name__in=['ACTIVE','CREATED'])
			if card_record.exists():
				if card_record.filter(gateway_profile=gateway_profile).exists():
					payload['response_status'] = '26'
					payload['response'] = 'Card Record Exists'
				else:
					payload['response_status'] = '26'
					payload['response'] = 'Card Record Added by a different Profile'
			else:
				account = Account.objects.filter(account_type__deposit_taking=True, is_default=True,\
						gateway_profile=gateway_profile)

				if account.exists():
					currency_code = account[0].account_type.product_item.currency.code
				else:
					currency_code = 'KES'
				cva = CardVerificationAmount.objects.get(currency__code=currency_code)
				amount = Decimal(random.uniform(float(cva.min_amount), float(cva.max_amount))).quantize(Decimal('.01'))

				payload['ignore_avs_result'] = False
				payload['ignore_cv_result'] = False

				payload['pan'] = pan
				payload['currency'] = currency_code
				payload['amount'] = amount
				chars = string.digits
				rnd = random.SystemRandom()
				pin = ''.join(rnd.choice(chars) for i in range(0,4))

				payload['activation_pin'] = '%s' % pin
				payload['merchant_descriptor'] = 'MIPAY*%s*CODE' % pin
				payload['reference'] = 'MIPAY*%s*CODE' % pin
				payload['response_status'] = '00'
				payload['response'] = 'Card Captured'
		except Exception as e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Card Verification Details: %s" % e)
		return payload

	def get_cards(self, payload, node_info):
		try:

			accountNumber = str(payload['card_accountnumber']).replace(' ','')

			pan = self.mask_pan(accountNumber)
			payload['pan'] = pan

			payload['response_status'] = '00'
			payload['response'] = 'Card Captured'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Card: %s" % e)
		return payload

class Registration(System):
	pass

class Trade(System):
	pass

class Payments(System):
	pass


lgr = get_task_logger(__name__)
#Celery Tasks Here
