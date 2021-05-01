from __future__ import absolute_import

import base64
import csv
import json
import logging
import operator
import time
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from functools import reduce

import pytz
import re
from celery import shared_task
from celery import group, chain
from celery.utils.log import get_task_logger
from secondary.finance.crc.models import *
from secondary.erp.crm.models import *
from django.apps import apps
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Sum, Max, Min, Avg, Q, F, Func, Value, CharField, Case, Value, When, TextField, BooleanField
from django.db.models.functions import Cast
from django.db.models.functions import Concat, Substr
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.timezone import utc
from secondary.channels.notify.models import *
from secondary.finance.paygate.models import *
from secondary.erp.pos.models import *
from secondary.erp.survey.models import *
from switch.celery import app
from switch.celery import single_instance_task
from secondary.finance.vbs.models import *
import numpy as np
import pandas as pd
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers

from secondary.channels.notify.mqtt import MqttServerClient
from primary.core.bridge import tasks as bridgetasks

from primary.core.upc.tasks import Wrappers as UPCWrappers
from secondary.channels.dsc.models import *

lgr = logging.getLogger('secondary.channels.dsc')


class Wrappers:
	def validateEmail(self, email):
		try:
			validate_email(str(email))
			return True
		except ValidationError:
			return False

	def service_call(self, service, gateway_profile, payload):
		lgr = get_task_logger(__name__)
		from primary.core.api.views import ServiceCall
		try:
			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

	def transaction_payload(self, payload):
		new_payload, transaction, count = {}, None, 1
		for k, v in payload.items():
			key = k.lower()
			if 'card' not in key and 'credentials' not in key and 'new_pin' not in key and \
					'validate_pin' not in key and 'password' not in key and 'confirm_password' not in key and \
					'pin' not in key and 'access_level' not in key and \
					'response_status' not in key and 'sec_hash' not in key and 'ip_address' not in key and \
					'service' not in key and key != 'lat' and key != 'lng' and \
					key != 'chid' and 'session' not in key and 'csrf_token' not in key and \
					'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
					'gateway_profile' not in key and 'transaction_timestamp' not in key and \
					'action_id' not in key and 'bridge__transaction_id' not in key and \
					'merchant_data' not in key and 'signedpares' not in key and \
					key != 'gpid' and key != 'sec' and \
					key not in ['ext_product_id', 'vpc_securehash', 'ext_inbound_id', 'currency', 'amount'] and \
					'institution_id' not in key and key != 'response' and key != 'input':
				if count <= 30:
					new_payload[str(k)[:30]] = str(v)[:40]
				else:
					break
			count = count + 1

		return json.dumps(new_payload)

	def mcsk_survey_summary(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:
			from thirdparty.mcsk.models import CodeRequest
			from secondary.erp.survey.tasks import System  as SurveySystem


			code_request = CodeRequest.objects.using('read').all().values('code_allocation','region__name','code_preview').\
					annotate(name=F('code_preview'),type=F('region__name'))

			for i in code_request:
				item = {}
				item['id'] = i['code_allocation']
				item['name'] = i['name']
				item['type'] = i['type']
				survey = SurveySystem().survey_tally({'institution_id':'42','survey_code':i['code_allocation']},{})
				item['kind'] = survey['survey']
				item['description'] = survey['response']
				item['count'] = survey['survey_tally']
				params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on report: %s' % e)
		return params


	def mcsk_survey(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:
			from thirdparty.mcsk.models import CodeRequest
			from secondary.erp.survey.tasks import System  as SurveySystem


			code_request = CodeRequest.objects.using('read').all().values('code_allocation','region__name','code_preview').\
					annotate(name=F('code_preview'),type=F('region__name'))

			for i in code_request:
				item = {}
				item['id'] = i['code_allocation']
				item['name'] = i['name']
				item['type'] = i['type']
				survey = SurveySystem().survey_tally({'institution_id':'42','survey_code':i['code_allocation']},{})
				item['kind'] = survey['survey']
				item['description'] = survey['response']
				item['count'] = survey['survey_tally']
				params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on report: %s' % e)
		return params

	def report(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['cols'] = []

		params['rows'] = []
		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Payload on report: %s' % payload)
		try:
			if 'session_gateway_profile_id' in payload.keys():
				gateway_profile = GatewayProfile.objects.get(gateway=gateway_profile.gateway, id=payload['session_gateway_profile_id'])

			model_class = apps.get_model(data.query.module_name, data.query.model_name)
			# model_class = globals()[data.query.model_name]

			duration_days_filters = data.query.duration_days_filters
			date_filters = data.query.date_filters
			duration_hours_filters = data.query.duration_hours_filters
			token_filters = data.query.token_filters

			not_filters = data.query.not_filters
			or_filters = data.query.or_filters
			and_filters = data.query.and_filters
			institution_filters = data.query.institution_filters
			institution_not_filters = data.query.institution_not_filters
			gateway_filters = data.query.gateway_filters
			gateway_profile_filters = data.query.gateway_profile_filters
			profile_filters = data.query.profile_filters
			role_filters = data.query.role_filters
			list_filters = data.query.list_filters

			values = data.query.values
			count_values = data.query.count_values
			sum_values = data.query.sum_values
			last_balance = data.query.last_balance
			avg_values = data.query.avg_values
			custom_values = data.query.custom_values
			order = data.query.order
			distinct = data.query.distinct
			limit = data.query.limit

			values_data = {}
			duration_days_filter_data = {}
			date_filter_data = {}
			duration_hours_filter_data = {}
			token_filters_data = {}

			not_filter_data = {}
			or_filter_data = {}
			and_filter_data = {}
			institution_filter_data = {}
			institution_not_filter_data = {}
			gateway_filter_data = {}
			gateway_profile_filter_data = {}
			profile_filter_data = {}
			role_filter_data = {}
			list_filter_data = {}

			case_values_data = {}
			link_values_data = {}

			lgr.info('\n\n\n')
			lgr.info('Model Name: %s' % data.query.name)


			lgr.info('Model Name: %s' % data.query.name)
			#lgr.info('Report List Count: %s' % len(report_list))
			#Gateway Filter is a default Filter
			if gateway_filters not in ['', None]:
				for f in gateway_filters.split("|"):
					if f not in ['',None]: gateway_filter_data[f] = gateway_profile.gateway
				if len(gateway_filter_data):
					gateway_query = reduce(operator.and_, (Q(k) for k in gateway_filter_data.items()))
					#lgr.info('Gateway Query: %s' % gateway_query)
					report_list = model_class.objects.using('read').filter(gateway_query)
				else: report_list = model_class.objects.using('read').all()
			else: report_list = model_class.objects.using('read').all()

			#lgr.info('Query Str 1: %s' % report_list.query.__str__())
			#lgr.info('Report List Count: %s' % len(report_list))
			if or_filters not in [None,'']:
				for f in or_filters.split("|"):
					of_list = f.split('%')
					if len(of_list)==2:
						if of_list[0] in payload.keys() and getattr(model_class, of_list[1].split('__')[0], False):
							or_filter_data[of_list[1]] = payload[of_list[0]]
						elif getattr(model_class, of_list[0].split('__')[0], False) and getattr(model_class, of_list[1].split('__')[0], False):
							k,v = of_list
							or_filter_data[k.strip()] = F(v.strip())
						elif getattr(model_class, of_list[0].split('__')[0], False):
							k,v = of_list
							v_list = v.split(',')

							if len(v_list)>1:
								v = [l.strip() for l in v_list if l]
							elif v.strip().lower() == 'false':
								v = False
							elif v.strip().lower() == 'true':
								v = True

							or_filter_data[k] = v if v not in ['',None] else None
					elif getattr(model_class, f.split('__')[0], False):
						if  f in payload.keys() and f.split('__')[-1] in ['exact','iexact','contains','icontains','isnull','regex','iregex']:
							if f not in ['',None]: or_filter_data[f] = payload[f]
						elif f in payload.keys():
							if f not in ['',None]: or_filter_data[f + '__icontains'] = payload[f]
						elif 'q' in payload.keys() and payload['q'] not in ['', None]:
							if f not in ['',None]: or_filter_data[f + '__icontains'] = payload['q']

			if len(or_filter_data):
				or_query = reduce(operator.or_, (Q(k) for k in or_filter_data.items()))
				#lgr.info('Or Query: %s' % or_query)
				report_list = report_list.filter(or_query)

			#lgr.info('Or Filters Report List Count: %s' % len(report_list))
			if and_filters not in [None,'']:
				for f in and_filters.split("|"):
					af_list = f.split('%')
					if len(af_list)==2:
						if af_list[0] in payload.keys() and getattr(model_class, af_list[1].split('__')[0], False):
							and_filter_data[af_list[1]] = payload[af_list[0]]
						elif getattr(model_class, af_list[0].split('__')[0], False) and getattr(model_class, af_list[1].split('__')[0], False):
							k,v = af_list
							and_filter_data[k.strip()] = F(v.strip())
						elif getattr(model_class, af_list[0].split('__')[0], False):
							k,v = af_list
							v_list = v.split(',')

							if len(v_list)>1:
								v = [l.strip() for l in v_list if l]
							elif v.strip().lower() == 'false':
								v = False
							elif v.strip().lower() == 'true':
								v = True

							and_filter_data[k] = v if v not in ['',None] else None
					elif getattr(model_class, f.split('__')[0], False):
						if  f in payload.keys() and f.split('__')[-1] in ['exact','iexact','contains','icontains','isnull','regex','iregex']:
							if f not in ['',None]: and_filter_data[f] = payload[f]
						elif f in payload.keys():
							if f not in ['',None]: and_filter_data[f + '__icontains'] = payload[f]
						elif 'q' in payload.keys() and payload['q'] not in ['', None]:
							if f not in ['',None]: and_filter_data[f + '__icontains'] = payload['q']


				if len(and_filter_data):
					and_query = reduce(operator.and_, (Q(k) for k in and_filter_data.items()))
					#lgr.info('AndQuery: %s' % and_query)
					report_list = report_list.filter(and_query)

			#lgr.info('And Filters Report List Count: %s' % len(report_list))
			if not_filters not in ['',None]:
				for f in not_filters.split("|"):
					nf_list = f.split('%')
					if len(nf_list)==2:
						if nf_list[0] in payload.keys() and getattr(model_class, nf_list[1].split('__')[0], False):
							not_filter_data[nf_list[1] + '__icontains'] = payload[nf_list[0]]
						elif getattr(model_class, nf_list[0].split('__')[0], False) and getattr(model_class, nf_list[1].split('__')[0], False):
							k,v = nf_list
							not_filter_data[k.strip()] = F(v.strip())
						elif getattr(model_class, nf_list[0].split('__')[0], False):
							k,v = nf_list
							v_list = v.split(',')

							if len(v_list)>1:
								v = [l.strip() for l in v_list if l]
							elif v.strip().lower() == 'false':
								v = False
							elif v.strip().lower() == 'true':
								v = True

							not_filter_data[k] = v if v not in ['',None] else None
					elif getattr(model_class, f.split('__')[0], False):
						if f in payload.keys():
							if f not in ['',None]: not_filter_data[f + '__icontains'] = payload[f]
						elif 'q' in payload.keys() and payload['q'] not in ['', None]:
							if f not in ['',None]: not_filter_data[f + '__icontains'] = payload['q']

				if len(not_filter_data):
					query = reduce(operator.and_, (~Q(k) for k in not_filter_data.items()))

					#lgr.info('Report List: %s' % len(report_list))
					#lgr.info('%s Not Filters Applied: %s' % (data.query.name,query))
					report_list = report_list.filter(query)
					#lgr.info('Report List: %s' % len(report_list))

			#lgr.info('Query Str 2: %s' % report_list.query.__str__())

			#lgr.info('Not Filters Report List Count: %s' % len(report_list))
			if duration_days_filters not in ['',None]:
				#lgr.info('Date Filters')
				for i in duration_days_filters.split("|"):
					k,v = i.split('%')
						#lgr.info('Date %s| %s' % (k,v))
					try: duration_days_filter_data[k] = timezone.now()+timezone.timedelta(days=float(v)) if v not in ['',None] else None
					except Exception as e: lgr.info('Error on date filter 0: %s' % e)


				if len(duration_days_filter_data):
						#lgr.info('Duration Filter Data: %s' % duration_days_filter_data)
					query = reduce(operator.and_, (Q(k) for k in duration_days_filter_data.items()))
					#lgr.info('Query: %s' % query)
					report_list = report_list.filter(query)


			#lgr.info('Duration Days Filters Report List Count: %s' % len(report_list))
			if duration_hours_filters not in ['',None]:
				for i in duration_hours_filters.split("|"):
					try:k,v = i.split('%')
					except: continue
					try: duration_hours_filter_data[k] = timezone.now()+timezone.timedelta(hours=float(v)) if v not in ['',None] else None
					except Exception as e: lgr.info('Error on time filter: %s' % e)

				if len(duration_hours_filter_data):
					query = reduce(operator.and_, (Q(k) for k in duration_hours_filter_data.items()))
					#lgr.info('Query: %s' % query)

					report_list = report_list.filter(query)

				#q_list = [Q(**{f:q}) for f in field_lookups]

			#lgr.info('Duration Hours Filters Report List Count: %s' % len(report_list))
			if date_filters not in ['',None]:
				#lgr.info('Date Filters')
				for i in date_filters.split("|"):
					df_list = i.split('%')
					if len(df_list)==2:
						if df_list[0] in payload.keys() and getattr(model_class, df_list[1].split('__')[0], False):
							try:date_filter_data[df_list[1]] = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(payload[df_list[0]], '%Y-%m-%d'))
							except Exception as e: lgr.info('Error on date filter 1: %s' % e)
						elif getattr(model_class, df_list[0].split('__')[0], False):
							k,v = df_list
							if v.strip().lower() == 'timezone.now':
								v = timezone.now().date().isoformat()
							try:date_filter_data[k] = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(v, '%Y-%m-%d')) if v not in ['',None] else None
							except Exception as e: lgr.info('Error on date filter 2: %s' % e)

					elif getattr(model_class, df_list[0].split('__')[0], False):
						if df_list[0] in payload.keys():
							try:date_filter_data[df_list[0]] = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(payload[df_list[0]], '%Y-%m-%d')) if payload[i] not in ['',None] else None
							except Exception as e: lgr.info('Error on date filter 3: %s' % e)
						elif 'start_date' in payload.keys() or 'end_date' in payload.keys():
							if 'start_date' in payload.keys():
								try:date_filter_data[i+'__gte'] = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(payload['start_date'], '%Y-%m-%d')) if payload['start_date'] not in ['',None] else None
								except Exception as e: lgr.info('Error on date filter 4: %s' % e)
							if 'end_date' in payload.keys():
								try:date_filter_data[i+'__lt'] = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(payload['end_date'], '%Y-%m-%d'))+timezone.timedelta(days=1) if payload['end_date'] not in ['',None] else None
								except Exception as e: lgr.info('Error on date filter 5: %s' % e)


				if len(date_filter_data):
						#lgr.info('Date Filter Data: %s' % date_filter_data)
					for k,v in date_filter_data.items(): 
						try:lgr.info('Date Data: %s' % v.isoformat())
						except: pass
						query = reduce(operator.and_, (Q(k) for k in date_filter_data.items()))
						#lgr.info('Query: %s' % query)
						report_list = report_list.filter(query)


			#lgr.info('Query Str 3: %s' % report_list.query.__str__())
			#lgr.info('Date Filters Report List Count: %s' % len(report_list))
			if token_filters not in ['',None]:
				for f in token_filters.split("|"):
						if 'csrfmiddlewaretoken' in payload.keys() and payload['csrfmiddlewaretoken'] not in ['', None]:
							if f not in ['',None]: token_filters_data[f + '__iexact'] = payload['csrfmiddlewaretoken']
						elif 'csrf_token' in payload.keys() and payload['csrf_token'] not in ['', None]:
							if f not in ['',None]: token_filters_data[f + '__iexact'] = payload['csrf_token']
						elif 'token' in payload.keys() and payload['token'] not in ['', None]:
							if f not in ['',None]: token_filters_data[f + '__iexact'] = payload['token']

				if len(token_filters_data):
					query = reduce(operator.and_, (Q(k) for k in token_filters_data.items()))
					#lgr.info('Query: %s' % query)

					report_list = report_list.filter(query)

			#lgr.info('Token Filters Report List Count: %s' % len(report_list))
			if list_filters not in [None,'']:
				for f in list_filters.split("|"):
					if getattr(model_class, f.split('__')[0], False):
						if f in payload.keys():
							if f not in ['',None]: list_filter_data[f + '__iexact'] = payload[f]

				if len(list_filter_data):
					and_query = reduce(operator.and_, (Q(k) for k in list_filter_data.items()))
					report_list = report_list.filter(and_query)

			#lgr.info('Institution Filters Report List Count: %s' % len(report_list))
			if institution_filters not in ['',None]:
				for f in institution_filters.split("|"):
					#if f not in ['',None]: institution_none_filter[f] = None
					if 'institution_id' in payload.keys() and payload['institution_id'] not in ['', None]:
						if f not in ['',None]: institution_filter_data[f + '__id'] = payload['institution_id']
					elif gateway_profile.institution not in ['', None]:
						if f not in ['',None]: institution_filter_data[f] = gateway_profile.institution
					else:
						#MQTT doesn't filter institution for push notifications
						if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
							pass
						else:
							if f not in ['',None]: institution_filter_data[f] = None

				if len(institution_filter_data):
					institution_query = reduce(operator.and_, (Q(k) for k in institution_filter_data.items()))
					#lgr.info('Institution Query: %s' % institution_query)
					report_list = report_list.filter(institution_query)


			#lgr.info('Institution Filters Report List Count: %s' % len(report_list))
			if institution_not_filters not in ['',None]:
				for f in institution_not_filters.split("|"):
					#if f not in ['',None]: institution_none_filter[f] = None
					if 'institution_id' in payload.keys() and payload['institution_id'] not in ['', None]:
						if f not in ['',None]: institution_not_filter_data[f + '__id'] = payload['institution_id']
					elif gateway_profile.institution not in ['', None]:
						if f not in ['',None]: institution_not_filter_data[f] = gateway_profile.institution
					else:
						#MQTT doesn't filter institution for push notifications
						if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
							pass
						else:
							if f not in ['',None]: institution_not_filter_data[f] = None

				if len(institution_not_filter_data):
					institution_query = reduce(operator.and_, (~Q(k) for k in institution_not_filter_data.items()))
					#lgr.info('Institution Query: %s' % institution_query)
					report_list = report_list.filter(institution_query)

			#lgr.info('Gateway Profile Filters Report List Count: %s' % len(report_list))
			if gateway_profile_filters not in ['', None]:
				for f in gateway_profile_filters.split("|"):
					#MQTT doesn't filter institution for push notifications
					if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
						pass
					else:
						if f not in ['',None]: gateway_profile_filter_data[f] = gateway_profile

				if len(gateway_profile_filter_data):
					gateway_profile_query = reduce(operator.and_, (Q(k) for k in gateway_profile_filter_data.items()))
					report_list = report_list.filter(gateway_profile_query)

			#lgr.info('Profile Filters Report List Count: %s' % len(report_list))
			if profile_filters not in ['', None]:
				for f in profile_filters.split("|"):
					#MQTT doesn't filter institution for push notifications
					if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
						pass
					else:
						if f not in ['',None]: profile_filter_data[f] = gateway_profile.user.profile

				if len(profile_filter_data):
					profile_query = reduce(operator.and_, (Q(k) for k in profile_filter_data.items()))
					report_list = report_list.filter(profile_query)

			#lgr.info('Role Filters Report List Count: %s' % len(report_list))
			if role_filters not in ['', None]:
				for f in role_filters.split("|"):
					#MQTT doesn't filter institution for push notifications
					if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
						pass
					elif gateway_profile.role: #Tep: Allow All roles functions to show if role=None
						if f not in ['',None]: role_filter_data[f] = gateway_profile.role

				if len(role_filter_data):
					role_query = reduce(operator.and_, (Q(k) for k in role_filter_data.items()))
					report_list = report_list.filter(role_query)


			#lgr.info('Query Str 4: %s' % report_list.query.__str__())

			join_query = DataListJoinQuery.objects.using('read').filter(query=data.query,join_inactive=False)

			#lgr.info('Join Query: %s' % join_query)
			for join in join_query:
				#lgr.info('Join: %s' % join)
				if join.join_fields or join.join_manytomany_fields or join.join_not_fields or join.join_manytomany_not_fields or join.join_case_fields:

					join_model_class = apps.get_model(join.join_module_name, join.join_model_name)
					join_gateway_filters = join.join_gateway_filters

					join_not_filters = join.join_not_filters
					join_or_filters = join.join_or_filters
					join_and_filters = join.join_and_filters

					join_gateway_profile_filters = join.join_gateway_profile_filters
					join_profile_filters = join.join_profile_filters
					join_role_filters = join.join_role_filters
					join_fields = join.join_fields
					join_institution_filters = join.join_institution_filters
					join_institution_not_filters = join.join_institution_not_filters
					join_duration_days_filters = join.join_duration_days_filters

					join_manytomany_fields = join.join_manytomany_fields
					join_not_fields = join.join_not_fields
					join_manytomany_not_fields = join.join_manytomany_not_fields

					join_case_fields = join.join_case_fields

					join_not_filter_data = {}
					join_or_filter_data = {}
					join_and_filter_data = {}

					join_gateway_filters_data = {}
					join_gateway_profile_filters_data  = {}
					join_profile_filter_data = {}
					join_role_filter_data = {}
					join_fields_data = {}
					join_institution_filter_data = {}
					join_institution_not_filter_data = {}
					join_duration_days_filter_data = {}

					join_manytomany_fields_data = {}
					join_not_fields_data = {}
					join_manytomany_not_fields_data = {}

					join_report_list = join_model_class.objects.using('read').all()

					if join_gateway_filters not in ['', None]:
						for f in join_gateway_filters.split("|"):
							if f not in ['',None]: join_gateway_filter_data[f] = gateway_profile.gateway
						if len(join_gateway_filter_data):
							join_gateway_query = reduce(operator.and_, (Q(k) for k in gateway_filter_data.items()))
							join_report_list = join_report_list.filter(join_gateway_query)

					if join_or_filters not in [None,'']:
						for f in join_or_filters.split("|"):
							of_list = f.split('%')
							if len(of_list)==2:
								if of_list[0] in payload.keys() and getattr(join_model_class, of_list[1].split('__')[0], False):
									join_or_filter_data[of_list[1]] = payload[of_list[0]]
								elif getattr(join_model_class, of_list[0].split('__')[0], False) and getattr(join_model_class, of_list[1].split('__')[0], False):
									k,v = of_list
									join_or_filter_data[k.strip()] = F(v.strip())
								elif getattr(join_model_class, of_list[0].split('__')[0], False):
									k,v = of_list
									v_list = v.split(',')

									if len(v_list)>1:
										v = [l.strip() for l in v_list if l]
									elif v.strip().lower() == 'false':
										v = False
									elif v.strip().lower() == 'true':
										v = True

									join_or_filter_data[k] = v if v not in ['',None] else None
							elif getattr(join_model_class, f.split('__')[0], False):
								if  f in payload.keys() and f.split('__')[-1] in ['exact','iexact','contains','icontains','isnull','regex','iregex']:
									if f not in ['',None]: join_or_filter_data[f] = payload[f]
								elif f in payload.keys():
									if f not in ['',None]: join_or_filter_data[f + '__icontains'] = payload[f]
								elif 'q' in payload.keys() and payload['q'] not in ['', None]:
									if f not in ['',None]: join_or_filter_data[f + '__icontains'] = payload['q']


						if len(join_or_filter_data):
							or_query = reduce(operator.or_, (Q(k) for k in join_or_filter_data.items()))
								#lgr.info('Join Or Query: %s' % or_query)
							join_report_list = join_report_list.filter(or_query)

					if join_and_filters not in [None,'']:
						for f in join_and_filters.split("|"):
							af_list = f.split('%')
							if len(af_list)==2:
								if af_list[0] in payload.keys() and getattr(join_model_class, af_list[1].split('__')[0], False):
									join_and_filter_data[af_list[1]] = payload[af_list[0]]
								elif getattr(join_model_class, af_list[0].split('__')[0], False) and getattr(join_model_class, af_list[1].split('__')[0], False):
									k,v = af_list
									join_and_filter_data[k.strip()] = F(v.strip())
								elif getattr(join_model_class, af_list[0].split('__')[0], False):
									k,v = af_list
									v_list = v.split(',')

									if len(v_list)>1:
										v = [l.strip() for l in v_list if l]
									elif v.strip().lower() == 'false':
										v = False
									elif v.strip().lower() == 'true':
										v = True

									join_and_filter_data[k] = v if v not in ['',None] else None
							elif getattr(join_model_class, f.split('__')[0], False):
								if  f in payload.keys() and f.split('__')[-1] in ['exact','iexact','contains','icontains','isnull','regex','iregex']:
									if f not in ['',None]: join_and_filter_data[f] = payload[f]
								elif f in payload.keys():
									if f not in ['',None]: join_and_filter_data[f + '__icontains'] = payload[f]
								elif 'q' in payload.keys() and payload['q'] not in ['', None]:
									if f not in ['',None]: join_and_filter_data[f + '__icontains'] = payload['q']

						if len(join_and_filter_data):
							and_query = reduce(operator.and_, (Q(k) for k in join_and_filter_data.items()))
								#lgr.info('Join And Query: %s' % and_query)
							join_report_list = join_report_list.filter(and_query)



					if join_not_filters not in ['',None]:
						for f in join_not_filters.split("|"):
							nf_list = f.split('%')
							if len(nf_list)==2:
								if nf_list[0] in payload.keys() and getattr(join_model_class, nf_list[1].split('__')[0], False):
									join_not_filter_data[nf_list[1] + '__icontains'] = payload[nf_list[0]]
								elif getattr(join_model_class, nf_list[0].split('__')[0], False) and getattr(join_model_class, nf_list[1].split('__')[0], False):
									k,v = nf_list
									join_not_filter_data[k.strip()] = F(v.strip())
								elif getattr(join_model_class, nf_list[0].split('__')[0], False):
									k,v = nf_list
									v_list = v.split(',')

									if len(v_list)>1:
										v = [l.strip() for l in v_list if l]
									elif v.strip().lower() == 'false':
										v = False
									elif v.strip().lower() == 'true':
										v = True

									join_not_filter_data[k] = v if v not in ['',None] else None
							elif getattr(join_model_class, f.split('__')[0], False):
								if f in payload.keys():
									if f not in ['',None]: join_not_filter_data[f + '__icontains'] = payload[f]
								elif 'q' in payload.keys() and payload['q'] not in ['', None]:
									if f not in ['',None]: join_not_filter_data[f + '__icontains'] = payload['q']

						if len(join_not_filter_data):
							query = reduce(operator.and_, (~Q(k) for k in join_not_filter_data.items()))

							#lgr.info('%s Not Join Filters Applied: %s' % (data.query.name,query))
							join_report_list = join_report_list.filter(query)

					if join_gateway_profile_filters not in ['', None]:
						for f in join_gateway_profile_filters.split("|"):
							if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
								pass
							else:
								if f not in ['',None]: join_gateway_profile_filter_data[f] = gateway_profile

						if len(join_gateway_profile_filter_data):
							gateway_profile_query = reduce(operator.and_, (Q(k) for k in join_gateway_profile_filter_data.items()))
							join_report_list = join_report_list.filter(gateway_profile_query)

					if join_profile_filters not in ['', None]:
						for f in join_profile_filters.split("|"):
							if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
								pass
							else:
								if f not in ['',None]: join_profile_filter_data[f] = gateway_profile.user.profile

						if len(join_profile_filter_data):
							profile_query = reduce(operator.and_, (Q(k) for k in join_profile_filter_data.items()))
							join_report_list = join_report_list.filter(profile_query)


					if join_role_filters not in ['', None]:
						for f in join_role_filters.split("|"):
							if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
								pass
							else:
								if f not in ['',None]: join_role_filter_data[f] = gateway_profile.role

						if len(join_role_filter_data):
							role_query = reduce(operator.and_, (Q(k) for k in join_role_filter_data.items()))
							join_report_list = join_report_list.filter(role_query)

					if join_institution_filters not in ['',None]:
						for f in join_institution_filters.split("|"):
							if 'institution_id' in payload.keys() and payload['institution_id'] not in ['', None]:
								if f not in ['',None]: join_institution_filter_data[f + '__id'] = payload['institution_id']
							elif gateway_profile.institution not in ['', None]:
								if f not in ['',None]: join_institution_filter_data[f] = gateway_profile.institution
							else:
								if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
									pass
								else:
									if f not in ['',None]: join_institution_filter_data[f] = None

						if len(join_institution_filter_data):
							institution_query = reduce(operator.and_, (Q(k) for k in join_institution_filter_data.items()))
							join_report_list = join_report_list.filter(institution_query)


					if join_institution_not_filters not in ['',None]:
						for f in join_institution_not_filters.split("|"):
							if 'institution_id' in payload.keys() and payload['institution_id'] not in ['', None]:
								if f not in ['',None]: join_institution_not_filter_data[f + '__id'] = payload['institution_id']
							elif gateway_profile.institution not in ['', None]:
								if f not in ['',None]: join_institution_not_filter_data[f] = gateway_profile.institution
							else:
								if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
									pass
								else:
									if f not in ['',None]: join_institution_not_filter_data[f] = None

						if len(join_institution_not_filter_data):
							institution_query = reduce(operator.and_, (~Q(k) for k in join_institution_not_filter_data.items()))
							join_report_list = join_report_list.filter(institution_query)


					if join_duration_days_filters not in ['',None]:
						#lgr.info('Date Filters')
						for i in join_duration_days_filters.split("|"):
							k,v = i.split('%')
								#lgr.info('Date %s| %s' % (k,v))
							try: join_duration_days_filter_data[k] = timezone.now()+timezone.timedelta(days=float(v)) if v not in ['',None] else None
							except Exception as e: lgr.info('Error on date filter 0: %s' % e)


						if len(join_duration_days_filter_data):
								#lgr.info('Duration Filter Data: %s' % join_duration_days_filter_data)
							for k,v in join_duration_days_filter_data.items(): 
								try:lgr.info('Duration Data: %s' % v.isoformat())
								except: pass
								query = reduce(operator.and_, (Q(k) for k in join_duration_days_filter_data.items()))
								#lgr.info('Query: %s' % query)
								join_report_list = join_report_list.filter(query)


					if join_fields not in ['',None]:
						for i in join_fields.split("|"):
							try:k,v = i.split('%')
							except: continue
							record = join_report_list.values_list(v,flat=True).distinct()
							join_fields_data[k+'__in'] = list(record)

						if len(join_fields_data):
							query = reduce(operator.and_, (Q(k) for k in join_fields_data.items()))

							#lgr.info('%s Join Fields Applied: %s' % (data.query.name,query))
							report_list = report_list.filter(query)

					if join_manytomany_fields not in ['',None]:
						for i in join_manytomany_fields.split("|"):
							try:k,v = i.split('%')
							except: continue
							record = join_report_list.values_list(v,flat=True).distinct()
							join_manytomany_fields_data[k+'__in'] = list(record)
						if len(join_manytomany_fields_data):
							query = reduce(operator.and_, (Q(k) for k in join_manytomany_fields_data.items()))

							#lgr.info('%s Join Many Fields Applied: %s' % (data.query.name,query))
							report_list = report_list.filter(query)

					if join_not_fields not in ['',None]:
						for i in join_not_fields.split("|"):
							try:k,v = i.split('%')
							except: continue
							record = join_report_list.values_list(v,flat=True).distinct()
							join_not_fields_data[k+'__in'] = list(record)

						if len(join_not_fields_data):
							query = reduce(operator.and_, (~Q(k) for k in join_not_fields_data.items()))

							#lgr.info('%s Join Not Fields Applied: %s' % (data.query.name,query))
							report_list = report_list.filter(query)

					if join_manytomany_not_fields not in ['',None]:
						for i in join_manytomany_not_fields.split("|"):
							try:k,v = i.split('%')
							except: continue
							record = join_report_list.values_list(v,flat=True).distinct()
							join_manytomany_not_fields_data[k+'__in'] = list(record)
						if len(join_manytomany_not_fields_data):
							query = reduce(operator.and_, (~Q(k) for k in join_manytomany_not_fields_data.items()))

							#lgr.info('%s Join Many Not Fields Applied: %s' % (data.query.name,query))
							report_list = report_list.filter(query)


					if join_case_fields not in ['',None]:
						join_case_when = []
						for i in join_case_fields.split('|'):
							try:case_field, k, v = i.split('%')
							except: continue
							record_data = {}

							record  =  join_report_list.values_list(v.strip(),flat=True).distinct()
							record_data[k.strip()+'__in'] =  list(record)

							record_data['then'] = True

							join_case_when.append(When(**record_data))
						#Final Case
						if join_case_when:
							values_data[case_field.strip()] = Case(*join_case_when, default=False, output_field=BooleanField())
							params['cols'].append({"label": case_field.strip(), "type": "boolean", "value": case_field.strip()})

			#lgr.info('Query Str 5: %s' % report_list.query.__str__())
			#lgr.info('Report List Count: %s' % len(report_list))
			#lgr.info('Report End Date')
			############################################VALUES BLOCK
			args = list(values_data.keys())
			if values not in [None,'']:
				for i in values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())
					value_type = model_class._meta.get_field(v.strip().split('__')[0]).get_internal_type()
					
					column_type = 'string'
					if value_type == 'DateField':
						column_type = 'date'
					elif value_type == 'DateTimeField':
						column_type = 'datetime'
					elif value_type == 'DecimalField':
						column_type = 'number'
					elif value_type == 'IntegerField':
						column_type = 'number'
					elif value_type == 'BigIntegerField':
						column_type = 'number'
					elif value_type == 'PositiveIntegerField':
						column_type = 'number'
					elif value_type == 'PositiveSmallIntegerField':
						column_type = 'number'
					elif value_type == 'SmallIntegerField':
						column_type = 'number'
					elif value_type == 'BooleanField':
						column_type = 'boolean'

					params['cols'].append({"label": k.strip(), "type": column_type, "value": v.strip()})
					if k != v:values_data[k.strip()] = F(v.strip())

			if len(values_data.keys()):
				report_list = report_list.annotate(**values_data)


			class DateTrunc(Func):
				function = 'DATE_TRUNC'
				def __init__(self, trunc_type, field_expression, **extra):
					super(DateTrunc, self).__init__(Value(trunc_type), field_expression, **extra)


			#lgr.info('Report Values: %s' % len(report_list))
			if data.query.date_values not in [None,'']:
				date_data = {}
				for i in data.query.date_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())

					date_data[k.strip()] = Cast(DateTrunc('day', v.strip()), CharField(max_length=32))
					params['cols'].append({"label": k.strip(), "type": "date", "value": v.strip()})

				if date_data:
					#lgr.info('Date Data: %s' % date_data)
					report_list = report_list.annotate(**date_data)

			#lgr.info('Report Date Values: %s' % len(report_list))
			if data.query.date_time_values not in [None,'']:
				date_time_data = {}
				for i in data.query.date_time_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())

					date_time_data[k.strip()] = Cast(F(v.strip()), CharField(max_length=32))
					params['cols'].append({"label": k.strip(), "type": "datetime", "value": v.strip()})

				if date_time_data:
					#lgr.info('Date Time Data: %s' % date_time_data)
					report_list = report_list.annotate(**date_time_data)


			#lgr.info('Report Date Time Values')

			if data.query.month_year_values not in [None,'']:

				month_year_data = {}
				for i in data.query.month_year_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())

					month_year_data[k.strip()] = Cast(DateTrunc('month', v.strip()), CharField(max_length=32))
					params['cols'].append({"label": k.strip(), "type": "date", "value": k.strip()})

				if month_year_data:
					#lgr.info('Month Year Data: %s' % month_year_data)
					report_list = report_list.annotate(**month_year_data)

			#lgr.info('Query Str 6: %s' % report_list.query.__str__())

			if data.data_response_type.name == 'DATA':
				#Values
				report_list = report_list.values(*args)
			elif data.data_response_type.name == 'LIST':
				#Values List
				report_list = report_list.values_list(*args)
			else:
				#Values List
				report_list = report_list.values_list(*args)
			############################################END VALUES BLOCK

			#args = []

			#lgr.info('Query Str 6.1: %s' % report_list.query.__str__())
			#Count Sum MUST come after values in order to group
			if count_values not in [None,'']:
				kwargs = {}
				for i in count_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())
					params['cols'].append({"label": k.strip(), "type": "number", "value": k.strip()})
					#Name of annotated column cannot be same as an existing column, hence k!=v
					if k != v:kwargs[k.strip()] = Count(v.strip())
				#lgr.info('Count: %s' % len(report_list))
				report_list = report_list.annotate(**kwargs)

			#lgr.info('Query Str 6.2: %s' % report_list.query.__str__())
			#lgr.info('Report Count Values: %s' % report_list)
			if sum_values not in [None,'']:
				kwargs = {}
				for i in sum_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())
					params['cols'].append({"label": k.strip(), "type": "number", "value": k.strip()})
					#Name of annotated column cannot be same as an existing column, hence k!=v
					if k != v:
						#Sum of the product of two or more fields is allowed with an * in the fields.
						v_list = v.split('*')
						if len(v_list)>1: kwargs[k.strip()] = Sum(reduce((lambda x, y: x * y), [F(v) for v in v_list]))
						else: kwargs[k.strip()] = Sum(v.strip())


				#lgr.info('Count Applied: %s' % kwargs)

				report_list = report_list.annotate(**kwargs)

			#lgr.info('Query Str 6.3: %s' % report_list.query.__str__())
			#lgr.info('Report Sum Values')
			if avg_values not in [None,'']:
				kwargs = {}
				for i in avg_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())
					params['cols'].append({"label": k.strip(), "type": "number", "value": k.strip()})
					#Name of annotated column cannot be same as an existing column, hence k!=v
					if k != v:kwargs[k.strip()] = Avg(v.strip())

				#lgr.info('Sum Applied: %s' % kwargs)
				report_list = report_list.annotate(**kwargs)



			#lgr.info('Query Str 6.4: %s' % report_list.query.__str__())
			#lgr.info('Report Sum Values')
			if custom_values not in [None,'']:
				kwargs = {}
				for i in custom_values.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())
					params['cols'].append({"label": k.strip(), "type": "string", "value": k.strip()})
					if k != v:kwargs[k.strip()] = Value(v.strip(), output_field=CharField())

				#lgr.info('Sum Applied: %s' % kwargs)
				report_list = report_list.annotate(**kwargs)


			#lgr.info('Query Str 6.5: %s' % report_list.query.__str__())
			#lgr.info('Report AVG Values')	
			if last_balance not in [None,'']:
				kwargs = {}
				for i in last_balance.split('|'):
					try:k,v = i.split('%')
					except: continue
					args.append(k.strip())
					params['cols'].append({"label": k.strip(), "type": "number", "value": v.strip()})
					if k != v:kwargs[k.strip()] = ( (( (Sum('balance_bf')*2) + Sum('amount') ) + Sum('charge'))*2  )/2
					#try:
					#	if k != v:kwargs[k.strip()] = str(report_list.filter(updated=0).values_list('balance_bf',flat=True)[0])
					#except:
					#	if k != v:kwargs[k.strip()] = str(Decimal(0))


				#lgr.info('AVG Applied: %s' % kwargs)
				report_list = report_list.annotate(**kwargs)



			#lgr.info('Query Str 6.6: %s' % report_list.query.__str__())
			#lgr.info('Last Balance')
			case_query = DataListCaseQuery.objects.using('read').filter(query=data.query,case_inactive=False)

			for case in case_query:
				case_name = case.case_name
				case_values = case.case_values
				case_default_value = case.case_default_value.strip()
				case_when = []

				args.append(case_name.strip())
				params['cols'].append({"label": case_name.strip(), "type": "string", "value": case_name.strip()})

				for i in case_values.split('|'):
					try:case_field, case_value, case_newvalue = i.split('%')
					except: continue
					case_data = {}
					case_value = payload[case_value.strip()] if case_value.strip() in payload.keys() else case_value.strip()
					if case_value == 'False': case_value = False
					elif case_value == 'True': case_value = True

					case_data[case_field.strip()] =  case_value
					case_data['then'] = F(case_newvalue) if getattr(model_class, case_newvalue.split('__')[0], False) else Value(case_newvalue)

					case_when.append(When(**case_data))

				#Final Case

				case_values_data[case_name.strip()] = Case(*case_when, default=F(case_default_value) if getattr(model_class, case_default_value.split('__')[0], False) else Value(case_default_value), output_field=CharField())

				if len(case_values_data.keys()):
					report_list = report_list.annotate(**case_values_data)

			#lgr.info('Query Str 6.7: %s' % report_list.query.__str__())
			#lgr.info('Case Values')
			link_query = DataListLinkQuery.objects.using('read').filter(Q(query=data.query), Q(link_inactive=False),\
							   Q(Q(gateway=gateway_profile.gateway) | Q(gateway=None)),\
						   Q(Q(channel__id=payload['chid']) | Q(channel=None)),\
						   Q(Q(access_level=gateway_profile.access_level) | Q(access_level=None)))

			if gateway_profile.role:
				link_query = link_query.filter(Q(role=None) | Q(role=gateway_profile.role))

			for link in link_query:
				link_name = link.link_name
				link_service = link.link_service.name
				link_icon = link.link_icon.icon
				link_case_filter = link.link_case_filter
				link_params = link.link_params
				case_when = []

				args.append(link_name.strip())
				params['cols'].append({"label": link_name.strip(), "type": "href", "value": link_name.strip()})

				href = { "url":"/"+link_service+"/", "service": link_service, "icon": link_icon, "params": {}}

				for i in link_params.split('|'):
					try:k,v = i.split('%')
					except: continue
					href['params'][k.strip()] = v.strip()
					
				link_value = json.dumps(href)

				#Final Case

				case_filter_data = {}
				if link_case_filter:
					for f in link_case_filter.split("|"):
						cf_list = f.split('%')
						if len(cf_list)==2:
							if cf_list[0] in payload.keys() and getattr(model_class, cf_list[1].split('__')[0], False):
								case_filter_data[cf_list[1]] = payload[cf_list[0]]
							elif getattr(model_class, cf_list[0].split('__')[0], False):
								k,v = cf_list
								v_list = v.split(',')

								if len(v_list)>1:
									v = [l.strip() for l in v_list if l]
								elif v.strip().lower() == 'false':
									v = False
								elif v.strip().lower() == 'true':
									v = True

								case_filter_data[k] = v if v not in ['',None] else None
						elif getattr(model_class, f.split('__')[0], False):
							if  f in payload.keys() and f.split('__')[-1] in ['exact','iexact','contains','icontains','isnull','regex','iregex']:
								if f not in ['',None]: case_filter_data[f] = payload[f]
							elif f in payload.keys():
								if f not in ['',None]: case_filter_data[f + '__icontains'] = payload[f]
							elif 'q' in payload.keys() and payload['q'] not in ['', None]:
								if f not in ['',None]: case_filter_data[f + '__icontains'] = payload['q']

				if case_filter_data:
					case_filter_data['then'] = Value(link_value)

					case_when.append(When(**case_filter_data))

					link_values_data[link_name.strip()] = Case(*case_when, default=Value(''), output_field=CharField())
				else:
					link_values_data[link_name.strip()] = Value(link_value, output_field=CharField())

				if len(link_values_data.keys()):
					report_list = report_list.annotate(**link_values_data)

			#lgr.info('Link Values')

			#lgr.info('Query Str 7: %s' % report_list.query.__str__())
			if or_filters not in [None,'']:
				# for a in filters.split("&"):
				for f in or_filters.split("|"):
					count = 0
					for i in params['cols']:
						if i['value'] == f.strip():
							i['search_filters'] = True
						params['cols'][count] = i
						count += 1

			#lgr.info('Query Str 7.1: %s' % report_list.query.__str__())
			if and_filters not in [None,'']:
				for f in and_filters.split("|"):
					count = 0
					for i in params['cols']:
						if i['value'] == f.strip():
							i['search_filters'] = True
						params['cols'][count] = i
						count += 1

			#lgr.info('Query Str 7.2: %s' % report_list.query.__str__())
			if list_filters not in [None,'']:
				for list_data in list_filters.split('|'):
					count = 0
					for i in params['cols']:
						try:
							if i['value'] == list_data.strip():
								list_filters_data = report_list.values(list_data.strip()).annotate(Count(list_data.strip())).order_by(list_data.strip())
								i['list_filters']= []
								for j in list_filters_data:
									i['list_filters'].append(j[list_data.strip()])
							params['cols'][count] = i
							count += 1
						except: pass

			#lgr.info('Query Str 7.3: %s' % report_list.query.__str__())
			if date_filters not in [None,'']:
				for f in date_filters.split("|"):
					try:k,v = f.split('%')
					except: k,v = f,f

					count = 0
					for i in params['cols']:
						if i['value'] == v.strip():
							agg = {}
							agg['min_'+v.strip()] = Min(v.strip())
							agg['max_'+v.strip()] = Max(v.strip())
							agg_data = report_list.aggregate(**agg)
							min_agg = agg_data['min_' + v.strip()].date().isoformat() if agg_data['min_' + v.strip()] else None
							max_agg = agg_data['max_' + v.strip()].date().isoformat() if agg_data['max_' + v.strip()] else None
							i['date_filters'] = [min_agg,max_agg]
						params['cols'][count] = i
						count += 1

			'''
			if data.query.links not in [None,'']:
				href = {"label": "Actions", "type": "href", "links": {}}

				for i in data.query.links.split('|'):
				link_data = i.split('%')
				name, service, icon = None,None,None
				if len(link_data) == 2:
					name,service = link_data
				elif len(link_data) == 3:
					name,service,icon = link_data

				href['links'][name] = { "url":"/"+service+"/", "service": service, "params": data.query.link_params,"icon":icon}
				#href['links'] = {"label": name, "type": "href","url":"/"+service+"/", "service": service, "params": data.query.link_params,"icon":icon}

				if data.query.link_params not in [None,'']:
						for i in data.query.link_params.split('|'):
						try:k,v = i.split('%')
						except: continue
						href['links'][name]['params'] = {k:v}
				params['cols'].append(href)
			'''

			###########################################################################


			#lgr.info('Query Str 8: %s' % report_list.query.__str__())

			cols = params['cols']
			new_cols = []
			#Indexing
			indexes = []
			if data.indexing not in ["",None]:
			
				for i in data.indexing.split('|'):
					for c in cols:
						if c['label'] == i:
							indexes.append(i)
							new_cols.append(c)
			
			if data.data_response_type.name == 'DATA':
				#Values
				report_list = report_list.values(*args)

				if indexes:
					report_list = report_list.values(*indexes)
					params['cols'] = new_cols

			elif data.data_response_type.name == 'LIST':
				#Values List
				report_list = report_list.values_list(*args)

				if indexes:
					report_list = report_list.values_list(*indexes)
					params['cols'] = new_cols

			else:
				#Values List
				report_list = report_list.values_list(*args)

				if indexes:
					report_list = report_list.values_list(*indexes)
					params['cols'] = new_cols

			##########################################################################

			#lgr.info('Report List 1: %s' % len(report_list))

			#lgr.info('Query Str 9: %s' % report_list.query.__str__())
			#if 'max_id' in payload.keys() and payload['max_id'] > 0:
			#	report_list = report_list.filter(id__lt=payload['max_id'])
			#if 'min_id' in payload.keys() and payload['min_id'] > 0:
			#	report_list = report_list.filter(id__gt=payload['min_id'])

			#lgr.info('Query Str 10: %s' % report_list.query.__str__())
			if distinct:
				distinct_list = distinct.split('|')
				report_list = report_list.distinct(*distinct_list)

			#lgr.info('Query Str 11: %s' % report_list.query.__str__())

			if 'order_by' in payload.keys():
				order_by = payload['order_by'].split(',')
				report_list = report_list.order_by(*order_by)
			else:

				if order:
					order_list  = order.split('|')
					report_list = report_list.order_by(*order_list)
				elif values not in [None,'']:
					i  = values.split('|')[0]
					k,v = i.split('%')
					report_list = report_list.order_by(v)
				else:
					report_list = report_list.order_by('id')

			#
			# report_list = report_list[:]
			#
			# trans = report_list.aggregate(max_id=Max('id'), min_id=Min('id'))
			# max_id = trans.get('max_id')
			# min_id = trans.get('min_id')

			#lgr.info('Report List 2: %s' % len(report_list))


			#Gateway Filter results are part of original report list
			#original_report_list = report_list


			if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
				if data.pn_id_field not in ['',None] and data.pn_update_field not in ['',None]:
					#Filter out (None|NULL). Filter to within the last 10 seconds MQTT runs every 2 seconds. 

					#lgr.info('Report List: %s | %s' % (data.data_name,len(report_list)))

					#report_list_groups = original_report_list.filter(~Q(Q(**{data.pn_id_field: None})|Q(**{data.pn_id_field: ''}))).\
					#					filter(date_modified__gte=timezone.now() - timezone.timedelta(minutes=30)).\
					#					values(data.pn_id_field).annotate(Count(data.pn_id_field))
					original_model_data =  model_class._meta


					id_field_data = data.pn_id_field.split('__')
					id_model_data = original_model_data.get_field(id_field_data[0])
					id_model_pk = ''

					if id_field_data[1:]:
						id_model_pk = id_field_data[0]
						for f in id_field_data[1:]:
							if f in id_field_data[len(id_field_data)-1:]:
								id_model_pk = id_model_pk + '__pk'
							else:
								id_model_pk = id_model_pk + '__' + f if id_model_pk else f

							id_model_data = id_model_data.related_model._meta.get_field(f)
					else: id_model_pk = 'pk'

					id_model_field = id_field_data[len(id_field_data)-1:][0]

					#lgr.info('ID Model Data: %s | ID Model Field: %s | PK: %s ' % (id_model_data.model, id_model_field, id_model_pk))

					update_field_data = data.pn_update_field.split('__')
					update_model_data = original_model_data.get_field(update_field_data[0])
					update_model_pk = ''

					if update_field_data[1:]:
						update_model_pk = update_field_data[0]
						for f in update_field_data[1:]:
							if f in update_field_data[len(update_field_data)-1:]:
								update_model_pk = update_model_pk + '__pk'
							else:
								update_model_pk = update_model_pk + '__' + f if update_model_pk else f

							update_model_data = update_model_data.related_model._meta.get_field(f)
					else: update_model_pk = 'pk'

					update_model_field = update_field_data[len(update_field_data)-1:][0]
					#selected_data[k.strip()] = "to_char("+ model_data.model._meta.app_label +"_"+ model_data.model._meta.model_name +"."+ field_data[len(field_data)-1:][0] +", 'DD, Month, YYYY')"

					#if model_class._meta.get_field(data.pn_id_field).get_internal_type() in ['AutoField','IntegerField','BigAutoField','BinaryField','DecimalField','SmallIntegerField']:
					#Limit report list groups to 50 for optimization
					if id_model_data.model._meta.get_field(id_model_field).get_internal_type() in ['AutoField','IntegerField','BigAutoField','BinaryField','DecimalField','SmallIntegerField']:
						report_list_groups = report_list.filter(~Q(**{data.pn_id_field+'__isnull': True})).\
										values(data.pn_id_field).annotate(Count(data.pn_id_field))[:50]
					else:
						report_list_groups = report_list.filter(~Q(Q(**{data.pn_id_field+'__isnull': True})|Q(**{data.pn_id_field: ''}))).\
										values(data.pn_id_field).annotate(Count(data.pn_id_field))[:50]

					#lgr.info('Report List Group: %s | %s' % (data.data_name,report_list_groups))

					@transaction.atomic
					def get_pn_data(report_list, channel, group):


						params['action'] = [d.name for d in data.pn_action.all()]

						pn_filter= {}
						pn_filter[data.pn_update_field] = False
						pn_filter[data.pn_id_field] = group[data.pn_id_field]
						query = reduce(operator.and_, (Q(k) for k in pn_filter.items()))
						#Lock Query till Marked as sent (SELECT FOR UPDATE) & Select for trigger and Update Unfiltered List
						#original_filtered_report_list = original_report_list.filter(query).select_for_update()

						original_filtered_report_list = report_list.filter(query).select_for_update()

						if data.pn_action.filter(name='REPLACE').exists():
							#Return full list to REPLACE existing list
							report_list = report_list.filter(**{data.pn_id_field: group[data.pn_id_field]})
						else:
							#Return specific list items for APPEND|UPDATE
							report_list = report_list.filter(query)

						if original_filtered_report_list.exists():

							#lgr.info('Sending MQTT: %s' % channel)
							#filtered_report_list_for_update = original_filtered_report_list

							if data.data_response_type.name == 'DATA':
								#lgr.info("#IF values_list is not used")
								#Set Data
								params['data'] = report_list
							elif data.data_response_type.name == 'LIST':
								#lgr.info("#IF values_list is used")
								report_list = np.asarray(report_list).tolist()
								#Set Data
								params['rows']= report_list
							elif data.data_response_type.name == 'STRING':
								#lgr.info("#IF values_list is used")
								report_list = np.asarray(report_list).tolist()
								#Set Data
							if report_list:
								pass
							elif data.ifnull_response not in [None, '']:
								report_list = [[data.ifnull_response]]

							params['lines']= report_list
						else:
							#lgr.info("#IF values_list is used")
							report_list = np.asarray(report_list).tolist()
							#Set Data
							params['rows']= report_list

							#lgr.info("Update notification Sent")

							'''
							record = original_filtered_report_list.values_list(data.pn_id_field,flat=True)
							id_filtered_report = id_model_data.model.objects.filter(**{ id_model_field +'__in': list(record) })
							lgr.info('ID Model Data. Count: %s' % id_filtered_report.count())
							'''

							#lgr.info('Model Data: %s | Field Data: %s | PK: %s' % (update_model_data.model, update_model_field, update_model_pk))
							record = original_filtered_report_list.values_list(update_model_pk,flat=True)
							update_filtered_report = update_model_data.model.objects.using('read').filter(**{ 'pk__in': list(record) })

							#lgr.info('UPDATE Model Data. Count: %s' % update_filtered_report.count())
							pn_update = {}
							pn_update[update_model_field] = True
							update_filtered_report.query.annotations.clear()
							update_filtered_report.filter().using('default').update(**pn_update)

							'''
							pn_update = {}
							pn_update[data.pn_update_field] = True
							#filtered_report_list_for_update.query.annotations.clear()
							#filtered_report_list_for_update.filter().update(**pn_update)
							original_filtered_report_list.query.annotations.clear()
							original_filtered_report_list.filter().update(**pn_update)
							'''

							#Update pn status
							push[channel] = params
							#lgr.info('Return MQTT: %s' % push)

						return push

					for group in report_list_groups:
						if data.push_service:
							channel = "%s/%s/%s/%s" % (gateway_profile.gateway.id, data.data_name,group[data.pn_id_field],data.push_service.name)
							push = get_pn_data(report_list, channel, group)

						else:
							channel = "%s/%s/%s" % (gateway_profile.gateway.id, data.data_name,group[data.pn_id_field])
							push = get_pn_data(report_list, channel, group)

			else:

				#lgr.info('Query Str 12: %s' % report_list.query.__str__())
				lgr.info('Limit: %s' % limit)

				if limit not in [None,""]:
					lgr.info('Limit: %s' % limit)
					report_list = report_list[:int(limit)] #Query Limit to limit Data
					paginator = TimeLimitedPaginator(report_list, payload.get('limit',50)) #Payload Limit to limit records per page
					ct = int(limit)
				else:
					lgr.info('No Limit - Using Paginator Count')
					paginator = TimeLimitedPaginator(report_list, payload.get('limit',50)) #Payload Limit to limit records per page
					ct = paginator.count

				lgr.info('Count: %s' % ct)

				#ct = report_list.count()
				#ct = len(report_list)
				#lgr.info('Count: %s' % ct)

				lgr.info('Query Str 13: %s' % report_list.query.__str__())


				try:
					page = int(payload.get('page', '1'))
				except ValueError:
					page = 1
				lgr.info('Past Page, Paginator')
				try:
					results = paginator.page(page)
				except (EmptyPage, InvalidPage):
					results = paginator.page(paginator.num_pages)

				lgr.info('Past Results, Paginator')

				report_list = results.object_list

				lgr.info('Past Object List, Paginator')

				if data.data_response_type.name == 'DATA':
					#Set Data
					params['data'] = report_list
				elif data.data_response_type.name == 'LIST':
					#IF values_list is used
					report_list = np.asarray(report_list).tolist()
					#Set Data
					params['rows'] = report_list
				elif data.data_response_type.name == 'STRING':
					#IF values_list is used
					report_list = np.asarray(report_list).tolist()
					#Set Data
					if report_list:
						pass
					elif data.ifnull_response not in [None, '']:
						report_list = [[data.ifnull_response]]

					params['lines'] = report_list
				else:
					#IF values_list is used
					report_list = np.asarray(report_list).tolist()
					#Set Data
					params['rows'] = report_list

				lgr.info('Past Formatted Response')
		except Exception as e:
			#import traceback
			lgr.info('Error on report: %s' % e)
			#lgr.info(traceback.format_exc())
		return params,max_id,min_id,ct,push


	def balance(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:

			#manager_list = FloatManager.objects.filter(Q(Q(institution=gateway_profile.institution)|Q(institution=None)),\

			manager_list = FloatManager.objects.using('read').filter(Q(institution=gateway_profile.institution),\
								Q(gateway=gateway_profile.gateway))

			float_type_list = manager_list.values('float_type__name','float_type__id').annotate(count=Count('float_type__id'))

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
		return params


	def contact_group_list(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:

			contact = Contact.objects.using('read').filter(contact_group__institution=gateway_profile.institution,\
					 product__notification__code__institution=gateway_profile.institution).\
			values('status__name', 'cart_item__currency__code'). \
			annotate(status_count=Count('status__name'), total_amount=Sum('cart_item__total'))


			for o in order:
				item = {}
				item['name'] = o['status__name']
				item['description'] = '%s %s' % (o['cart_item__currency__code'], '{0:,.2f}'.format(o['total_amount']))
				item['count'] = '%s' % '{0:,.2f}'.format(o['status_count'])
				params['rows'].append(item)
		except Exception as e:
			lgr.info('Error on contact group list: %s' % e)
		return params


	def purchases_summary(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:
			order = PurchaseOrder.objects.using('read').filter(cart_item__product_item__institution=gateway_profile.institution). \
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
		return params

	@transaction.atomic
	def bid_ranking(self,payload,gateway_profile,profile_tz,data):

		params = {}
		params['cols'] = [
			{"label":"id","value":"id","type":"string"},
			{"label": "position","value": "position", "type": "string"},
			{"label":"name","value":"name","type":"string"},
			{"label":"total_price","value":"total_price","type":"string"},
			{"type":"href","label":"Actions","links":{"Unit Prices":{"service":"VIEW REQUIREMENT APPLICATIONS","icon":"icons:home","params":{"bid_app_id":"id"}}}}
		]

		params['rows'] = []
		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
		try:
			from thirdparty.bidfather.models import Bid,BidRequirementApplication


			if data.pn_data and 'push_request' in payload.keys() and payload['push_request']:
				#push = {}
				import copy
				# Loop through a report to get the different pn_id_fields to be updated | Limit to 50 for optimization
				bid_req_app =  BidRequirementApplication.objects.using('read').select_for_update().filter(pn=False)[:50]
			#lgr.info(bid_req_app)	
			if bid_req_app.exists():
				#lgr.info('push updates exist')
				for req_app in bid_req_app:
					lgr.info('notify bid : {}'.format(req_app))
					#Bid Owner
					channel = "%s/%s/%s" % (gateway_profile.gateway.id, 'bid_ranking', req_app.bid_requirement.bid.institution.id)
					params['rows'] = req_app.bid_requirement.bid.app_rankings(req_app.bid_requirement.bid.institution)
					push[channel] = copy.deepcopy(params)

					#Bid Application
					channel = "%s/%s/%s" % (gateway_profile.gateway.id, 'bid_ranking', req_app.bid_application.institution.id)
					params['rows'] = req_app.bid_requirement.bid.app_rankings(req_app.bid_application.institution)
					push[channel] = copy.deepcopy(params)

				#Update gotta come at the end to prevent filter of data on loop
				bid_req_app.using('default').update(pn=True)

				#lgr.info(push)

				return params,max_id, min_id, ct, push
			else:
				bid = Bid.objects.using('read').get(pk=payload['bid_id'])
				rows = bid.app_rankings(gateway_profile.institution, gateway_profile)
				params['rows'] = rows

				return params,max_id,min_id,ct,push
			
		except Exception as e:
			lgr.info('Error on bid rankings: %s',e)


	def industries_categories(self,payload,gateway_profile,profile_tz,data):
		r = []
		iss = IndustrySection.objects.using('read').all()
		'''
		for i in iss:
			cl = {
			'name':i.isic_code,
			'id':i.pk,
			'description':i.description,
			'divisions':[
				 {
				'name':division.isic_code,
				'id':division.pk,
				'description': division.description,
				'groups':[
					{
					'name':group.isic_code,
					'id':group.pk,
					'description': group.description,
					'classes':[
						{
						'name': industry_class.isic_code,
						'id':industry_class.pk,
						'description': industry_class.description,
						} for industry_class in group.industryclass_set.all()
					]
						} for group in division.industrygroup_set.all()
				]
					} for division in i.industrydivision_set.all()
			]

				}
			r.append(cl)
		#lgr.info(r)
		params = dict(
			data=r
		)

		'''

		c = [{"label": "name", "type": "string"}, {"label": "id", "type": "number"},
				  {"label": "description", "type": "string"}, {"label": "level", "type": "object"}]

		def _class(industryclass_set):
			return [[industry_class.pk,industry_class.isic_code,industry_class.description] for industry_class in industryclass_set]
		def _group(industrygroup_set): 
			return [[group.pk,group.isic_code,group.description, _class(group.industryclass_set.all())] for group in industrygroup_set]
		def _division(industrydivision_set):	
			return [[division.pk,division.isic_code,division.description, _group(division.industrygroup_set.all())] for division in industrydivision_set]

		for i in iss:
			r.append([i.pk,i.isic_code,i.description, _division(i.industrydivision_set.all())])

		#lgr.info(r)
		params = dict(
			rows=r,
			cols=c
		)
		return params

	def purchases(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:
			order = PurchaseOrder.objects.using('read').filter(cart_item__product_item__institution=gateway_profile.institution). \
			extra(select={'month_year': "to_char(pos_purchaseorder.date_created, 'Month, YYYY')"}). \
			values('cart_item__product_item__product_type__name', 'status__name', 'cart_item__currency__code',
				   'month_year'). \
			annotate(status_count=Count('status__name'), total_amount=Sum('cart_item__total'))

			for o in order:
				item = {}
				item['name'] = o['cart_item__product_item__product_type__name']
				item['description'] = '%s %s' % (o['cart_item__currency__code'], o['total_amount'])
				item['count'] = '%s %s' % (o['status_count'], o['status__name'])
				item['date_time'] = '%s' % (o['month_year'])
				params['rows'].append(item)
		except Exception as e:
			lgr.info('Error on purchases: %s' % e)
		return params


	def above_60days_defaulters(self, payload, gateway_profile, profile_tz, data):

		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "name", "type": "string"}, {"label": "msisdn", "type": "string"},
				  {"label": "email", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "count", "type": "string"}, {"label": "date_time", "type": "string"}]


		try:

			account_manager = AccountManager.objects.using('read').filter(credit=False,credit_paid=False,dest_account__account_type__institution=gateway_profile.institution,\
					dest_account__account_type__gateway=gateway_profile.gateway,\
					dest_account__account_type__deposit_taking=False, credit_due_date__lt=timezone.now()-timezone.timedelta(days=60))

			for i in account_manager:
				item = {}
				item['id'] = i.id
				item['name'] = '%s %s' % (i.dest_account.profile.user.first_name, i.dest_account.profile.user.last_name)
				#item['msisdn'] = '%s' % (i.dest_account.gateway_profile.msisdn)
				item['email'] = '%s' % (i.dest_account.profile.user.email)

				item['description'] = 'Amount: %s Charge: %s Balance BF: %s' % (i.amount,i.charge,i.balance_bf)
				item['count'] = 'Loan Time: %s' % (i.credit_time)
				if i.credit_due_date:
					item['date_time'] = '%s' % (profile_tz.normalize(i.credit_due_date.astimezone(profile_tz)).strftime("%d %b %Y %I:%M:%S %p %Z %z"))

				params['rows'].append(item)


		except Exception as e:
			lgr.info('Error on above_60days_defaulters: %s' % e)
		return params

	def credit_account_list(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]

		try:

			account_manager = AccountManager.objects.using('read').\
					filter(credit=False,dest_account__account_type__institution=gateway_profile.institution,\
					dest_account__account_type__gateway=gateway_profile.gateway,dest_account__account_type__deposit_taking=False).\
					extra(select={'month_year': "to_char( vbs_accountmanager.date_created, 'Month, YYYY')"}).\
					values('dest_account__account_type__name','credit_paid','month_year').\
					annotate(Sum('balance_bf'),Sum('charge'),Count('dest_account__id'))

			for i in account_manager:
				item = {}
				item['name'] = '%s | Paid %s' % (i['dest_account__account_type__name'],i['credit_paid'])
				#item['name'] = 'Credit'
				loan = '{0:,.2f}'.format(i['balance_bf__sum'])
				interest = '{0:,.2f}'.format(i['charge__sum'])
				item['description'] = 'Interest: %s | Loan %s | Credit Paid: %s | Loan Accounts: %s ' % (interest, loan, i['credit_paid'],i['dest_account__id__count'])
				#item['description'] = 'Interest: %s | Loan %s' % (interest, loan)
				item['date_time'] = '%s' % (i['month_year'])
				params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on credit account list: %s' % e)
		return params




	def credit_account(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:
			account_manager = AccountManager.objects.using('read').filter(credit=False,dest_account__account_type__institution=gateway_profile.institution,\
					dest_account__account_type__gateway=gateway_profile.gateway,\
					dest_account__account_type__deposit_taking=False)

			total_amount = Decimal(0)
			credit_details = {'PAID':Decimal(0),'OUTSTANDING':Decimal(0),'OVERDUE':Decimal(0),'30 DAYS OVERDUE':Decimal(0), '60 DAYS OVERDUE':Decimal(0)}

			for i in account_manager:
				'''
				if i.credit_paid:
					credit_details['PAID'] = credit_details['PAID'] + i.balance_bf
				elif i.credit_due_date and i.credit_due_date < timezone.now():
					credit_details['OUTSTANDING'] = credit_details['OUTSTANDING'] + i.balance_bf
				elif i.credit_due_date and i.credit_due_date > timezone.now() and i.credit_due_date > timezone.now()-timezone.timedelta(days=30) and i.credit_due_date < timezone.now()-timezone.timedelta(days=60):
					credit_details['30 DAYS OVERDUE'] = credit_details['30 DAYS OVERDUE'] + i.balance_bf
				elif i.credit_due_date and i.credit_due_date > timezone.now() and i.credit_due_date > timezone.now()-timezone.timedelta(days=60):
					credit_details['60 DAYS OVERDUE'] = credit_details['60 DAYS OVERDUE'] + i.balance_bf
				else:
					credit_details['OVERDUE'] = credit_details['OVERDUE'] + i.amount
				'''
				if i.credit_paid:
					credit_details['PAID'] = credit_details['PAID'] + i.balance_bf
				elif i.credit_due_date and i.credit_due_date < timezone.now()-timezone.timedelta(days=30) and i.credit_due_date > timezone.now()-timezone.timedelta(days=60):
					credit_details['30 DAYS OVERDUE'] = credit_details['30 DAYS OVERDUE'] + i.balance_bf
				elif i.credit_due_date and i.credit_due_date <= timezone.now()-timezone.timedelta(days=60):
					credit_details['60 DAYS OVERDUE'] = credit_details['60 DAYS OVERDUE'] + i.balance_bf
				elif i.credit_due_date and i.credit_due_date and i.credit_due_date <= timezone.now():
					credit_details['OUTSTANDING'] = credit_details['OUTSTANDING'] + i.balance_bf
				else:
					credit_details['OVERDUE'] = credit_details['OVERDUE'] + i.amount



				for k,v in credit_details.items():
					item = {}
					item['name'] = str(k)
					item['count'] = '%s' % '{0:,.2f}'.format(v)
					params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on credit account: %s' % e)
		return params


	def investment_summary_chart(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "date_time", "type": "date"}]
		init_rows = [None]
		init_cols = []
		try:

			from thirdparty.amkagroup_co_ke.models import Investment, InvestmentType
			investment_list = Investment.objects.using('read').all().\
					extra(select={'month_year': "to_char( amkagroup_co_ke_investment.date_created, 'Month, YYYY')"}).values('investment_type__product_item__product_type__name','month_year').\
					annotate(Count('investment_type__product_item__product_type__name'))

			investment_list_name = investment_list.values('investment_type__product_item__product_type__name').annotate(Count('investment_type__product_item__product_type__name'))
			for a in investment_list_name:
				params['cols'].append({"label": str(a['investment_type__product_item__product_type__name']), "type": "number" })
				init_rows.append(None)
				init_cols.append(str(a['investment_type__product_item__product_type__name']))

				for i in investment_list:
					item = list(init_rows)

					item[0] = i['month_year']
					count = 1
					for c in init_cols:
						if c == str(i['investment_type__product_item__product_type__name']):
							item[count] = str( i['investment_type__product_item__product_type__name__count'] )
						count += 1

					params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on investment summary chart: %s' % e)
		return params



	def enrollments_summary_chart(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "date_time", "type": "date"}]
		init_rows = [None]
		init_cols = []
		try:

			enrollment_list = Enrollment.objects.using('read').filter(enrollment_type__product_item__institution=gateway_profile.institution, status__name='ACTIVE').\
					extra(select={'month_year': "to_char( crm_enrollment.date_created, 'Month, YYYY')"}).values('enrollment_type__product_item__product_type__name','month_year').\
					annotate(Count('enrollment_type__product_item__product_type__name'))

			#.values('dest_account__id').annotate(Count('dest_account__id')).annotate(Max('id')).values('balance_bf','dest_account__gateway_profile').extra(select={'day': 'date( vbs_accountmanager.date_created )'}).values('dest_account__id','','days')

			enrollment_list_name = enrollment_list.values('enrollment_type__product_item__product_type__name').annotate(Count('enrollment_type__product_item__product_type__name'))
			for a in enrollment_list_name:
				params['cols'].append({"label": str(a['enrollment_type__product_item__product_type__name']), "type": "number" })
				init_rows.append(None)
				init_cols.append(str(a['enrollment_type__product_item__product_type__name']))

				for i in enrollment_list:
					item = list(init_rows)

					item[0] = i['month_year']
					count = 1
					for c in init_cols:
						if c == str(i['enrollment_type__product_item__product_type__name']):
							item[count] = str( i['enrollment_type__product_item__product_type__name__count'] )
						count += 1

					params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on enrollment summary chart: %s' % e)
		return params




	def credit_account_chart(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "date_time", "type": "date"}]

		try:

			account_manager = AccountManager.objects.using('read').\
					filter(credit=False,dest_account__account_type__institution=gateway_profile.institution,dest_account__account_type__gateway=gateway_profile.gateway,dest_account__account_type__deposit_taking=False).\
					extra(select={'month_year': "to_char( vbs_accountmanager.date_created, 'Month, YYYY')"}).values('balance_bf','dest_account__account_type__name','month_year')

			#.values('dest_account__id').annotate(Count('dest_account__id')).annotate(Max('id')).values('balance_bf','dest_account__gateway_profile').extra(select={'day': 'date( vbs_accountmanager.date_created )'}).values('dest_account__id','','days')

			account_manager_name = account_manager.values('dest_account__account_type__name').annotate(Count('dest_account__account_type__name'))
			for a in account_manager_name:
				params['cols'].append({"label": str(a['dest_account__account_type__name']), "type": "number" })

				for i in account_manager:
					item = []
					#item.append( str(i['dest_account__account_type__name']) )

					item.append( i['month_year'] )
					item.append( str( i['balance_bf'] ) )
					params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on credit account: %s' % e)
		return params

	def investment_summary(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:

			from thirdparty.amkagroup_co_ke.models import Investment, InvestmentType
			investment = Investment.objects.using('read').values('account__id').annotate(Count('account__id'))

			investment_type = investment.values('investment_type__id','investment_type__name','investment_type__value').annotate(Count('investment_type__id'))
			for i in investment_type:
				pie_total = investment.filter(investment_type__id=i['investment_type__id']).annotate(Max('pie')).aggregate(Sum('pie__max'))

				item = {}
				item['name'] = i['investment_type__name']
				item['description'] = '%s' % (i['investment_type__value'] * pie_total['pie__max__sum'])
				item['count'] = '%s' % '{0:,.2f}'.format(pie_total['pie__max__sum'])
				params['rows'].append(item)

		except Exception as e:
			lgr.info('Error on investment summary: %s' % e)
		return params


	def notifications(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]


		try:
			outbound = Outbound.objects.using('read').filter(
				contact__product__notification__code__institution=gateway_profile.institution). \
			extra(select={'month_year': "to_char(notify_outbound.date_created, 'Month, YYYY')"}). \
			values('contact__product__name', 'state__name', 'contact__product__notification__name', 'month_year'). \
			annotate(state_count=Count('state__name'))

			for o in outbound:
				item = {}
				item['name'] = o['contact__product__name']
				item['type'] = o['contact__product__notification__name']
				# item['description'] =
				item['count'] = '%s %s' % (o['state_count'], o['state__name'])
				item['date_time'] = '%s' % (o['month_year'])
				params['rows'].append(item)
		except Exception as e:
			lgr.info('Error on notifications: %s' % e)
		return params

	def process_data_list(self, data_list, payload, gateway_profile, profile_tz, data):
		#lgr.info("Wrapper process_data_list")
		cols = []
		rows = []
		lines = []
		groups = []
		data = []
		min_id = 0
		max_id = 0
		t_count = 0
		push = {}
		try:
			#lgr.info('Fetching from Data List')
			collection = {}
			for d in data_list:
				if d.command_function not in ['', None] and d.node_system:
				#lgr.info('Is a Function: ')
					try:

						node_to_call = d.node_system.URL.lower()
						class_name = d.data_response_type.name.title()
						#lgr.info("Node To Call: %s Class Name: %s" % (node_to_call, class_name))


						'''
						class_command = 'from '+node_to_call+'.data import '+class_name+' as c'
						#lgr.info('Class Command: %s' % class_command)
						try:exec (class_command)
						except Exception as e: lgr.info('Error on Exec: %s' % e)

						#lgr.info("Class: %s" % class_name)
						fn = c()
						func = getattr(fn, d.command_function)
						#lgr.info("Run Func: %s TimeOut: %s" % (func, d.node_system.timeout_time))
						'''

						import importlib
						module =  importlib.import_module(node_to_call+'.data')
						#module = __import__.import_module(node_to_call+'.tasks')
						lgr.info('Module: %s' % module)
						my_class = getattr(module, class_name)
						lgr.info('My Class: %s' % my_class)
						fn = my_class()
						lgr.info("Call Class: %s" % fn)

						func = getattr(fn, d.command_function)


						#responseParams = func(payload, node_info)
						params,max_id,min_id,t_count,push[d.data_name] = func(payload, gateway_profile, profile_tz, d)

						#lgr.info('After Call')
						'''
						func = getattr(self, d.function.strip())
						params,max_id,min_id,t_count,push[d.data_name] = func(payload, gateway_profile, profile_tz, d)
						'''

						cols = params['cols'] if 'cols' in params.keys() else []
						rowsParams = params['rows'] if 'rows' in params.keys() else []
						dataParams = params['data'] if 'data' in params.keys() else []
						linesParams = params['lines'] if 'lines' in params.keys() else []
						for item in rowsParams:
							if d.group is not None:
								if d.group.name not in collection.keys():
									collection[d.group.name] = [item]
								else:
									collection[d.group.name].append(item)

								#lgr.info('rowParams | collection: %s' % item)
							else:
								#lgr.info('rowParams: %s' % item)
								rows.append(item)

						for item in dataParams:
							if d.group is not None:
								if d.group.name not in collection.keys():
									collection[d.group.name] = [item]
								else:
									collection[d.group.name].append(item)
							else:
								data.append(item)
						for item in linesParams:
							if d.group is not None:
								if d.group.name not in collection.keys():
									collection[d.group.name] = [item]
								else:
									collection[d.group.name].append(item)
							else:
								lines.append(item)

					except Exception as e:
						lgr.info('Error on Data List Function: %s' % e,exc_info=True)

				elif d.query:
					#lgr.info('Is a Query: ')
					try:
						params,max_id,min_id,t_count,push[d.data_name] = self.report(payload, gateway_profile, profile_tz, d)
						cols = params['cols'] if 'cols' in params.keys() else []
						rowsParams = params['rows'] if 'rows' in params.keys() else []
						dataParams = params['data'] if 'data' in params.keys() else []
						linesParams = params['lines'] if 'lines' in params.keys() else []
						for item in rowsParams:
							if d.group is not None:
								if d.group.name not in collection.keys():
									collection[d.group.name] = [item]
								else:
									collection[d.group.name].append(item)
							else:
								rows.append(item)

						for item in dataParams:
							if d.group is not None:
								if d.group.name not in collection.keys():
									collection[d.group.name] = [item]
								else:
									collection[d.group.name].append(item)
							else:
								data.append(item)
						for item in linesParams:
							if d.group is not None:
								if d.group.name not in collection.keys():
									collection[d.group.name] = [item]
								else:
									collection[d.group.name].append(item)
							else:
								lines.append(item)


					except Exception as e:
						lgr.info('Error on Data List Query: %s' % e)
				else:
					lgr.info('Not a Function')
					if d.group is not None:
						item = {"url": d.url, "description": d.content, "type": d.group.name, "name": d.title}
						if d.group.name not in collection.keys():
							collection[d.group.name] = [item]
						else:
							collection[d.group.name].append(item)

					else:
						rows.append([d.url, d.content,d.title])

			groups = sorted(collection.keys())
			data = [collection[k] for k in groups]

		except Exception as e:
			lgr.info('Error on process_data_list: %s' % e)
		#lgr.info(2058)
		#lgr.info(cols)
		#lgr.info(rows)
		return cols,rows,lines,groups,data,min_id,max_id,t_count, push


class System(Wrappers):
	def data_source(self, payload, node_info):
		try:
			lgr.info('DSC Data %s Payload: %s' % (('data_name' in payload.keys()), payload))
			cols = []
			rows = []
			lines = []
			groups = []
			data = []
			min_id = 0
			max_id = 0
			t_count = 0
			gateway_profile = GatewayProfile.objects.using('read').get(id=payload['gateway_profile_id'])
			profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)

			# Get value from first = sign
			v = payload['data_name']
			data_name, data_name_val = None, None
			n = v.find("=")
			if n >= 0:
				data_name = v[:n].lower()
				data_name_val = v[(n + 1):].strip()
			else:
				data_name = v.lower()

			if data_name_val and data_name not in payload.keys():
				payload[data_name] = data_name_val

			#lgr.info('Data Source: data_name: %s val: %s' % (data_name, data_name_val))
			data_list = DataList.objects.using('read').filter(Q(data_name=data_name.strip()), Q(status__name='ACTIVE'), \
							Q(Q(gateway=gateway_profile.gateway) | Q(gateway=None)), \
							Q(Q(channel__id=payload['chid']) | Q(channel=None)), \
							Q(Q(access_level=gateway_profile.access_level) | Q(access_level=None))).order_by('level')

			if 'institution_id' in payload.keys():
				data_list = data_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
			else:
				data_list = data_list.filter(institution=None)

			cols, rows, lines, groups, data, min_id, max_id, t_count, push = self.process_data_list(data_list, payload, gateway_profile, profile_tz, data)

			payload['response'] = {
				'cols': cols,
				'rows': rows,
				'lines': lines,
				'groups': groups,
				'data': data,
				'min_id': min_id,
				'max_id': max_id,
				'row_count': t_count,
				}
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Data from Source: %s" % e)
		return payload


	def upload_file(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'
			filename = payload['file_upload']
			tmp_file = media_temp + str(filename)
			upload = FileUpload.objects.filter(trigger_service__name=payload['SERVICE'])

			if upload.exists():
				extension_chunks = str(filename).split('.')
				extension = extension_chunks[len(extension_chunks) - 1]
				try:
					original_filename = base64.urlsafe_b64decode(filename.replace(extension, '')).decode()
				except:
					original_filename = filename.replace(extension, '')
				activity_status = FileUploadActivityStatus.objects.get(name='CREATED')
				channel = Channel.objects.get(id=payload['chid'])
				activity = FileUploadActivity(name=original_filename[:45], file_upload=upload[0], status=activity_status, \
								  gateway_profile=gateway_profile,
								  details=self.transaction_payload(payload), channel=channel)
				if 'description' in payload.keys():
					activity.description = payload['description']

				#with open(tmp_file, 'rb+') as f:
				with open(tmp_file, 'r',encoding="utf8", errors='ignore') as f:
					activity.file_path.save(filename, File(f), save=False)
				f.close()


				activity.save()

				payload['response'] = "File Saved. Wait to Process"
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '21'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Uploading File: %s" % e)
		return payload

	def image_list_details(self,payload,node_info):
		try:
			image_lists  = ImageList.objects.using('read').filter(pk=payload['image_list_id'])
			if image_lists.exists():
				image_list = image_lists[0]		
				
				payload['image_list_name'] = image_list.name
				payload['image_list_image'] = image_list.image.url
				
				payload['response_status'] = '00'
				payload['response'] = "Retrieved ImageList Details"

			else:
				payload['response_status'] = '21'
				payload['response'] = "ImageList Not Found"

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info('Error retrieving ImageList details: ',exc_info=True)

		return payload


	def upload_image_list_bulk(self, payload, node_info):
		try:
			
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			bulk_uploads = payload['bulk_uploads']
			for bulk_upload in bulk_uploads.split('|'):
				response_name = bulk_upload.split(':')
				image_list = ImageList()
				image_list.name = response_name[1]
				image_list.description = None
				image_list.image_list_type = ImageListType.objects.get(name='GALLERY')
				media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'
				tmp_image = media_temp + str(response_name[0])
				with open(tmp_image, 'r') as f:
					image_list.image.save(response_name[1],File(f),save=False)
				f.close()
				image_list.save()
				image_list.institution.add(gateway_profile.institution)
				image_list.gateway.add(gateway_profile.gateway)

				payload['response'] = 'Uploads Processed Successfully'
				payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on processing bulk uploads.",exc_info=True)
		return payload




class Trade(System):
	pass
class Payments(System):
	pass

#Process File with Pands
@app.task(ignore_result=True, soft_time_limit=259200)
def pre_process_file_upload(payload):
	payload = json.loads(payload)
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	u =FileUploadActivity.objects.using('read').get(id=payload['id'])
	try:

		rf = u.file_path
		df = pd.read_csv(rf)
		lgr.info('Data Frame Columns: %s' % df.columns)
		lgr.info('Data Frame: \n%s' % df.head())
		lgr.info('Data Frame: \n%s' % df.tail())

		df.fillna('', inplace=True)

		df.columns = [c.strip().lower().replace(' ','_')   for c in df.columns]

		lgr.info('Data Frame Columns: %s' % df.columns)
		if 'recipient' in df.columns:
			lgr.info('RECIPIENT Exists: %s' % df['recipient'].dtype)
			df['recipient'] = pd.to_numeric(df['recipient'], errors='coerce')
			df = df.dropna()
			df['recipient'] = df['recipient'].astype(int)

		if 'msisdn' in df.columns:
			lgr.info('MSISDN Exists: %s' % df['msisdn'].dtype)
			df['msisdn'] = pd.to_numeric(df['msisdn'], errors='coerce')
			df = df.dropna()
			df['msisdn'] = df['msisdn'].astype(int)

		tasks = []
		for row in df.itertuples():
			payload = json.loads(u.details)
			for i in range(len(df.columns)):
				payload[df.columns[i]] = row[i+1]

			payload['chid'] = u.channel.id
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = '127.0.0.1'

			lgr.info('Payload: %s' % payload)
			service = u.file_upload.activity_service
			gateway_profile = u.gateway_profile

			tasks.append(bridgetasks.service_call.s(service.name, gateway_profile.id, payload))


		chunks, chunk_size = len(tasks), 500
		file_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]

		#file_tasks = group(*tasks)()


		payload['response'] = "File Processed"
		payload['response_status'] = '00'
	except Exception as e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload



