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
from secondary.finance.vbs.models import *
from thirdparty.wahi.models import *

import logging
lgr = logging.getLogger('wahi')


class Wrappers:
	pass

class System(Wrappers):
	def credit_probability_limit_review(self, payload, node_info):
		try:
			session_account = Account.objects.get(id=payload['session_account_id'])
			if session_account.credit_limit:
				wahiloan_base_limit = session_account.credit_limit
				probability = Decimal(100) + (Decimal(100) - Decimal(payload['credit_probability']))
				credit_limit = (probability/100)*wahiloan_base_limit

			else:
				wahiloan_base_limit = Decimal(5000)
				probability = Decimal(100) - Decimal(payload['credit_probability'])
				credit_limit = (probability/100)*wahiloan_base_limit

			session_account.credit_limit = credit_limit.quantize(Decimal('.01'), rounding=ROUND_DOWN)
			session_account.save()

			payload['credit_limit'] = session_account.credit_limit
			payload['response'] = 'Loan Limit Reviewed'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Investment Details: %s" % e)
		return payload



class Trade(System):
	pass

class Payments(System):
	pass
