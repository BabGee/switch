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
from thirdparty.sortika.models import *

import logging
lgr = logging.getLogger('sortika')


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
			investment_list = InvestmentManager.objects.filter(account=session_account)
			if investment_list.exists():
				pass
				#Check Session Account for 6 loan cycles, and if first loan and now >= 6 months.
				#Log Into Sortika 3X qualified users table | An asynchronous task to do a membership registrations and create a sortika account.
			payload['credit_limit'] = session_account.credit_limit
			payload['response'] = 'Loan Limit Reviewed'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Investment Details: %s" % e)
		return payload


	def investment_details(self, payload, node_info):
		try:
			payload['account_type_id'] = 6 #Sortika Loan AccounT
			payload['response'] = 'Investment Detail Captured'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Investment Details: %s" % e)
		return payload


	def log_investment(self, payload, node_info):
		try:
			session_account = Account.objects.get(id=payload['session_account_id'])
			investment_type = InvestmentAccountType.objects.get(product_item__id=payload['product_item_id'])
			investment_list = InvestmentManager.objects.filter(account=session_account).order_by('-date_created')


			amount = Decimal(payload['amount'])
			share_value = Decimal(0)
			nominal_value = investment_type.nominal_value

			if investment_list.exists():	
				balance_bf= investment_list[0].balance_bf + amount
				share_value = investment_list[0].share_value
			else:
				balance_bf = amount


			if nominal_value is not None:
				share_value = share_value + \
					(amount/nominal_value)
			else:
				share_value = share_value+0

			credit_limit = (investment_type.investment_loan_allowed/100)*balance_bf

			investment = InvestmentManager(investment_type=investment_type, account=session_account, amount=amount, share_value=share_value, balance_bf=balance_bf)
			investment.save()

			#Allocate a loan Limit
			session_account.credit_limit = credit_limit
			session_account.save()
				
			payload['share_value'] = investment.share_value
			payload['response'] = 'Investment Logged'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Log Investment: %s" % e)
		return payload