# Allow file to process for 72hrs| Means maximum records can process is: 432,000
@app.task(ignore_result=True, soft_time_limit=259200)
def process_file_upload_activity(payload):
	payload = json.loads(payload)
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	u =FileUploadActivity.objects.get(id=payload['id'])
	try:

		rf = u.file_path

		f = rf.path
		extension_chunks = str(f).split('.')
		extension = extension_chunks[len(extension_chunks) - 1]
		w = f.replace('.' + extension, '_processed.' + extension)

		with open(w, 'w+') as ff:
			u.processed_file_path.save(rf.name, File(ff), save=False)
			u.save()
			ff.close()

			wf = u.processed_file_path
			payload = json.loads(u.details)

			rfile_obj = default_storage.open(rf, 'r')
			wfile_obj = default_storage.open(wf, 'w+')

			r = csv.reader(rfile_obj)
			w = csv.writer(wfile_obj)
			lgr.info('Captured CSV Objects: %s|%s' % (r, w))
			count = 0
			header = []
			for c in r:
				if count == 0:
					for i in c:
						header.append(i)
				else:
					#if len(c) == len(header):
					lgr.info('HEader: %s' % header)

					lgr.info('Row: %s' % c)
					try:
						for i in range(len(header)):
							if c[i] not in [None, ""]:
								key = header[i]
								lgr.info('Key: %s' % key)
								key = key.decode('utf-8','ignore').strip()
								lgr.info('Key: %s' % key)
								key = key.lower().replace(" ", "_").replace("/", "_")
								lgr.info('Key: %s' % key)
								value = c[i]
								lgr.info('Value: %s' % value)
								value = value.decode('utf-8','ignore').strip()
								#value = c[i].encode('ascii','ignore').decode('utf-8','ignore').strip()
								lgr.info('Value: %s' % value)
								payload[key] = value
					except Exception as e:
						lgr.info('Error: %s' % e)
						continue

					# exec payload
					payload['chid'] = u.channel.id
					payload['ip_address'] = '127.0.0.1'
					payload['gateway_host'] = '127.0.0.1'

					lgr.info('Payload: %s' % payload)

					try:
						valid = True
						if 'email' in payload.keys():
							valid = Wrappers().validateEmail(payload['email'])

						if valid and 'msisdn' in payload.keys():
							valid =  UPCWrappers().get_msisdn(payload)

						if valid:
							try:
								Wrappers().service_call(u.file_upload.activity_service, u.gateway_profile, payload)

								service = u.file_upload.activity_service
								gateway_profile = u.gateway_profile

								#bridge_task = bridgetasks.background_service_call(service.name, gateway_profile.id, payload)

							except Exception as e:
								lgr.info('Error on Service Call: %s' % e)

							c.append('PROCESSED')
							w.writerow(c)
						else:
							c.append('INVALID DATA')
							w.writerow(c)
					except Exception as e:
						lgr.info('Error on Service Call: %s' % e)
						c.append('FAILED')
						w.writerow(c)

				count += 1
			rfile_obj.close()
			wfile_obj.close()

		payload['response'] = "File Processed"
		payload['response_status'] = '00'
	except Exception as e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload


