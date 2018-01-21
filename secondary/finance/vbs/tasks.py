from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from switch.celery import single_instance_task

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q, F
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json, pytz
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError, DatabaseError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.db import transaction
from django.core.files import File
import base64, re, operator
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers

from secondary.finance.vbs.models import *
from primary.core.upc.tasks import Wrappers as UPCWrappers
import logging
lgr = logging.getLogger('vbs')

class Wrappers:
        def validateEmail(self, email):
                try:
                        validate_email(str(email))
                        return True
                except ValidationError:
                        return False

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
	def log_installment(self, payload, node_info):
		try:

			session_account = Account.objects.get(id=payload['session_account_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			account_manager = AccountManager.objects.get(id=payload['account_manager_id'])
			amount = account_manager.amount
			charge =  account_manager.charge

			credit_type = SavingsCreditType.objects.filter(account_type=account_manager.dest_account.account_type,\
					 min_time__lte=int(payload['loan_time']), max_time__gte=int(payload['loan_time']))

			interest = Decimal(0)
			savings_credit_list = []
			chunks,chunk_size = 0, 0
			count = 0
			if credit_type.exists() and account_manager.credit_time > credit_type[0].installment_time:
				chunks, chunk_size = account_manager.credit_time, credit_type[0].installment_time
				for i in range(0, chunks, chunk_size): count += 1
			elif 'installment_time' in payload.keys() and account_manager.credit_time > int(payload['installment_time']):
				chunks, chunk_size = account_manager.credit_time, int(payload['installment_time'])
				for i in range(0, chunks, chunk_size): count += 1

			if count > 1:
				for i in range(0, chunks, chunk_size):
					installment_time = i+chunk_size
					installment_amount = amount/count
					installment_charge = charge/count
					due_date = timezone.now()+timezone.timedelta(days=installment_time)
					savings_credit_manager = SavingsCreditManager(account_manager=account_manager,\
								credit=account_manager.credit,installment_time=installment_time,\
								amount=installment_amount,charge=installment_charge,\
								due_date=due_date)
					savings_credit_list.append(savings_credit_manager)
			else:

					savings_credit_manager = SavingsCreditManager(account_manager=account_manager,\
								credit=account_manager.credit,installment_time=account_manager.credit_time,\
								amount=account_manager.amount,charge=account_manager.charge,\
								due_date=account_manager.credit_due_date)
					savings_credit_list.append(savings_credit_manager)

			if len(savings_credit_list)>0: SavingsCreditManager.objects.bulk_create(savings_credit_list)
			payload['response_status'] = '00'
			payload['response'] = 'Installment Logged'


		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on log installment: %s" % e)
		return payload


	def get_account_details(self, payload, node_info):
		try:
			account = Account.objects.get(id=payload['account_id'])

			payload['full_names'] = '%s %s %s' % (account.profile.user.first_name, account.profile.middle_name, account.profile.user.last_name)
			#payload['msisdn'] = '%s' % account.gateway_profile.msisdn
			payload['loan_limit'] = account.credit_limit
			payload['account_type'] = account.account_type.name
			payload['national_id'] = account.profile.national_id

			payload['response_status'] = '00'
			payload['response'] = 'Details Captured'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on get account details: %s" % e)
		return payload

	def account_option(self, payload, node_info):
		try:
			from upc.tasks import System as UPCSystem
			from vcs.tasks import System as VCSSystem
			from notify.tasks import System as NotifySystem
			from paygate.tasks import System as PaygateSystem

			if payload['account_option'] == 'Change Pin':
				payload = UPCSystem().get_profile(payload, node_info)
				if payload['response_status'] == '00':
					payload = UPCSystem().set_profile_pin(payload, node_info)
			elif payload['account_option'] == 'Add/Change Email':
				payload = UPCSystem().get_profile(payload, node_info)
				if payload['response_status'] == '00':
					payload = UPCSystem().add_change_email(payload, node_info)
				if payload['response_status'] == '00':
					payload['SERVICE'] = 'RESET PASSWORD'
					payload['chid'] = '1'
					payload = VCSSystem().session(payload, node_info) 
				if payload['response_status'] == '00':
					payload = UPCSystem().get_gateway_details(payload, node_info)
				if payload['response_status'] == '00':
					payload = NotifySystem().get_email_notification(payload, node_info)
				if payload['response_status'] == '00':
					payload = PaygateSystem().debit_float(payload, node_info)
				if payload['response_status'] == '00':
					payload = NotifySystem().send_notification(payload, node_info)
			elif payload['account_option'] == 'General Inquiry':
				payload = UPCSystem().get_profile(payload, node_info)

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on account option: %s" % e)
		return payload



	def account_statement(self, payload, node_info):
		try:
			account = Account.objects.get(id=payload['session_account_id'])

			account_manager_list = AccountManager.objects.filter(dest_account=account,dest_account__account_type__id=payload['account_type_id']).\
						order_by('-date_created')[:5]

			statement_info = 'Balance-Charges-Amount-Date'
			if account_manager_list.exists():
				for a in account_manager_list:
					tdate = a.date_created.strftime("%d/%b/%Y")
					statement_info = '%s\n%s(%s)%s-%s-%s-%s' % (statement_info,'Credit' if a.credit else 'Debit',\
							a.dest_account.account_type.product_item.currency.code,\
							'{0:,.2f}'.format(a.balance_bf),'{0:,.2f}'.format(a.charge),'{0:,.2f}'.format(a.amount),tdate)
			else:
				statement_info = 'No Transaction Record Available'

			payload['response_status'] = '00'
			payload['response'] = statement_info

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan status: %s" % e)
		return payload

	def mipay_account_balance(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			#MIPAY is an overall gateway account for MIPAY PROFILES only tagged by MSISDN/EMAIL/PROFILE
			if 'msisdn' in payload.keys():
				msisdn = UPCWrappers().get_msisdn(payload)
				session_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,msisdn__phone_number=msisdn)
			elif 'email' in payload.keys() and payload['email'] not in [None,""] and self.validateEmail(payload['email']):
				session_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,user__email=payload['email'])
			elif gateway_profile.msisdn is not None:
				session_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,msisdn__phone_number=gateway_profile.msisdn.phone_number)
			elif gateway_profile.user.email not in ['', none] and self.validateEmail(gateway_profile.user.email):
				session_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,user__email=gateway_profile.user.email)
			else:
				session_gateway_profile = GatewayProfile.objects.none()

			if session_gateway_profile.exists():
				account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
								dest_account__profile=session_gateway_profile[0].user.profile,\
								dest_account__account_type__gateway__name='MIPAY').order_by("-date_created")[:1]
			else:
				account_manager = AccountManager.objects.none()

			if account_manager.exists():
				manager = account_manager[0]
				payload['balance_bf'] = manager.balance_bf
				payload['amount'] = manager.balance_bf
				payload['currency'] = account_manager[0].dest_account.account_type.product_item.currency.code
				payload['response_status'] = '00'
				payload['response'] = '%s %s' % (payload['currency'], '{0:,.2f}'.format(payload['amount']))
			else:
				payload['balance_bf'] = Decimal(0)
				payload['amount'] = Decimal(0)
				payload['currency'] = 'KES'
				payload['response_status'] = '00'
				payload['response'] = '%s %s' % (payload['currency'], '{0:,.2f}'.format(payload['amount']))

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on get account: %s" % e)
		return payload

	def account_balance(self, payload, node_info):
		try:
			lgr.info('Session Account ID: %s' % payload['session_account_id'])
			account_manager = AccountManager.objects.filter(dest_account__id=payload['session_account_id']).order_by("-date_created")[:1]

			if account_manager.exists():
				manager = account_manager[0]
				payload['balance_bf'] = manager.balance_bf
				payload['amount'] = manager.balance_bf
				payload['currency'] = account_manager[0].dest_account.account_type.product_item.currency.code
				payload['response_status'] = '00'
				payload['response'] = '%s %s' % (payload['currency'], '{0:,.2f}'.format(payload['amount']))
			else:

				payload['response'] = 'No Account Balance Record Found'
				payload['response_status'] = '25'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on get account: %s" % e)
		return payload


	def debit_account_reversal(self, payload, node_info):
		try:
			account_manager = AccountManager.objects.filter(transaction_reference=payload['bridge__transaction_id']).order_by("-date_created")
		
			if len(account_manager)>0:
				for m in account_manager:
					if m.is_reversal:
						break
					else:
						if m.credit:
							credit = False
							if m.dest_account.account_type.product_item.product_type.name=='Ledger Account': #Ledger accounts add charges on DR as other accounts deduct charges on DR
								balance_bf = Decimal((m.balance_bf - m.charge) - m.amount)
							else:
								balance_bf = Decimal((m.balance_bf + m.charge) - m.amount)
						else:
							credit = True
							if m.dest_account.account_type.product_item.product_type.name=='Ledger Account': #Ledger accounts add charges on DR as other accounts deduct charges on DR
								balance_bf = Decimal((m.balance_bf - m.charge) + m.amount)
							else:
								balance_bf = Decimal((m.balance_bf + m.charge) + m.amount)

						manager = AccountManager(credit=credit, transaction_reference=payload['bridge__transaction_id'],\
							is_reversal=True,source_account=m.source_account,dest_account=m.dest_account,\
							amount=Decimal(m.amount).quantize(Decimal('.01'), rounding=ROUND_DOWN),
							charge=m.charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
							balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN))


						manager.save()

				payload['response_status'] = '00'
				payload['response'] = 'Account Debiting  Reversed'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No Reversal Activities Found'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on debit account reversal: %s" % e)
		return payload

	def credit_account_reversal(self, payload, node_info):
		try:

			account_manager = AccountManager.objects.filter(transaction_reference=payload['bridge__transaction_id']).order_by("-date_created")

			if len(account_manager)>0:
				for m in account_manager:
					if m.is_reversal:
						break
					else:
						if m.credit:
							credit = False
							if m.dest_account.account_type.product_item.product_type.name=='Ledger Account': #Ledger accounts add charges on DR as other accounts deduct charges on DR
								balance_bf = Decimal((m.balance_bf - m.charge) - m.amount)
							else:
								balance_bf = Decimal((m.balance_bf + m.charge) - m.amount)
						else:
							credit = True
							if m.dest_account.account_type.product_item.product_type.name=='Ledger Account': #Ledger accounts add charges on DR as other accounts deduct charges on DR
								balance_bf = Decimal((m.balance_bf - m.charge) + m.amount)
							else:
								balance_bf = Decimal((m.balance_bf + m.charge) + m.amount)


						manager = AccountManager(credit=credit, transaction_reference=payload['bridge__transaction_id'],\
							is_reversal=True,source_account=m.source_account,dest_account=m.dest_account,\
							amount=Decimal(m.amount).quantize(Decimal('.01'), rounding=ROUND_DOWN),
							charge=m.charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
							balance_bf=balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN))
						manager.save()

				payload['response_status'] = '00'
				payload['response'] = 'Account Crediting Reversed'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No Reversal Activities Found'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on get account: %s" % e)
		return payload

	def loan_notification_details(self, payload, node_info):
		try:
			#Edit Debit Account
			session_account = Account.objects.get(id=payload['session_account_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Check loan exists
			#session_manager = AccountManager.objects.get(id=payload['account_manager_id'], credit_paid=False, credit_due_date__lte=timezone.now())
			session_manager = AccountManager.objects.get(id=payload['account_manager_id'], credit_paid=False)

			#Find the last loan amount
			session_manager_list = AccountManager.objects.filter(id__gte=payload['account_manager_id'],credit=False,\
						dest_account=session_manager.dest_account, dest_account__account_type=session_manager.dest_account.account_type,\
						credit_paid=False).order_by('-date_created')[:1]
			o = session_manager_list[0]
			amount = o.balance_bf*Decimal(-1)

			due_date = session_manager.credit_due_date
			due_date = due_date.strftime("%d/%b/%Y")
			payload['due_date'] = due_date

			payload['currency'] = session_manager.dest_account.account_type.product_item.currency.code
			payload['amount'] = amount.quantize(Decimal('.01'), rounding=ROUND_DOWN)

			payload['response_status'] = '00'
			payload['response'] = 'Loan Notification Details Captured'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan rollover details: %s" % e)
		return payload


	def loan_rollover_details(self, payload, node_info):
		try:
			#Edit Debit Account
			session_account = Account.objects.get(id=payload['session_account_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			session_manager = AccountManager.objects.get(id=payload['account_manager_id'], credit_paid=False, credit_due_date__lte=timezone.now())
			amount = session_manager.amount + session_manager.charge


			credit_type = SavingsCreditType.objects.filter(account_type=session_manager.dest_account.account_type,\
					 min_time__lte=int(payload['rollover_loan_time']), max_time__gte=int(payload['rollover_loan_time']))

			interest = Decimal(0)
			for c in credit_type:
				interest =  interest + ((c.interest_rate/100)*(int(payload['rollover_loan_time'])/c.interest_time)*Decimal(amount))

			due_date = session_manager.credit_due_date
			due_date = due_date.strftime("%d/%b/%Y")
			payload['due_date'] = due_date

			payload['quantity'] = interest.quantize(Decimal('.01'), rounding=ROUND_DOWN)
			payload['amount'] = interest.quantize(Decimal('.01'), rounding=ROUND_DOWN)

			payload['response_status'] = '00'
			payload['response'] = 'Rollover Details Captured'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan rollover details: %s" % e)
		return payload

	@transaction.atomic
	def debit_account(self, payload, node_info):
		try:

			session_account = Account.objects.get(id=payload['session_account_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Ensure Branch does not conflict to give more than one result
			gl_account_type = AccountType.objects.filter(product_item__currency__code=payload['currency'],\
						product_item__product_type__name='Ledger Account',\
						gateway=session_account.account_type.gateway)
			if 'institution_id' in payload.keys():
				gl_account_type = gl_account_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))


			gl_acccount = Account.objects.filter(account_status__name='ACTIVE',account_type=gl_account_type[0])



			session_account_manager = AccountManager.objects.select_for_update(nowait=True).filter(dest_account = session_account,dest_account__account_type=session_account.account_type).order_by('-date_created')
			gl_account_manager = AccountManager.objects.filter(dest_account = gl_acccount[0],dest_account__account_type=gl_account_type[0]).order_by('-date_created')


			#Get Charge amount and transfer charge amount to charge account (just like MIPAY LEDGER)
			charge = Decimal(0)
			charge_list = AccountCharge.objects.filter(account_type=session_account.account_type, min_amount__lte=Decimal(payload['amount']), service__name=payload['SERVICE'],\
					max_amount__gte=Decimal(payload['amount']),credit=False)
			if 'payment_method' in payload.keys():
				charge_list = charge_list.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))
			for c in charge_list:
				if c.is_percentage:
					charge = charge + ((c.charge_value/100)*Decimal(payload['amount']))
				else:
					charge = charge+c.charge_value		

			#For loan Accounts (Adding Interest To Charge) #Loans only Debit accounts
			'''
			if account_type.loan_interest_rate and account_type.loan_time:
				charge = charge + ((account_type.loan_interest_rate/100)*Decimal(payload['amount']))
			'''

			#For loan Accounts (Adding Interest To Charge) #Loans only Debit accounts
			if 'is_loan' in payload.keys() and payload['is_loan'] and 'loan_time' in payload.keys():
				credit_type = SavingsCreditType.objects.filter(account_type=session_account.account_type,\
								 min_time__lte=int(payload['loan_time']), max_time__gte=int(payload['loan_time']))

				for c in credit_type:
					charge = charge + ((c.interest_rate/100)*(int(payload['loan_time'])/c.interest_time)*Decimal(payload['amount']))

				payload['quantity'] = Decimal(payload['amount'])+charge
	
			#gl account #GL A/c ALWAYS adds Charges (GL also Charge Account)
			if len(gl_account_manager)>0:
				gl_balance_bf = Decimal(gl_account_manager[0].balance_bf) + (Decimal(payload['amount']) + charge)
			else:
				gl_balance_bf = Decimal(payload['amount']) + charge

			#session account
			if session_account_manager.exists():
				session_balance_bf = Decimal(session_account_manager[0].balance_bf) - (Decimal(payload['amount']) + charge)
			else:
				session_balance_bf = Decimal(0) - (Decimal(payload['amount']) + charge)

			credit_overdue = None
			if 'credit_overdue_id' in payload.keys() and 'product_item_id' in payload.keys():
				try:
					credit_overdue = CreditOverdue.objects.get(id=payload['credit_overdue_id'],product_item__id=payload['product_item_id'])
				except CreditOverdue.DoesNotExist: pass

			if ( Decimal(session_balance_bf) <= Decimal(session_account.account_type.max_balance) and Decimal(session_balance_bf) >= Decimal(session_account.account_type.min_balance) ) or credit_overdue:

				#Last Balance Check
				if session_account_manager.exists():session_account_manager.filter(id=session_account_manager[:1][0].id).update(updated=True)

				session_manager = AccountManager(credit=False, transaction_reference=payload['bridge__transaction_id'],\
					source_account=gl_acccount[0],dest_account=session_account,\
					amount=Decimal(payload['amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
					charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
					balance_bf=session_balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN))

				if 'is_loan' in payload.keys() and payload['is_loan'] and 'loan_time' in payload.keys():
					session_manager.credit_time = int(payload['loan_time'])
					session_manager.credit_due_date = timezone.now() + timezone.timedelta(days=int(payload['loan_time']))

				session_manager.save()

				if 'credit_overdue_id' in payload.keys():
					session_manager.credit_overdue.add(CreditOverdue.objects.get(id=payload['credit_overdue_id']))

				gl_manager = AccountManager(credit=True, transaction_reference=payload['bridge__transaction_id'],\
					source_account=session_account,dest_account=gl_acccount[0],\
					amount=Decimal(payload['amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
					charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
					balance_bf=gl_balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN))
				gl_manager.save()

				payload['account_manager_id'] = session_manager.id
				payload['balance_out'] = session_manager.amount
				payload['balance_bf'] = session_manager.balance_bf
				payload['response_status'] = '00'
				payload['response'] = 'Account Debited'
			else:
				payload['response_status'] = '61' #Exceeds Withdrawal Limit
		except DatabaseError, e:
			transaction.set_rollback(True)


		except Exception, e:
			payload['response_status'] = '96'
			#payload['response'] = str(e)
			lgr.info("Error on debit account: %s" % e)
		return payload


	@transaction.atomic
	def credit_account(self, payload, node_info):
		try:

			session_account = Account.objects.get(id=payload['session_account_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Ensure Branch does not conflict to give more than one result
			gl_account_type = AccountType.objects.filter(product_item__currency__code=payload['currency'],\
						product_item__product_type__name='Ledger Account',\
						gateway=session_account.account_type.gateway)
			if 'institution_id' in payload.keys():
				gl_account_type = gl_account_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))

			gl_acccount = Account.objects.filter(account_status__name='ACTIVE',account_type=gl_account_type[0])

			session_account_manager = AccountManager.objects.select_for_update(nowait=True).filter(dest_account = session_account, dest_account__account_type=session_account.account_type).order_by('-date_created')
			gl_account_manager = AccountManager.objects.filter(dest_account = gl_acccount[0], dest_account__account_type=gl_account_type[0]).order_by('-date_created')

			charge = Decimal(0)
			charge_list = AccountCharge.objects.filter(account_type=session_account.account_type, min_amount__lte=Decimal(payload['amount']), service__name=payload['SERVICE'],\
					max_amount__gte=Decimal(payload['amount']),credit=True)
			if 'payment_method' in payload.keys():
				charge_list = charge_list.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			for c in charge_list:
				if c.is_percentage:
					charge = charge + ((c.charge_value/100)*Decimal(payload['amount']))
				else:
					charge = charge+c.charge_value		

			#gl account #GL A/c ALWAYS adds Charges (GL also Charge Account)
			if len(gl_account_manager)>0:
				gl_balance_bf = Decimal((gl_account_manager[0].balance_bf + charge) - Decimal(payload['amount']))
			else:
				gl_balance_bf = Decimal((Decimal(0) + charge) - Decimal(payload['amount']))

			#session account
			if session_account_manager.exists():
				session_balance_bf = Decimal(session_account_manager[0].balance_bf) + (Decimal(payload['amount']) - charge)
			else:
				session_balance_bf = Decimal(payload['amount']) - charge

			if Decimal(session_balance_bf) <= Decimal(session_account.account_type.max_balance) and Decimal(session_balance_bf) >= Decimal(session_account.account_type.min_balance):

				#Last Balance Check
				if session_account_manager.exists():session_account_manager.filter(id=session_account_manager[:1][0].id).update(updated=True)

				session_manager = AccountManager(credit=True, transaction_reference=payload['bridge__transaction_id'],\
					source_account=gl_acccount[0],dest_account=session_account,\
					amount=Decimal(payload['amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
					charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
					balance_bf=session_balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN))

				session_manager.save()

				gl_manager = AccountManager(credit=False, transaction_reference=payload['bridge__transaction_id'],\
					source_account=session_account,dest_account=gl_acccount[0],\
					amount=Decimal(payload['amount']).quantize(Decimal('.01'), rounding=ROUND_DOWN),
					charge=charge.quantize(Decimal('.01'), rounding=ROUND_DOWN),
					balance_bf=gl_balance_bf.quantize(Decimal('.01'), rounding=ROUND_DOWN))

				gl_manager.save()

				payload['account_manager_id'] = session_manager.id
				payload['balance_in'] = session_manager.amount
				payload['balance_bf'] = session_manager.balance_bf
				payload['response_status'] = '00'
				payload['response'] = 'Account Credited'
			else:
				payload['response_status'] = '98' #Exceeds cash limit
				payload['response'] = 'Max Deposit limit reached'
		except DatabaseError, e:
			transaction.set_rollback(True)

		except Exception, e:
			payload['response_status'] = '96'
			#payload['response'] = str(e)
			lgr.info("Error on credit account: %s" % e)
		return payload


	def get_mipay_account(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if 'msisdn' in payload.keys():
				msisdn = UPCWrappers().get_msisdn(payload)
				mipay_gateway_profile = GatewayProfile.objects.filter(gateway__name='MIPAY',msisdn__phone_number=msisdn)
			elif 'email' in payload.keys() and payload['email'] not in [None,""] and self.validateEmail(payload['email']):
				mipay_gateway_profile = GatewayProfile.objects.filter(gateway__name='MIPAY',user__email=payload['email'])
			elif gateway_profile.msisdn is not None:
				mipay_gateway_profile = GatewayProfile.objects.filter(gateway__name='MIPAY',msisdn__phone_number=gateway_profile.msisdn.phone_number)
			elif gateway_profile.user.email not in ['', none] and self.validateEmail(gateway_profile.user.email):
				mipay_gateway_profile = GatewayProfile.objects.filter(gateway__name='MIPAY',user__email=gateway_profile.user.email)
			else:
				mipay_gateway_profile = GatewayProfile.objects.none()

			if mipay_gateway_profile.exists():
				session_account = Account.objects.filter(account_status__name='ACTIVE',
									profile=mipay_gateway_profile[0].user.profile,\
									account_type__gateway__name='MIPAY')
			else:
				session_account = Account.objects.none()

			if 'account_type_id' in payload.keys():
				session_account = session_account.filter(account_type__id=payload['account_type_id'])

			if 'account_name' in payload.keys():
				session_account = session_account.filter(account_type__name=payload['account_name'])

			if 'currency' in payload.keys():
				session_account = session_account.filter(account_type__product_item__currency__code=payload['currency'])

			#No institution ID check as MIPAY is institution agnostic

			if session_account.exists():
				payload['session_account_id'] = session_account[0].id
				payload['response_status'] = '00'
				payload['response'] = 'Account Captured'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No MIPAY Account Found'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on get account: %s" % e)
		return payload




	def get_account(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if 'session_gateway_profile_id' in payload.keys():
				session_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,id=payload['session_gateway_profile_id'])
			else:
				session_gateway_profile = GatewayProfile.objects.none()

			if session_gateway_profile.exists():
				session_account = Account.objects.filter(account_status__name='ACTIVE', profile=session_gateway_profile[0].user.profile)
			else:
				session_account = Account.objects.filter(account_status__name='ACTIVE', profile=gateway_profile.user.profile)

			#Filters
			if 'account_type_id' in payload.keys():
				session_account = session_account.filter(account_type__id=payload['account_type_id'])

			if 'account_name' in payload.keys():
				session_account = session_account.filter(account_type__name=payload['account_name'])

			if 'currency' in payload.keys():
				session_account = session_account.filter(account_type__product_item__currency__code=payload['currency'])

			if 'institution_id' in payload.keys():
				session_account = session_account.filter(Q(account_type__institution__id=payload['institution_id'])|Q(account_type__institution=None))

			if session_account.exists():
				payload['session_account_id'] = session_account[0].id

				payload['response_status'] = '00'
				payload['response'] = 'Account Captured'

			else:
				if session_gateway_profile.exists():
					profile = session_gateway_profile[0].user.profile
				else:
					profile = gateway_profile.user.profile


				#create account
				if 'currency' in payload.keys():
					currency = Currency.objects.get(code=payload['currency'])
				else:
					currency = Currency.objects.get(code='KES')

				status = AccountStatus.objects.get(name='ACTIVE')

				account_type = AccountType.objects.filter(Q(product_item__currency=currency),\
						Q(gateway=gateway_profile.gateway),\
						~Q(product_item__product_type__name='Ledger Account'))

				lgr.info('Account Type: %s' % account_type)
				if 'account_type' in payload.keys():
					account_type = account_type.filter(name=payload['account_type'])

				lgr.info('Account Type: %s' % account_type)
				if 'account_type_id' in payload.keys():
					account_type = account_type.filter(id=payload['account_type_id'])

				lgr.info('Account Type: %s' % account_type)
				if 'institution_id' in payload.keys():
					account_type = account_type.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))

				lgr.info('Account Type: %s' % account_type)
				if account_type.exists():
					session_account = Account(profile=profile,\
							account_status=status, account_type=account_type[0])

					#Check if profile account is first then default
					if Account.objects.filter(profile=profile,\
					 account_type__gateway=gateway_profile.gateway, account_type__deposit_taking=True).exists() == False and account_type[0].deposit_taking:
						session_account.is_default = True

					session_account.save()
					payload['session_account_id'] = session_account.id
					payload['response_status'] = '00'
					payload['response'] = 'Account Captured'
				else:
					payload['response_status'] = '25'
					payload['response'] = 'Account Type Does not Exist'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on get account: %s" % e)
		return payload


class Trade(System):
	pass

class Payments(System):
	def send_money_details(self, payload, node_info):
		try:
			account = Account.objects.get(id=payload['session_account_id'])
			product_item = account.account_type.product_item
			payload['product_item_id'] = product_item.id
			#payload['till_number'] = product_item.product_type.institution_till.till_number
			payload['currency'] = product_item.currency.code
			payload['float_amount'] = payload['amount']
			payload['response'] = 'Captured'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on funds transfer item details: %s" % e)
		return payload


	def funds_transfer_item_details(self, payload, node_info):
		try:
			account_type = AccountType.objects.get(id=payload['account_type_id'])
			product_item = account_type.product_item
			payload['product_item_id'] = product_item.id
			#payload['till_number'] = product_item.product_type.institution_till.till_number
			payload['currency'] = product_item.currency.code
			payload['float_amount'] = payload['amount']
			payload['response'] = 'Captured'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on funds transfer item details: %s" % e)
		return payload


	def loan_repayment(self, payload, node_info):
		try:
			account_manager = AccountManager.objects.get(id=payload['account_manager_id'])
			account_manager.credit_paid = True
			account_manager.save()

			payload['response'] = 'Loan Repaid'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan repayment: %s" % e)
		return payload


	def loan_status(self, payload, node_info):
		try:
			account = Account.objects.get(id=payload['session_account_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			profile_tz = pytz.timezone(session_gateway_profile.user.profile.timezone)

			account_manager_list = AccountManager.objects.filter(credit=False,dest_account=account,dest_account__account_type__id=payload['account_type_id'],credit_paid=False)

			available_credit,credit_total = Decimal(0),Decimal(0)
			overdue_credit, credit_info = False,'Principal-Loan-Due Date'

			if account_manager_list.exists():
				credit = {}
				available = account.credit_limit
				overdue, due_date = False, None
				currency = account.account_type.product_item.currency.code
				for a in account_manager_list:
					principal, total = Decimal(0), Decimal(0)
					if a.dest_account.account_type.product_item.currency.code == currency:
						lgr.info('Got status logic: %s' % a)

						lgr.info('Got status logic')
						principal = a.amount

						lgr.info('Got status logic')
						total = Decimal(a.charge)+Decimal(a.amount)

						lgr.info('Got status logic')
						if a.credit_due_date:
							due_date = timezone.localtime(a.credit_due_date)
							overdue = timezone.now()>due_date
							due_date = profile_tz.normalize(due_date.astimezone(profile_tz)).strftime("%d/%b/%Y")
						else:
							due_date = None

						lgr.info('Got status logic')
						available = available - a.amount
	
						lgr.info('Got status logic.2')
					else:
						lgr.info('Currency Conversion to Happen')

					credit_info = '%s\n%s %s-%s %s-%s' % (credit_info,currency,'{0:,.2f}'.format(principal),currency,'{0:,.2f}'.format(total),due_date)
					if overdue:
						overdue_credit = True
						credit_info = '%s-Overdue' % credit_info
			else:
				credit_info = 'No Loan Record Available'
			payload['credit_total'] = credit_total
			payload['available_credit'] = available_credit
			payload['overdue_credit'] = overdue_credit

			payload['response_status'] = '00'
			payload['response'] = credit_info

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan status: %s" % e)
		return payload

	def loan_limit(self, payload, node_info):
		try:
			account = Account.objects.get(id=payload['session_account_id'])
			account_manager = AccountManager.objects.filter(credit=False,dest_account=account,dest_account__account_type__id=payload['account_type_id'],credit_paid=False).order_by('-date_created')[:1]

			limit_total = Decimal(0)
			currency = account.account_type.product_item.currency.code
			if account_manager.exists():
				if account_manager[0].dest_account.account_type.product_item.currency.code == currency:
					limit_total = account_manager[0].balance_bf
				else:
					lgr.info('Currency Conversion to Happen')

			if account.credit_limit:
				credit_limit = account.credit_limit
				available_limit = (account.credit_limit + limit_total)
			else:
				credit_limit = Decimal(0)
				available_limit = limit_total

			payload['available_limit'] = available_limit
			payload['credit_limit'] = credit_limit

			#Format for view
			credit_limit = '{0:,.2f}'.format(credit_limit)
			available_limit = '{0:,.2f}'.format(available_limit)


			payload['response_status'] = '00'
			payload['response'] = 'Credit Limit %s %s\nAvailable Limit %s %s' % (currency,credit_limit,currency,available_limit)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on getting account limit: %s" % e)
		return payload

	def loan_details(self, payload, node_info):
		try:
			account_type = AccountType.objects.get(id=payload['account_type_id'])

			account_item = Account.objects.filter(id=payload['session_account_id'])

			if account_item.exists():
				product_item = account_type.product_item
				payload['institution_id'] = product_item.institution.id
				payload['product_item_id'] = product_item.id
				#payload['till_number'] = product_item.product_type.institution_till.till_number
				payload['currency'] = product_item.currency.code

				payload['response'] = 'Captured'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan details: %s" % e)
		return payload



	def loan_request_details(self, payload, node_info):
		try:
			#Authorize Limit
			credit_total = payload['credit_total']
			available_credit = payload['available_credit']
			overdue_credit = payload['overdue_credit']
			
			if overdue_credit:
				lgr.info('Overdue Credit')
				payload['response'] = 'An overdue Loan Exists'
				payload['response_status'] = '05'
			else:
				credit_limit = payload['credit_limit']
				available_limit = payload['available_limit']
				account_type = AccountType.objects.get(id=payload['account_type_id'])

				if Decimal(payload['amount'])<account_type.product_item.unit_limit_min:
					payload['response'] = 'Min Amount: %s' % account_type.product_item.unit_limit_min
					payload['response_status'] = '13'
				elif Decimal(payload['amount'])>account_type.product_item.unit_limit_max:
					payload['response'] = 'Max Amount: %s' % account_type.product_item.unit_limit_max
					payload['response_status'] = '13'
				elif (credit_total+Decimal(payload['amount'])) > credit_limit or Decimal(payload['amount'])>available_limit:
					lgr.info('Max Limit Amount Reached: ct:%s|wl:%s|ac:%s' % (credit_total, available_limit, available_credit))
					payload['response_status'] = '61'
				else:
					lgr.info('Succesfully Captured Amount')

					account_item = Account.objects.filter(id=payload['session_account_id'])
					#Log account manager record
					#debit_account - Add credit loan Account
					#payload['ext_service_id'] = payload['Payment']
					if account_item.exists():
						product_item = account_type.product_item
						payload['institution_id'] = product_item.institution.id
						payload['product_item_id'] = product_item.id
						#payload['till_number'] = product_item.product_type.institution_till.till_number
						payload['currency'] = product_item.currency.code


						loan_amount = Decimal(payload['amount'])
						credit_type = SavingsCreditType.objects.filter(account_type=account_type,\
								 min_time__lte=int(payload['loan_time']), max_time__gte=int(payload['loan_time']))

						for c in credit_type:
							interest = ((c.interest_rate/100)*(int(payload['loan_time'])/c.interest_time)*Decimal(payload['amount']))
						#loan_cost = '{0:,.2f}'.format(loan_amount) if loan_amount > 0 else None #Formatter

						due_date = timezone.localtime(timezone.now())+timezone.timedelta(days=int(payload['loan_time']))
						due_date = due_date.strftime("%d/%b/%Y")
						payload['due_date'] = due_date
						payload['is_loan'] = True
						if account_type.disburse_deductions:
							payload['quantity'] = loan_amount + interest
							payload['float_amount'] = loan_amount
						else:
							payload['quantity'] = loan_amount
							payload['float_amount'] = loan_amount - interest

						payload['response'] = 'Captured'
						payload['response_status'] = '00'
					else:
						payload['response_status'] = '25'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on loan request details: %s" % e)
		return payload

	def loan_query_options(self, payload, node_info):
		try:

			if payload['loan_option'] == 'Loan Limit':
				payload = self.loan_limit(payload,node_info)
			elif payload['loan_option'] == 'Loan Status':
				payload = self.loan_status(payload,node_info)
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on getting loan options: %s" % e)
		return payload


class Trade(System):
	pass

@app.task(ignore_result=True)
def overdue_credit_service_call(payload):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	from api.views import ServiceCall
	try:


		lgr.info('%s|%s|%s|%s' % (a.id, (timezone.now()-a.credit_due_date).days, a.amount, a.balance_bf))
		a.credit_overdue.add(c)

		payload = json.loads(c.notification_details)	
		profile= a.dest_account.profile
		gateway_profile_list = GatewayProfile.objects.filter(gateway=a.account_type.gateway,user=profile.user)
		gateway_profile = gateway_profile_list[0]
		service = c.service

		payload['service_id'] = service.id
		payload['gateway_profile_id'] = gateway_profile.id
		payload['credit_overdue_id'] = c.id

		if c.product_item:
			payload['product_item_id'] = c.product_item.id
			payload['institution_id'] = c.product_item.institution.id
			#payload['till_number'] = c.product_item.product_type.institution_till.till_number
			payload['currency'] = c.product_item.currency.code

		payload['session_account_id'] = a.dest_account.id
		payload['session_gateway_profile_id'] = gateway_profile.id
		payload['transaction_reference'] = a.transaction_reference
		payload['account_manager_id'] = a.id
		payload['account_type_id'] = a.dest_account.account_type.id
		payload['chid'] = 2
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = '127.0.0.1'
		payload['lat'] = '0.0'
		payload['lng'] = '0.0'

		lgr.info('Service: %s | Payload: %s' % (service, payload))
		payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

		payload = ServiceCall().api_service_call(service, gateway_profile, payload)
		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception, e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload

@app.task(ignore_result=True, soft_time_limit=25920) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_overdue_credit2():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)

	credit_overdue_activity = CreditOverdueActivity.objects.filter(Q(credit_overdue__status__name='ENABLED'),~Q(credit__overdue__service=None),\
					Q(account__manager__credit_due_date__lte=(timezone.now()-timezone.timedelta(days=F('credit_overdue__overdue_time')))),\
					Q(account_manager__credit_due_date__gte=(timezone.now()-timezone.timedelta(days=(F('credit_overdue__overdue_time')+3) ))),\
					Q(account_manager__credit_paid=False))[:10]

	for a in credit_overdue_activity:
		overdue_credit_service_call.delay(a)


@app.task(ignore_result=True)
def service_call(payload):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	from api.views import ServiceCall
	try:
		payload = json.loads(payload)
		payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

		service = Service.objects.get(id=payload['service_id'])
		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)
		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception, e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload




@app.task(ignore_result=True, soft_time_limit=25920) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_overdue_credit():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)

	credit_overdue = CreditOverdue.objects.filter(status__name='ENABLED')

	for c in credit_overdue:
		try:
			lgr.info('Credit Overdue: %s' % c)
			account_manager = AccountManager.objects.filter(Q(credit_due_date__lte=(timezone.now()-timezone.timedelta(days=c.overdue_time))),\
					Q(credit_due_date__gte=(timezone.now()-timezone.timedelta(days=(c.overdue_time+3) ))),Q(credit_paid=False),\
					~Q(credit_overdue=c))[:10]
			for a in account_manager:
				lgr.info('%s|%s|%s|%s' % (a.id, (timezone.now()-a.credit_due_date).days, a.amount, a.balance_bf))
				a.credit_overdue.add(c)

				payload = json.loads(c.notification_details)	
				profile= a.dest_account.profile
				gateway_profile_list = GatewayProfile.objects.filter(gateway=a.dest_account.account_type.gateway,user=profile.user)
				gateway_profile = gateway_profile_list[0]
				service = c.service

				payload['service_id'] = service.id
				payload['gateway_profile_id'] = gateway_profile.id
				payload['credit_overdue_id'] = c.id

				if c.product_item:
					payload['product_item_id'] = c.product_item.id
					payload['institution_id'] = c.product_item.institution.id
					#payload['till_number'] = c.product_item.product_type.institution_till.till_number
					payload['currency'] = c.product_item.currency.code

				payload['session_account_id'] = a.dest_account.id
				payload['session_gateway_profile_id'] = gateway_profile.id
				payload['transaction_reference'] = a.transaction_reference
				payload['account_manager_id'] = a.id
				payload['account_type_id'] = a.dest_account.account_type.id
				payload['chid'] = 2
				payload['ip_address'] = '127.0.0.1'
				payload['gateway_host'] = '127.0.0.1'
				payload['lat'] = '0.0'
				payload['lng'] = '0.0'

				lgr.info('Service: %s | Payload: %s' % (service, payload))
				if service is None:
					lgr.info('No Service to process for product: %s' % c.product_type)
				else:

	    				payload = json.dumps(payload, cls=DjangoJSONEncoder)
					try:service_call(payload)
					except Exception, e: lgr.info('Error on Service Call: %s' % e)

		except Exception, e:
			lgr.info('Error processing overdue credit: %s | %s' % (c,e))

