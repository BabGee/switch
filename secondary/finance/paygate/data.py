import base64
import csv
import json
import logging
import operator
import time
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

import pytz
import re
from django.apps import apps
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Sum, Max, Min, Avg, Q, F, Func, Value, CharField, Case, Value, When, TextField
from django.db.models.functions import Cast
from django.db.models.functions import Concat, Substr
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.timezone import utc
import numpy as np
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers

from .models import *

lgr = logging.getLogger('secondary.finance.paygate')

class List:
	def balance(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]

		params['rows'] = []
		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started Balance')

		try:

			#manager_list = FloatManager.objects.filter(Q(Q(institution=gateway_profile.institution)|Q(institution=None)),\
			lgr.info('Balance')
			if gateway_profile.institution:
				manager_list = FloatManager.objects.filter(Q(institution=gateway_profile.institution),\
										Q(gateway=gateway_profile.gateway))
			else:
				manager_list = FloatManager.objects.filter(Q(gateway=gateway_profile.gateway))

			float_type_list = manager_list.values('float_type__name','float_type__id').annotate(count=Count('float_type__id'))

			lgr.info('Balance')
			for f in float_type_list:
				manager = manager_list.filter(float_type__id=f['float_type__id'])
				if manager.exists():
					manager_item = manager.last()
					item = {}
					item['name'] = '%s' % manager_item.float_type.name
					item['description'] = '%s' % (manager_item.float_type.description)
					item['count'] = '%s' % '{0:,.2f}'.format(manager_item.balance_bf)
					params['rows'].append(item)
		except Exception as e:
		    lgr.info('Error on balance: %s' % e)

		return params,max_id,min_id,ct,push