@app.task(ignore_result=True)  # Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60 * 10)
def process_file_upload():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		upload = FileUploadActivity.objects.select_for_update().filter(status__name='CREATED', \
									   date_modified__lte=timezone.now() - timezone.timedelta(
										   seconds=10))
		tasks = []
		for u in upload:
			try:
				u.status = FileUploadActivityStatus.objects.get(name='PROCESSING')
				u.save()
				lgr.info('Captured Upload: %s' % u)
				payload = {}
				payload['id'] = u.id


				payload = json.dumps(payload, cls=DjangoJSONEncoder)
				#process_file_upload_activity.delay(payload)
				tasks.append(pre_process_file_upload.s(payload))

				u.status = FileUploadActivityStatus.objects.get(name='PROCESSED')
				u.save()

				lgr.info("Files Written to and Closed")
			except Exception as e:
				u.status = FileUploadActivityStatus.objects.get(name='FAILED')
				u.save()

				lgr.info('Error on creating file preprocessing request: %s | %s' % (u, e))


		file_tasks = group(*tasks)()
	except Exception as e:
		lgr.info('Error on process file upload')


def push_update(k, v):
	try:

		msc = MqttServerClient()

		channel = k
		channel_list = channel.split('/')
		if len(channel_list) == 3:
			#lgr.info('Channel: %s' % channel)
			itms = json.dumps(v, cls=DjangoJSONEncoder)
			#lgr.info('Items: %s' % itms)

			msc.publish(
				channel,
				itms
			)
		elif len(channel_list) == 4:
			for i in v['data']:
				params = i.copy()
				service = Service.objects.using('read').get(name=channel_list[3])
				gateway = Gateway.objects.using('read').get(id=channel_list[0])
				if 'session_gateway_profile_id' in params.keys():
					gateway_profile = GatewayProfile.objects.using('read').get(id=params['session_gateway_profile_id'])
				elif 'gateway_profile_id' in params.keys():
					gateway_profile = GatewayProfile.objects.using('read').get(id=params['gateway_profile_id'])
				else:
					gateway_profile = GatewayProfile.objects.using('read').get(gateway=gateway,user__username='System@User',status__name__in=['ACTIVATED'])
				payload = {}
				for k,v in params.items():
					try: v = json.loads(v)
					except: pass
					if isinstance(v, dict): payload.update(v)
					else: payload[k] = v
				payload['chid'] = 2
				payload['ip_address'] = '127.0.0.1'
				payload['gateway_host'] = '127.0.0.1'

				lgr.info('Service: %s | Gateway Profile: %s | Data: %s' % (service, gateway_profile, payload))
				bridgetasks.background_service_call.delay(service.name, gateway_profile.id, payload)

		msc.disconnect()
	except Exception as e: lgr.info('Push update Failure: %s ' % e)
	#disconnect after loop

