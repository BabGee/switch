from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
import base64, re
from decimal import Decimal, ROUND_UP, ROUND_DOWN
from django.db.models import Max
from thirdparty.amkagroup_co_ke.models import *

import logging
lgr = logging.getLogger('amkagroup_co_ke')


class Wrappers:
	pass

class System(Wrappers):
	pass

class Trade(System):
	pass

class Payments(System):
	def credit_limit_review(self, payload, node_info):
		try:
			session_account = Account.objects.get(id=payload['session_account_id'])
			investment_list = Investment.objects.filter(account=session_account)
			if investment_list.exists():
				credit_limit = session_account.credit_limit
				investment_list = investment_list.values('investment_type','investment_type__limit_review_rate',\
						'investment_type__value').annotate(Max('date_created'),Max('pie'))
				pie_value = Decimal(0)

				for i in investment_list:
					pie = Decimal((i['investment_type__limit_review_rate']/100)*i['investment_type__value'])

					if i['pie__max']>0:
						pie = pie*i['pie__max']
						pie_value = pie_value + Decimal(i['pie__max']*i['investment_type__value'])
					else:
						pie_value = pie_value + i['investment_type__value']
				
					credit_limit = credit_limit + pie
				#Review Loan Limit
				if credit_limit <=pie_value: #Investment upto 100% investment value
					session_account.credit_limit = credit_limit.quantize(Decimal('.01'), rounding=ROUND_DOWN)
					session_account.save()

			payload['credit_limit'] = session_account.credit_limit
			payload['response'] = 'Loan Limit Reviewed'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Investment Details: %s" % e)
		return payload


	def investment_details(self, payload, node_info):
		try:
			payload['account_type_id'] = 3 #Amka Loan AccounT
			payload['response'] = 'Investment Detail Captured'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Investment Details: %s" % e)
		return payload


	def log_investment(self, payload, node_info):
		try:
			session_account = Account.objects.get(id=payload['session_account_id'])
			investment_type = InvestmentType.objects.get(product_item__id=payload['product_item_id'])
			investment_list = Investment.objects.filter(account=session_account).order_by('-date_created')
			if investment_list.exists() and investment_type.name <> 'M-Chaama Enrollment':
				amount = Decimal(payload['amount'])
				quantity = Decimal(payload['quantity']) if 'quantity' in payload.keys() else Decimal(1)
				pie = investment_list[0].pie + quantity
				balance_bf= investment_list[0].balance_bf + amount
				investment = Investment(investment_type=investment_type, account=session_account, amount=amount, pie=pie, balance_bf=balance_bf)
				investment.save()
			else:
				amount = Decimal(payload['amount'])
				quantity = Decimal(payload['quantity']) if 'quantity' in payload.keys() else Decimal(1)
				pie = Decimal(0) if investment_type.name == 'M-Chaama Enrollment' else quantity
				balance_bf= amount
				investment = Investment(investment_type=investment_type, account=session_account, amount=amount, pie=pie, balance_bf=balance_bf)
				investment.save()

				#Allocate a loan Limit
				session_account.credit_limit = Decimal(1000)
				session_account.credit_limit_currency = Currency.objects.get(code='KES')
				session_account.save()
				
			payload['amka_pie'] = pie
			payload['response'] = 'Investment Logged'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Log Investment: %s" % e)
		return payload



