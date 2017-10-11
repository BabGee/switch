from __future__ import absolute_import

from celery import shared_task
from celery import task
#from celery.contrib.methods import task_method
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
from django.shortcuts import render
from switch.celery import app
from switch.celery import single_instance_task
from django.db import transaction

# from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
import base64, re
from decimal import Decimal, ROUND_UP, ROUND_DOWN
from django.db.models import Max, Min, Count, Sum
from products.nikobizz.models import *
import pytz, time, json, pycurl

from django.core.serializers.json import DjangoJSONEncoder
import paho.mqtt.client as mqtt
from django.db.models import Sum, F

import logging

lgr = logging.getLogger('nikobizz')


class Wrappers:
    pass

class System(Wrappers):
	def subdomain_details(self, payload, node_info):
		try:
			lgr.info('Started Subdomain Details')
			if 'subdomain' in payload.keys() and payload['subdomain'] not in [None,'']:
				subdomain = Subdomain.objects.filter(subdomain=payload['subdomain'],status__name='ACTIVE')
				lgr.info('Subdomain: %s' % subdomain)
				if subdomain.exists():
					lgr.info('Found Subdomain: %s' % subdomain)
					payload['institution_id'] = subdomain[0].institution.id
					payload['response'] = 'Subdomain Details Updated'
					payload['response_status'] = '00'
				else:
					lgr.info('Subdomain not found')
					payload['response'] = 'Subdomain not found.'
					payload['response_status'] = '00'
			else:
				lgr.info('Subdomain not in request')
				payload['response'] = 'Subdomain not in request.'
				payload['response_status'] = '00'
				
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Subdomain Details: %s" % e)

		return payload


class Trade(System):
    pass


class Payments(System):
    pass