@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_push_request():
	lgr = get_task_logger(__name__)
	try:

		lgr.info('Start Push Request')
		pu = push_update
		#lgr.info('Push Update: %s' % pu)
		#from celery.utils.log import get_task_logger
		cols = []
		rows = []
		lines = []
		groups = []
		data = []
		min_id = 0
		max_id = 0
		t_count = 0

		gateway_profile_list = GatewayProfile.objects.using('read').filter(access_level__name='SYSTEM',status__name='ACTIVATED',user__username='PushUser')
		for gateway_profile in gateway_profile_list:
			profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
			data_list = DataList.objects.using('read').filter(Q(status__name='ACTIVE'),Q(pn_data=True),\
						Q(Q(gateway=gateway_profile.gateway) | Q(gateway=None))).order_by('level')

			if data_list.exists():
				lgr.info('push notification datalists : %s' % data_list)
				payload = {}
				payload['push_request'] = True
				payload['chid'] = 2
				cols, rows, lines, groups, data, min_id, max_id, t_count, push = Wrappers().process_data_list(data_list, payload, gateway_profile, profile_tz, data)

				lgr.info("MQTT task: %s" % push)

				for key,value in push.items():
					lgr.info("%s PN: %s" % (key,value))
					#for k,v in value.items():
					#	pu(k,v)
					result = map(lambda kv: pu(kv[0],kv[1]), value.items())

		lgr.info('End Push Request')
	except Exception as e: lgr.info('Error on process push request: %s' % e)
