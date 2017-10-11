from __future__ import absolute_import

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.contrib.gis.geoip import GeoIP
from django.conf import settings
from django.core.files import File
import base64, re, crypt
from django.utils.http import urlquote

from primary.core.bridge.models import *

import logging
lgr = logging.getLogger('upc')

#from celery import shared_task
#from celery.contrib.methods import task_method
#from celery.contrib.methods import t
from celery import shared_task
#from celery import task_method
from celery import task
from switch.celery import app


class Wrappers:
	def validateEmail(self, email):
		try:
			validate_email(str(email))
			return True
		except ValidationError:
			return False


	def profile_update_if_null(self, user, payload):
		if 'full_names' in payload.keys():
			full_names = payload["full_names"].split(" ")
			if len(full_names) == 1:
				payload['first_name'] = full_names[0]
			if len(full_names) == 2:
				payload['first_name'],payload['last_name'] = full_names
			elif len(full_names) == 3:
				payload['first_name'],payload['middle_name'],payload['last_name'] = full_names

		if 'chid' in payload.keys() and int(payload["chid"]) in [4,5,11]: #Allow auto profile update on USSD/SMS/INTEGRATOR only
			if 'email' in payload.keys() and user.email in [None,""] and self.validateEmail(payload["email"]):user.email = payload["email"]
			if 'first_name' in payload.keys() and user.first_name in [None,""]: user.first_name = payload['first_name']
			if 'last_name' in payload.keys() and user.last_name in [None,""]: user.last_name = payload['last_name']
			user.save()

			profile = user.profile #User is a OneToOne field
			if 'middle_name' in payload.keys() and profile.middle_name in [None,""]: profile.middle_name = payload['middle_name']
			if 'national_id' in payload.keys() and profile.national_id in [None,""]: profile.national_id = payload['national_id']
			if 'physical_address' in payload.keys() and profile.physical_address in [None,""]: profile.physical_address = payload['physical_address']
			if 'city' in payload.keys() and profile.city in [None,""]: profile.city = payload['city']
			if 'region' in payload.keys() and profile.region in [None,""]: profile.region = payload['region']
			if 'postal_code' in payload.keys() and profile.postal_code in [None,""]: profile.postal_code = payload['postal_code']
			if 'country' in payload.keys() and profile.country in [None,""]: profile.country = Country.objects.get(iso2=payload['country'])
			if 'address' in payload.keys() and profile.address in [None,""]: profile.address = payload['address']
			if 'gender' in payload.keys() and profile.gender in [None,""]:
				try: gender = Gender.objects.get(code=payload['gender']); profile.gender = gender
				except Exception, e: lgr.info('Error on Gender: %s' % e)
			if 'dob' in payload.keys() and profile.dob in [None,""]: 
				try: profile.dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()
				except Exception, e: lgr.info('Error on DOB: %s' % e)

			profile.save()

		return user, payload


	def profile_update(self, user, payload):
		if 'full_names' in payload.keys():
			full_names = payload["full_names"].split(" ")
			if len(full_names) == 1:
				payload['first_name'] = full_names[0]
			if len(full_names) == 2:
				payload['first_name'],payload['last_name'] = full_names
			elif len(full_names) == 3:
				payload['first_name'],payload['middle_name'],payload['last_name'] = full_names

		if 'email' in payload.keys() and self.validateEmail(payload["email"]):user.email = payload["email"]
		if 'first_name' in payload.keys(): user.first_name = payload['first_name']
		if 'last_name' in payload.keys(): user.last_name = payload['last_name']
		user.save()

		profile = user.profile #User is a OneToOne field
		if 'middle_name' in payload.keys(): profile.middle_name = payload['middle_name']
		if 'national_id' in payload.keys(): profile.national_id = payload['national_id']
		if 'physical_address' in payload.keys(): profile.physical_address = payload['physical_address']
		if 'city' in payload.keys(): profile.city = payload['city']
		if 'region' in payload.keys(): profile.region = payload['region']
		if 'postal_code' in payload.keys(): profile.postal_code = payload['postal_code']
		if 'country' in payload.keys(): profile.country = Country.objects.get(iso2=payload['country'])
		if 'address' in payload.keys(): profile.address = payload['address']
		if 'gender' in payload.keys():
			try: gender = Gender.objects.get(code=payload['gender']); profile.gender = gender
			except Exception, e: lgr.info('Error on Gender: %s' % e)
		if 'dob' in payload.keys():
			try: profile.dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()
			except Exception, e: lgr.info('Error on DOB: %s' % e)


		profile.save()

		return user, payload



	def profile_capture(self, gateway_profile, payload, profile_error):

		if ('email' in payload.keys() and self.validateEmail(payload["email"]) ) and \
		('msisdn' in payload.keys() and self.get_msisdn(payload)):

			msisdn_session_gateway_profile = GatewayProfile.objects.filter(Q(msisdn__phone_number=self.get_msisdn(payload)),Q(gateway=gateway_profile.gateway))
			email_session_gateway_profile = GatewayProfile.objects.filter(Q(user__email=payload["email"]),Q(gateway=gateway_profile.gateway))

			if msisdn_session_gateway_profile.exists() and email_session_gateway_profile.exists():
				if msisdn_session_gateway_profile[0] == email_session_gateway_profile[0]:
					session_gateway_profile = msisdn_session_gateway_profile
				elif msisdn_session_gateway_profile[0].user == email_session_gateway_profile[0].user:
					session_gateway_profile = msisdn_session_gateway_profile
				else:
					profile_error = email_session_gateway_profile[0]
					session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)
			elif msisdn_session_gateway_profile.exists():
				session_gateway_profile = msisdn_session_gateway_profile
			elif email_session_gateway_profile.exists():
				session_gateway_profile = email_session_gateway_profile
			else:
				session_gateway_profile = msisdn_session_gateway_profile


		elif 'email' in payload.keys() and self.validateEmail(payload["email"]):
			session_gateway_profile = GatewayProfile.objects.filter(user__email=payload["email"],\
					 gateway=gateway_profile.gateway)
		elif 'msisdn' in payload.keys() and self.get_msisdn(payload):
			session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=self.get_msisdn(payload),\
					 gateway=gateway_profile.gateway)
		elif 'session_gateway_profile_id' in payload.keys():
			session_gateway_profile = GatewayProfile.objects.filter(id=payload['session_gateway_profile_id'])
		elif 'reference' in payload.keys():
			if 'reference' in payload.keys() and self.validateEmail(payload["reference"]):
				session_gateway_profile = GatewayProfile.objects.filter(user__email=payload["reference"],\
						 gateway=gateway_profile.gateway)
			else:
				payload['msisdn'] = payload['reference']
				msisdn = self.get_msisdn(payload)
				if msisdn:
					session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=msisdn,\
							 gateway=gateway_profile.gateway)
				else:
					del payload['msisdn']
					session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)
		else:
			session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)

		return session_gateway_profile, payload, profile_error

	def get_msisdn(self, payload):
		lng = payload['lng'] if 'lng' in payload.keys() else 0.0
		lat = payload['lat'] if 'lat' in payload.keys() else 0.0
               	trans_point = Point(float(lng), float(lat))
		g = GeoIP()

		msisdn = None
		if "msisdn" in payload.keys():
			msisdn = str(payload['msisdn'])
			msisdn = msisdn.strip().replace(' ','').replace('-','')
			if len(msisdn) >= 9 and msisdn[:1] == '+':
				msisdn = str(msisdn)
			elif len(msisdn) >= 7 and len(msisdn) <=10 and msisdn[:1] == '0':
				country_list = Country.objects.filter(mpoly__intersects=trans_point)
				ip_point = g.geos(str(payload['ip_address']))
				#Allow Country from web and apps
				if country_list.exists() and country_list[0].ccode and int(payload['chid']) in [1,3,7,8,9,10]:
					msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
				elif ip_point and int(payload['chid']) in [1,3,7,8,9,10]:
					country_list = Country.objects.filter(mpoly__intersects=ip_point)
					if country_list.exists() and country_list[0].ccode:
						msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
					else:
						msisdn = None
				else:
					msisdn = '+254%s' % msisdn[1:]
			elif len(msisdn) >=10  and msisdn[:1] <> '0' and msisdn[:1] <> '+':
				msisdn = '+%s' % msisdn #clean msisdn for lookup
			else:
				msisdn = None

		return msisdn

	#@app.task(filter=task_method, ignore_result=True)
	@app.task(ignore_result=True)

	def saveImage(self, filename, image_obj):

		from celery.utils.log import get_task_logger
		lgr = get_task_logger(__name__)
		try:
			fromdir_name = settings.MEDIA_ROOT + '/tmp/uploads/'
			from_file = fromdir_name + str(filename)
			lgr.info('Filename: %s' % filename)

			with open(from_file, 'r') as f:
				myfile = File(f)
				image_obj.image.save(filename, myfile, save=False)
			image_obj.save()
			myfile.close()
			f.close()
		except Exception, e:
			lgr.info("Unable to save image: %s to: %s because: %s" % (filename, image_obj, e))


