from django.shortcuts import HttpResponseRedirect, HttpResponse
import simplejson as json
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from primary.core.api.views import *
from primary.core.bridge.models import Service
from primary.core.upc.models import Profile
from django.views.decorators.csrf import csrf_protect
from django.contrib.gis.geoip import GeoIP
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import pytz, time, json, pycurl

import logging
lgr = logging.getLogger('primary.core.administration')

class WebService:
	def validate_url(self, url):
		val = URLValidator()
		try:
			val(url)
			return True
		except ValidationError, e:
			lgr.info("URL Validation Error: %s" % e)
			return False


	def post_request(self, payload, node, timeout=30):
		try:
			if self.validate_url(node):
				jdata = json.dumps(payload)
				#response = urllib2.urlopen(node, jdata, timeout = timeout)
				#jdata = response.read()
				#payload = json.loads(jdata)
				c = pycurl.Curl()
				#Timeout in 30 seconds
				c.setopt(pycurl.CONNECTTIMEOUT, timeout)
				c.setopt(pycurl.TIMEOUT, timeout)
				c.setopt(pycurl.NOSIGNAL, 1)
				c.setopt(pycurl.URL, str(node) )
				c.setopt(pycurl.POST, 1)
				content_type = 'Content-Type: application/json; charset=utf-8'
				content_length = 'Content-Length: '+str(len(jdata))
				header=[str(content_type),str(content_length)]
				c.setopt(pycurl.HTTPHEADER, header)
				c.setopt(pycurl.POSTFIELDS, str(jdata))
				import StringIO
				b = StringIO.StringIO()
				c.setopt(pycurl.WRITEFUNCTION, b.write)
				c.perform()
				response = b.getvalue()
				payload = json.loads(response)
		except Exception, e:
			lgr.info("Error Posting Request: %s" % e)
			payload['response_status'] = '96'

		return payload


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


