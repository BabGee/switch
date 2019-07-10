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

lgr = logging.getLogger('secondary.erp.pos')

class List:
	def purchases_summary(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                          {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                          {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                          {"label": "color", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started purchases_summary')

		try:
			order = PurchaseOrder.objects.filter(cart_item__product_item__institution=gateway_profile.institution).\
				values('status__name', 'cart_item__currency__code'). \
				annotate(status_count=Count('status__name'), total_amount=Sum('cart_item__total'))
				
			for o in order:
				item = {}
				item['name'] = o['status__name']
				item['description'] = '%s %s' % (o['cart_item__currency__code'], '{0:,.2f}'.format(o['total_amount']))
				item['count'] = '%s' % '{0:,.2f}'.format(o['status_count'])
				params['rows'].append(item)

		except Exception as e:
		    lgr.info('Error on purchases: %s' % e)

		return params,max_id,min_id,ct,push



