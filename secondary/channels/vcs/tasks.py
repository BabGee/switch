from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from django.template import Context, loader
from django.shortcuts import render
from django.shortcuts import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
import simplejson as json
from django.core.exceptions import PermissionDenied
from secondary.channels.vcs.models import *
from primary.core.bridge.models import *
import os, random, string
from django.db.models import Q
from itertools import chain
import base64
from django.utils.encoding import smart_str
from django.core.mail import EmailMultiAlternatives
from django.utils.http import urlquote

import logging
lgr = logging.getLogger('secondary.channels.vcs')

#Check on out of range issue with int
class Wrappers:
	@app.task(ignore_result=True)
	def send_email(self, payload, node_info):
		lgr = get_task_logger(__name__)
		lgr.info('Sending Email')
		try:
                        subject, from_email, to = payload['name']+': '+payload["SERVICE"].title(), payload['name']+'<noreply@'+payload['gateway_host']+'>', payload["email"]
                        text_content = 'For more info, go to http://%s.' % payload["gateway_host"]
		
			url = {'sec': payload['session'],'SERVICE':'EMAIL VERIFICATION','gpid':payload['session_gateway_profile_id']}
			import urllib
			main_url = 'http://'+payload['gateway_host']+'/index/#?'+urllib.urlencode(url)
                        html_content = loader.get_template('send_mail.html') #html template with utf-8 charset
                        d = Context({'main_url':main_url,'payload':payload})
                        html_content = html_content.render(d)
                        html_content = smart_str(html_content)
                        msg = EmailMultiAlternatives(subject, text_content, from_email, [to.strip()], headers={'Reply-To': 'No Reply'})

                        msg.attach_alternative(html_content, "text/html")
                        msg.send()              

		except Exception, e:
			lgr.info('Error Sending Mail: %s' % e)

		except BadHeaderError:
			lgr.info('Bad Header: Error Sending Mail')

class System(Wrappers):
	def create_ussd_menu(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			#CREATE CODE
			code_type = CodeType.objects.get(name='SHORT CODE')
			mno = MNO.objects.filter(name__in=payload['ussd_mno'].split(","))
			institution = Institution.objects.get(id=payload['institution_id'])
			channel = Channel.objects.get(name='USSD')
			session_state = SessionState.objects.get(name=payload['ussd_session_state'])
			input_variable = InputVariable.objects.get(name='String Entry')
			menu_status = MenuStatus.objects.get(name='ENABLED')
			menu = Menu(page_string=payload['ussd_page_string'], level=payload['ussd_level'], group_select=payload['ussd_group_select'],\
				session_state=session_state, input_variable=input_variable,menu_description=payload['ussd_menu_description'],\
				menu_status=menu_status)

			if 'ussd_service' in payload.keys():
				service = Service.objects.get(name=payload['ussd_service'])
				menu.service = service
			if 'ussd_submit' in payload.keys():
				menu.submit = payload['ussd_submit']
			if 'ussd_selection_preview' in payload.keys():
				menu.selection_preview = payload['ussd_selection_preview']

			menu.save()

			access_level_list = AccessLevel.objects.filter(name__in=payload['ussd_access_level'].split(","))
			for a in access_level_list:
				menu.access_level.add(a)

			for m in mno:
				code = Code(code=payload['ussd_code'],mno=m, institution=institution,channel=channel,\
					code_type=code_type, description=payload['ussd_description'], gateway=gateway_profile.gateway)
				code.save()

				menu.code.add(code)

			#get menu STATUS
			#GET MENU SESSION STATE
			#DEFAULT INPUT VARIABLE (STRING)

			payload['response'] = 'USSD Menu Created'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Creating USSD Menu Failed: %s' % e)
			payload['response_status'] = '96'

		return payload


	def vcs_menu(self, payload, node_info):

		from secondary.channels.vcs.views import VAS
		lgr.info('VCS MENU| payload: %s' % payload)

		#
		#
		#Get code
		view_data = VAS().menu_input(payload, node_info)
	
		#view_data["PAGE_STRING"] = 'VCS MENU'
		#view_data["MNO_RESPONSE_SESSION_STATE"] = 'END'
		#view_data['SESSION_ID'] = payload['sessionID']
		#view_data['MSISDN'] = payload["msisdn"]
		lgr.info('Final Payload: %s' % payload)
		payload['response'] = view_data
		payload['response_status'] = '00'

		return payload

	def set_user_password(self, payload, node_info):
		payload['trigger_state'] = True
		payload['response_status'] = '00'
		payload['response'] = 'Password Set'

		return payload

	def session(self, payload, node_info):
		try:
			#CREATE SIGN UP SESSION, GET SESSION_ID (To expire within - 24 - 48hrs) VCSSystem().session(payload, node_info)
			chars = string.ascii_letters + string.punctuation + string.digits
			rnd = random.SystemRandom()
			s = ''.join(rnd.choice(chars) for i in range(150))
			session_id = s.encode('base64')
			channel = Channel.objects.get(id=payload["chid"])
			session_hop = SessionHop(session_id=session_id.lower(),channel=channel,num_of_tries=0,num_of_sends=0)
			if 'email' in payload.keys():
				session_hop.reference = payload["email"]
			session_hop.save()

			if 'session_gateway_profile_id' in payload.keys():
				gateway_profile=GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				session_hop.gateway_profile=gateway_profile
				session_hop.save()

			encoded_session = base64.urlsafe_b64encode(session_hop.session_id.encode('hex'))
			payload['session'] = urlquote(encoded_session)
			payload['response'] = encoded_session
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Creating Session Failed: %s' % e)
			payload['response_status'] = '96'

		return payload

	def email_credentials(self, payload, node_info):
                try:
			lgr.info('Payload: %s' % payload)
			self.send_email.delay(payload, node_info)
			payload['response_status'] = '00'
                        payload['response'] = 'Credentials Sent'

		except Exception, e:
			lgr.info('Error Sending Mail: %s' % e)
			payload['response'] = 'Error Sending email'
			payload['response_status'] = '96'

		except BadHeaderError:
			lgr.info('Bad Header: Error Sending Mail')
			payload['response'] = 'Error Sending Mail'
			payload['response_status'] = '96'


		return payload

class Trade(System):
	pass
