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
lgr = logging.getLogger('crc')
	

class Wrapper:
	pass

class System(Wrapper):
	def get_cards(self, payload, node_info):
		try:

	                q=payload['card_accountnumber']
                	p="%s%s%s" % (q[:4],"".join(['*' for v in range(len(q)-8)]),q[len(q)-4:])
	                payload['card_accountnumber'] = p

			payload['response_status'] = '00'
			payload['response'] = 'Card Captured'
		except Exception, e:
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
