from django.shortcuts import HttpResponseRedirect, HttpResponse
import simplejson as json
from django.core.exceptions import PermissionDenied
import hashlib, hmac, base64, string
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from secondary.channels.vcs.models import *
from django.contrib.auth import authenticate
from primary.core.bridge.views import *
from django.db.models import Q
from django.http import Http404
from decimal import Decimal, ROUND_DOWN

import logging
lgr = logging.getLogger('primary.core.api')

@csrf_protect
def default(request):
	return HttpResponse()  


@csrf_protect
def service_call(request):
		return HttpResponse("Protected Section")  

class ServiceCall:
	def api_service_call(self, service, gateway_profile, payload):
		try:
			payload = dict(filter(lambda x:x[1], payload.items())) #Remove empty value items
			payload = ServiceProcessor().do_process(service, gateway_profile, payload.copy())

			'''
			payload['action_id'] = response['action_id']
			payload['last_response'] = response['last_response']
			payload['response'] = response['response']
			payload['response_status'] = response['response_status']
			if 'transaction_reference' in response.keys(): payload['transaction_reference'] = response['transaction_reference']
			if 'timestamp' in response.keys(): payload['timestamp'] = response['timestamp']
			'''
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Service Processing Failed: %s" % e)

		return payload

class Authorize:
	def secure(self, payload, API_KEY):
                new_payload = {}
                for key, value in payload.items():
                        if 'sec_hash' not in key and 'credentials' not in key:
				try:value=json.loads(value, parse_float=Decimal);value=str(value) if isinstance(value,Decimal) else value #(BUG!!) JSON loads converts decimal places
				except:pass
				if isinstance(value, dict) is False: new_payload[key]=value
		p = []
		for n in sorted(new_payload.keys()):
			k = '%s=%s' % (n,new_payload[n])
			p.append(k)
		p1 = '&'.join(p)
		#lgr.info('Hash: %s' % p1)
		a = hmac.new( base64.b64decode(API_KEY), p1, hashlib.sha256)
		return base64.b64encode(a.digest())

	def check_hash(self, payload, API_KEY):
		lgr.info("Check Hash: %s" % base64.b64decode(API_KEY))
		payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value) ), payload.items()))
		secret = payload['sec_hash']
		#remove sec_hash and hash_type	
		sec_hash = self.secure(payload,API_KEY) 
		if base64.b64decode(secret) == base64.b64decode(sec_hash):
			payload['response_status'] = '00'
		else:
			lgr.info("Secret: %s Sec Hash: %s" % (str(secret)[:100], str(sec_hash)[:100]))
			payload['response_status'] = '15'

		return payload

	def return_hash(self, payload, API_KEY):
		lgr.info("Return Hash")
		sec_hash = self.secure(payload,API_KEY) 
		payload['sec_hash'] =  sec_hash
		return payload

