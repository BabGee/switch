from __future__ import absolute_import

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
from celery import shared_task
from celery.contrib.methods import task
from celery.contrib.methods import task_method
from celery.utils.log import get_task_logger
from crc.models import *
from crm.models import *
from django.apps import apps
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Sum, Max, Min, Avg, Q, F, Func, Value, CharField, CharField, Case, Value, When
from django.db.models.functions import Concat, Substr
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.timezone import utc
from dsc.models import *
from dsc.models import *
from muziqbit.models import *
from notify.models import *
from paygate.models import *
from pos.models import *
from survey.models import *
from switch.celery import app
from switch.celery import single_instance_task
from thirdparty.amkagroup_co_ke.models import *
from thirdparty.bidfather.models import *
from vbs.models import *
import numpy as np
from django.core.paginator import Paginator, EmptyPage, InvalidPage

lgr = logging.getLogger('dsc')


class Wrappers:
    def validateEmail(self, email):
        try:
            validate_email(str(email))
            return True
        except ValidationError:
            return False

    @app.task(filter=task_method, ignore_result=True)
    def service_call(self, service, gateway_profile, payload):
        lgr = get_task_logger(__name__)
        from api.views import ServiceCall
        try:
            payload = ServiceCall().api_service_call(service, gateway_profile, payload)
            lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info('Unable to make service call: %s' % e)
        return payload

    # Allow file to process for 72hrs| Means maximum records can process is: 432,000
    @app.task(filter=task_method, ignore_result=True, soft_time_limit=259200)
    def process_file_upload_activity(self, u):
        from celery.utils.log import get_task_logger
        lgr = get_task_logger(__name__)
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
                    if len(c) == len(header):
                        for i in range(len(header)):
                            if c[i] not in [None, ""]:
                                key = header[i].lower().replace(" ", "_").replace("/", "_")
                                payload[key] = c[i]

                        # exec payload
                        payload['chid'] = u.channel.id
                        payload['ip_address'] = '127.0.0.1'
                        payload['gateway_host'] = '127.0.0.1'

                        try:
                            valid = False
                            if 'email' in payload.keys():
                                if self.validateEmail(payload['email']):
                                    valid = True
                                else:
                                    del payload['email']

                            if 'msisdn' in payload.keys():
                                payload["msisdn"] = '+%s' % payload["msisdn"] if '+' not in payload["msisdn"] else \
                                    payload["msisdn"]
                                pr = re.compile(r'^\+\d{9,15}$')
                                if pr.match(payload['msisdn']):
                                    valid = True
                                else:
                                    del payload['msisdn']

                            if valid:
                                try:
                                    self.service_call(u.file_upload.activity_service, u.gateway_profile, payload)
                                except Exception, e:
                                    lgr.info('Error on Service Call: %s' % e)

                                c.append('PROCESSED')
                                w.writerow(c)
                            else:
                                c.append('INVALID DATA')
                                w.writerow(c)
                        except Exception, e:
                            lgr.info('Error on Service Call: %s' % e)
                            c.append('FAILED')
                            w.writerow(c)

                count += 1
            rfile_obj.close()
            wfile_obj.close()

            payload['response'] = "File Processed"
            payload['response_status'] = '00'
        except Exception, e:
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
                            'service' not in key and key <> 'lat' and key <> 'lng' and \
                            key <> 'chid' and 'session' not in key and 'csrf_token' not in key and \
                            'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
                            'gateway_profile' not in key and 'transaction_timestamp' not in key and \
                            'action_id' not in key and 'bridge__transaction_id' not in key and \
                            'merchant_data' not in key and 'signedpares' not in key and \
                            key <> 'gpid' and key <> 'sec' and \
                            key not in ['ext_product_id', 'vpc_securehash', 'ext_inbound_id', 'currency', 'amount'] and \
                            'institution_id' not in key and key <> 'response' and key <> 'input':
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
		from survey.tasks import System  as SurveySystem


		code_request = CodeRequest.objects.all().values('code_allocation','region__name','code_preview').\
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

        except Exception, e:
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
		from survey.tasks import System  as SurveySystem


		code_request = CodeRequest.objects.all().values('code_allocation','region__name','code_preview').\
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

        except Exception, e:
            lgr.info('Error on report: %s' % e)
        return params

    def report(self, payload, gateway_profile, profile_tz, data):
        params = {}
        params['rows'] = []
        params['cols'] = []
        max_id = 0
        min_id = 0
        ct = 0


        try:
            model_class = apps.get_model(data.query.module_name, data.query.model_name)
            # model_class = globals()[data.query.model_name]
            filters = data.query.filters
            date_filters = data.query.date_filters
            time_filters = data.query.time_filters
            token_filter = data.query.token_filter

            not_filters = data.query.not_filters
            or_filters = data.query.or_filters
            and_filters = data.query.and_filters
            institution_filters = data.query.institution_filters
            gateway_filters = data.query.gateway_filters
            gateway_profile_filters = data.query.gateway_profile_filters

            list_filters = data.query.list_filters

            values = data.query.values
            count_values = data.query.count_values
            sum_values = data.query.sum_values
            last_balance = data.query.last_balance
            avg_values = data.query.avg_values

            filter_data = {}
            date_filter_data = {}
            time_filter_data = {}
            token_filter_data = {}

            not_filter_data = {}
            or_filter_data = {}
            and_filter_data = {}
            institution_filter_data = {}
            gateway_filter_data = {}
            gateway_profile_filter_data = {}

	    list_filter_data = {}

	    lgr.info('Model Name: %s' % data.query.name)
            report_list = model_class.objects.all()

	    lgr.info('Report List')
            if filters not in ['',None]:
                for i in filters.split("|"):
                    k,v = i.split('%')
		    if model_class._meta.get_field(k.split('__')[0]).get_internal_type()=='BooleanField':
			v = True if v not in ['',None,'False',False,'false'] else False
                    filter_data[k] = v if v not in ['',None] else None
                if len(filter_data):
                    query = reduce(operator.and_, (Q(k) for k in filter_data.items()))

		    lgr.info('Report List: %s' % report_list.count())
		    lgr.info('Filters Applied: %s' % query)
                    report_list = report_list.filter(query)
		    lgr.info('Report List: %s' % report_list.count())

	    lgr.info('Report Filters')
            if not_filters not in ['',None]:
                for i in not_filters.split("|"):
                    k,v = i.split('%')
		    if model_class._meta.get_field(k.split('__')[0]).get_internal_type()=='BooleanField':
			v = True if v not in ['',None,'False',False,'false'] else False
                    not_filter_data[k] = v if v not in ['',None] else None
                if len(not_filter_data):
                    query = reduce(operator.and_, (~Q(k) for k in not_filter_data.items()))

		    lgr.info('Report List: %s' % report_list.count())
		    lgr.info('Not Filters Applied: %s' % query)
                    report_list = report_list.filter(query)
		    lgr.info('Report List: %s' % report_list.count())

	    lgr.info('Report Not Filters')
            if date_filters not in ['',None]:
	        lgr.info('Date Filters')
                for i in date_filters.split("|"):
                    k,v = i.split('%')
	    	    lgr.info('Date %s| %s' % (k,v))
		    try: date_filter_data[k] = (timezone.now()+timezone.timedelta(days=float(v))).date() if v not in ['',None] else None
		    except Exception, e: lgr.info('Error on date filter: %s' % e)
                if len(date_filter_data):
	    	    lgr.info('Date Filter Data: %s' % date_filter_data)
                    query = reduce(operator.and_, (Q(k) for k in date_filter_data.items()))
		    lgr.info('Query: %s' % query)
                    report_list = report_list.filter(query)

	    lgr.info('Report Date Filters')
            if time_filters not in ['',None]:
                for i in time_filters.split("|"):
                    k,v = i.split('%')
		    try: time_filter_data[k] = timezone.now()+timezone.timedelta(hours=float(v)) if v not in ['',None] else None
		    except Exception, e: lgr.info('Error on time filter: %s' % e)

                if len(time_filter_data):
                    query = reduce(operator.and_, (Q(k) for k in time_filter_data.items()))
		    lgr.info('Query: %s' % query)

                    report_list = report_list.filter(query)

            #q_list = [Q(**{f:q}) for f in field_lookups]
	    lgr.info('Report Token Filters')
            if token_filter not in ['',None]:
                for f in token_filter.split("|"):
            	    if 'csrfmiddlewaretoken' in payload.keys() and payload['csrfmiddlewaretoken'] not in ['', None]:
                    	if f not in ['',None]: token_filter_data[f + '__iexact'] = payload['csrfmiddlewaretoken']
            	    elif 'csrf_token' in payload.keys() and payload['csrf_token'] not in ['', None]:
                    	if f not in ['',None]: token_filter_data[f + '__iexact'] = payload['csrf_token']
            	    elif 'fingerprint' in payload.keys() and payload['fingerprint'] not in ['', None]:
                    	if f not in ['',None]: token_filter_data[f + '__iexact'] = payload['fingerprint']

                if len(token_filter_data):
                    query = reduce(operator.and_, (Q(k) for k in token_filter_data.items()))
		    lgr.info('Query: %s' % query)

                    report_list = report_list.filter(query)

	    lgr.info('Report Time Filters')
	    if or_filters not in [None,'']:
                # for a in filters.split("&"):
                for f in or_filters.split("|"):
            	    if 'q' in payload.keys() and payload['q'] not in ['', None]:
                    	if f not in ['',None]: or_filter_data[f + '__icontains'] = payload['q']
            	    if f in payload.keys():
                    	if f not in ['',None]: or_filter_data[f + '__icontains'] = payload[f]

                if len(or_filter_data):
                    or_query = reduce(operator.or_, (Q(k) for k in or_filter_data.items()))
                    report_list = report_list.filter(or_query)

	    lgr.info('Report Or Filters')
	    if and_filters not in [None,'']:
                for f in and_filters.split("|"):
            	    if 'q' in payload.keys() and payload['q'] not in ['', None]:
                    	if f not in ['',None]: and_filter_data[f + '__icontains'] = payload['q']

            	    if f in payload.keys():
                    	if f not in ['',None]: and_filter_data[f + '__icontains'] = payload[f]

                if len(and_filter_data):
                    and_query = reduce(operator.and_, (Q(k) for k in and_filter_data.items()))
                    report_list = report_list.filter(and_query)


	    lgr.info('Report And Filters')
	    if list_filters not in [None,'']:
                for f in list_filters.split("|"):
            	    if 'q' in payload.keys() and payload['q'] not in ['', None]:
                    	if f not in ['',None]: list_filter_data[f + '__icontains'] = payload['q']
            	    if f in payload.keys():
                    	if f not in ['',None]: list_filter_data[f + '__iexact'] = payload[f]

                if len(list_filter_data):
                    and_query = reduce(operator.and_, (Q(k) for k in list_filter_data.items()))
                    report_list = report_list.filter(and_query)


	    lgr.info('Report List Filters')
	    institution_none_filter = {}
	    if institution_filters not in ['',None]:
                for f in institution_filters.split("|"):
                    if f not in ['',None]: institution_none_filter[f] = None
            	    if 'institution_id' in payload.keys() and payload['institution_id'] not in ['', None]:
                    	if f not in ['',None]: institution_filter_data[f + '__id'] = payload['institution_id']
            	    elif gateway_profile.institution not in ['', None]:
                    	if f not in ['',None]: institution_filter_data[f] = gateway_profile.institution
		    else:
                    	if f not in ['',None]: institution_filter_data[f] = None

                if len(institution_filter_data):
                    institution_query = reduce(operator.and_, (Q(k) for k in institution_filter_data.items()))
                    institution_none_query = reduce(operator.or_, (Q(k) for k in institution_none_filter.items()))
                    report_list = report_list.filter(institution_query|institution_none_query)


	    lgr.info('Report Institution Filters')
            if gateway_filters not in ['', None]:
                for f in gateway_filters.split("|"):
                    if f not in ['',None]: gateway_filter_data[f] = gateway_profile.gateway
                if len(gateway_filter_data):
                    gateway_query = reduce(operator.and_, (Q(k) for k in gateway_filter_data.items()))
                    report_list = report_list.filter(gateway_query)

	    lgr.info('Report Gateway Filters')
            if gateway_profile_filters not in ['', None]:
                for f in gateway_profile_filters.split("|"):
                    if f not in ['',None]: gateway_profile_filter_data[f] = gateway_profile
                if len(gateway_profile_filter_data):
                    gateway_profile_query = reduce(operator.and_, (Q(k) for k in gateway_profile_filter_data.items()))
                    report_list = report_list.filter(gateway_profile_query)

	    lgr.info('Report Gateway Profile Filters')
            if 'start_date' in payload.keys():
                try:
                    date_obj = datetime.strptime(payload["start_date"] + ' 12:00 am', '%d/%m/%Y %I:%M %p')
                except:
                    date_obj = None
                if date_obj is not None:
                    profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
                    start_date = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
                else:
                    date = timezone.now().date().strftime('%d/%m/%Y')
                    date_obj = datetime.strptime(date + ' 12:00 am', '%d/%m/%Y %I:%M %p')
                    profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
                    start_date = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
                report_list = report_list.filter(date_created__gte=start_date)

	    lgr.info('Report Start Date')
            if 'end_date' in payload.keys():
                try:
                    date_obj = datetime.strptime(payload["end_date"] + ' 11:59 pm', '%d/%m/%Y %I:%M %p')
                except:
                    date_obj = None
                if date_obj is not None:
                    profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
                    end_date = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
                else:
                    date = timezone.now().date().strftime('%d/%m/%Y')
                    date_obj = datetime.strptime(date + ' 11:59 pm', '%d/%m/%Y %I:%M %p')
                    profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
                    end_date = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
                report_list = report_list.filter(date_created__lte=end_date)


	    lgr.info('Report End Date')
	    ############################################VALUES BLOCK
            args = []
            kwargs = {}
	    if values not in [None,'']:
            	for i in values.split('|'):
                	k,v = i.split('%')
	                args.append(k.strip())
        	        params['cols'].append({"label": k.strip(), "type": "string", "value": v.strip()})
                	if k <> v:kwargs[k.strip()] = F(v.strip())

	    lgr.info('Report Values')
	    selected_data = {}
	    if data.query.date_values not in [None,'']:
	            for i in data.query.date_values.split('|'):
			k,v = i.split('%')
	                args.append(k.strip())
			selected_data[k.strip()] = "to_char("+ data.query.module_name +"_"+ data.query.model_name +"."+v+", 'DD, Month, YYYY')"
                    	params['cols'].append({"label": k.strip(), "type": "string", "value": v.strip()})

	    lgr.info('Report Date Values')
	    if data.query.date_time_values not in [None,'']:
	            for i in data.query.date_time_values.split('|'):
			k,v = i.split('%')
	                args.append(k.strip())
			selected_data[k.strip()] = "to_char("+ data.query.module_name +"_"+ data.query.model_name +"."+v+", 'DD, Month, YYYY HH:MI:SS TZ')"
                    	params['cols'].append({"label": k.strip(), "type": "string", "value": v.strip()})

	    lgr.info('Report Date Time Values')

	    if data.query.month_year_values not in [None,'']:
	            for i in data.query.month_year_values.split('|'):
			k,v = i.split('%')
	                args.append(k.strip())
			selected_data[k.strip()] = "to_char("+ data.query.module_name +"_"+ data.query.model_name +"."+v+", 'Month, YYYY')"
                    	params['cols'].append({"label": k.strip(), "type": "string", "value": k.strip()})

	    lgr.info('Report Month Year Values')
            report_list = report_list.extra(select=selected_data)


	    if data.data_response:
		    #Values
        	    report_list = report_list.annotate(**kwargs).values(*args)
	    else:
		    #Values List
        	    report_list = report_list.annotate(**kwargs).values_list(*args)

	    ############################################END VALUES BLOCK


	    #Count Sum MUST come after values in order to group
            if count_values not in [None,'']:
                kwargs = {}
                for i in count_values.split('|'):
                    k,v = i.split('%')
                    params['cols'].append({"label": k.strip(), "type": "string", "value": k.strip()})
                    if k <> v:kwargs[k.strip()] = Count(v.strip())

                report_list = report_list.annotate(**kwargs)

	    lgr.info('Report Count Values')
            if sum_values not in [None,'']:
                kwargs = {}
                for i in sum_values.split('|'):
                    k,v = i.split('%')
                    params['cols'].append({"label": k.strip(), "type": "string", "value": k.strip()})
                    if k <> v:kwargs[k.strip()] = Sum(v.strip())

                report_list = report_list.annotate(**kwargs)

	    lgr.info('Report Sum Values')
            if avg_values not in [None,'']:
                kwargs = {}
                for i in avg_values.split('|'):
                    k,v = i.split('%')
                    params['cols'].append({"label": k.strip(), "type": "string", "value": k.strip()})
                    if k <> v:kwargs[k.strip()] = Avg(v.strip())

                report_list = report_list.annotate(**kwargs)


	    lgr.info('Report AVG Values')
	    
            if last_balance not in [None,'']:
                kwargs = {}
                for i in last_balance.split('|'):
                    k,v = i.split('%')
                    params['cols'].append({"label": k.strip(), "type": "string", "value": v.strip()})
                    #if k <> v:kwargs[k.strip()] = ( (( (Sum('balance_bf')*2) + Sum('amount') ) + Sum('charge'))*2  )/2
                    if k <> v:kwargs[k.strip()] = (Sum('balance_bf')+((( Sum('amount')- Sum('charge'))/2)+Sum('charge')))

                report_list = report_list.annotate(**kwargs)
	    

	    lgr.info('Report Last Balance')
	    if or_filters not in [None,'']:
                # for a in filters.split("&"):
                for f in or_filters.split("|"):
		    count = 0
		    for i in params['cols']:
			if i['value'] == f.strip():
				i['search_filters'] = True
			params['cols'][count] = i
			count += 1

	    if and_filters not in [None,'']:
                for f in and_filters.split("|"):
		    count = 0
		    for i in params['cols']:
			if i['value'] == f.strip():
				i['search_filters'] = True
			params['cols'][count] = i
			count += 1

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
					k,v = i.split('%')
					href['links'][name]['params'] = {k:v}
		    params['cols'].append(href)

            ct = report_list.count()

            #if 'max_id' in payload.keys() and payload['max_id'] > 0:
            #    report_list = report_list.filter(id__lt=payload['max_id'])
            #if 'min_id' in payload.keys() and payload['min_id'] > 0:
            #    report_list = report_list.filter(id__gt=payload['min_id'])


            if 'order_by' in payload.keys():
		order_by = payload['order_by'].split(',')
                report_list = report_list.order_by(*order_by)
            #
            # report_list = report_list[:]
            #
            # trans = report_list.aggregate(max_id=Max('id'), min_id=Min('id'))
            # max_id = trans.get('max_id')
            # min_id = trans.get('min_id')


            paginator = Paginator(report_list, payload.get('limit',50))

            try:
                page = int(payload.get('page', '1'))
            except ValueError:
                page = 1

            try:
                results = paginator.page(page)
            except (EmptyPage, InvalidPage):
                results = paginator.page(paginator.num_pages)


            report_list = results.object_list



	    if data.data_response:
		#Set Data
		params['data'] = report_list
	    else:
		#IF values_list is used
		report_list = np.asarray(report_list).tolist()
		#Set Data
		params['rows'] = report_list


        except Exception, e:
            lgr.info('Error on report: %s' % e)
        return params,max_id,min_id,ct


    def balance(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                          {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                          {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                          {"label": "color", "type": "string"}]


        try:


	    manager_list = FloatManager.objects.filter(Q(Q(institution=gateway_profile.institution)|Q(institution=None)),\
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
        except Exception, e:
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

	    contact = Contact.objects.filter(contact_group__institution=gateway_profile.institution,\
				 product__notification__code__institution=gateway_profile.institution).\
                values('status__name', 'cart_item__currency__code'). \
                annotate(status_count=Count('status__name'), total_amount=Sum('cart_item__total'))


            for o in order:
                item = {}
                item['name'] = o['status__name']
                item['description'] = '%s %s' % (o['cart_item__currency__code'], '{0:,.2f}'.format(o['total_amount']))
                item['count'] = '%s' % '{0:,.2f}'.format(o['status_count'])
                params['rows'].append(item)
        except Exception, e:
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
            order = PurchaseOrder.objects.filter(cart_item__product_item__institution=gateway_profile.institution). \
                values('status__name', 'cart_item__currency__code'). \
                annotate(status_count=Count('status__name'), total_amount=Sum('cart_item__total'))


            for o in order:
                item = {}
                item['name'] = o['status__name']
                item['description'] = '%s %s' % (o['cart_item__currency__code'], '{0:,.2f}'.format(o['total_amount']))
                item['count'] = '%s' % '{0:,.2f}'.format(o['status_count'])
                params['rows'].append(item)
        except Exception, e:
            lgr.info('Error on purchases: %s' % e)
        return params


    def purchases(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                          {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                          {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                          {"label": "color", "type": "string"}]


        try:
            order = PurchaseOrder.objects.filter(cart_item__product_item__institution=gateway_profile.institution). \
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
        except Exception, e:
            lgr.info('Error on purchases: %s' % e)
        return params


    def above_60days_defaulters(self, payload, gateway_profile, profile_tz, data):

        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "name", "type": "string"}, {"label": "msisdn", "type": "string"},
                          {"label": "email", "type": "string"}, {"label": "description", "type": "string"},
                          {"label": "count", "type": "string"}, {"label": "date_time", "type": "string"}]


        try:

            account_manager = AccountManager.objects.filter(credit=False,credit_paid=False,dest_account__account_type__institution=gateway_profile.institution,\
				dest_account__account_type__gateway=gateway_profile.gateway,\
				dest_account__account_type__deposit_taking=False, credit_due_date__lt=timezone.now()-timezone.timedelta(days=60))

	    for i in account_manager:
		item = {}
		item['id'] = i.id
                item['name'] = '%s %s' % (i.dest_account.gateway_profile.user.first_name, i.dest_account.gateway_profile.user.last_name)
                item['msisdn'] = '%s' % (i.dest_account.gateway_profile.msisdn)
                item['email'] = '%s' % (i.dest_account.gateway_profile.user.email)

                item['description'] = 'Amount: %s Charge: %s Balance BF: %s' % (i.amount,i.charge,i.balance_bf)
                item['count'] = 'Loan Time: %s' % (i.credit_time)
		if i.credit_due_date:
	                item['date_time'] = '%s' % (profile_tz.normalize(i.credit_due_date.astimezone(profile_tz)).strftime("%d %b %Y %I:%M:%S %p %Z %z"))

                params['rows'].append(item)


        except Exception, e:
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

	    account_manager = AccountManager.objects.\
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

        except Exception, e:
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
            account_manager = AccountManager.objects.filter(credit=False,dest_account__account_type__institution=gateway_profile.institution,\
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

        except Exception, e:
            lgr.info('Error on credit account: %s' % e)
        return params


    def investment_summary_chart(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "date_time", "type": "date"}]
	init_rows = [None]
	init_cols = []
        try:

	    investment_list = Investment.objects.all().\
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

        except Exception, e:
            lgr.info('Error on investment summary chart: %s' % e)
        return params



    def enrollments_summary_chart(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "date_time", "type": "date"}]
	init_rows = [None]
	init_cols = []
        try:

	    enrollment_list = Enrollment.objects.filter(enrollment_type__product_item__institution=gateway_profile.institution, status__name='ACTIVE').\
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

        except Exception, e:
            lgr.info('Error on enrollment summary chart: %s' % e)
        return params




    def credit_account_chart(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "date_time", "type": "date"}]

        try:

	    account_manager = AccountManager.objects.\
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

        except Exception, e:
            lgr.info('Error on credit account: %s' % e)
        return params


    def notifications_summary(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                          {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                          {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                          {"label": "color", "type": "string"}]


        try:
            outbound = Outbound.objects.filter(
                    contact__product__notification__code__institution=gateway_profile.institution). \
                values('state__name'). \
                annotate(state_count=Count('state__name'))

            for o in outbound:
                item = {}
                item['name'] = o['state__name']
                item['count'] = '%s' % '{0:,.2f}'.format(o['state_count'])
                params['rows'].append(item)
        except Exception, e:
            lgr.info('Error on notifications: %s' % e)
        return params


    def investment_summary(self, payload, gateway_profile, profile_tz, data):
        params = {}
	params['rows'] = []
	params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                          {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                          {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                          {"label": "color", "type": "string"}]


        try:
	    investment = Investment.objects.values('account__id').annotate(Count('account__id'))

	    investment_type = investment.values('investment_type__id','investment_type__name','investment_type__value').annotate(Count('investment_type__id'))
	    for i in investment_type:
		pie_total = investment.filter(investment_type__id=i['investment_type__id']).annotate(Max('pie')).aggregate(Sum('pie__max'))

                item = {}
                item['name'] = i['investment_type__name']
                item['description'] = '%s' % (i['investment_type__value'] * pie_total['pie__max__sum'])
                item['count'] = '%s' % '{0:,.2f}'.format(pie_total['pie__max__sum'])
                params['rows'].append(item)

        except Exception, e:
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
            outbound = Outbound.objects.filter(
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
        except Exception, e:
            lgr.info('Error on notifications: %s' % e)
        return params


class System(Wrappers):
    def data_source(self, payload, node_info):
        try:
            lgr.info('DSC Data %s Payload: %s' % (('data_name' in payload.keys()), payload))
            report = []
            cols = []
            rows = []
            groups = []
            data = []
            min_id = 0
            max_id = 0
            t_count = 0
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
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

            lgr.info('Data Source: data_name: %s val: %s' % (data_name, data_name_val))
            data_list = DataList.objects.filter(Q(data_name=data_name.strip()), Q(status__name='ACTIVE'), \
                                                Q(Q(gateway=gateway_profile.gateway) | Q(gateway=None)), \
                                                Q(Q(channel__id=payload['chid']) | Q(channel=None)), \
                                                Q(Q(access_level=gateway_profile.access_level) | Q(access_level=None))).order_by('level')

            if 'institution_id' in payload.keys():
                data_list = data_list.filter(Q(institution__id=payload['institution_id'])|Q(institution=None))
	    else:
                data_list = data_list.filter(institution=None)

            if data_list.exists():
                lgr.info('Fetching from Data List')
                collection = {}
                for d in data_list:
                    if d.function not in ['', None]:
                        lgr.info('Is a Function: ')
                        try:
                            func = getattr(self, d.function.strip())
                            params = func(payload, gateway_profile, profile_tz, d)
			    cols = params['cols'] if 'cols' in params.keys() else []
			    rowsParams = params['rows'] if 'rows' in params.keys() else []
                            dataParams = params['data'] if 'data' in params.keys() else []
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
                        except Exception, e:
                            lgr.info('Error on Data List Function: %s' % e)

                    elif d.query not in ['', None]:
                        lgr.info('Is a Query: ')
                        try:
                            params,max_id,min_id,t_count = self.report(payload, gateway_profile, profile_tz, d)
                            cols = params['cols'] if 'cols' in params.keys() else []
                            rowsParams = params['rows'] if 'rows' in params.keys() else []
                            dataParams = params['data'] if 'data' in params.keys() else []
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
                        except Exception, e:
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

            else:
                lgr.info('Not a Data List')
                if 'survey' in data_name:

                    collection = {}
                    items = SurveyItem.objects.filter(survey__data_name=data_name, status__name="ACTIVE")
                    if 'institution_id' in payload.keys():
                        items = items.filter(survey__institution__id=payload['institution_id'])
                    elif 'institution_id' not in payload.keys() and gateway_profile.institution is not None:
                        items = items.filter(survey__institution=gateway_profile.institution)

                    for i in items:
                        name = i.name
                        survey_type = i.survey.name
                        image = None
                        item = {"index": i.id, "name": name, "image": image, "type": survey_type,}
                        rows.append(item)
                        if survey_type not in collection.keys():
                            collection[survey_type] = [item]
                        else:
                            collection[survey_type].append(item)
                    groups = collection.keys()
                    data = collection.values()


                elif 'data_name' in data_name: #Fetches all Data List items on report
                    data_list = DataList.objects.filter(Q(is_report=True), Q(status__name='ACTIVE'), \
                                                        Q(Q(gateway=gateway_profile.gateway) | Q(gateway=None)), \
                                                        Q(Q(channel__id=payload['chid']) | Q(channel=None)), \
                                                        Q(Q(access_level=gateway_profile.access_level) | Q(
                                                                access_level=None))). \
                        order_by('level')

                    if 'institution_id' in payload.keys():
                        data_list = data_list.filter(Q(institution__id=payload['institution_id']) | Q(institution=None))
                    elif 'institution_id' not in payload.keys() and gateway_profile.institution is not None:
                        data_list = data_list.filter(Q(institution=gateway_profile.institution) | Q(institution=None))
                    for d in data_list:
                        rows.append([d.data_name, d.title])

                elif data_name == 'music_list' or data_name == 'music_album_list':
                    collection = {}
                    # music = Music.objects.filter(,\
                    if "q" in payload.keys():
                        query0 = reduce(operator.or_,
                                        (Q(product_item__name__icontains=s.strip()) for s in payload['q'].split(" ")))
                        query1 = reduce(operator.or_,
                                        (Q(artiste__icontains=s.strip()) for s in payload['q'].split(" ")))
                        query2 = reduce(operator.and_,
                                        (Q(product_item__name__icontains=s.strip()) for s in payload['q'].split(" ")))
                        query3 = reduce(operator.and_,
                                        (Q(artiste__icontains=s.strip()) for s in payload['q'].split(" ")))

                        music = Music.objects.filter(query0 | query1, product_item__status__name='ACTIVE',
                                                     product_item__institution__gateway=gateway_profile.gateway). \
                            select_related('product_item__product_type', 'product_item')

                        if len(music) > 1:
                            music0 = music.filter(query0 | query1)
                            if len(music0) > 1:
                                music1 = music0.filter(
                                        Q(product_item__name__icontains=payload['q']) | Q(
                                            artiste__icontains=payload['q']))
                                if len(music1) > 1:
                                    music = music1
                                else:
                                    music2 = music0.filter(query0, query1)
                                    if len(music2) > 1:
                                        music = music2
                                    else:
                                        music = music0

                    else:
                        music = Music.objects.filter(Q(product_item__status__name="ACTIVE"), \
                                                     Q(product_item__institution__gateway=gateway_profile.gateway)). \
                            select_related('product_item__product_type', 'product_item')

                    if 'institution_id' in payload.keys():
                        music = music.filter(product_item__institution__id=payload['institution_id'])
                    elif 'institution_id' not in payload.keys() and gateway_profile.institution is not None:
                        music = music.filter(product_item__institution=gateway_profile.institution)

                    if data_name == 'music_album_list':
                        albums = music.order_by('album').distinct('album').values_list('album', flat=True)[:40]
                        for g in albums:
                            lgr.info('G: %s' % g)
                            m = music.filter(album=g).select_related('product_item__product_type', 'product_item'). \
                                    order_by('?')[:10]
                            for i in m:
                                name = i.product_item.name
                                product_type = i.product_item.product_type.name
                                if i.product_item.image_path:
                                    image = i.product_item.image_path.name
                                else:
                                    image = "crm_productitem_imagepath/muziqbit_icon.png"
                                description = i.artiste + ' | ' + i.album
                                url = "#?SERVICE=MUSIC&music_id=" + str(i.id)
                                item = {"index": i.id, "name": name, "image": image, "type": g,
                                        "description": description,
                                        "url": url, "path": i.file_path.name, "start": i.stream_start,
                                        "duration": i.stream_duration,
                                        "price": i.product_item.unit_cost, "min": i.product_item.unit_limit_min,
                                        "max": i.product_item.unit_limit_max,
                                        "vat": i.product_item.vat, "discount": i.product_item.discount,
                                        "currency": i.product_item.currency.code}

                                rows.append(item)
                                if g not in collection.keys():
                                    collection[g] = [item]
                                else:
                                    collection[g].append(item)


                    else:
                        genre_types = music.order_by('product_item__product_type__name').distinct(
                                'product_item__product_type__name').values_list('product_item__product_type__name',
                                                                                flat=True)[:40]
                        for g in genre_types:
                            lgr.info('G: %s' % g)
                            m = music.filter(product_item__product_type__name=g). \
                                    select_related('product_item__product_type__name', 'product_item__name'). \
                                    order_by('?')[:10]
                            for i in m:
                                name = i.product_item.name
                                product_type = i.product_item.product_type.name
                                if i.product_item.image_path:
                                    image = i.product_item.image_path.name
                                else:
                                    image = "crm_productitem_imagepath/muziqbit_icon.png"
                                description = i.artiste + ' | ' + i.album
                                url = "#?SERVICE=MUSIC&music_id=" + str(i.id)
                                item = {"index": i.id, "name": name, "image": image, "type": product_type,
                                        "description": description,
                                        "url": url, "path": i.file_path.name, "start": i.stream_start,
                                        "duration": i.stream_duration,
                                        "price": i.product_item.unit_cost, "min": i.product_item.unit_limit_min,
                                        "max": i.product_item.unit_limit_max,
                                        "vat": i.product_item.vat, "discount": i.product_item.discount,
                                        "currency": i.product_item.currency.code}

                                rows.append(item)
                                if product_type not in collection.keys():
                                    collection[product_type] = [item]
                                else:
                                    collection[product_type].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'pos_product_items':
                    collection = {}
                    items = ProductItem.objects.filter(Q(institution=gateway_profile.institution),
                                                       Q(status__name="ACTIVE"), \
                                                       Q(institution_till__till_type__name='ONLINE TILL') | Q(
                                                               institution_till__till_type__name='SHOP'))
                    for i in items:
                        name = i.name
                        product_type = i.product_type.name
                        image = None
                        item = {"index": i.id, "name": name, "image": image, "type": product_type,
                                "price": i.unit_cost, "quantity": i.unit_limit_min,}
                        rows.append(item)
                        if product_type not in collection.keys():
                            collection[product_type] = [item]
                        else:
                            collection[product_type].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'institution_id':

                    institution_list = Institution.objects.filter(gateway=gateway_profile.gateway)

                    for a in institution_list:
                        rows.append([a.id, a.name])

                elif data_name == 'industry_id':

                    industry_list = Industry.objects.all()

                    for i in industry_list:
                        rows.append([i.id, i.name])

                elif data_name == 'industry_section_id':

                    industry_section_list = IndustrySection.objects.all()

                    for i in industry_section_list:
                        name = '%s (%s)' % (i.description, i.isic_code)
                        rows.append([i.id, name])


                elif data_name == 'industry_class_id':

                    industry_class_list = IndustryClass.objects.all()

                    for i in industry_class_list:
                        name = '%s (%s%s)' % (i.description, i.group.division.section.isic_code, i.isic_code)
                        rows.append([i.id, name])

                elif data_name == 'reference':

                    bill = BillManager.objects.filter(order__status__name='UNPAID',
                                                      order__gateway_profile=gateway_profile). \
                        distinct('order__id', 'order__date_created').order_by('-order__date_created')
                    if 'institution_id' in payload.keys():
                        bill = bill.filter(order__cart_item__product_item__institution__id=payload['institution_id'])

                    if data_name_val not in ['', None]:
                        bill = bill.filter(order__cart_item__product_item__product_type__name=data_name_val)

                    item = ''
                    item_list = []
                    if bill.exists():
                        for i in bill:
                            lgr.info('Bill Items: %s' % i)
                            cost = '{0:,.2f}'.format(i.balance_bf)
                            name = '%s %s-%s-%s' % (
                                i.order.currency.code, cost, i.order.date_created.strftime("%d/%b/%Y"),
                                i.order.reference)
                            rows.append([i.order.reference, name])

                elif data_name == 'product_item_id':

                    product_item_list = ProductItem.objects.filter(institution__gateway=gateway_profile.gateway)
		    if data_name_val and data_name_val == 'Remittance':
			float_manager = FloatManager.objects.filter(Q(institution=gateway_profile.institution,gateway=gateway_profile.gateway)\
						|Q(gateway=gateway_profile.gateway,institution=None)).\
						distinct('float_type__id')
			collection = {}
			product_item_list = product_item_list.filter(product_type__in=[f.float_type.float_product_type for f in float_manager])

                    elif data_name_val is not None:
                        data = data_name_val.split("|")
                        query = reduce(operator.or_, (Q(product_type__name=d.strip()) for d in data))
                        product_item_list = product_item_list.filter(query)
                        lgr.info(data)
                        if 'Investment' in data and 'Investor Enrollment' in data:
                            lgr.info('Investment and Enrollment Exist')
                            investment = Investment.objects.filter(account__gateway_profile=gateway_profile)[:1]

                            investment_type = InvestmentType.objects.filter(
                                    ~Q(
                                        name='M-Chaama Enrollment'))  # Enrollment investment not needed if investment exists
                            if investment.exists():
                                lgr.info('User Investment Exists')
                                product_item_list = product_item_list.filter(
                                        id__in=[i.product_item.id for i in investment_type])
                            else:
                                product_item_list = product_item_list.filter(
                                        ~Q(id__in=[i.product_item.id for i in investment_type]))

                    for a in product_item_list:
                        cost = '{0:,.2f}'.format(a.unit_cost) if a.unit_cost > 0 else 0
                        name = '%s(%s %s)' % (a.name, a.currency.code, cost)
                        rows.append([a.id, name])


                elif data_name == 'item':

                    product_item_list = ProductItem.objects.filter(institution__gateway=gateway_profile.gateway)
		    if data_name_val and data_name_val == 'Remittance':
			float_manager = FloatManager.objects.filter(Q(institution=gateway_profile.institution,gateway=gateway_profile.gateway)\
						|Q(gateway=gateway_profile.gateway,institution=None)).\
						distinct('float_type__id')
			collection = {}
			product_item_list = product_item_list.filter(product_type__in=[f.float_type.float_product_type for f in float_manager])

                    elif data_name_val is not None:
                        data = data_name_val.split("|")
                        query = reduce(operator.or_, (Q(product_type__name=d.strip()) for d in data))
                        product_item_list = product_item_list.filter(query)
                        lgr.info(data)
                        if 'Investment' in data and 'Investor Enrollment' in data:
                            lgr.info('Investment and Enrollment Exist')
                            investment = Investment.objects.filter(account__gateway_profile=gateway_profile)[:1]

                            investment_type = InvestmentType.objects.filter(
                                    ~Q(
                                        name='M-Chaama Enrollment'))  # Enrollment investment not needed if investment exists
                            if investment.exists():
                                lgr.info('User Investment Exists')
                                product_item_list = product_item_list.filter(
                                        id__in=[i.product_item.id for i in investment_type])
                            else:
                                product_item_list = product_item_list.filter(
                                        ~Q(id__in=[i.product_item.id for i in investment_type]))

                    for a in product_item_list:
                        cost = '{0:,.2f}'.format(a.unit_cost) if a.unit_cost > 0 else 0
                        name = '%s(%s %s)' % (a.name, a.currency.code, cost)
                        rows.append([a.name, name])

                elif data_name == 'access_level_id':
                    access_level = AccessLevel.objects.filter(Q(status__name='ACTIVE'),
                                                              Q(hierarchy__gt=gateway_profile.access_level.hierarchy), \
                                                              ~Q(name__in=['CUSTOMER', 'SYSTEM']))
                    for a in access_level:
                        rows.append([a.id, a.name])

                elif data_name == 'account_type_id':

                    account_list = Account.objects.filter(Q(gateway_profile=gateway_profile),
                                                          Q(account_status__name='ACTIVE'), \
                                                          Q(account_type__gateway=gateway_profile.gateway) | Q(
                                                                  account_type__gateway=None)).order_by(
                            'account_type__name')

                    if data_name_val not in ['', None]:
                        account_list = account_list.filter(account_type__product_item__product_type__name=data_name_val)

                    item = ''
                    item_list = []
                    for i in account_list:
			preview_name = '%s(%s)' % (i.account_type.name, i.account_type.product_item.currency.code)

			rows.append([i.account_type.id, preview_name])

                elif data_name == 'payment_method':
                    item = ''
                    item_list = []

                    if 'reference' in payload.keys():
                        bill_manager_list = BillManager.objects.filter(order__reference=payload['reference'],
                                                                       order__status__name='UNPAID').order_by(
                                "-date_created")
                        if 'institution_id' in payload.keys():
                            bill_manager_list = bill_manager_list.filter(
                                    order__cart_item__product_item__institution__id=payload['institution_id'])
                        # else:
                        #	bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution=gateway_profile.institution)

                        if bill_manager_list.exists():
                            payment_method = []
                            cart_item_list = bill_manager_list[0].order.cart_item.all()
                            cart_item_payment_method = cart_item_list.filter(
                                    Q(product_item__product_type__payment_method__channel__id=payload['chid']) | Q(
                                            product_item__product_type__payment_method__channel=None)). \
                                values('product_item__product_type__payment_method__name'). \
                                annotate(num_payments=Count('product_item__product_type__payment_method__name'))
                            max_payment_method = cart_item_payment_method.aggregate(Max('num_payments'))

                            for i in cart_item_payment_method:
                                if max_payment_method['num_payments__max'] == i['num_payments']:
                                    account_balance = None
                                    if i['product_item__product_type__payment_method__name'] == 'MIPAY':
                                        session_account_manager = AccountManager.objects.filter(
                                                dest_account__account_status__name='ACTIVE', \
                                                dest_account__gateway_profile=gateway_profile). \
                                            order_by('-date_created')

                                        if session_account_manager.exists():
                                            f_session_account_manager = session_account_manager.filter(
                                                    dest_account__is_default=True)
                                            if len(f_session_account_manager) > 0:
                                                account_balance = f_session_account_manager[0].balance_bf
                                            else:
                                                account_balance = session_account_manager[0].balance_bf
                                        else:
                                            continue
                                        if account_balance is not None and account_balance > 0:
                                            pass
                                        else:
                                            continue
                                    name = '%s' % (i['product_item__product_type__payment_method__name'])
                                    if account_balance is not None and account_balance > 0:
                                        account_balance = '{0:,.2f}'.format(account_balance)
                                        item = '%s(%s)' % (item, account_balance)
                                        rows.append([name, item])
                                    else:
                                        rows.append([name, name])
                    elif 'product_item_id' in payload.keys() or  ('item' in payload.keys() and 'institution_id' in payload.keys()):
			if 'product_item_id' in payload.keys():
	                        product_item = ProductItem.objects.filter(product_item_id=payload['product_item_id'],status__name='ACTIVE')
			else:
	                        product_item = ProductItem.objects.filter(name=payload['item'],
                                                                  institution__id=payload['institution_id'],
                                                                  status__name='ACTIVE').order_by('id')
                        if data_name_val not in ['', None]:
                            product_item = product_item.filter(Q(product_type__name=data_name_val) | Q(
                                    product_type__product_category__name=data_name_val))

			product_item = product_item[:10]

                        if product_item.exists():
                            payment_method = product_item[0].product_type.payment_method.filter(
                                    Q(channel__id=payload['chid']) | Q(channel=None))
                            for i in payment_method:
                                account_balance = None
                                if i.name == 'MIPAY':
                                    session_account_manager = AccountManager.objects.filter(
                                            dest_account__account_status__name='ACTIVE', \
                                            dest_account__gateway_profile=gateway_profile). \
                                        order_by('-date_created')

                                    if session_account_manager.exists():
                                        f_session_account_manager = session_account_manager.filter(
                                                dest_account__is_default=True)
                                        if len(f_session_account_manager) > 0:
                                            account_balance = f_session_account_manager[0].balance_bf
                                        else:
                                            account_balance = session_account_manager[0].balance_bf
                                    else:
                                        continue
                                    if account_balance is not None and account_balance > 0:
                                        pass
                                    else:
                                        continue
                                name = '%s' % (i.name)
                                if account_balance is not None and account_balance > 0:
                                    account_balance = '{0:,.2f}'.format(account_balance)
                                    item = '%s(%s)' % (item, account_balance)
                                    rows.append([name, item])
                                else:
                                    rows.append([name, name])

                    elif 'account_type_id' in payload.keys():
                        lgr.info('Captured Account Type ID')
                        account_type = AccountType.objects.get(id=payload['account_type_id'])
                        payment_method = account_type.product_item.product_type.payment_method.filter(
                                Q(channel__id=payload['chid']) | Q(channel=None))

                        lgr.info('PaymentMethod: %s' % payment_method)

                        if data_name_val not in [None, '']:
                            if data_name_val == 'Send':
                                payment_method = payment_method.filter(send=True)
                            elif data_name_val == 'Receive':
                                payment_method = payment_method.filter(receive=True)

                        lgr.info('PaymentMethod: %s' % payment_method)

                        for i in payment_method:
                            account_balance = None
                            if i.name == 'MIPAY' and data_name_val <> 'Send' and gateway_profile.msisdn not in [None,'']:
                                session_account_manager = AccountManager.objects.filter(
                                        dest_account__account_status__name='ACTIVE', \
                                        dest_account__gateway_profile__msisdn=gateway_profile.msisdn). \
                                    order_by('-date_created')

                                if len(session_account_manager) > 0:
                                    f_session_account_manager = session_account_manager.filter(
                                            dest_account__is_default=True)
                                    if len(f_session_account_manager) > 0:
                                        account_balance = f_session_account_manager[0].balance_bf
                                    else:
                                        account_balance = session_account_manager[0].balance_bf
                                else:
                                    continue
                                if (account_balance is not None and account_balance > 0) or data_name_val == 'Send':
                                    pass
                                else:
                                    continue
                            name = '%s' % (i.name)
                            if account_balance is not None and account_balance > 0:
                                account_balance = '{0:,.2f}'.format(account_balance)
                                item = '%s(%s)' % (item, account_balance)
                                rows.append([name, item])
                            else:
                                rows.append([name, name])

                    else:

                        payment_method = PaymentMethod.objects.filter(Q(channel__id=payload['chid']) | Q(channel=None))

                        lgr.info('PaymentMethod: %s' % payment_method)

                        if data_name_val not in [None, '']:
                            if data_name_val == 'Send':
                                payment_method = payment_method.filter(send=True)
                            elif data_name_val == 'Receive':
                                payment_method = payment_method.filter(receive=True)

                        lgr.info('PaymentMethod: %s' % payment_method)

                        for i in payment_method:
                            account_balance = None
                            if i.name == 'MIPAY' and data_name_val <> 'Send' and gateway_profile.msisdn not in [None,'']:
                                session_account_manager = AccountManager.objects.filter(
                                        dest_account__account_status__name='ACTIVE', \
                                        dest_account__gateway_profile__msisdn=gateway_profile.msisdn). \
                                    order_by('-date_created')

                                if len(session_account_manager) > 0:
                                    f_session_account_manager = session_account_manager.filter(
                                            dest_account__is_default=True)
                                    if len(f_session_account_manager) > 0:
                                        account_balance = f_session_account_manager[0].balance_bf
                                    else:
                                        account_balance = session_account_manager[0].balance_bf
                                else:
                                    continue
                                if (account_balance is not None and account_balance > 0) or data_name_val == 'Send':
                                    pass
                                else:
                                    continue
                            name = '%s' % (i.name)
                            if account_balance is not None and account_balance > 0:
                                account_balance = '{0:,.2f}'.format(account_balance)
                                item = '%s(%s)' % (item, account_balance)
                                rows.append([name, item])
                            else:
                                rows.append([name, name])


                elif data_name == 'bill_to_address_country':
                    payment_method = PaymentMethod.objects.filter(name='CARD')
                    for p in payment_method:
                        countries = p.country.all().order_by('name')
                        for c in countries:
                            rows.append([c.iso2, c.name.title()])

                elif data_name == 'card_type':
                    card_type = CardType.objects.filter(status__name='ACTIVE')
                    for c in card_type:
                        rows.append([c.reference, c.name])

                elif data_name == 'programs':
                    programs = Program.objects.filter(status__name='ACTIVE')
                    cols = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                            {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                            {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                            {"label": "color", "type": "string"}]
                    for p in programs:
                        rows.append([p.id, p.name, None, None, None, p.description, None])

                elif data_name == 'genre_types':
                    genre_types = ProductType.objects.filter(product_category__industry__id=13)
                    for g in genre_types:
                        rows.append([g.id, g.name])

                elif data_name == 'genres':
                    genres = Genre.objects.all()
                    for g in genres:
                        rows.append([g.id, g.name])

                elif data_name == 'country':
                    countries = Country.objects.all()
                    for c in countries:
                        rows.append([c.iso2, c.name])

                elif data_name == 'gender':
                    genders = Gender.objects.all()
                    for c in genders:
                        rows.append([c.id, c.name])

                elif data_name == 'currency':
                    payment_method = PaymentMethod.objects.filter(name='CARD')
                    for p in payment_method:
                        currencies = p.currency.all().order_by('currency')
                        for c in currencies:
                            rows.append([c.code, c.currency.title()])

                elif data_name == 'sale_contact_type':
                    retailer_type = SaleContactType.objects.all()
                    for s in retailer_type:
                        rows.append([s.id, s.name])

                elif data_name == 'sale_contact_list':
                    sale_contacts = SaleContact.objects.filter(created_by=gateway_profile)
                    collection = {}
                    for s in sale_contacts:
                        name = s.name
                        image = None
                        sale_contact_type = s.sale_contact_type.name
                        item = {"index": s.id, "name": name, "image": image, "type": sale_contact_type,
                                "date_time": profile_tz.normalize(s.date_modified.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}
                        rows.append(item)
                        if sale_contact_type not in collection.keys():
                            collection[sale_contact_type] = [item]
                        else:
                            collection[sale_contact_type].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'inbound':
                    inbound = Inbound.objects.filter(
                            contact__product__notification__code__gateway=gateway_profile.gateway, \
                            contact__product__notification__code__institution=gateway_profile.institution).order_by(
                            '-date_modified', 'date_created')[:500]
                    collection = {}
                    for i in inbound:
                        name = i.contact.product.notification.name
                        item = {"index": i.id, "name": name,
                                "description": str(i.contact.gateway_profile.msisdn)[:-3] + '... : ' + i.message,
                                "date_time": profile_tz.normalize(i.date_created.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}
                        rows.append(item)
                        if name not in collection.keys():
                            collection[name] = [item]
                        else:
                            collection[name].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'outbound':
                    outbound = Outbound.objects.filter(
                            contact__product__notification__code__gateway=gateway_profile.gateway, \
                            contact__product__notification__code__institution=gateway_profile.institution).order_by(
                            '-date_modified', 'date_created')[:500]
                    collection = {}
                    for i in outbound:
                        name = i.contact.product.notification.name
                        item = {"index": i.id, "name": name,
                                "description": str(i.contact.gateway_profile.msisdn)[:-3] + '... : ' + i.message,
                                "state": i.state.name,
                                "date_time": profile_tz.normalize(i.date_created.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}
                        rows.append(item)
                        if name not in collection.keys():
                            collection[name] = [item]
                        else:
                            collection[name].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'created_bids':
                    bid_list = Bid.objects.filter(institution=gateway_profile.institution)

                    collection = []
                    bid_types = bid_list.distinct('industry_section__description')
                    for itype in bid_types:
                        collection.append(itype.industry_section.description)

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_list = bid_list.filter(name__icontains=payload['q'].strip())

                    if "type" in payload.keys() and payload['type'] not in ["", None]:
                        bid_list = bid_list.filter(industry_section__description__iexact=payload['type'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_list = bid_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_list = bid_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_list = bid_list.order_by('-date_created')[:50]

                    for i in bid_list:
                        itype = i.industry_section.description
                        name = '%s' % i.name
                        desc = '%s' % i.description

                        item = {"index": i.id, "name": name, "type": itype,
                                "description": desc, "image": i.image.name,
                                "href": {
                                    "Add New requirement": {"url": "/bid_requirement/?bid_id=" + str(i.id),
                                                         "params":{"bid_id": str(i.id)},
                                                         "service": "BID REQUIREMENT"
                                                         },
                                    "Add New Document Requirement": {"url": "/bid_document_requirement/?bid_id=" + str(i.id),
                                                         "params": {"bid_id": str(i.id)},
                                                         "service": "BID DOCUMENT FORM"
                                                         },
                                    "Edit": {"url": "/view_edit_bid/?bid_id=" + str(i.id),
                                             "params": {"bid_id": str(i.id)},
                                             "service": "VIEW EDIT BID"
                                             },
                                    "Delete": {"url": "/view_delete_bid/",
                                             "params": {"bid_id": str(i.id)},
                                             "service": "VIEW DELETE BID"
                                             },
                                    "Bid Applications": {"url": "/view_bid_applications/",
                                             "params": {"bid_id": str(i.id)},
                                             "service": "VIEW BID APPLICATIONS"
                                             },
                                    "View": {"url": "/view_created_bid/?bid_id=" + str(i.id),
                                             "params": {"bid_id": str(i.id)},
                                             "service": "CREATED BID DETAILS"
                                             }
                                },
                                "bid_open": profile_tz.normalize(i.bid_open.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p"),
                                "closing": profile_tz.normalize(i.bid_close.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p")
                                }

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'selected_bids':
                    bid_application_list = BidApplication.objects.filter(
                        institution=gateway_profile.institution,
                        completed=True
                    )

                    collection = []
                    bid_types = bid_application_list.distinct('bid__industry_section__description')
                    for itype in bid_types:
                        collection.append(itype.bid.industry_section.description)

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_application_list = bid_application_list.filter(bid__name__icontains=payload['q'].strip())

                    if "type" in payload.keys() and payload['type'] not in ["", None]:
                        typ = payload['type'].strip()
                        if typ == 'Approved':
                            bid_application_list = bid_application_list.filter(status__name="Approved")

                        if typ == 'Denied':
                            bid_application_list = bid_application_list.filter(status__name="Denied")


                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_application_list = bid_application_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_application_list = bid_application_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_application_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_application_list = bid_application_list.order_by('-date_created')[:50]

                    for i in bid_application_list:
                        itype = i.status.name
                        name = '%s' % i.bid.name
                        desc = '%s | %s' % (i.bid.institution.name, i.bid.description)

                        item = dict(index=i.bid.id,
                                    name=name,
                                    type=itype,
                                    description=desc,
                                    href={},
                                    image=i.bid.image.name,
                                    bid_open=profile_tz.normalize(i.bid.bid_open.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p"),
                                    closing=profile_tz.normalize(i.bid.bid_close.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p"))

                        if i.completed and i.status.name != 'Denied' and i.status.name != 'Created':
                            item["href"]["Live Auction"] = {
                                            "url": "/view_selected_bid/?bid_id=" + str(i.bid.id),
                                            "params": {"bid_id": str(i.bid.id)},
                                            "service": "SELECTED BID DETAILS",
                                            "target": "_blank"

                            }
                            #item["href"]["Set Initial Prices"] = {
                            #    "params": {"bid_id": str(i.bid.id)},
                            #    "service": "SELECTED BID REQUIREMENTS"
                            #}

                        if not i.bid.closed() and not i.completed:
                            item["href"]["Finish Application"] = {
                                            "url": "/bid_application/?bid_id=" + str(i.bid.id),
                                            "params": {"bid_id": str(i.bid.id)},
                                            "service": "BID APPLICATION"

                            }

                        rows.append([item])

                    groups = sorted(['All', 'Approved', 'Denied'])
                    data = rows

                elif data_name == 'bids':
                    bid_application_list = BidApplication.objects.filter(
                        institution=gateway_profile.institution,
                        completed=True
                    )
                    bid_created_list = Bid.objects.filter(institution=gateway_profile.institution)

                    bid_list = Bid.objects.filter(Q(institution__gateway=gateway_profile.gateway),
                                                  #Q(industry_section=gateway_profile.institution.industry_class.group.division.section), \
                                                  ~Q(id__in=[i.bid.id for i in bid_application_list]),
                                                  ~Q(id__in=[k.id for k in bid_created_list])
                                                  )

                    collection = []
                    bid_types = bid_list.distinct('industry_section__description')
                    for itype in bid_types:
                        collection.append(itype.industry_section.description)

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_list = bid_list.filter(name__icontains=payload['q'].strip())

                    if "type" in payload.keys() and payload['type'] not in ["", None]:
                        typ = payload['type'].strip()

                        if typ == 'Open':
                            bid_list = bid_list.filter( bid_open__lte=datetime.today(), bid_close__gte=datetime.today())

                        if typ == 'Closed':
                            bid_list = bid_list.filter(bid_open__lte=datetime.today(), bid_close__lte=datetime.today())
                        if typ == 'Upcoming':
                            bid_list = bid_list.filter(bid_open__gte=datetime.today(), bid_close__gte=datetime.today())


                        #bid_list = bid_list.filter(industry_section__description__iexact=payload['type'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_list = bid_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_list = bid_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_list = bid_list.order_by('-date_created')[:50]

                    for i in bid_list:
                        item = i.get_dsc_item(gateway_profile)
                        rows.append([item])

                    groups = sorted(['All','Open','Upcoming','Closed'])
                    data = rows
                elif data_name == 'bid_requirement_id':
                    bid_requirement_list = BidRequirement.objects.filter(bid__id=payload['bid_id'])

                    collection = []

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_requirement_list = bid_requirement_list.filter(name__icontains=payload['q'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_requirement_list = bid_requirement_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_requirement_list = bid_requirement_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_requirement_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_requirement_list = bid_requirement_list.order_by('-date_created')[:50]

                    for i in bid_requirement_list:
                        itype = i.bid.name
                        name = '%s' % i.name
                        desc = '%s | %s' % (i.bid.description, i.bid.institution)

                        item = {"index": i.id,
                                "name": name,
                                "count":i.quantity,
                                "type": itype,
                                "description": desc,
                                "href": {
                                    "Edit": {
                                        "url": "/edit_bid_requirement/?bid_requirement_id=" + str(i.id),
                                        "params": {"bid_requirement_id": str(i.id)},
                                        "service": "VIEW EDIT BID REQUIREMENT"
                                    },
                                    "Delete": {
                                        "url": "/delete_bid_requirement/?bid_requirement_id=" + str(i.id),
                                        "params": {"bid_requirement_id": str(i.id)},
                                        "service": "CONFIRM DELETE BID REQUIREMENT"
                                    }
                                } if i.bid.institution==gateway_profile.institution else {},
                                "image": i.image.name,
                                "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'uploaded_bid_documents':
                    bid_document_app_list = BidDocumentApplication.objects.filter(
                        bid_application__id=payload['bid_app_id']
                    )

                    collection = []

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_document_app_list = bid_document_app_list.filter(name__icontains=payload['q'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_document_app_list = bid_document_app_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_document_app_list = bid_document_app_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_document_app_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_document_app_list = bid_document_app_list.order_by('-date_created')[:50]

                    for i in bid_document_app_list:
                        itype = i.bid_document.name
                        name = '%s' % i.bid_document.name
                        #desc = '%s | %s' % (i.bid.description, i.bid.institution)

                        item = {"index": i.id,
                                "name": name,
                                "type": itype,
                                "attachment": i.attachment.url if i.attachment else '',
                                "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                                    "%d %b %Y %I:%M:%S %p %Z %z")
                                }

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'bid_documents':
                    bid_documents_list = BidDocument.objects.filter(bid__id=payload['bid_id'])

                    collection = []

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_documents_list = bid_documents_list.filter(name__icontains=payload['q'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_documents_list = bid_documents_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_documents_list = bid_documents_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_documents_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_documents_list = bid_documents_list.order_by('-date_created')[:50]

                    for i in bid_documents_list:
                        itype = i.bid.name
                        name = '%s' % i.name
                        desc = '%s | %s' % (i.bid.description, i.bid.institution)

                        item = {"index": i.id,
                                "name": name,
                                "type": itype,
                                "description": desc,
                                "href": {
                                    "Edit": {
                                        "url": "/edit_bid_document/?bid_document_id=" + str(i.id),
                                        "params": {"bid_document_id": str(i.id)},
                                        "service": "VIEW EDIT BID DOCUMENT"
                                    },
                                    "Delete": {
                                        "url": "/delete_bid_document/?bid_document_id=" + str(i.id),
                                        "params": {"bid_document_id": str(i.id)},
                                        "service": "CONFIRM DELETE BID DOCUMENT"
                                    }
                                } if i.bid.institution==gateway_profile.institution else {},
                                "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'pending_bid_documents':
                    bid_documents_list = BidDocument.objects.filter(bid__id=payload['bid_id'])

                    collection = []

                    # query filters
                    #if "q" in payload.keys() and payload['q'] not in ["", None]:
                    #    bid_documents_list = bid_documents_list.filter(name__icontains=payload['q'].strip())

                    # filter last_id
                    #if 'max_id' in payload.keys() and payload['max_id'] > 0:
                    #    bid_documents_list = bid_documents_list.filter(id__lt=payload['max_id'])
                    #if 'min_id' in payload.keys() and payload['min_id'] > 0:
                    #    bid_documents_list = bid_documents_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    #trans = bid_documents_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    #max_id = trans.get('max_id')
                    #min_id = trans.get('min_id')
                    #lgr.info(bid_documents_list.count())
                    #bid_documents_list = bid_documents_list.order_by('-date_created')[:50]


                    for i in bid_documents_list:

                        doc_app = i.biddocumentapplication_set.filter(
                            bid_application__institution=gateway_profile.institution
                        )

                        #name = i.name + (' Submitted' if len(doc_app) else ' Not Submitted')
                        if not len(doc_app): rows.append([i.id, i.name])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'bid_invoices':
                    bid_invoices_list = BidInvoice.objects.filter(bid__institution=gateway_profile.institution)

                    collection = []

                    bid_invoices_list = bid_invoices_list.order_by('-date_created')[:50]

                    for i in bid_invoices_list:
                        itype = i.bid.name
                        name = '%s' % i.bid_invoice_type.name
                        desc = 'Processed' if i.processed else 'Not processed'

                        item = {"index": i.id,
                                "name": name,
                                "amount": i.amount,

                                "type": itype,
                                "description": 'Rate '+str(i.bid_invoice_type.invoicing_rate)+' | '+ desc,
                                "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'bid_requirements':
                    bid_requirement_list = BidRequirement.objects.filter(bid__id=payload['bid_id'])

                    collection = []

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_requirement_list = bid_requirement_list.filter(name__icontains=payload['q'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_requirement_list = bid_requirement_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_requirement_list = bid_requirement_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_requirement_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_requirement_list = bid_requirement_list.order_by('-date_created')[:50]

                    for i in bid_requirement_list:
                        itype = i.bid.name
                        name = '%s' % i.name
                        desc = '%s | %s' % (i.bid.description, i.bid.institution)

                        try:
                            current_application = BidRequirementApplication.objects.get(
                                bid_application__institution=gateway_profile.institution,
                                bid_requirement= i
                            )
                            amount=current_application.unit_price
                            edit_apply = {
                                    "Edit Application": {
                                             "params": {"bid_requirement_id": str(i.id)},
                                             "service": "VIEW REQUIREMENT APPLICATION"
                                             }

                                }

                        except BidRequirementApplication.DoesNotExist:
                            amount='Not set'
                            edit_apply = {
                                "Requirement Application": {
                                    "params": {"bid_requirement_id": str(i.id)},
                                    "service": "REQUIREMENT APPLICATION"
                                }

                            }

                        item = {"index": i.id,
                                "name": name,
                                "type": itype,
                                "count": i.quantity,
                                "description": desc,
                                "image": i.image.name,
                                "href": edit_apply,
                                "amount":amount,
                                "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows
                elif data_name == 'bid_applications':
                    bid_applications_list = BidApplication.objects.filter(bid__id=payload['bid_id'])

                    collection = ['All', 'Approved', 'Denied']

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        bid_applications_list = bid_applications_list.filter(description__icontains=payload['q'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        bid_applications_list = bid_applications_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        bid_applications_list = bid_applications_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = bid_applications_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    bid_applications_list = bid_applications_list.order_by('-date_created')[:50]

                    for i in bid_applications_list:

                        name = '%s' % i.institution.name
                        desc = "Application Completed" if i.completed else "Application Not Completed"

                        if i.status.name == "Created":
                            actions = {
                                "Approve": {
                                    "params": {"bid_app_id": str(i.id)},
                                    "service": "APPROVE BID APPLICATION"
                                },
                                "Deny": {
                                    "params": {"bid_app_id": str(i.id)},
                                    "service": "DENY BID APPLICATION"
                                }
                            }

                        elif i.status.name == "Approved":
                            actions = {
                                    "Deny": {
                                             "params": {"bid_app_id": str(i.id)},
                                             "service": "DENY BID APPLICATION"
                                             }

                                }

                        else:
                            actions = {
                                "Approve": {
                                    "params": {"bid_app_id": str(i.id)},
                                    "service": "APPROVE BID APPLICATION"
                                }

                            }

                        if i.bid.biddocument_set.count():
                            actions["View Documents"]= {
                                    "params": {"bid_app_id": str(i.id)},
                                    "service": "BID APPLICATION DETAILS"
                                }

                        item = {"index": i.id,
                                "name": name,
                                "type": i.status.name,
                                "description": desc,
                                "href": actions,
                                "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p")}

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'bid_ranking':
                    #bid_application_list = BidApplication.objects.filter(bid__id=payload['bid_id'])
                    bid = Bid.objects.get(pk=payload['bid_id'])


                    collection = []

                    groups = sorted(collection)
                    #data = rows
                    data = bid.app_rankings(gateway_profile.institution,gateway_profile)

                elif data_name == 'float_manager_list':

                    float_manager_list = FloatManager.objects.filter(institution=gateway_profile.institution)

                    collection = []
                    float_types = float_manager_list.distinct('float_type__name')
                    for ftype in float_types:
                        collection.append(ftype.float_type.name)

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        float_manager_list = float_manager_list.filter(ext_outbound_id__iexact=payload['q'].strip())

                    if "type" in payload.keys() and payload['type'] not in ["", None]:
                        float_manager_list = float_manager_list.filter(float_type__name__iexact=payload['type'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        float_manager_list = float_manager_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        float_manager_list = float_manager_list.filter(id__gt=payload['min_id'])

                    # get last_id
                    trans = float_manager_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    float_manager_list = float_manager_list.order_by('-date_created')[:50]

                    for f in float_manager_list:
                        ftype = f.float_type.name
                        name = 'Credit' if f.credit else 'Debit'
                        desc = 'ext: %s | ' % f.ext_outbound_id
                        amount = '{0:,.2f}'.format(f.float_amount)
                        charge = '{0:,.2f}'.format(f.charge)
                        balance = '{0:,.2f}'.format(f.balance_bf)

                        item = {"index": f.id, "name": name, "type": ftype,
                                "description": desc + 'Amount: ' + amount + ' Charge: ' + charge + ' Balance: ' + balance,
                                "date_time": profile_tz.normalize(f.date_created.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'account_manager_list':
                    float_manager_list = AccountManager.objects.filter(source_account_id=payload['account_id'])

                    collection = []
                    float_manager_list = float_manager_list.order_by('-date_created')[:50]

                    for f in float_manager_list:
                        ftype = f.credit_time
                        name = 'Debit' if f.credit else 'Credit'
                        desc = 'ext: %s | ' % f.dest_account
                        amount = '{0:,.2f}'.format(f.amount)
                        charge = '{0:,.2f}'.format(f.charge)
                        balance = '{0:,.2f}'.format(f.balance_bf)

                        item = {
                            "index": f.id,
                            "name": name,
                            "type": ftype,
                            "description":'Dest Account: '+ desc + 'Amount: ' + amount + ' Charge: ' + charge + ' Balance: ' + balance,
                            "date_time": profile_tz.normalize(f.date_created.astimezone(profile_tz)).strftime("%d %b %Y %I:%M:%S %p %Z %z")
                        }

                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'transaction_list':
                    transaction_list = Transaction.objects.filter(
                            service__access_level__hierarchy__gte=gateway_profile.access_level.hierarchy, \
                            gateway=gateway_profile.gateway).select_related('service', 'gateway_profile')
                    if gateway_profile.institution is not None:
                        transaction_list = transaction_list.filter(
                                Q(gateway_profile=gateway_profile) | Q(institution=gateway_profile.institution) \
                                | Q(gateway_profile__institution=gateway_profile.institution))
                    else:
                        transaction_list = transaction_list.filter(gateway_profile=gateway_profile)

                    collection = []
                    transaction_types = transaction_list.distinct('service__name')
                    for ttype in transaction_types:
                        collection.append(ttype.service.name)

                    # query filters
                    if "q" in payload.keys() and payload['q'] not in ["", None]:
                        query0 = reduce(operator.or_, (Q(gateway_profile__user__username__icontains=s.strip()) for s in
                                                       payload['q'].split(" ")))
                        query1 = reduce(operator.or_,
                                        (Q(gateway_profile__user__first_name__icontains=s.strip()) for s in
                                         payload['q'].split(" ")))
                        query2 = reduce(operator.or_, (Q(gateway_profile__user__last_name__icontains=s.strip()) for s in
                                                       payload['q'].split(" ")))
                        query3 = reduce(operator.or_,
                                        (Q(request__icontains=s.strip()) for s in payload['q'].split(" ")))
                        query4 = reduce(operator.or_,
                                        (Q(response__icontains=s.strip()) for s in payload['q'].split(" ")))
                        query5 = reduce(operator.or_,
                                        (Q(msisdn__phone_number__icontains=s.strip()) for s in payload['q'].split(" ")))
                        query6 = reduce(operator.or_, (Q(gateway_profile__user__email__icontains=s.strip()) for s in
                                                       payload['q'].split(" ")))
                        query7 = reduce(operator.or_, (Q(id__icontains=s.strip()) for s in payload['q'].split(" ")))

                        transaction_list = transaction_list.filter(
                                query0 | Q(query1, query2) | query3 | query4 | query5 | query6 | query7)

                    if "type" in payload.keys() and payload['type'] not in ["", None]:
                        transaction_list = transaction_list.filter(service__name__iexact=payload['type'].strip())

                    # filter last_id
                    if 'max_id' in payload.keys() and payload['max_id'] > 0:
                        transaction_list = transaction_list.filter(id__lt=payload['max_id'])
                    if 'min_id' in payload.keys() and payload['min_id'] > 0:
                        transaction_list = transaction_list.filter(id__gt=payload['min_id'])

                    transaction_list = transaction_list.values('id', 'gateway_profile__user__username',
                                                               'gateway_profile__user__first_name',
                                                               'gateway_profile__user__last_name', \
                                                               'transaction_status__name',
                                                               'transaction_status__description', \
                                                               'response_status__description',
                                                               'overall_status__description', 'service__name',
                                                               'request', \
                                                               'response', 'date_created', 'date_modified').order_by(
                            '-date_created').annotate(Count('id', unique=True))[:50]

                    # get last_id
                    trans = transaction_list.aggregate(max_id=Max('id'), min_id=Min('id'))
                    max_id = trans.get('max_id')
                    min_id = trans.get('min_id')

                    for t in transaction_list:
                        name = '%s %s' % (t['gateway_profile__user__first_name'], t['gateway_profile__user__last_name'])
                        desc = '%s|Response Status: %s|Overall Status: %s' % (
                            t['transaction_status__name'], t['response_status__description'],
                            t['overall_status__description'])
                        item = {"index": t['id'], "name": name, "type": t['service__name'],
                                "description": desc,
                                "request": json.loads(t['request']), "response": json.loads(t['response']),
                                "date_time": profile_tz.normalize(t['date_created'].astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}
                        rows.append([item])

                    groups = sorted(collection)
                    data = rows

                elif data_name == 'transaction_auth':
                    # Succesful response status not required for listing in auth: removed 19/1/2016 -  Q(overall_status__response='00'),
                    transaction_list = Transaction.objects.filter(~Q(next_command=None), Q(
                            next_command__access_level__name=payload['access_level']), \
                                                                  Q(
                                                                          gateway_profile__institution=gateway_profile.institution)). \
                                           order_by('-id')[:500]
                    collection = {}
                    for t in transaction_list:
                        ttype = t.service.name
                        name = '%s' % t.gateway_profile
                        desc = t.transaction_status.name
                        item = {"index": t.id, "name": name, "type": ttype,
                                "description": desc,
                                "request": json.loads(t.request), "response": json.loads(t.response),
                                "date_time": profile_tz.normalize(t.date_created.astimezone(profile_tz)).strftime(
                                        "%d %b %Y %I:%M:%S %p %Z %z")}

                        rows.append(item)
                        if ttype not in collection.keys():
                            collection[ttype] = [item]
                        else:
                            collection[ttype].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'recent_profiles':
                    if gateway_profile.institution not in [None, '']:
                        gateway_profile_list = GatewayProfile.objects.filter(institution=gateway_profile.institution,
                                                                             gateway=gateway_profile.gateway)
                    else:
                        gateway_profile_list = GatewayProfile.objects.filter(
                                institution__gateway=gateway_profile.gateway, gateway=gateway_profile.gateway)

                    collection = {}
                    for c in gateway_profile_list:
                        name = c.user.first_name + ' ' + c.user.last_name
                        desc = c.access_level.name + '(' + c.status.name + ')'
                        c_type = c.access_level.name
                        item = {"index": c.id, "name": name, "type": c_type, \
                                "description": desc,}
                        rows.append(item)
                        if c_type not in collection.keys():
                            collection[c_type] = [item]
                        else:
                            collection[c_type].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]

                elif data_name == 'contact_list':
                    contact = Contact.objects.filter(
                            product__notification__code__institution=gateway_profile.institution, \
                            product__notification__code__gateway=gateway_profile.gateway, subscribed=True, \
                            status__name='ACTIVE', product__notification__status__name='ACTIVE')
                    if 'notification_product' in payload.keys():
                        contact = contact.filter(product__id=payload['notification_product'])
                    contact = contact[:500]
                    collection = {}
                    for c in contact:
                        name = str(c.gateway_profile)
                        item = {"index": c.id, "name": name,}
                        rows.append(item)
                        if name not in collection.keys():
                            collection[name] = [item]
                        else:
                            collection[name].append(item)
                    groups = []
                    data = collection.values()

                elif data_name == 'notification_product':
                    contact = Contact.objects.filter(
                            product__notification__code__institution=gateway_profile.institution, \
                            product__notification__code__gateway=gateway_profile.gateway, subscribed=True, \
                            status__name='ACTIVE', product__notification__status__name='ACTIVE'). \
                        values('product__id', 'product__name', 'product__keyword', 'product__description', \
                               'product__notification__name').annotate(Count('id'))
                    collection = {}
                    for c in contact:
                        name = c['product__notification__name']
                        desc = c['product__name'] + ' (' + c['product__keyword'] + '): ' + c['product__description']
                        item = {"index": c['product__id'], "name": name, \
                                "description": desc, "count": str(c['id__count']) + ' Subscriber(s)'}
                        rows.append(item)
                        if name not in collection.keys():
                            collection[name] = [item]
                        else:
                            collection[name].append(item)

                    groups = sorted(collection.keys())
                    data = [collection[k] for k in groups]


                elif data_name == 'msisdn':
                    if 'reference' in payload.keys():
                        bill_manager_list = BillManager.objects.filter(order__reference=payload['reference'],
                                                                       order__status__name='UNPAID').order_by(
                                "-date_created")
                        if 'institution_id' in payload.keys():
                            bill_manager_list = bill_manager_list.filter(
                                    order__cart_item__product_item__institution__id=payload['institution_id'])
                        # else:
                        #	bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution=gateway_profile.institution)

                        item = ''
                        item_list = []
                        count = 1
                        if bill_manager_list.exists():
                            cart_item_list = bill_manager_list[0].order.cart_item.all()
                            if 'payment_method' in payload.keys():
                                cart_item_list = cart_item_list.filter(
                                        product_item__product_type__payment_method__name=payload['payment_method'])
                            lgr.info('Cart Item List: %s' % cart_item_list)
                            cart_item_country_list = cart_item_list.filter(
                                    Q(product_item__product_type__payment_method__channel__id=payload['chid']) | Q(
                                            product_item__product_type__payment_method__channel=None)). \
                                values('product_item__product_type__payment_method__country__ccode',
                                       'product_item__product_type__payment_method__country__name'). \
                                annotate(
                                    num_country=Count('product_item__product_type__payment_method__country__ccode'))
                            max_country = cart_item_country_list.aggregate(Max('num_country'))

                            lgr.info('\n\n\n\tCart Item Country List: %s|Max(%s)\n\n\n' % (
                                cart_item_country_list, max_country))

                            for i in cart_item_country_list:
                                if max_country['num_country__max'] == i['num_country']:
                                    rows.append([i['product_item__product_type__payment_method__country__ccode'],
                                                 i['product_item__product_type__payment_method__country__name']])
                    else:
                        country_list = Country.objects.all()
                        collection = {}
                        for c in country_list:
                            rows.append([c.ccode, c.name])

                elif data_name == 'notification_product_id':
                    product = NotificationProduct.objects.filter(
                            notification__code__institution=gateway_profile.institution, \
                            notification__code__gateway=gateway_profile.gateway, subscribable=False, \
                            notification__status__name='ACTIVE')
                    collection = {}
                    for c in product:
                        rows.append([c.id, c.name])

                else:
                    cols = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
                            {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
                            {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
                            {"label": "color", "type": "string"}]

                    rows = [["YES", "YES"], ["NO", "NO"]]

            payload['response'] = {
                'cols': cols,
                'rows': rows,
                'groups': groups,
                'data': data,
                'min_id': min_id,
                'max_id': max_id,
                'row_count': t_count,
            }
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Fetching Data from Source: %s" % e)
        return payload


class Trade(System):
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
                    original_filename = base64.urlsafe_b64decode(filename.replace(extension, ''))
                except:
                    original_filename = filename.replace(extension, '')
                activity_status = FileUploadActivityStatus.objects.get(name='CREATED')
                channel = Channel.objects.get(id=payload['chid'])
                activity = FileUploadActivity(name=original_filename, file_upload=upload[0], status=activity_status, \
                                              gateway_profile=gateway_profile,
                                              details=self.transaction_payload(payload), channel=channel)
                if 'description' in payload.keys():
                    activity.description = payload['description']

                with open(tmp_file, 'r') as f:
                    activity.file_path.save(filename, File(f), save=False)
                activity.save()
                f.close()

                payload['response'] = "File Saved. Wait to Process"
                payload['response_status'] = '00'
            else:
                payload['response_status'] = '21'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Uploading File: %s" % e)
        return payload


class Payments(System):
    pass


@app.task(
        ignore_result=True)  # Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60 * 10)
def process_file_upload():
    from celery.utils.log import get_task_logger
    lgr = get_task_logger(__name__)
    # One file every 10 seconds, means a total of 6 files per minute
    upload = FileUploadActivity.objects.select_for_update().filter(status__name='CREATED', \
                                                                   date_modified__lte=timezone.now() - timezone.timedelta(
                                                                           seconds=10))[:1]

    for u in upload:
        try:
            u.status = FileUploadActivityStatus.objects.get(name='PROCESSING')
            u.save()
            lgr.info('Captured Upload: %s' % u)

            Wrappers().process_file_upload_activity.delay(u)

            u.status = FileUploadActivityStatus.objects.get(name='PROCESSED')
            u.save()

            lgr.info("Files Written to and Closed")
        except Exception, e:
            u.status = FileUploadActivityStatus.objects.get(name='FAILED')
            u.save()

            lgr.info('Error processing file upload: %s | %s' % (u, e))
