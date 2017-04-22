from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import pytz, time, json
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.files import File
from django.db.models import Count

from survey.models import *
from django.db.models import Q
import operator

import logging
lgr = logging.getLogger('survey')

class Wrappers:
	pass

class System(Wrappers):
	def survey_tally(self, payload, node_info):
		try:
			survey_response = SurveyResponse.objects.filter(item__code=payload['survey_code'],\
					 item__survey__institution__id=payload['institution_id'],status__name='ACTIVE').\
					values('item__name','item__survey__name').annotate(Count('id'))

			survey_tally = 0

			lgr.info("Response: %s" % survey_response)
			if len(survey_response)>0:
				response = survey_response[0]
				survey_tally = response['id__count']

				payload['survey_item'] = response['item__name']
				payload['survey'] = response['item__survey__name']
			else:
				survey_item = SurveyItem.objects.filter(code=payload['survey_code'])
				payload['survey_item'] = survey_item[0].name
				payload['survey'] = survey_item[0].survey.name

			#Rank Item
			survey_response_rank = SurveyResponse.objects.values('item__name','item__survey__name').\
						annotate(rank_count=Count('id')).\
						filter(item__survey__name=payload['survey'], rank_count__gt=survey_tally,\
						 item__survey__institution__id=payload['institution_id'],status__name='ACTIVE').count()

			lgr.info('survey_response_rank: %s' % survey_response_rank)
			payload['survey_tally'] = survey_tally
			payload['survey_rank'] = survey_response_rank+1
			payload["response"] = "%s responses | Position: %s" % (payload['survey_tally'], payload['survey_rank'])
			payload['response_status'] = '00'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating survey item: %s" % e)
		return payload

	def activate_survey_response(self, payload, node_info):
		try:
			outbound_survey = str(payload['ext_outbound_id']).split("-")
			if len(outbound_survey)== 2 and outbound_survey[0] == 'SURVEY':
				survey_response = SurveyResponse.objects.filter(id=outbound_survey[1], status__name='INACTIVE')
				if len(survey_response)>0:
					response = survey_response[0]
					status = SurveyResponseStatus.objects.get(name='ACTIVE')
					response.status = status
					response.save()
					payload["response"] = "Survey Response Activated"
				else:
					payload["response"] = "Survey Response not Found"
			else:
				payload['response'] = 'Not a Survey Response'
			payload["response_status"] = "00"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating survey item: %s" % e)
		return payload


	def log_survey_response(self, payload, node_info):
		try:

			survey_item = SurveyItem.objects.filter(survey__institution__id=payload['institution_id'],\
					code=payload['survey_code'],status__name='ACTIVE').order_by('id')

			if len(survey_item)>0:
				status = SurveyResponseStatus.objects.get(name=payload['survey_response_status'])
				response = SurveyResponse(item=survey_item[0],status=status)
				if 'session_gateway_profile_id' in payload.keys():
					session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
					response.gateway_profile = session_gateway_profile

				if 'bridge__transaction_id' in payload.keys():
					response.transaction_reference = payload['bridge__transaction_id']

				response.save()

				payload['survey_response_id'] = response.id

				payload['ext_outbound_id'] = 'SURVEY-%s' % response.id

				payload["response_status"] = "00"
				payload["response"] = "Survey Item Created"
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No Survey Item Found'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating survey item: %s" % e)
		return payload

	def create_survey_item(self, payload, node_info):
		try:
			survey = Survey.objects.filter(Q(name=payload['item'])|Q(product_item__name=payload['item']),\
				institution__id=payload['institution_id'],status__name='ACTIVE').order_by('id')
			lgr.info('Survey: %s' % survey)

			if 'group' in payload.keys():
				survey = survey.filter(Q(group__data_name=payload['group'])\
					|Q(product_item__product_type__name=payload['group'])\
					|Q(product_type__name=payload['group'])|Q(group__name=payload['group']))

			lgr.info('Survey after Group: %s' % survey)
			status = SurveyItemStatus.objects.get(name="ACTIVE")
			survey_item = SurveyItem(name=payload['entry'], survey=survey[0], status=status)
			if 'survey_code' in payload.keys():
				survey_item.code=payload['survey_code']
			survey_item.save()

			#payload['product_item_id'] = survey[0].product_item.id

			payload["response_status"] = "00"
			payload["response"] = "Survey Item Created"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating survey item: %s" % e)
		return payload


	def log_survey(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload["gateway_profile_id"])
			status = SurveyResponseStatus.objects.get(name="ACTIVE")
			till,profile,institution,sale_contact = None,None,None,None
			if 'till_id' in payload.keys():
				till = InstitutionTill.objects.get(id=payload["till_id"])
			if 'profile_id' in payload.keys():
				profile = Profile.objects.get(id=payload["profile_id"])
			if 'institution_id' in payload.keys():
				institution = Institution.objects.get(id=payload['institution_id'])
			if 'sale_contact_id' in payload.keys():
				sale_contact = SaleContact.objects.get(id=payload['sale_contact_id'])

			lgr.info("Started Loop")
			for key,value in payload.items():
				if 'survey' in key and payload[key] not in [None, ""]:
					lgr.info("Survey Found: %s" % key)
					surveyitem = SurveyItem.objects.filter(id__in=payload[key].split(","))
					lgr.info("Survey Item Found: %s" % surveyitem)
					for i in surveyitem:
						lgr.info("Captured Item: %s" % i)
						response = SurveyResponse(item=i,created_by=gateway_profile,status=status)
						if profile is not None:
							response.profile = profile
						if till is not None:
							response.till = till
						response.save() 

			payload["response_status"] = "00"
			payload["response"] = "Survey Logged"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Logging Survey: %s" % e)
		return payload

class Trade(System):
	pass



lgr = get_task_logger(__name__)
#Celery Tasks Here
