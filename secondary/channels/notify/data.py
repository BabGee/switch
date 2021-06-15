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
import numpy as np
import pandas as pd
#from django.db.models.functions import TruncDate, TruncDay, TruncHour, TruncMinute, TruncSecond
from switch.cassandra import app as _cassandra

from .models import *

lgr = logging.getLogger('secondary.channels.notify')

def pandas_factory(colnames, rows):
    return pd.DataFrame(rows, columns=colnames)

class DateTrunc(Func):
	function = 'DATE_TRUNC'
	def __init__(self, trunc_type, field_expression, **extra): 
		super(DateTrunc, self).__init__(Value(trunc_type), field_expression, **extra)                      

class List:
	#def balance(self, payload, gateway_profile, profile_tz, data):
	def notifications_summary(self, payload, gateway_profile, profile_tz, data):
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

		lgr.info('Started Notifications')

		try:
			outbound = Outbound.objects.using('read').filter(contact__product__notification__code__gateway=gateway_profile.gateway,\
				contact__product__notification__code__institution=gateway_profile.institution, date_created__gte=timezone.now()-timezone.timedelta(days=7)). \
				values('state__name'). \
				annotate(state_count=Count('state__name'))

			for o in outbound:
				item = {}
				item['name'] = o['state__name']
				item['count'] = '%s' % '{0:,.2f}'.format(o['state_count'])
				params['rows'].append(item)
		except Exception as e:
			lgr.info('Error on notifications: %s' % e)
		return params,max_id,min_id,ct,push



	def recipient_contact(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info(f'Started Recipient Contact {payload}')

		try:
			session = _cassandra
			session.set_keyspace('notify')
			session.row_factory = pandas_factory
			session.default_fetch_size = 10000000 #needed for large queries, otherwise driver will do pagination. Default is 50000.

			query=f"select * from recipient_contact where contact_group_id=? and status=?"

			prepared_query = session.prepare(query)
			bound = prepared_query.bind(dict(contact_group_id=int(payload['recipient_contact']), status=str('ACTIVE'))) 
			rows = session.execute(bound)
			df = rows._current_rows
			lgr.info(f'Rows {df.head()}')
			dtype = {'float': 'number','int': 'number','datetime': 'datetime', 'object': 'string','datetime64[ns, UTC]':'datetime','float64':'number','int64':'number'}
			for c in df.columns:
				lgr.info(df[c].dtype)
				if df[c].dtype in dtype.keys():
					cols = {'label': c, 'type': 'string' }
					for k,v in dtype.items(): 
						if k == str(df[c].dtype):
							cols = {'label': c, 'type': v }
					params['cols'].append(cols)
				else:
					params['cols'].append({'label': c, 'type': 'string' })

			lgr.info(f'Params {params}')
			report_list  = df.astype(str).values.tolist()

			lgr.info(f'Report List {report_list[:5]}')
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
			lgr.info('Error on  Recipient Contact: %s' % e,exc_info=True)
		return params,max_id,min_id,ct,push


	def outbound_status_report(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started Outbound Status Report')

		try:

			#.annotate(send_date=Cast(DateTrunc('minute','scheduled_send'), CharField(max_length=32)))\
			outbound_list = Outbound.objects.using('read').filter(contact__product__notification__code__institution=gateway_profile.institution,\
							contact__product__notification__code__gateway=gateway_profile.gateway, date_created__gte=timezone.now()-timezone.timedelta(days=7))\
							.annotate(send_date=Cast(F('scheduled_send'), CharField(max_length=32)))\
							.values('send_date')\
							.annotate(total_count=Count('send_date')).filter(total_count__gte=5)\
							.values_list('send_date','message','contact__product__notification__code__alias','contact_group','state__name','total_count')\
							.order_by('-send_date')

			outbound=np.asarray(outbound_list)
			df = pd.DataFrame({'DATE': outbound[:,0], 'MESSAGE': outbound[:,1], 'CODE': outbound[:,2], 'CONTACT': outbound[:,3], 'STATE': outbound[:,4], 'TOTAL': outbound[:,5],})

			df['DATE'] = pd.to_datetime(df['DATE'])
			df['CONTACT'] = df['CONTACT'].fillna('')
			df['TOTAL'] = pd.to_numeric(df['TOTAL'])
			df1=df[['DATE','MESSAGE','CODE','CONTACT']]
			df2= df[['STATE','TOTAL']].pivot(columns='STATE',values='TOTAL').fillna(0)
			df3=pd.concat([df1,df2], ignore_index=False, axis=1)
			df = df3.groupby(['DATE','MESSAGE','CODE','CONTACT']).sum()

			for d in df2.columns:
				df[d+'(%)'] = ((df[d]/df[df2.columns].sum(axis=1))*100).round(2)

			df = df.reset_index().sort_values('DATE',ascending=False)
			dtype = {'float': 'number','int': 'number','datetime': 'datetime', 'object': 'string','datetime64[ns, UTC]':'datetime','float64':'number','int64':'number'}
			for c in df.columns:
				lgr.info(df[c].dtype)
				if df[c].dtype in dtype.keys():
					cols = {'label': c, 'type': 'string' }
					for k,v in dtype.items(): 
						if k == str(df[c].dtype):
							cols = {'label': c, 'type': v }
					params['cols'].append(cols)
				else:
					params['cols'].append({'label': c, 'type': 'string' })

			report_list  = df.astype(str).values.tolist()
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
			lgr.info('Error on  Outbound Status Report: %s' % e,exc_info=True)
		return params,max_id,min_id,ct,push

