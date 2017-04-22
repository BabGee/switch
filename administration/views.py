from django.shortcuts import HttpResponseRedirect, HttpResponse
import simplejson as json
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from api.views import *
from bridge.models import Service
from upc.models import Profile
from django.views.decorators.csrf import csrf_protect
from django.contrib.gis.geoip import GeoIP

import logging
lgr = logging.getLogger('administration')

class WebService:
        def create_payload(self, request, payload):
                lgr.info('Started Creating Payload')

		ip_address = request.META.get('REMOTE_ADDR')

		@csrf_protect		
		def on_site(request, payload):
			payload['chid'] = '1'
			payload['gateway'] = 'SWITCH'
			g = GeoIP()
			city = g.city(ip_address)
			lgr.info('City: %s' % city)
			if city is not None:
				lgr.info('Got Params')
				payload['lat'] = city['latitude']
				payload['lng'] = city['longitude']
			else:
				lgr.info('No Params')
				payload['lat'] = '0.0'
				payload['lng'] = '0.0'
			payload['ip_address'] = ip_address 
			session_id = request.session.get('session_id')
			if session_id is not None:payload['session_id'] = session_id
			profile_id = request.session.get('profile_id')
			if profile_id is not None:payload['profile_id'] = profile_id

			lgr.info('Sending Payload: %s' % str(payload)[:100])
			return HttpResponse(payload)  
		try:
			payload_check = on_site(request, payload)
			if payload_check.status_code == 403:
				lgr.info('Did Not Pass Onsite Check')
				if payload['ip_address'] <> ip_address:
					lgr.info('IP ADDRESS: %s' % ip_address)
					payload['ip_address'] = None
			elif payload_check.status_code == 200:
				lgr.info('Onsite Check Passed')

				#Payload automaticaly inherits the newly created items by django dict injection
			else:
				pass
			lgr.info('Payload with Protect: %s' % str(payload)[:100])

		except Exception, e:
			lgr.info('Error on Protect: %s ' % e)

                return payload


	def response_processor(self, request, service, payload):
		try:
			lgr.info('Service: %s' % service)
			lgr.info('Response Payload: %s' % str(payload)[:100])	

			if payload['response_status'] == '00':
				lgr.info('Succesful Response Status')
				if service == 'LOGIN':
					lgr.info('Login Service')
					request.session['user_email'] = payload['response']['login']['user_email']
					request.session['first_name'] = payload['response']['login']['first_name']
					request.session['last_name'] = payload['response']['login']['last_name']
					request.session['api_key'] = payload['response']['login']['api_key']
					request.session['gateway'] = payload['response']['login']['gateway']
					request.session['profile_status'] = payload['response']['login']['profile_status']
					request.session['profile_id'] = payload['response']['login']['profile_id']
					request.session['access_level'] = payload['response']['login']['access_level']
					request.session['session_id'] = payload['response']['session']
			else:
				lgr.info('Failed Transaction')
		except Exception, e:
			lgr.info('Error Processing response: %s' % e)
			payload['response_status'] = '96'

		return payload

	def request_processor(self, request, service, payload):
		try:
			lgr.info('SERVICE : %s' % service)
			access_level = request.session.get('access_level')
			if access_level is None:
				access_level = 'SYSTEM'
			payload=self.create_payload(request, payload)
			#request.method = 'POST'
			#new_req = request.POST.copy()
			#request.POST.update(json.dumps(payload))
			import copy
			req_copy = copy.copy(request)
			req_copy.method = "POST"
			req_copy.POST = request.POST.copy()
			req_copy.POST.update(payload)

			response = Interface().interface(req_copy, access_level, service)
			if response.status_code == 200:
				payload = json.loads(response.content)
			else:
				payload['response_status'] = '96'
			#return HttpResponseRedirect(reverse('polls:results', payload))
			lgr.info('Final Payload: %s' % str(payload)[:100])	
		except Exception, e:
			lgr.info('Error Processing request: %s' % e)
			payload['response_status'] = '96'

		return payload


