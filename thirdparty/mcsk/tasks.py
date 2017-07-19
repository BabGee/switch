from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
import base64, re

from survey.models import *
from thirdparty.mcsk.models import *

import logging
lgr = logging.getLogger('mcsk')


class Wrappers:
	pass

class System(Wrappers):
	def get_survey_code(self, payload, node_info):
		try:
			code = None
			if 'mamtag code' in payload.keys():
				code = payload['mamtag code']

			elif 'access_point' in payload.keys():
				access_point = payload['access_point']
				access_point = access_point.replace("*868*","")
				code = access_point.replace("#","")

			lgr.info('Survey Code: %s' % code)
			request_list = CodeRequest.objects.filter(code_allocation=code,request_type__name='MAMTAG VOTING CODE')
			if len(request_list)>0:
				request = request_list[0]
				payload['code_preview'] = request.code_preview
				payload['survey_code'] = code
				payload['survey_response_status'] = 'INACTIVE'
				payload['response_status'] = '00'
				payload['response'] = 'Survey Code Captured'
			else:
				payload['response'] = 'Code Not Found'
				payload['response_status'] = '25'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Survey Code: %s" % e)
		return payload

	def allocate_mamtag_code(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			request_type = CodeRequestType.objects.get(name='MAMTAG VOTING CODE')

			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			request = CodeRequest(request_type=request_type, gateway_profile=session_gateway_profile,\
					phone_number=payload['msisdn'])
			request.code_preview = '%s as %s of the year.' % (payload['entry'],payload['item'])
			#code allocation
			request_list = CodeRequest.objects.filter(request_type=request_type).order_by('-code_allocation')
			if len(request_list)>0:
				code_allocation = int(request_list[0].code_allocation)+1
			else:
				code_allocation = 2001

			if 'region' in payload.keys():
				request.region = Region.objects.get(name=payload['region'])

			request.code_allocation = code_allocation
			request.save()


			payload['survey_code'] = request.code_allocation
			payload['ussd_code'] = "*868*%s#" % request.code_allocation
			payload['ussd_description'] = 'MAMTAG Voting Code'
			success_response = 'To complete voting for %s as %s of the year, ensure you have followed the steps and received an SMS@KES10 with a VID.' % (payload['entry'],payload['item'])
			payload['ussd_page_string'] = '[RESPONSE_SUMMARY=%s|Voting is currently unavailable. Please try again later]' % success_response[:160]
			payload['ussd_service'] = 'MAMTAG VOTING'
			payload['ussd_session_state'] = 'END'
			payload['ussd_level'] = 0
			payload['ussd_group_select'] = 0
			payload['ussd_mno'] = 'Safaricom,Airtel'
			payload['ussd_submit'] = True
			payload['ussd_menu_description'] = 'survey_code'
			payload['ussd_selection_preview'] = False
			payload['ussd_access_level'] = 'CUSTOMER,SYSTEM,MANAGER,OPERATOR,ADMINISTRATOR,SUPERVISOR,SUPER ADMINISTRATOR,API USER,SALES DELIVERY'
			payload['response'] = 'Mamtag Code Allocated'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Allocating Mamtag Code: %s" % e)
		return payload

	def code_request(self, payload, node_info):
		try:
			request_type = CodeRequestType.objects.get(name='SHIKANGOMA RESELLER CODE')

			request = CodeRequest(request_type=request_type, full_names=payload['full names'],\
				phone_number=payload['msisdn'],\
				passport_id_no=payload['id number'],member_number=payload['member number'])
			member = Member.objects.filter(member_number=payload['member number'])
			name_count, member_number_count = 0,0
			if len(member)>0:
				request.member = member[0]
				member_full_names = payload['full names'].split(' ')
				for n in member_full_names:
					if n in member[0].full_names:
						name_count = name_count+1
				if payload['member number'].strip() == member[0].member_number:
					member_number_count = 1
			request.details_match = '%s:%s' % (name_count,member_number_count)

			request.code_preview = payload['preview']
			#code allocation
			request_list = CodeRequest.objects.filter(request_type=request_type).order_by('-code_allocation')
			if len(request_list)>0:
				code_allocation = int(request_list[0].code_allocation)+1
			else:
				code_allocation = 201

			request.code_allocation = code_allocation
			request.save()
			payload['response'] = 'Code Request Received for Approval.'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Code Request: %s" % e)
		return payload



	def award_registration(self, payload, node_info):
		try:
			#payload['ext_service_id'] = payload['Payment']
			survey = Survey.objects.filter(product_item__name=payload["item"],group__name=payload['group'], institution__id=payload['institution_id'], status__name='ACTIVE').order_by('id')
			if len(survey) > 0:
				payload['product_item_id'] = survey[0].product_item.id
				payload['institution_till_id'] = survey[0].product_item.institution_till.all()[0].id
				payload['currency'] = survey[0].product_item.currency.code
				payload['amount'] = survey[0].product_item.unit_cost
				payload['response'] = 'Awards Registration'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on awards registration: %s" % e)
		return payload


class Trade(System):
	pass


lgr = get_task_logger(__name__)
#Celery Tasks Here
