from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task


from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point

from django.conf import settings
from django.core.files import File

from django.utils.http import urlquote
from django.contrib.auth.hashers import check_password

from django.db import transaction
from primary.core.bridge.models import *

import logging
lgr = logging.getLogger('primary.core.administration')

import base64, re
import binascii

try:
	# hack for modules not installable on windows
	from django.contrib.gis.geoip2 import GeoIP2
	import crypt
except ImportError:
	if os.name == 'nt':
		lgr.error('Ignored Import Error',exc_info=True)
	else:
		# raise on Linux
		raise

#from celery import shared_task
#from celery.contrib.methods import task_method
#from celery.contrib.methods import t
from celery import shared_task
#from celery import task_method
from celery import task
from switch.celery import app

class Wrappers: pass


class System(Wrappers):
	def add_role(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if payload.get('role_name') and (payload.get('role_access_level') or payload.get('role_access_level_id') ):
				role_name = payload.get('role_name').strip()
				role_status = AccessLevelStatus.objects.get(name='ACTIVE')
				role_access_level = None
				if payload.get('role_access_level'):
					role_access_level = AccessLevel.objects.get(name=payload.get('role_access_level').strip())
				elif payload.get('role_access_level_id'):
					role_access_level = AccessLevel.objects.get(name=payload.get('role_access_level_id').strip())

				role_description = payload.get('role_description')
				role_session_expiry = payload.get('role_session_expiry')

				_role = Role.objects.filter(name=role_name, gateway=gateway_profile.gateway)
				if _role.exists():
					payload['response'] = 'Role with name already exists'
					payload['response_status'] = '26'
				else:
					role = Role(name=role_name, status=role_status, access_level=role_access_level, gateway=gateway_profile.gateway)
					if role_description:
						role.description = role_description
					else:
						role.description = role_name

					if role_session_expiry and role_session_expiry.isdigit():
						role.session_expiry = role_session_expiry

					role.save()

					payload['role_id'] = role.id
					payload['response'] = 'Role Created'
					payload['response_status'] = '00'

			else:
				payload['response'] = 'Role Details do not exist'
				payload['response_status'] = '25'

		except Exception as e:
			lgr.info('Error on add role: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload




class Trade(System):
	pass

class Payments(System):
	pass