class Interface(Authorize, ServiceCall):
	@csrf_exempt
	def interface(self, request, SERVICE):
		if request.method == 'POST':
                        try:
                                #view_data = request.GET.copy()
                                try:view_data = request.read();un_payload = json.loads(view_data)
                                except:view_data = request.POST.copy();un_payload= view_data

				#Clean Request
				'''
				payload, count = {},1
				for key, value in un_payload.items():
					if count <=45 and isinstance(value, dict) is False:
						payload[key] = str(value)
					elif isinstance(value, dict):
						payload[key] = json.dumps(value)
					else:
						break
					count = count+1
				'''
				#payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value) ), un_payload.items()))

				payload = dict(map(lambda (key, value):(string.lower(key), value ), un_payload.items()))

				'''#RISK IN REVIEW
				for key, value in un_payload.items():
					#Remove any injected sensitive data
					if 'session_gateway_profile_id' in payload.keys():
						del payload['session_gateway_profile_id']
				'''
                        except Exception, e:
                                payload = {}
                                lgr.info('Error on Post%s' % e)
			try:
				lgr.info("SERVICE: %s" % SERVICE)
				gateway_profile_list, service = GatewayProfile.objects.none(), Service.objects.none()
				session_active = True

				if 'session_id' not in payload.keys() and 'credentials' not in payload.keys():
					#To use this access, one would require the System@User API_KEY
					#This access can create any user's session thus get any users API_KEY
					lgr.info('# A system User Login')
					gateway_profile_list = GatewayProfile.objects.filter(Q(Q(allowed_host__host=str(payload['gateway_host'])),Q(allowed_host__status__name='ENABLED'))\
								|Q(Q(gateway__default_host__host=str(payload['gateway_host'])),Q(gateway__default_host__status__name='ENABLED')),\
								Q(user__username='System@User'),Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS'])).\
								prefetch_related('user','msisdn','gateway')[:1]

				#Integration would need an API Key for the specific user.
				#Integration would require the user credentials on call so as to select user for API KEY check
				#If unable to locate record status is received on app, redirect to logout or call logout function
				elif 'session_id' not in payload.keys() and 'credentials' in payload.keys():
					#This allows any user with credentials to access services enabled within their access level
					#System services are excluded. (System services are the most sensitive)
					lgr.info('# A Credentials User Login')
					credentials = payload['credentials']
					gateway_profile_list = GatewayProfile.objects.filter(Q(allowed_host__host=payload['gateway_host'],\
								allowed_host__status__name='ENABLED')|Q(gateway__default_host__host=payload['gateway_host'],\
								gateway__default_host__status__name='ENABLED'),\
								Q(Q(user__username=credentials['username'])|Q(user__email=credentials['username'])),\
								Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS']))#Cant Filter as password check continues

                	        	if gateway_profile_list.exists():
						gp = None
						for g in gateway_profile_list:
							if g.user.check_password(credentials['password']):
								gp = g
								break
						if gp <> None:
							lgr.info('This User Active')
							gateway_profile_list = gateway_profile_list.filter(id=gp.id).\
										prefetch_related('user','msisdn','gateway')
						else:
							gateway_profile_list = GatewayProfile.objects.none()
					else:
						gateway_profile_list = GatewayProfile.objects.none()

				elif 'session_id' in payload.keys():
					#This user can access services within its access level
					lgr.info('Session ID available')
					try:
						lgr.info('SessionID: %s' % payload['session_id'])
						session_id = base64.urlsafe_b64decode(str(payload['session_id']))
						session = Session.objects.filter(Q(session_id=session_id.decode('hex')),\
							Q(channel__id=payload['chid']),\
							Q(gateway_profile__allowed_host__host=payload['gateway_host'],\
							gateway_profile__allowed_host__status__name='ENABLED')|\
							Q(gateway_profile__gateway__default_host__host=payload['gateway_host'],\
							gateway_profile__gateway__default_host__status__name='ENABLED'),\
							Q(gateway_profile__status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS'])).\
							prefetch_related('gateway_profile')[:1]

						if session.exists():
							user_session = session[0]
							session_expiry = user_session.gateway_profile.gateway.session_expiry
							#if True:#Check date_created/modified for expiry time

							if session_expiry and timezone.now() < user_session.last_access + timezone.timedelta(minutes=session_expiry):
								session_active = False
								user_session.status = SessionStatus.objects.get(name='EXPIRED')
								user_session.save()

							if (session_expiry == None) or (session_expiry and session_active):
								try: gateway_profile_list = GatewayProfile.objects.filter(id=user_session.gateway_profile.id).\
										prefetch_related('user','msisdn','gateway')
								except: pass
							else:
								#Expired Session
								lgr.info('session_id expired and is Customer')#Prompt For Credentials to Login
					except Exception, e:
						lgr.info('Error: %s' % e)
					#session should be encrypted and salted in base64
					#Session should last around 24 - 48 hours before pasword is prompted once again for access
					#Get Session from VCS and capture user #Pass the captured user for transaction
					#IF A WRONG SESSION IS PASSED, CLOSE PREVIOUS SESSION
					#iF SESSION TIME MORE THAN N-HOURS Request Credentials from USER
					#Country of Session must remain Consistent
				else:
					lgr.info('None of the Above')

				if gateway_profile_list.exists():
					lgr.info('Got Gateway Profile')
					service = Service.objects.filter(name=SERVICE).prefetch_related('access_level')
					service = service.filter(Q(access_level__in=[gateway_profile.access_level for gateway_profile in gateway_profile_list])|Q(access_level=None))
					if service.exists():
						payload_check = service_call(request)
						if payload_check.status_code == 403:
							lgr.info('Did Not Pass Onsite Check')
							API_KEY = gateway_profile_list[0].user.profile.api_key
							#lgr.info('Payload: %s' % payload)
							payload = self.check_hash(payload, API_KEY)
							if payload['response_status'] == '00':
								#Call Services as 
								payload = self.api_service_call(service[0], gateway_profile_list[0], payload)
							else:
								payload['response'] = {'overall_status': 'Hash Check Failed'}	
							#Remove sensitive data
							#try: del payload["session_id"]
							#except: pass

							#lgr.info('Payload: %s' % payload)
							payload = self.return_hash(payload, API_KEY)

							#lgr.info('Payload: %s' % payload)
						elif payload_check.status_code == 200:
							lgr.info('Onsite Check Passed')
							payload = self.api_service_call(service[0], gateway_profile_list[0], payload)
						else:
							pass
					else: 
						payload['response'] = {'overall_status': 'Service Does not Exist' }
						payload['response_status'] = '96'
				elif session_active == False:
					lgr.info('Session Has expired')
					payload['response'] = {'overall_status': 'Session Has Expired', 'redirect': '/logout' , 'logout': True}
					payload['response_status'] = '58'
				else:
					lgr.info('Didnt Get Gateway Profile')
					payload['response'] = {'overall_status': 'Profile Does not Exist' }
					payload['response_status'] = '25'
			except Exception, e:
				payload['response_status'] = '96'
				lgr.info('Error on receiving payload: %s' % e)


			#clean protected elements
			for k,v in payload.items():
				if 'card' in k.lower():
					del payload[k]

			json_results = json.dumps(payload)
			return HttpResponse(json_results, content_type='application/json')
		else:
                        raise PermissionDenied