class System(Wrappers):
	def session(self, payload, node_info):
		try:
			#CREATE SIGN UP SESSION, GET SESSION_ID (To expire within - 24 - 48hrs) VCSSystem().session(payload, node_info)
			chars = string.ascii_letters + string.punctuation + string.digits
			rnd = random.SystemRandom()
			s = ''.join(rnd.choice(chars) for i in range(150))
			session_id = s.encode('base64')
			channel = Channel.objects.get(id=payload["chid"])
			session = Session(session_id=session_id.lower(),channel=channel,num_of_tries=0,num_of_sends=0,status=SessionStatus.objects.get(name='CREATED'))
			if 'email' in payload.keys():
				session.reference = payload["email"]
			session.save()

			if 'session_gateway_profile_id' in payload.keys():
				gateway_profile=GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				session.gateway_profile=gateway_profile
				session.save()

			encoded_session = base64.urlsafe_b64encode(session.session_id.encode('hex'))
			payload['session'] = urlquote(encoded_session)
			payload['response'] = encoded_session
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Creating Session Failed: %s' % e)
			payload['response_status'] = '96'

		return payload


	def profile_is_registered(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			if session_gateway_profile.status.name <> 'REGISTERED':
				payload['response'] = 'Profile Exists'
				payload['response_status'] = '26'
			else:
				payload['response'] = 'Profile Details Captured'
				payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on get profile details: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def get_profile_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			user = gateway_profile.user
			profile = user.profile

			payload["email"] = user.email
			payload['first_name'] = user.first_name
			payload['last_name'] = user.last_name
			payload['middle_name'] = profile.middle_name
			payload['national_id'] = profile.national_id
			payload['physical_address'] = profile.physical_address
			payload['city'] = profile.city
			payload['region'] = profile.region
			payload['postal_code'] = profile.postal_code
			payload['country'] = profile.country.iso2
			payload['address'] = profile.address

			payload['response'] = 'Profile Details Captured'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on get profile details: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def avs_check(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			def avs_triggers(session_gateway_profile, payload):

				detail_missing = False
				if session_gateway_profile.user.email in [None,''] or self.validateEmail(session_gateway_profile.user.email) == False:
					payload['trigger'] = 'no_email%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.msisdn in [None,'']:
					payload['trigger'] = 'no_msisdn%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.user.first_name in [None,'']:
					payload['trigger'] = 'no_first_name%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.user.last_name in [None,'']:
					payload['trigger'] = 'no_last_name%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.user.profile.physical_address in [None,'']:
					payload['trigger'] = 'no_address%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.user.profile.city in [None,'']:
					payload['trigger'] = 'no_city%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.user.profile.postal_code in [None,'']:
					payload['trigger'] = 'no_postal_code%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if session_gateway_profile.user.profile.country in [None,'']:
					payload['trigger'] = 'no_country%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					detail_missing = True
				if detail_missing:
					payload['trigger'] = 'detail_missing%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				return payload

			payload = avs_triggers(gateway_profile, payload)

			payload['response'] = 'AVS Details Captured'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on avs check: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def registration_check(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			def avs_triggers(session_gateway_profile, payload):
				if session_gateway_profile.user.first_name in [None,'']:
					payload['trigger'] = 'no_first_name%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				if session_gateway_profile.user.last_name in [None,'']:
					payload['trigger'] = 'no_last_name%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				if session_gateway_profile.user.profile.physical_address in [None,'']:
					payload['trigger'] = 'no_address%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				if session_gateway_profile.user.profile.city in [None,'']:
					payload['trigger'] = 'no_city%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				if session_gateway_profile.user.profile.postal_code in [None,'']:
					payload['trigger'] = 'no_postal_code%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				if session_gateway_profile.user.profile.country in [None,'']:
					payload['trigger'] = 'no_country%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				return payload

			if 'email_msisdn' in payload.keys() and self.validateEmail(payload["email_msisdn"]):
				lgr.info('With Email')
				gateway_profile_list = GatewayProfile.objects.filter(user__email=payload['email_msisdn'], gateway=gateway_profile.gateway)

				if gateway_profile_list.exists() and gateway_profile_list[0].msisdn not in [None,'']:
					payload['msisdn'] = gateway_profile_list[0].msisdn.phone_number
					payload['trigger'] = 'with_email,is_registered,%s%s' % (gateway_profile_list[0].status.name,','+payload['trigger'] if 'trigger' in payload.keys() else '')
				elif gateway_profile_list.exists():
					#check postal code, address, country
					lgr.info('Profile With Email: %s' % gateway_profile_list[0])
					payload['trigger'] = 'with_email,is_registered,%s%s' % (gateway_profile_list[0].status.name,','+payload['trigger'] if 'trigger' in payload.keys() else '')
					payload = avs_triggers(gateway_profile_list[0],payload)

				else:

					lgr.info('No Profile With Email')
					payload['trigger'] = 'with_email,not_registered%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['email'] = payload['email_msisdn']
				payload['response'] = 'Email Captured'
				payload['response_status'] = '00'
			else:


				lgr.info('Without Email')
				msisdn = None
				if "email_msisdn" in payload.keys():
		 			payload['msisdn'] = str(payload['email_msisdn'])
					msisdn = self.get_msisdn(payload)
				lgr.info('MSISDN: %s' % msisdn)
				if msisdn is not None:
					lgr.info('With MSISDN')
					gateway_profile_list = GatewayProfile.objects.filter(msisdn__phone_number=msisdn, gateway=gateway_profile.gateway)

					lgr.info('With MSISDN Profile: %s' % gateway_profile_list)
					if gateway_profile_list.exists() and self.validateEmail(gateway_profile_list[0].user.email):
						lgr.info('Profile With Email: %s' % gateway_profile_list[0])
						payload['email'] = gateway_profile_list[0].user.email
						payload['trigger'] = 'with_email,with_msisdn,is_registered,%s%s' % (gateway_profile_list[0].status.name,','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload = avs_triggers(gateway_profile_list[0],payload)
					elif gateway_profile_list.exists():
						lgr.info('Profile With No Email: %s' % gateway_profile_list[0])
						payload['trigger'] = 'no_email,with_msisdn,is_registered,%s%s' % (gateway_profile_list[0].status.name,','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload = avs_triggers(gateway_profile_list[0],payload)
					else:
						lgr.info('No Profile With No Email')
						payload['trigger'] = 'no_email,with_msisdn,not_registered%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

					payload['msisdn'] = msisdn
					payload['response'] = 'Phone Number Captured'
					payload['response_status'] = '00'
				else:

					if 'msisdn' in payload.keys(): del payload['msisdn']
					payload['response'] = 'MSISDN or Email Not Found'
					payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on registration check: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload

	def device_verification(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			msisdn = self.get_msisdn(payload)
			lgr.info('MSISDN: %s' % msisdn)
			if msisdn is not None:

				gateway_profile_list = GatewayProfile.objects.filter(msisdn__phone_number=msisdn, \
						gateway=gateway_profile.gateway, activation_device_id = payload['fingerprint'])

				if gateway_profile_list.exists():
					session_gateway_profile = gateway_profile_list[0]
					hash_pin = crypt.crypt(str(payload['code']), str(session_gateway_profile.id))
					if hash_pin == session_gateway_profile.activation_code:
						session_gateway_profile.device_id = payload['fingerprint']
						session_gateway_profile.save()
						payload['response'] = 'Device Verified'
						payload['response_status'] = '00'
					else:
						payload['response_status'] = '55'
				else:
					payload['response'] = 'MSISDN Not Found'
					payload['response_status'] = '25'
			else:
				payload['response'] = 'MSISDN Not Found'
				payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on device verification: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def device_activation(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			msisdn = self.get_msisdn(payload)
			lgr.info('MSISDN: %s' % msisdn)
			if msisdn is not None:
				gateway_profile_list = GatewayProfile.objects.filter(msisdn__phone_number=msisdn, \
						gateway=gateway_profile.gateway)

				if gateway_profile_list.exists():
					session_gateway_profile = gateway_profile_list[0]

					chars = string.digits
					rnd = random.SystemRandom()
					pin = ''.join(rnd.choice(chars) for i in range(0,4))
					hash_pin = crypt.crypt(str(pin), str(session_gateway_profile.id))

					session_gateway_profile.activation_code = hash_pin
					session_gateway_profile.activation_device_id = payload['fingerprint']

					session_gateway_profile.save()

					payload['activation_code'] = pin

					payload['response'] = 'Device Activation Request'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'MSISDN Not Found'
					payload['response_status'] = '25'
			else:
				payload['response'] = 'MSISDN Not Found'
				payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on device activation: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def device_validation(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			msisdn = self.get_msisdn(payload)
			lgr.info('MSISDN: %s' % msisdn)
			if msisdn is not None:
				gateway_profile_list = GatewayProfile.objects.filter(msisdn__phone_number=msisdn, \
						gateway=gateway_profile.gateway)

				gateway_profile_device = gateway_profile_list.filter(device_id=payload['fingerprint'])

				if gateway_profile_list.exists() and gateway_profile_device.exists() and gateway_profile_device[0].status.name=='ONE TIME PIN':
					payload['trigger'] = 'one_time_pin%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					payload['response'] = 'Device Validation'
					payload['response_status'] = '00'
				elif gateway_profile_list.exists() and gateway_profile_device.exists():
					payload['trigger'] = 'device_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					payload['response'] = 'Device Validation'
					payload['response_status'] = '00'
				elif gateway_profile_list.exists():
					payload['trigger'] = 'device_not_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					payload['response'] = 'Device Validation'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'MSISDN Not Found'
					payload['response_status'] = '25'
			else:
				payload['response'] = 'MSISDN Not Found'
				payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on validating institution: %s' % e)
			payload['response_status'] = '96'
		return payload


	def verify_msisdn(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Ensure session Gateway Profile is not used as it would use a profile of an existing account with MSISDN

			msisdn = self.get_msisdn(payload)
			lgr.info('MSISDN: %s' % msisdn)
			if msisdn is not None:
				try:msisdn = MSISDN.objects.get(phone_number=msisdn)
				except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();

			try:

				change_msisdn = gateway_profile.changeprofilemsisdn
				lgr.info('Has Change Profile MSISDN')
				change_msisdn.msisdn = msisdn
				if msisdn == change_msisdn.msisdn:
					if change_msisdn.status.name == 'PROCESSED' and change_msisdn.expiry >= timezone.now():
						hash_pin = crypt.crypt(str(payload['verification_code']), str(gateway_profile.id))

						if hash_pin == change_msisdn.change_pin:
							change_msisdn.status = ChangeProfileMSISDNStatus.objects.get(name='VALIDATED')
							change_msisdn.save()

							gateway_profile.msisdn = msisdn
							gateway_profile.save()

							payload['response_status'] = '00'
							payload['response'] = 'Change Request Logged' 
						else:
							payload['response_status'] = '25'
							payload['response'] = 'Wrong Code'
					else:
						payload['response_status'] = '19'
						payload['response'] = 'Verification Code Expired' 
				else:
					payload['response_status'] = '25'
					payload['response'] = 'MSISDN Did not Match Change MSISDN' 
			except ObjectDoesNotExist:
				payload['response_status'] = '96'
				payload['response'] = 'No Change MSISDN Found' 
		except Exception, e:
			lgr.info('Error on verify MSISDN: %s' % e)
			payload['response_status'] = '96'
		return payload


	def change_msisdn(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Ensure session Gateway Profile is not used as it would use a profile of an existing account with MSISDN

			msisdn = self.get_msisdn(payload)
			lgr.info('MSISDN: %s' % msisdn)
			if msisdn is not None:
				try:msisdn = MSISDN.objects.get(phone_number=msisdn)
				except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();

				chars = string.digits
				rnd = random.SystemRandom()
				pin = ''.join(rnd.choice(chars) for i in range(0,4))
				change_pin = crypt.crypt(str(pin), str(gateway_profile.id))
				expiry = timezone.localtime(timezone.now())+timezone.timedelta(minutes=5)
				status = ChangeProfileMSISDNStatus.objects.get(name='ACTIVE')


				check_gateway_profile = GatewayProfile.objects.filter(~Q(id=gateway_profile.id),Q(msisdn=msisdn),Q(gateway=gateway_profile.gateway))

				if check_gateway_profile.exists():
					payload['response'] = 'A profile with the Phone Number exists. Contact support for assistance'
					payload['response_status'] = '26'
				elif gateway_profile.msisdn == msisdn:
					payload['response'] = 'Your profile is already Mapped to the given Phone Number'
					payload['response_status'] = '26'
				else:

					try:

						change_msisdn = gateway_profile.changeprofilemsisdn
						lgr.info('Has Change Profile MSISDN')
						change_msisdn.msisdn = msisdn
						change_msisdn.expiry = expiry
						change_msisdn.change_pin = change_pin
						change_msisdn.status = status
						change_msisdn.save()
	
						lgr.info('Updating change profile MSISDN')
						payload['change_pin'] = pin
						payload['response_status'] = '00'
						payload['response'] = 'Change Request Logged' 

					except ObjectDoesNotExist:

						change_msisdn = ChangeProfileMSISDN(gateway_profile=gateway_profile,msisdn=msisdn,\
									expiry=expiry,change_pin=change_pin,status=status)
						change_msisdn.save()

						lgr.info('No change profile MSISDN')
						payload['change_pin'] = pin
						payload['response_status'] = '00'
						payload['response'] = 'Change Request Logged' 
			else:
				payload['response_status'] = '25'
				payload['response'] = 'No MSISDN' 



		except Exception, e:
			lgr.info('Error on change MSISDN: %s' % e)
			payload['response_status'] = '96'
		return payload


	def validate_institution(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if gateway_profile.institution:
				if 'institution_id' in payload.keys() and str(payload['institution_id']).strip() == str(gateway_profile.institution.id):
					payload['response'] = 'Institution Validated'
					payload['response_status'] = '00'
				elif 'institution_id' not in payload.keys():
					payload['institution_id'] = gateway_profile.institution.id
					payload['response'] = 'Institution Captured'
					payload['response_status'] = '00'
				else:
					payload['response_status'] = '03'
					payload['response'] = 'Institution did not match profile'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'Profile Institution Does not Exist %s' % gateway_profile

		except Exception, e:
			lgr.info('Error on validating institution: %s' % e)
			payload['response_status'] = '96'
		return payload



	def add_change_email(self, payload, node_info):
		try:
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			if 'email' in payload.keys() and self.validateEmail(payload["email"]): 
				existing_gateway_profile = GatewayProfile.objects.filter(Q(user__email=payload['email']), ~Q(id=session_gateway_profile.id),\
							Q(gateway=session_gateway_profile.gateway),Q(status__name__in=['ACTIVATED','ONE TIME PIN']))
				if existing_gateway_profile.exists():
					payload['response'] = 'Profile With Email Already exists'
					payload['response_status'] = '26'
				else:
					session_gateway_profile.user.email = payload["email"]
					session_gateway_profile.user.save()

					payload['response'] = 'Email Updated'
					payload['response_status'] = '00'
			else:
				lgr.info('Invalid Email:%s' % payload)
				payload['response'] = 'No Valid Email Found'
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on Set Profile Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def set_profile_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			if payload['pin'] == payload['confirm_pin']:
				hash_pin = crypt.crypt(str(payload['pin']), str(session_gateway_profile.id))
				session_gateway_profile.pin = hash_pin
				session_gateway_profile.status = ProfileStatus.objects.get(name='ACTIVATED')
				session_gateway_profile.save()
				payload['response'] = 'New PIN isSet'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '55'
				payload['response'] = 'Confirm PIN did not match New PIN'

		except Exception, e:
			lgr.info('Error on Set Profile Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def validate_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			hash_pin = crypt.crypt(str(payload['pin']), str(session_gateway_profile.id))

			if hash_pin == session_gateway_profile.pin:
				session_gateway_profile.pin_retries = 0
				session_gateway_profile.save()
				payload['response'] = 'Valid PIN'
				payload['response_status'] = '00'
			else:
				if session_gateway_profile.pin_retries >= 3:
					session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
				session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
				session_gateway_profile.save()
				payload['response_status'] = '55'
				payload['response'] = 'Invalid PIN'

		except Exception, e:
			lgr.info('Error on Validating Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def validate_one_time_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			hash_pin = crypt.crypt(str(payload['one_time_pin']), str(session_gateway_profile.id))

			if hash_pin == session_gateway_profile.pin:
				session_gateway_profile.pin_retries = 0
				session_gateway_profile.status = ProfileStatus.objects.get(name='ACTIVATED')
				session_gateway_profile.save()
				payload['response'] = 'Valid One Time PIN'
				payload['response_status'] = '00'
			else:
				if session_gateway_profile.pin_retries >= 3:
					session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
				session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
				session_gateway_profile.save()
				payload['response_status'] = '55'
				payload['response'] = 'Invalid One Time PIN'

		except Exception, e:
			lgr.info('Error on Validating One Time Pin: %s' % e)
			payload['response_status'] = '96'
		return payload

	def one_time_password(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			chars = string.ascii_letters + string.punctuation + string.digits
			rnd = random.SystemRandom()
			password = ''.join(rnd.choice(chars) for i in range(8))

			session_gateway_profile.user.set_password(password)
			session_gateway_profile.status = ProfileStatus.objects.get(name='ONE TIME PASSWORD')
			session_gateway_profile.save()

			payload['one_time_password'] = password
			payload['response'] = 'One Time Password Set'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on One Time Password: %s' % e)
			payload['response_status'] = '96'
		return payload


	def one_time_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			chars = string.digits
			rnd = random.SystemRandom()
			pin = ''.join(rnd.choice(chars) for i in range(0,4))
			hash_pin = crypt.crypt(str(pin), str(session_gateway_profile.id))

			session_gateway_profile.pin = hash_pin
			session_gateway_profile.status = ProfileStatus.objects.get(name='ONE TIME PIN')
			session_gateway_profile.save()

			payload['one_time_pin'] = pin
			payload['response'] = 'One Time Pin Set'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on One Time Pin: %s' % e)
			payload['response_status'] = '96'
		return payload

	def verify_password(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			if gateway_profile.user.is_active and gateway_profile.user.check_password(payload['current password']):
				payload['response'] = 'Password Verified'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on verifying Password: %s' % e)
			payload['response_status'] = '96'

		return payload

	def set_password(self, payload, node_info):
		try:
			password = payload['password']
			confirm_password = payload['confirm password']
			error = ''

			if re.search(r'\d', password) is None: error += 'Digit, ' 
			if re.search(r'[A-Z]', password) is None: error += 'Uppercase, '
			if re.search(r'[a-z]', password) is None: error += 'Lowercase, '
			if len(password) >=6 is None: error += 'More than 6 Characters, '
			if len(password) <=30 is None: error += 'Less than 30 Characters, '
			if re.search(r"[ !@#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None: error += 'Special character, '
			if password <> confirm_password: error += "Matching, " 
			if error == '':
				status = ProfileStatus.objects.get(name="ACTIVATED")
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				session_gateway_profile.status = status
				session_gateway_profile.save()
				session_gateway_profile.user.set_password(password)
				session_gateway_profile.user.is_active = True
				session_gateway_profile.user.save()
				payload['response'] = 'Password Set'
				payload['response_status'] = '00'
			else:
				payload['response'] = 'Requires('+error+')'
				payload['response_status'] = '30'
		except Exception, e:
			lgr.info('Error on Setting Password: %s' % e)
			payload['response_status'] = '96'

		return payload

	def reset_password(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			session_gateway_profile = GatewayProfile.objects.filter(Q(user__username=payload['username'])|Q(user__email=payload['username']),\
								Q(gateway=gateway_profile.gateway),Q(status__name__in=['ACTIVATED','ONE TIME PIN']))
			if len(session_gateway_profile) > 0:
				email = session_gateway_profile[0].user.email
				if  email not in [None,""] and self.validateEmail(email):
					payload["email"] = email
					payload['session_gateway_profile_id'] = session_gateway_profile[0].id
					payload['response'] = 'Reset Profile Captured'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'No Valid Email in File'
					payload['response_status'] = 25
			else:
				payload['response'] = 'Profile not Found'
				payload['response_status'] = 25

		except Exception, e:
			lgr.info('Error on Setting Password: %s' % e)
			payload['response_status'] = '96'

		return payload

	def create_institution_till(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			lgr.info('Gateway Profile : %s|%s' % (gateway_profile, payload))
			#till_type - determined by service name, default(ONLINE)
			till_type = TillType.objects.get(id=payload["till_type"])
			lgr.info("Finished Till Type")

			#till_currency = currency
			till_currency = Currency.objects.get(code=str(payload["currency"]))
			lgr.info("Finished Currency")

			#logo, if exists
			#Create co-ordinates if dont exist
			lng = payload['lng'] if 'lng' in payload.keys() else 0.0
			lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	                trans_point = Point(float(lng), float(lat))

			lgr.info("Finished Transaction")

			#qr_code, if exist
			#city = from geometry
			#Details({}) - [address,till_phone_number,till_business_number]
			details = json.dumps({})
			lgr.info("Starting Generating Till Number")
			all_tills = InstitutionTill.objects.filter(institution=gateway_profile.institution).order_by("-till_number")
			if len(all_tills)>0:
				till_number = all_tills[0].till_number+1
			else:
				till_number = 1

			description = payload["description"] if "description" in payload.keys() and payload["description"] not in ["",None] else payload["till_name"]

			is_default = payload["is_default"] if 'is_default' in payload.keys() else False
			lgr.info("Finished Genrating Items")

			till = InstitutionTill(name=payload["till_name"],institution=gateway_profile.institution,till_type=till_type, till_number=till_number,\
						till_currency=till_currency,description=description,physical_address=payload["till_location"],\
						is_default=is_default,geometry=trans_point,details=details)
 
			till.save()
			#save image if exist
			if 'till_image' in payload.keys():
				self.saveImage.delay(payload["till_image"], till)


			payload['till_id'] = till.id
			payload['till_number'] = till.till_number
			payload['response'] = 'Institution Till Created'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on Creating Institution Till: %s' % e)
			payload['response_status'] = '96'

		return payload

	def get_gateway_details(self, payload, node_info):
		try:
                        gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			gateway = gateway_profile.gateway
			details = {}

			if gateway_profile.access_level.name <> 'SYSTEM':
				details['profile'] = {}
				details['profile']['profile_photo'] = gateway_profile.user.profile.photo.name
				details['profile']['first_name'] = gateway_profile.user.first_name
				details['profile']['last_name'] = gateway_profile.user.last_name
				details['profile']['access_level'] = gateway_profile.access_level.name

			institution = None
			if 'institution_id' in payload.keys() and payload['institution_id'] not in ["",None,'None']:
				institution_list = Institution.objects.filter(status__name='ACTIVE',id=payload['institution_id']).\
							prefetch_related('gateway')
				if len(institution_list)>0:
					institution = institution_list[0]
			elif gateway_profile.institution is not None:
				institution = gateway_profile.institution
			if institution is not None:
				details['logo'] =institution.logo.name
				details['name'] =institution.name
				details['tagline'] =institution.tagline
				details['background_image'] = institution.background_image
				details['host'] =gateway.default_host.all()[0].host
				details['default_color'] = institution.default_color
				details['primary_color'] = institution.primary_color
				details['secondary_color'] = institution.secondary_color
				details['accent_color'] = institution.accent_color

				if gateway_profile.access_level.name == 'SYSTEM':
					details['theme'] = institution.theme.name
				else:
					details['theme'] = gateway.theme.name

			else:
				details['logo'] =gateway.logo.name
				details['name'] =gateway.name
				details['tagline'] =gateway.description
				details['background_image'] =gateway.background_image
				details['host'] =gateway.default_host.all()[0].host
				details['default_color'] = gateway.default_color
				details['primary_color'] = gateway.primary_color
				details['secondary_color'] = gateway.secondary_color
				details['accent_color'] = gateway.accent_color
				details['theme'] = gateway.theme.name


			payload.update(details)
			payload['response'] = details
			payload['response_status'] = '00'
			lgr.info('\n\n\n\t#####Host: %s' % gateway_profile)
			#payload['trigger_state'] = True		
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Host Details: %s" % e)

		return payload

	def create_user_profile(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			host = Host.objects.get(host=payload['gateway_host'], status__name='ENABLED')

			profile_error = None
			existing_gateway_profile, payload, profile_error = self.profile_capture(gateway_profile, payload, profile_error)

			def create_gateway_profile_details(create_gateway_profile, payload):
				if "msisdn" in payload.keys() and self.get_msisdn(payload):
					msisdn = self.get_msisdn(payload)
					try:msisdn = MSISDN.objects.get(phone_number=msisdn)
					except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();
					if create_gateway_profile.msisdn in [None,'']:
						create_gateway_profile.msisdn = msisdn

				if "access_level_id" in payload.keys() and create_gateway_profile.institution in [None,'']:
					access_level = AccessLevel.objects.get(id=payload["access_level_id"])
					if 'institution_id' in payload.keys():
						create_gateway_profile.institution = Institution.objects.get(id=payload['institution_id'])
					elif 'institution_id' not in payload.keys() and access_level.name not in ['CUSTOMER','SUPER ADMINISTRATOR'] and gateway_profile.institution:
						create_gateway_profile.institution = gateway_profile.institution 
				else:
					access_level = AccessLevel.objects.get(name="CUSTOMER")

				if create_gateway_profile.access_level in [None,''] or (create_gateway_profile.access_level not in \
				 [None,''] and create_gateway_profile.access_level.hierarchy>access_level.hierarchy):
					create_gateway_profile.access_level = access_level
				#if create_gateway_profile.created_by in [None,'']:create_gateway_profile.created_by = gateway_profile.user.profile 
				create_gateway_profile.save()
				payload["profile_id"] = create_gateway_profile.user.profile.id
				payload['response'] = 'User Profile Created'
				payload['response_status'] = '00'
				payload['session_gateway_profile_id'] = create_gateway_profile.id

				return payload

			if profile_error:
				payload['response'] = 'Profile Error: Email/Phone Number Exists in another profile. Please contact us'
				payload['response_status'] = '63'
				create_gateway_profile = None

			elif existing_gateway_profile.exists() and 'national_id' in payload.keys() and\
			 GatewayProfile.objects.filter(user__profile__national_id=payload['national_id'].strip(),\
			 gateway=gateway_profile.gateway).exists() and existing_gateway_profile[0].user.profile.national_id in [None,''] and\
			 GatewayProfile.objects.filter(user__profile__national_id=payload['national_id'].strip(),\
			 gateway=gateway_profile.gateway)[0].user <> existing_gateway_profile[0].user:
				#check update national_id profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile and to match user profiles.
				payload['response'] = 'Profile Error: National ID exists in another profile. Please contact us'
				payload['response_status'] = '63'

			elif existing_gateway_profile.exists() == False and 'national_id' in payload.keys() and\
			 GatewayProfile.objects.filter(user__profile__national_id=payload['national_id'].strip(),\
			 gateway=gateway_profile.gateway).exists():
				#check create national_id profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile.
				payload['response'] = 'Profile Error: National ID exists in another profile. Please contact us'
				payload['response_status'] = '63'

			elif existing_gateway_profile.exists():
				user = existing_gateway_profile[0].user

				user, payload = self.profile_update_if_null(user, payload)
				create_gateway_profile = existing_gateway_profile[0]

				payload = create_gateway_profile_details(create_gateway_profile, payload)

			else:
				def createUsername(original):
					u = User.objects.filter(username=original)
					if len(u)>0:
						chars = string.ascii_letters + string.digits
						rnd = random.SystemRandom()
						append_char = ''.join(rnd.choice(chars) for i in range(1,6))
						new_original = original+append_char
						return createUsername(new_original)
					else:
						return original.lower()


				username = ''

				if 'national_id' in payload.keys():
					username = createUsername(payload["national_id"])
				elif 'email' in payload.keys() and self.validateEmail(payload["email"]):
					username = createUsername(payload["email"].split('@')[0])
				elif 'msisdn' in payload.keys() and self.get_msisdn(payload):
					#username = '%s' % (time.time()*1000)
					username = '%s' % self.get_msisdn(payload)
					username = createUsername(username)

				payload['username'] = username
				username = username.lower()[:100]
				user = User.objects.create_user(username, '','')#username,email,password
				lgr.info("Created User: %s" % user)

				chars = string.ascii_letters + string.punctuation + string.digits
				rnd = random.SystemRandom()
				api_key = ''.join(rnd.choice(chars) for i in range(10))

				#Create co-ordinates if dont exist
				lng = payload['lng'] if 'lng' in payload.keys() else 0.0
				lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	                	trans_point = Point(float(lng), float(lat))

				profile_status = ProfileStatus.objects.get(name="REGISTERED")
				profile = Profile(api_key=api_key.encode('base64'),timezone=gateway_profile.user.profile.timezone,\
					language=gateway_profile.user.profile.language,geometry=trans_point,
					user=user)
				profile.status = profile_status

				user, payload = self.profile_update(user, payload)

				create_gateway_profile = GatewayProfile(user=user, gateway=gateway_profile.gateway, status=profile_status)

				payload = create_gateway_profile_details(create_gateway_profile, payload)

		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Creating User Profile: %s" % e)
		return payload

	def get_profile(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			profile_error = None
			session_gateway_profile, payload, profile_error = self.profile_capture(gateway_profile, payload, profile_error)

			if profile_error:
				payload['response'] = 'Profile Error: Email exists. Please contact us'
				payload['response_status'] = '63'

			elif session_gateway_profile.exists() and 'national_id' in payload.keys() and\
			 GatewayProfile.objects.filter(user__profile__national_id=payload['national_id'].strip(),\
			 gateway=gateway_profile.gateway).exists() and session_gateway_profile[0].user.profile.national_id in [None,''] and\
			 GatewayProfile.objects.filter(user__profile__national_id=payload['national_id'].strip(),\
			 gateway=gateway_profile.gateway)[0].user <> session_gateway_profile[0].user:
				#check update national_id profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile and to match user profiles.
				payload['response'] = 'Profile Error: National ID exists in another profile. Please contact us'
				payload['response_status'] = '63'

			elif session_gateway_profile.exists():
				payload['session_gateway_profile_id'] = session_gateway_profile[0].id
				user, payload = self.profile_update_if_null(session_gateway_profile[0].user, payload)

				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if 'first_name' in payload.keys()  else user.first_name
				payload['last_name'] = payload['last_name'] if 'last_name' in payload.keys()  else user.last_name

				payload['national_id'] = user.profile.national_id

				payload['response_status'] = '00'
				payload['response'] = 'Session Profile Captured'

			else:
				payload = self.create_user_profile(payload, node_info)
				if 'response_status' in payload.keys() and payload['response_status'] == '00':
					payload['response'] = 'Session Profile Captured'
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on getting session gateway Profile: %s" % e)
		return payload



	def get_update_profile(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			profile_error = None
			session_gateway_profile, payload, profile_error = self.profile_capture(gateway_profile, payload, profile_error)

			if profile_error:
				payload['response'] = 'Profile Error: Email exists. Please contact us'
				payload['response_status'] = '63'
			elif session_gateway_profile.exists():
				payload['session_gateway_profile_id'] = session_gateway_profile[0].id
				user, payload = self.profile_update(session_gateway_profile[0].user, payload)

				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if 'first_name' in payload.keys()  else user.first_name
				payload['last_name'] = payload['last_name'] if 'last_name' in payload.keys()  else user.last_name

				payload['national_id'] = user.profile.national_id

				payload['response_status'] = '00'
				payload['response'] = 'Session Profile Captured'

			else:
				payload = self.create_user_profile(payload, node_info)
				if 'response_status' in payload.keys() and payload['response_status'] == '00':
					payload['response'] = 'Session Profile Captured'
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on getting session gateway Profile: %s" % e)
		return payload


	def get_profile_deprecated(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			profile_error = None
			if ('email' in payload.keys() and self.validateEmail(payload["email"]) ) and \
			('msisdn' in payload.keys() and self.get_msisdn(payload)):

				msisdn_session_gateway_profile = GatewayProfile.objects.filter(Q(msisdn__phone_number=self.get_msisdn(payload)),Q(gateway=gateway_profile.gateway))
				email_session_gateway_profile = GatewayProfile.objects.filter(Q(user__email=payload["email"]),Q(gateway=gateway_profile.gateway))

				if msisdn_session_gateway_profile.exists() and email_session_gateway_profile.exists():
					if msisdn_session_gateway_profile[0] == email_session_gateway_profile[0]:
						session_gateway_profile = msisdn_session_gateway_profile
					else:
						profile_error = email_session_gateway_profile[0]
						session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)
				elif msisdn_session_gateway_profile.exists():
					session_gateway_profile = msisdn_session_gateway_profile
				elif email_session_gateway_profile.exists():
					session_gateway_profile = email_session_gateway_profile
				else:
					session_gateway_profile = msisdn_session_gateway_profile


			elif 'email' in payload.keys() and self.validateEmail(payload["email"]):
				session_gateway_profile = GatewayProfile.objects.filter(user__email=payload["email"],\
						 gateway=gateway_profile.gateway)
			elif 'msisdn' in payload.keys() and self.get_msisdn(payload):
				session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=self.get_msisdn(payload),\
						 gateway=gateway_profile.gateway)
			elif 'session_gateway_profile_id' in payload.keys():
				session_gateway_profile = GatewayProfile.objects.filter(id=payload['session_gateway_profile_id'])
			elif 'reference' in payload.keys():
				if 'reference' in payload.keys() and self.validateEmail(payload["reference"]):
					session_gateway_profile = GatewayProfile.objects.filter(user__email=payload["reference"],\
							 gateway=gateway_profile.gateway)
				else:
					payload['msisdn'] = payload['reference']
					msisdn = self.get_msisdn(payload)
					if msisdn:
						session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=msisdn,\
								 gateway=gateway_profile.gateway)
					else:
						del payload['msisdn']
						session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)
			else:
				session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)

			'''
			elif session_gateway_profile.exists() and session_gateway_profile[0].access_level.name == 'SYSTEM':
				payload['response'] = 'System User Not Allowed'
				payload['response_status'] = '63'
			'''

			if profile_error:
				payload['response'] = 'Profile Error: Email exists. Please contact us'
				payload['response_status'] = '63'
			elif session_gateway_profile.exists():
				payload['session_gateway_profile_id'] = session_gateway_profile[0].id
				user = session_gateway_profile[0].user

				if 'full_names' in payload.keys():
					full_names = payload["full_names"].split(" ")
					if len(full_names) == 1:
						payload['first_name'] = full_names[0]
					if len(full_names) == 2:
						payload['first_name'],payload['last_name'] = full_names
					elif len(full_names) == 3:
						payload['first_name'],payload['middle_name'],payload['last_name'] = full_names

				if 'chid' in payload.keys() and int(payload["chid"]) in [4,5,11]: #Allow auto profile update on USSD/SMS/INTEGRATOR only
					if 'email' in payload.keys() and user.email in [None,""] and self.validateEmail(payload["email"]):user.email = payload["email"]
					if 'first_name' in payload.keys() and user.first_name in [None,""]: user.first_name = payload['first_name']
					if 'last_name' in payload.keys() and user.last_name in [None,""]: user.last_name = payload['last_name']
					user.save()

					profile = Profile.objects.get(user=user) #User is a OneToOne field
					if 'middle_name' in payload.keys() and profile.middle_name in [None,""]: profile.middle_name = payload['middle_name']
					if 'national_id' in payload.keys() and profile.national_id in [None,""]: profile.national_id = payload['national_id']
					if 'physical_address' in payload.keys() and profile.physical_address in [None,""]: profile.physical_address = payload['physical_address']
					if 'city' in payload.keys() and profile.city in [None,""]: profile.city = payload['city']
					if 'region' in payload.keys() and profile.region in [None,""]: profile.region = payload['region']
					if 'postal_code' in payload.keys() and profile.postal_code in [None,""]: profile.postal_code = payload['postal_code']
					if 'country' in payload.keys() and profile.country in [None,""]: profile.country = Country.objects.get(iso2=payload['country'])
					if 'address' in payload.keys() and profile.address in [None,""]: profile.address = payload['address']
					if 'gender' in payload.keys() and profile.gender in [None,""]:
						try: gender = Gender.objects.get(code=payload['gender']); profile.gender = gender
						except Exception, e: lgr.info('Error on Gender: %s' % e)
					if 'dob' in payload.keys() and profile.dob in [None,""]: 
						try: profile.dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()
						except Exception, e: lgr.info('Error on DOB: %s' % e)


					profile.save()


				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if 'first_name' in payload.keys() and payload['first_name'] not in ['',None] else user.first_name
				payload['last_name'] = payload['last_name'] if 'last_name' in payload.keys() and payload['last_name'] not in ['',None] else user.last_name

				profile = Profile.objects.get(user=user) #User is a OneToOne field
				payload['national_id'] = profile.national_id

				payload['response_status'] = '00'
				payload['response'] = 'Session Profile Captured'

			else:
				payload = self.create_user_profile(payload, node_info)
				if 'response_status' in payload.keys() and payload['response_status'] == '00':
					payload['response'] = 'Session Profile Captured'
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on getting session gateway Profile: %s" % e)
		return payload

	def login(self, payload, node_info):
		try:
                        details = {}
                        #Check if LOGIN or SIGN UP
			authorized_gateway_profile = None
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if ('username' in payload.keys() or ('email' in payload.keys() and self.validateEmail(payload['email']))) and 'password' in payload.keys():
				lgr.info("Returning User")
				#CHECK CREDENTIALS and 
				if 'email' in payload.keys() and self.validateEmail(payload['email']):
					lgr.info('Login with Valid Email')
					gateway_login_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,user__email__iexact=payload['email'].strip())

				elif 'username' in payload.keys() and self.validateEmail(payload['username']):
					lgr.info('Login with Username as Valid Email')
					gateway_login_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,user__email__iexact=payload['username'].strip())
				elif 'username' in payload.keys():
					lgr.info('Login with Username')
					gateway_login_profile = GatewayProfile.objects.filter(Q(gateway=gateway_profile.gateway),Q(user__username__iexact=payload['username'].strip())|\
								Q(user__email__iexact=payload['username'].strip()))
				else:
					lgr.info('Login Details not found')
					gateway_login_profile = GatewayProfile.objects.none()

				for p in gateway_login_profile: #Loop through all profils matching username
					if p.user.is_active and p.user.check_password(payload['password']):
						authorized_gateway_profile = p
						break

			elif 'sec' in payload.keys() and 'gpid' in payload.keys():
				session_id = base64.urlsafe_b64decode(payload['sec'])
				lgr.info('Session Got: %s' % session_id.decode('hex'))
				session = Session.objects.filter(session_id=session_id.decode('hex'),gateway_profile__id=payload['gpid'],\
						gateway_profile__gateway=gateway_profile.gateway,\
						date_created__gte=timezone.localtime(timezone.now())-timezone.timedelta(hours=12))
				lgr.info('Fectch Existing session: %s' % session)
				if session.exists():
					authorized_gateway_profile = session[0].gateway_profile
					#payload['trigger'] = "SET PASSWORD"

			elif 'msisdn' in payload.keys() and 'fingerprint' in payload.keys() and 'pin' in payload.keys():

				msisdn = self.get_msisdn(payload)
				lgr.info('MSISDN: %s' % msisdn)
				if msisdn is not None:
					gateway_profile_list = GatewayProfile.objects.filter(msisdn__phone_number=msisdn, \
							gateway=gateway_profile.gateway, device_id = payload['fingerprint'])

					if gateway_profile_list.exists():
						session_gateway_profile = gateway_profile_list[0]
						hash_pin = crypt.crypt(str(payload['pin']), str(session_gateway_profile.id))
						if hash_pin == session_gateway_profile.pin:
							session_gateway_profile.pin_retries = 0
							session_gateway_profile.save()
							authorized_gateway_profile = session_gateway_profile

						else:
							if session_gateway_profile.pin_retries >= 3:
								session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
							session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
							session_gateway_profile.save()


			if authorized_gateway_profile is not None and authorized_gateway_profile.status.name in ['ACTIVATED','ONE TIME PIN','ONE TIME PASSWORD']:
				details['api_key'] = authorized_gateway_profile.user.profile.api_key
				details['status'] = authorized_gateway_profile.status.name
				details['access_level'] = authorized_gateway_profile.access_level.name

				payload['response'] = details
				payload['session_gateway_profile_id'] = authorized_gateway_profile.id #Authenticating Gateway Profile id replace not to clash with parent service
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Login: %s" % e)
		return payload

class Trade(System):
	pass

class Payments(System):
	pass


#from celery.utils.log import get_task_logger
#lgr = get_task_logger(__name__)
#Celery Tasks Here
