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
from django.db.models.functions import Cast, Concat, Substr, Lower
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.timezone import utc
import numpy as np
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers
import numpy as np
import pandas as pd

from .models import *

lgr = logging.getLogger('secondary.finance.paygate')

class RegexpMatches(Func):
	function = 'REGEXP_MATCHES'
	def __init__(self, source, regexp, flags=None, group=None, output_field=None, **extra):
		template = '%(function)s(%(expressions)s)'
		if group:
			if not hasattr(regexp, 'resolve_expression'):
				regexp = Value(regexp)
			template = '({})[{}]'.format(template, str(group))
		expressions = (source, regexp)
		if flags:
			if not hasattr(flags, 'resolve_expression'):
				flags = Value(flags)
			expressions += (flags,)
		self.template = template
		super().__init__(*expressions, output_field=output_field, **extra)


class DateTrunc(Func):
	function = 'DATE_TRUNC'
	def __init__(self, trunc_type, field_expression, **extra): 
		super(DateTrunc, self).__init__(Value(trunc_type), field_expression, **extra)

class List:
	def incoming_status_report(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started Incoming Status Report')

		try:

			#.annotate(send_date=Cast(DateTrunc('minute','scheduled_send'), CharField(max_length=32)))\
			#reference_lower=Lower('reference')
			incoming_list = Incoming.objects.using('read').filter(remittance_product__institution=gateway_profile.institution,\
							remittance_product__institution__gateway=gateway_profile.gateway, date_created__gte=timezone.now()-timezone.timedelta(days=7))\
							.annotate(received_date=Cast(DateTrunc('day','date_created'), CharField(max_length=32)))\
							.values('received_date')\
							.annotate(reference_lower=RegexpMatches('reference',r'[^a-zA-Z]'), total_count=Count('received_date'), total_amount=Sum('amount')).filter(total_count__gte=5)\
							.values_list('received_date','remittance_product__ext_product_id','reference_lower','remittance_product__name','total_count','total_amount')\
							.order_by('-received_date')

			lgr.info('Incoming List: %s' % incoming_list)
			if len(incoming_list):
				incoming=np.asarray(incoming_list)
				lgr.info('Incoming: %s' % incoming)
				df = pd.DataFrame({'DATE': incoming[:,0], 'CODE': incoming[:,1], 'REFERENCE': incoming[:,2], 'PRODUCT': incoming[:,3], 'TOTAL_COUNT': incoming[:,4], 'TOTAL_AMOUNT': incoming[:,5],})
				lgr.info('DF: %s' % df)
				df['DATE'] = pd.to_datetime(df['DATE'])
				df['REFERENCE'] = df['REFERENCE'].fillna('')
				df['TOTAL_COUNT'] = pd.to_numeric(df['TOTAL_COUNT'])
				df['TOTAL_AMOUNT'] = pd.to_numeric(df['TOTAL_AMOUNT'])
				df1=df[['DATE','PRODUCT','CODE']]
				df2= df[['REFERENCE','TOTAL_COUNT','TOTAL_AMOUNT']].pivot(columns='REFERENCE',values=['TOTAL_COUNT','TOTAL_AMOUNT']).fillna(0)
				df3=pd.concat([df1,df2], ignore_index=False, axis=1)
				df = df3.groupby(['DATE','PRODUCT','CODE']).sum()

				#df2= df[['REFERENCE','TOTAL_AMOUNT']].pivot(columns='REFERENCE',values='TOTAL_AMOUNT').fillna(0)
				#df3= df[['REFERENCE','TOTAL_COUNT']].pivot(columns='REFERENCE',values='TOTAL_COUNT').fillna(0)
				#df4=pd.concat([df1,df2,df3], ignore_index=False, axis=1)
				#df = df4.groupby(['DATE','PRODUCT','CODE']).sum()

				#lgr.info('DF 2: %s' % df)
				#for d in df2.columns:
				#	df[d+'(%)'] = ((df[d]/df[df2.columns].sum(axis=1))*100).round(2)

				lgr.info('DF 3: %s' % df)
				df = df.reset_index().sort_values('DATE',ascending=False)
				dtype = {'float': 'number','int': 'number','datetime': 'datetime', 'object': 'string','datetime64[ns, UTC]':'datetime','float64':'number','int64':'number'}
				for c in df.columns:
					lgr.info(df[c].dtype)
					if df[c].dtype in dtype.keys():
						cols = {'label': ' '.join(c) if isinstance(c, tuple) else c, 'type': 'string' }
						for k,v in dtype.items(): 
							if k == str(df[c].dtype):
								cols = {'label': ' '.join(c) if isinstance(c, tuple) else c, 'type': v }
						params['cols'].append(cols)
					else:
						params['cols'].append({'label': ' '.join(c) if isinstance(c, tuple) else c, 'type': 'string' })

				lgr.info('DF 4: %s' % df)
				report_list  = df.astype(str).values.tolist()
			else:
				report_list = list()
			paginator = Paginator(report_list, payload.get('limit',50))

			try:
				page = int(payload.get('page', '1'))
			except ValueError:
				page = 1

			try:
				results = paginator.page(page)
			except(EmptyPage, InvalidPage):
				results = paginator.page(paginator.num_pages)


			report_list = results.object_list


			params['rows'] = report_list


		except Exception as e:
			lgr.info('Error on  Incoming Status Report: %s' % e,exc_info=True)
		return params,max_id,min_id,ct,push



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



