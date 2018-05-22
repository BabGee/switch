from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task


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

from django.db import transaction
from primary.core.bridge.models import *

import logging
lgr = logging.getLogger('primary.core.upc')

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



	def profile_state(self, session_gateway_profile, payload, profile_error):

		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		if profile_error:
			#payload['response'] = 'Profile Error: Email exists. Please contact us'
			payload['response'] = 'Profile Error: Email/Phone Number Exists in another profile. Please contact us'
			payload['response_status'] = '63'
			profile_error = True
		elif session_gateway_profile.exists() and 'national_id' in payload.keys() and\
		 GatewayProfile.objects.filter(user__profile__national_id__iexact=payload['national_id'].replace(' ','').strip(),\
		 gateway=gateway_profile.gateway).exists() and\
		 GatewayProfile.objects.filter(user__profile__national_id__iexact=payload['national_id'].replace(' ','').strip(),\
		 gateway=gateway_profile.gateway)[0].user <> session_gateway_profile[0].user:
			#check update national_id profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile and to match user profiles.
			payload['response'] = 'Profile Error: National ID exists in another profile. Please contact us'
			payload['response_status'] = '63'
			profile_error = True
		elif session_gateway_profile.exists() == False and 'national_id' in payload.keys() and\
		 GatewayProfile.objects.filter(user__profile__national_id__iexact=payload['national_id'].strip(),\
		 gateway=gateway_profile.gateway).exists():
			#check create national_id profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile.
			payload['response'] = 'Profile Error: National ID exists in another profile. Please contact us'
			payload['response_status'] = '63'
			profile_error = True
		elif session_gateway_profile.exists() and 'passport_number' in payload.keys() and\
		 GatewayProfile.objects.filter(user__profile__passport_number__iexact=payload['passport_number'].replace(' ','').strip(),\
		 gateway=gateway_profile.gateway).exists() and\
		 GatewayProfile.objects.filter(user__profile__passport_number__iexact=payload['passport_number'].replace(' ','').strip(),\
		 gateway=gateway_profile.gateway)[0].user <> session_gateway_profile[0].user:
			#check update passport_number profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile and to match user profiles.
			payload['response'] = 'Profile Error: Passport Number exists in another profile. Please contact us'
			payload['response_status'] = '63'
			profile_error = True
		elif session_gateway_profile.exists() == False and 'passport_number' in payload.keys() and\
		 GatewayProfile.objects.filter(user__profile__passport_number__iexact=payload['passport_number'].replace(' ','').strip(),\
		 gateway=gateway_profile.gateway).exists():
			#check create passport_number profile is unique, else,fail. Additional gateway profiles to be added using existing gateway profile.
			payload['response'] = 'Profile Error: Passport Number exists in another profile. Please contact us'
			payload['response_status'] = '63'
			profile_error = True

		return session_gateway_profile, payload, profile_error

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
			if 'national_id' in payload.keys() and profile.national_id in [None,""]: profile.national_id = payload['national_id'].replace(' ','').strip()
			if 'passport_number' in payload.keys() and profile.passport_number in [None,""]: 
				profile.passport_number = payload['passport_number'].replace(' ','').strip()
				if 'passport_expiry_date' in payload.keys() and profile.passport_expiry_date in [None,""]: 
					try: profile.passport_expiry_date = datetime.strptime(payload['passport_expiry_date'], '%Y-%m-%d').date()
					except Exception, e: lgr.info('Error on Passport Expiry Date: %s' % e)

			if 'tax_pin' in payload.keys() and profile.tax_pin in [None,""]: profile.tax_pin = payload['tax_pin']
			if 'physical_address' in payload.keys() and profile.physical_address in [None,""]: profile.physical_address = payload['physical_address']
			if 'city' in payload.keys() and profile.city in [None,""]: profile.city = payload['city']
			if 'region' in payload.keys() and profile.region in [None,""]: profile.region = payload['region']
			if 'postal_address' in payload.keys() and profile.postal_address in [None,""]: 
				postal_address = payload['postal_address']
				postal_address_list = str(postal_address).split('-')
				if len(postal_address_list)>1 and 'postal_code' not in payload.keys():
					profile.postal_address = postal_address_list[0]
					payload['postal_code'] = postal_address_list[1]
				else:
					profile.postal_address = postal_address

			if 'postal_code' in payload.keys() and profile.postal_code in [None,""]: profile.postal_code = payload['postal_code']
			if 'country' in payload.keys() and profile.country in [None,""]: profile.country = Country.objects.get(iso2=payload['country'])
			if 'address' in payload.keys() and profile.address in [None,""]: profile.address = payload['address']
			if 'gender' in payload.keys() and profile.gender in [None,""]:
				try: gender = Gender.objects.get(code=payload['gender']); profile.gender = gender
				except Exception, e: lgr.info('Error on Gender: %s' % e)
			if 'dob' in payload.keys() and profile.dob in [None,""]: 
				try: profile.dob = datetime.strptime(payload['dob'], '%Y-%m-%d').date()
				except Exception, e: lgr.info('Error on DOB: %s' % e)

			profile.save()

		return user, payload


	def profile_update(self, user, payload):
		if 'full_names' in payload.keys():
			full_names = payload["full_names"].strip().split(" ")
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
		if 'national_id' in payload.keys(): profile.national_id = payload['national_id'].replace(' ','').strip()
		if 'passport_number' in payload.keys(): 
			profile.passport_number = payload['passport_number'].replace(' ','').strip()
			if 'passport_expiry_date' in payload.keys():
				try: profile.passport_expiry_date = datetime.strptime(payload['passport_expiry_date'], '%Y-%m-%d').date()
				except Exception, e: lgr.info('Error on Passport Expiry Date: %s' % e)

		if 'tax_pin' in payload.keys(): profile.tax_pin = payload['tax_pin']
		if 'physical_address' in payload.keys(): profile.physical_address = payload['physical_address']
		if 'city' in payload.keys(): profile.city = payload['city']
		if 'region' in payload.keys(): profile.region = payload['region']
		if 'postal_address' in payload.keys():
			postal_address = payload['postal_address']
			postal_address_list = str(postal_address).split('-')
			if len(postal_address_list)>1 and 'postal_code' not in payload.keys():
				profile.postal_address = postal_address_list[0]
				profile.postal_code = postal_address_list[1]
			else:
				profile.postal_address = postal_address
				profile.postal_code =  None

		if 'postal_code' in payload.keys(): profile.postal_code = payload['postal_code']
		if 'country' in payload.keys(): profile.country = Country.objects.get(iso2=payload['country'])
		if 'address' in payload.keys(): profile.address = payload['address']
		if 'gender' in payload.keys():
			try: gender = Gender.objects.get(code=payload['gender']); profile.gender = gender
			except Exception, e: lgr.info('Error on Gender: %s' % e)
		if 'dob' in payload.keys():
			try: profile.dob = datetime.strptime(payload['dob'], '%Y-%m-%d').date()
			except Exception, e: lgr.info('Error on DOB: %s' % e)

		if 'photo' in payload.keys():
			try:
				filename = payload['photo']
				fromdir_name = settings.MEDIA_ROOT + '/tmp/uploads/'
				from_file = fromdir_name + str(filename)
				with open(from_file, 'r') as f:
					myfile = File(f)
					profile.photo.save(filename, myfile, save=False)
			except Exception, e:
				lgr.info('Error on saving Profile Image: %s' % e)

		profile.save()

		return user, payload



	def profile_capture(self, gateway_profile, payload, profile_error):
		lgr.info('Profile Capture')
		if ('email' in payload.keys() and self.validateEmail(payload["email"]) ) and \
		('msisdn' in payload.keys() and self.get_msisdn(payload)):
			msisdn_session_gateway_profile = GatewayProfile.objects.filter(Q(msisdn__phone_number=self.get_msisdn(payload)),Q(gateway=gateway_profile.gateway))
			email_session_gateway_profile = GatewayProfile.objects.filter(Q(user__email__iexact=payload["email"]),Q(gateway=gateway_profile.gateway))

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
			session_gateway_profile = GatewayProfile.objects.filter(user__email__iexact=payload["email"],\
					 gateway=gateway_profile.gateway)
		elif 'msisdn' in payload.keys() and self.get_msisdn(payload):
			session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=self.get_msisdn(payload),\
					 gateway=gateway_profile.gateway)
		elif 'session_gateway_profile_id' in payload.keys():
			session_gateway_profile = GatewayProfile.objects.filter(id=payload['session_gateway_profile_id'])
		elif 'national_id' in payload.keys() and payload['national_id'] not in ["",None,"None"]:
			session_gateway_profile = GatewayProfile.objects.filter(user__profile__national_id__iexact=payload['national_id'].replace(' ','').strip(),\
					 gateway=gateway_profile.gateway)
		elif 'passport_number' in payload.keys() and payload['passport_number'] not in ["",None,"None"]:
			session_gateway_profile = GatewayProfile.objects.filter(user__profile__passport_number__iexact=payload['passport_number'].replace(' ','').strip(),\
					 gateway=gateway_profile.gateway)
		elif 'reference' in payload.keys() and (self.validateEmail(payload['reference']) or self.simple_get_msisdn(payload['reference'], payload)):
			if self.validateEmail(payload["reference"]):
				session_gateway_profile = GatewayProfile.objects.filter(user__email__iexact=payload["reference"],\
						 gateway=gateway_profile.gateway)
			else:
				msisdn = self.simple_get_msisdn(payload['reference'], payload)
				if msisdn:
					session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=msisdn,\
							 gateway=gateway_profile.gateway)
					payload['msisdn'] = msisdn
				else:
					session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)

		elif 'email_msisdn' in payload.keys() and  self.validateEmail(payload['email_msisdn'].strip()):
			session_gateway_profile = GatewayProfile.objects.filter(user__email__iexact=payload['email_msisdn'].strip(), gateway=gateway_profile.gateway)
		elif  'email_msisdn' in payload.keys() and  self.simple_get_msisdn(payload['email_msisdn'].strip(), payload):
			session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=self.simple_get_msisdn(payload['email_msisdn'].strip(), payload), gateway=gateway_profile.gateway)
		elif  'email_msisdn' in payload.keys() and  GatewayProfile.objects.filter(gateway=gateway_profile.gateway, user__username__iexact=payload['email_msisdn'].strip()).exists():
			session_gateway_profile = GatewayProfile.objects.filter(user__username__iexact=payload['email_msisdn'].strip(), gateway=gateway_profile.gateway)
		else:
			session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)

		return session_gateway_profile, payload, profile_error

	def simple_kra_pin(self, kra_pin):
		kra_pin = str(kra_pin).replace(' ','').strip()
		try: kra_pin = int(kra_pin)
		except: pass

		if re.search(r"([a-zA-Z]{1})(\d{9})([a-zA-Z]{1}$)", str(kra_pin)):
			kra_pin = str(kra_pin)
		else:
			kra_pin = None
		lgr.info('Simple KRA Pin: %s' % kra_pin)
		return kra_pin


	def simple_id_passport(self, id_passport):
		id_passport = str(id_passport).replace(' ','').strip()
		try: id_passport = int(id_passport)
		except: pass

		if isinstance(id_passport, int) and len(str(id_passport)) >=6 and len(str(id_passport))<=10:
			id_passport = str(id_passport)
		elif re.search(r"([a-zA-Z]{1})(\d{7}$)", str(id_passport)):
			id_passport = str(id_passport)
		else:
			id_passport = None
		lgr.info('Simple ID/Passport: %s' % id_passport)
		return id_passport


	def simple_get_msisdn(self, msisdn, payload={}):
		lng = payload['lng'] if 'lng' in payload.keys() else 0.0
		lat = payload['lat'] if 'lat' in payload.keys() else 0.0
               	trans_point = Point(float(lng), float(lat))
		g = GeoIP()

		msisdn = str(msisdn)
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
	def login_verification(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			email_msisdn = payload['email_msisdn'].strip()
			def device_verification(gateway_profile, payload):
				gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile=gateway_profile, \
						gateway_profile__gateway=gateway_profile.gateway, activation_device_id = payload['fingerprint'],\
						channel__id=payload['chid'])

				if gateway_profile_device_list.exists():
					session_gateway_profile_device = gateway_profile_device_list[0]
					salt = str(session_gateway_profile_device.gateway_profile.id)
					salt = '0%s' % salt if len(salt) < 2 else salt
					hash_pin = crypt.crypt(str(payload['one_time_code']), salt)
					if hash_pin == session_gateway_profile_device.activation_code:
						session_gateway_profile_device.device_id = payload['fingerprint']
						session_gateway_profile_device.save()
						payload['response'] = 'Device Verified'
						payload['response_status'] = '00'
					else:
						payload['response_status'] = '55'
				else:
					payload['response'] = 'Device Not Found'
					payload['response_status'] = '25'

				return payload

			lgr.info('GatewayProfile: %s' % gateway_profile)
			if self.validateEmail(email_msisdn):
				lgr.info('With Email')
				validate_gateway_profile = GatewayProfile.objects.get(user__email__iexact=email_msisdn, gateway=gateway_profile.gateway)
				payload = device_verification(validate_gateway_profile, payload)

			elif self.simple_get_msisdn(email_msisdn, payload):
				lgr.info('With MSISDN')
				validate_gateway_profile = GatewayProfile.objects.get(msisdn__phone_number=self.simple_get_msisdn(email_msisdn, payload), gateway=gateway_profile.gateway)
				payload = device_verification(validate_gateway_profile, payload)

			elif GatewayProfile.objects.filter(gateway=gateway_profile.gateway, user__username__iexact=email_msisdn).exists():
				lgr.info('With Username')

				lgr.info('GatewayProfile: %s' % gateway_profile)
				validate_gateway_profile = GatewayProfile.objects.get(user__username__iexact=email_msisdn, gateway=gateway_profile.gateway)
				payload = device_verification(validate_gateway_profile, payload)

			else:
				payload['response'] = 'MSISDN or Email Not Found'
				payload['response_status'] = '25'


		except GatewayProfile.DoesNotExist:
			payload['response'] = 'Profile Not Found'
			payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on device verification: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def login_activation(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			email_msisdn = payload['email_msisdn'].strip()
			def device_activation(gateway_profile, payload):
				gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile=gateway_profile, \
						gateway_profile__gateway=gateway_profile.gateway, channel__id=payload['chid'])

				if gateway_profile_device_list.exists():
					session_gateway_profile_device = gateway_profile_device_list[0]

					chars = string.digits
					rnd = random.SystemRandom()
					pin = ''.join(rnd.choice(chars) for i in range(0,4))
					salt = str(session_gateway_profile_device.gateway_profile.id)
					salt = '0%s' % salt if len(salt) < 2 else salt

					hash_pin = crypt.crypt(str(pin), salt)

					session_gateway_profile_device.activation_code = hash_pin
					session_gateway_profile_device.activation_device_id = payload['fingerprint']

					session_gateway_profile_device.save()

					payload['activation_code'] = pin

					payload['response'] = 'Device Activation Request'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'Device Not Found'
					payload['response_status'] = '25'

				return payload

			lgr.info('GatewayProfile: %s' % gateway_profile)
			if self.validateEmail(email_msisdn):
				lgr.info('With Email')
				validate_gateway_profile = GatewayProfile.objects.get(user__email__iexact=email_msisdn, gateway=gateway_profile.gateway)
				payload = device_activation(validate_gateway_profile, payload)

			elif self.simple_get_msisdn(email_msisdn, payload):
				lgr.info('With MSISDN')
				validate_gateway_profile = GatewayProfile.objects.get(msisdn__phone_number=self.simple_get_msisdn(email_msisdn, payload), gateway=gateway_profile.gateway)
				payload = device_activation(validate_gateway_profile, payload)

			elif GatewayProfile.objects.filter(gateway=gateway_profile.gateway, user__username__iexact=email_msisdn).exists():
				lgr.info('With Username')

				lgr.info('GatewayProfile: %s' % gateway_profile)
				validate_gateway_profile = GatewayProfile.objects.get(user__username__iexact=email_msisdn, gateway=gateway_profile.gateway)
				payload = device_activation(validate_gateway_profile, payload)

			else:
				payload['response'] = 'MSISDN or Email Not Found'
				payload['response_status'] = '25'

		except GatewayProfile.DoesNotExist:
			payload['response'] = 'Profile Not Found'
			payload['response_status'] = '25'


		except Exception, e:
			lgr.info('Error on device activation: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def login_validation(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			email_msisdn = payload['email_msisdn'].strip()
			lgr.info('GatewayProfile: %s' % gateway_profile)
			def device_validation(gateway_profile, payload):
				gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile=gateway_profile, \
						gateway_profile__gateway=gateway_profile.gateway, channel__id=payload['chid'])

				gateway_profile_device = gateway_profile_device_list.filter(device_id=payload['fingerprint'])

				if gateway_profile_device_list.exists() and gateway_profile_device.exists():
					profile_status = gateway_profile_device[0].gateway_profile.status.name.lower().replace(' ','_')
					if gateway_profile_device[0].gateway_profile.access_level.name == 'CUSTOMER':
						payload['trigger'] = 'customer,device_valid,%s%s' % (profile_status, ','+payload['trigger'] if 'trigger' in payload.keys() else '')
					else:
						payload['trigger'] = 'device_valid,%s%s' % (profile_status, ','+payload['trigger'] if 'trigger' in payload.keys() else '')
					lgr.info('Profile Status - Trigger: %s' % payload['trigger'])
					payload['response'] = 'Device Validation device_valid'
					payload['response_status'] = '00'
				elif gateway_profile_device_list.exists():
					payload['trigger'] = 'device_not_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					payload['response'] = 'Device Validation device_not_valid'
					payload['response_status'] = '00'
				else:
					payload['trigger'] = 'device_not_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					gateway_profile_device = GatewayProfileDevice(channel=Channel.objects.get(id=payload['chid']),\
											gateway_profile=gateway_profile)
					gateway_profile_device.save()
					payload['response'] = 'Device Validation device_not_valid new device'
					payload['response_status'] = '00'

				return payload

			lgr.info('GatewayProfile: %s' % gateway_profile)
			if self.validateEmail(email_msisdn):
				lgr.info('With Email')
				validate_gateway_profile = GatewayProfile.objects.get(user__email__iexact=email_msisdn, gateway=gateway_profile.gateway)
				payload = device_validation(validate_gateway_profile, payload)

			elif self.simple_get_msisdn(email_msisdn, payload):
				lgr.info('With MSISDN')
				validate_gateway_profile = GatewayProfile.objects.get(msisdn__phone_number=self.simple_get_msisdn(email_msisdn, payload), gateway=gateway_profile.gateway)
				payload = device_validation(validate_gateway_profile, payload)

			elif GatewayProfile.objects.filter(gateway=gateway_profile.gateway, user__username__iexact=email_msisdn).exists():
				lgr.info('With Username')

				lgr.info('GatewayProfile: %s' % gateway_profile)
				validate_gateway_profile = GatewayProfile.objects.get(user__username__iexact=email_msisdn, gateway=gateway_profile.gateway)
				payload = device_validation(validate_gateway_profile, payload)

			else:
				payload['response'] = 'MSISDN or Email Not Found'
				payload['response_status'] = '25'

		except GatewayProfile.DoesNotExist:
			payload['response'] = 'Profile Not Found'
			payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on validating device: %s' % e)
			payload['response_status'] = '96'
		return payload


	def profile_contact_check(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			if session_gateway_profile.user.email and session_gateway_profile.msisdn:
				lgr.info('With Email and MSISDN')
				payload['trigger'] = 'with_email,with_msisdn%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['response'] = 'Email & MSISDN Captured'
				payload['response_status'] = '00'
			elif session_gateway_profile.user.email:
				lgr.info('With Email')
				payload['trigger'] = 'with_email%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['response'] = 'Email Captured'
				payload['response_status'] = '00'
			elif session_gateway_profile.msisdn:
				lgr.info('With MSISDN')
				payload['trigger'] = 'with_msisdn%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['response'] = 'MSISDN Captured'
				payload['response_status'] = '00'
			else:
				payload['response'] = 'MSISDN or Email Not Found'
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on profile contact check: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload



	def contact_check(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if 'email' in payload.keys() and self.validateEmail(payload["email"]) and 'msisdn' in payload.keys() and self.get_msisdn(payload):
				lgr.info('With Email and MSISDN')
				payload['trigger'] = 'with_email,with_msisdn%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['response'] = 'Email & MSISDN Captured'
				payload['response_status'] = '00'
			elif 'email' in payload.keys() and self.validateEmail(payload["email"]):
				lgr.info('With Email')
				payload['trigger'] = 'with_email%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['response'] = 'Email Captured'
				payload['response_status'] = '00'
			elif 'msisdn' in payload.keys() and self.get_msisdn(payload):
				lgr.info('With MSISDN')
				payload['trigger'] = 'with_msisdn%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

				payload['response'] = 'MSISDN Captured'
				payload['response_status'] = '00'
			else:
				payload['response'] = 'MSISDN or Email Not Found'
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on contact check: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


	def capture_identity_document(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			document_number = str(payload['document_number']).replace(' ','').strip() if 'document_number' in payload.keys() else None

			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id']) if 'session_gateway_profile_id' in payload.keys() else None

			try: document_number = int(document_number)
			except: pass

			if isinstance(document_number, int) and len(str(document_number)) >=6 and len(str(document_number))<=10:
				payload['national_id'] = str(document_number)
				payload['trigger'] = 'national_id%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'National ID Captured'
				payload['response_status'] = '00'
			elif re.search(r"([a-zA-Z]{1})(\d{7}$)", str(document_number)):
				payload['passport_number'] = str(document_number)
				payload['trigger'] = 'passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Passport Number Captured'
				payload['response_status'] = '00'
			elif 'national_id' in payload.keys()  and len(str(payload['national_id'])) >=6 and len(str(payload['national_id']))<=10:
				payload['trigger'] = 'national_id%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'National ID Captured'
				payload['response_status'] = '00'
			elif 'passport_number' in payload.keys() and re.search(r"([a-zA-Z]{1})(\d{7}$)", str(payload['passport_number'])):
				payload['trigger'] = 'passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Passport Number Captured'
				payload['response_status'] = '00'
			elif 'national_id' in payload.keys()  and len(str(payload['national_id'])) >=6 and len(str(payload['national_id']))<=10 and \
			'passport_number' in payload.keys() and re.search(r"([a-zA-Z]{1})(\d{7}$)", str(payload['passport_number'])):
				payload['trigger'] = 'national_id,passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'ID & Passport Number Captured'
				payload['response_status'] = '00'
			elif session_gateway_profile and session_gateway_profile.user.profile.national_id:
				payload['national_id'] = str(session_gateway_profile.user.profile.national_id)
				payload['trigger'] = 'national_id%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'National ID Captured'
				payload['response_status'] = '00'
			elif session_gateway_profile and session_gateway_profile.user.profile.passport_number:
				payload['passport_number'] = str(session_gateway_profile.user.profile.passport_number)
				payload['trigger'] = 'passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Passport Number Captured'
				payload['response_status'] = '00'
			elif gateway_profile and gateway_profile.user.profile.national_id:
				payload['national_id'] = str(gateway_profile.user.profile.national_id)
				payload['trigger'] = 'national_id%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'National ID Captured'
				payload['response_status'] = '00'
			elif gateway_profile and gateway_profile.user.profile.passport_number:
				payload['passport_number'] = str(gateway_profile.user.profile.passport_number)
				payload['trigger'] = 'passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Passport Number Captured'
				payload['response_status'] = '00'
			elif gateway_profile and gateway_profile.user.profile.national_id and gateway_profile.user.profile.passport_number:
				payload['national_id'] = str(gateway_profile.user.profile.national_id)
				payload['passport_number'] = str(gateway_profile.user.profile.passport_number)
				payload['trigger'] = 'national_id,passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'ID & Passport Number Captured'
				payload['response_status'] = '00'
			else:
				payload['response'] = 'Identity Document not found'
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on capture_identity_document: %s' % e)
			payload['response_status'] = '96'

		return payload


	def capture_identity_document_strict(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			document_number = str(payload['document_number']).replace(' ','').strip() if 'document_number' in payload.keys() else None

			try: document_number = int(document_number)
			except: pass

			if isinstance(document_number, int) and len(str(document_number)) >=6 and len(str(document_number))<=10:
				payload['national_id'] = str(document_number)
				payload['trigger'] = 'national_id%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'National ID Captured'
				payload['response_status'] = '00'
			elif re.search(r"([a-zA-Z]{1})(\d{7}$)", str(document_number)):
				payload['passport_number'] = str(document_number)
				payload['trigger'] = 'passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Passport Number Captured'
				payload['response_status'] = '00'
			elif 'national_id' in payload.keys()  and len(str(payload['national_id'])) >=6 and len(str(payload['national_id']))<=10:
				payload['trigger'] = 'national_id%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'National ID Captured'
				payload['response_status'] = '00'
			elif 'passport_number' in payload.keys() and re.search(r"([a-zA-Z]{1})(\d{7}$)", str(payload['passport_number'])):
				payload['trigger'] = 'passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Passport Number Captured'
				payload['response_status'] = '00'
			elif 'national_id' in payload.keys()  and len(str(payload['national_id'])) >=6 and len(str(payload['national_id']))<=10 and \
			'passport_number' in payload.keys() and re.search(r"([a-zA-Z]{1})(\d{7}$)", str(payload['passport_number'])):
				payload['trigger'] = 'national_id,passport_number%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'ID & Passport Number Captured'
				payload['response_status'] = '00'
			else:
				payload['response'] = 'Identity Document not found'
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on capture_identity_document strict: %s' % e)
			payload['response_status'] = '96'

		return payload


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
			if 'session_gateway_profile_id' in payload.keys():
				gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			user = gateway_profile.user
			profile = user.profile

			payload["email"] = user.email
			payload['first_name'] = user.first_name if user.first_name else ''
			payload['last_name'] = user.last_name if user.last_name else ''
			payload['middle_name'] = profile.middle_name if profile.middle_name else ''
			payload['national_id'] = profile.national_id
			payload['passport_number'] = profile.passport_number
			if profile.passport_expiry_date: payload['passport_expiry_date'] = profile.passport_expiry_date.isoformat()
			payload['physical_address'] = profile.physical_address
			payload['tax_pin'] = profile.tax_pin if profile.tax_pin else ''
			payload['city'] = profile.city
			payload['region'] = profile.region
			payload['postal_address'] = profile.postal_address
			payload['postal_code'] = profile.postal_code
			if profile.country:payload['country'] = profile.country.iso2
			payload['address'] = profile.address
			if gateway_profile.msisdn:payload['msisdn'] = gateway_profile.msisdn.phone_number
			if gateway_profile.role:payload['role_id'] = gateway_profile.role.pk

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
				gateway_profile_list = GatewayProfile.objects.filter(user__email__iexact=payload['email_msisdn'], gateway=gateway_profile.gateway)

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

				gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile__msisdn__phone_number=msisdn, \
						gateway_profile__gateway=gateway_profile.gateway, activation_device_id = payload['fingerprint'],\
						channel__id=payload['chid'])

				if gateway_profile_device_list.exists():
					session_gateway_profile_device = gateway_profile_device_list[0]
					salt = str(session_gateway_profile_device.gateway_profile.id)
					salt = '0%s' % salt if len(salt) < 2 else salt
					hash_pin = crypt.crypt(str(payload['one_time_code']), salt)
					if hash_pin == session_gateway_profile_device.activation_code:
						session_gateway_profile_device.device_id = payload['fingerprint']
						session_gateway_profile_device.save()
						payload['response'] = 'Device Verified'
						payload['response_status'] = '00'
					else:
						payload['response_status'] = '55'
				else:
					payload['response'] = 'Device Not Found'
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
				gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile__msisdn__phone_number=msisdn, \
						gateway_profile__gateway=gateway_profile.gateway, channel__id=payload['chid'])

				if gateway_profile_device_list.exists():
					session_gateway_profile_device = gateway_profile_device_list[0]

					chars = string.digits
					rnd = random.SystemRandom()
					pin = ''.join(rnd.choice(chars) for i in range(0,4))
					salt = str(session_gateway_profile_device.gateway_profile.id)
					salt = '0%s' % salt if len(salt) < 2 else salt

					hash_pin = crypt.crypt(str(pin), salt)

					session_gateway_profile_device.activation_code = hash_pin
					session_gateway_profile_device.activation_device_id = payload['fingerprint']

					session_gateway_profile_device.save()

					payload['activation_code'] = pin

					payload['response'] = 'Device Activation Request'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'Device Not Found'
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
				if gateway_profile_list.exists():
					gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile__msisdn__phone_number=msisdn, \
							gateway_profile__gateway=gateway_profile.gateway, channel__id=payload['chid'])

					gateway_profile_device = gateway_profile_device_list.filter(device_id=payload['fingerprint'])

					if gateway_profile_device_list.exists() and gateway_profile_device.exists() and gateway_profile_device[0].gateway_profile.status.name=='ONE TIME PIN':
						payload['trigger'] = 'one_time_pin%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload['response'] = 'Device Validation one_time_pin'
						payload['response_status'] = '00'
					elif gateway_profile_device_list.exists() and gateway_profile_device.exists():
						payload['trigger'] = 'device_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload['response'] = 'Device Validation device_valid'
						payload['response_status'] = '00'
					elif gateway_profile_device_list.exists():
						payload['trigger'] = 'device_not_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload['response'] = 'Device Validation device_not_valid'
						payload['response_status'] = '00'
					else:
						payload['trigger'] = 'device_not_valid%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
						gateway_profile_device = GatewayProfileDevice(channel=Channel.objects.get(id=payload['chid']),\
												gateway_profile=gateway_profile_list[0])
						gateway_profile_device.save()
						payload['response'] = 'Device Validation device_not_valid new device'
						payload['response_status'] = '00'
				else:
					payload['response'] = 'MSISDN Not Found'
					payload['response_status'] = '25'
			else:
				payload['response'] = 'MSISDN Not Found'
				payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on validating device: %s' % e)
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
						salt = str(gateway_profile.id)
						salt = '0%s' % salt if len(salt) < 2 else salt

						hash_pin = crypt.crypt(str(payload['verification_code']), salt)

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

				salt = str(gateway_profile.id)
				salt = '0%s' % salt if len(salt) < 2 else salt

				change_pin = crypt.crypt(str(pin), salt)
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
			if 'email' in payload.keys() and self.validateEmail(payload["email"].strip()):
				email = payload["email"].strip()
				existing_gateway_profile = GatewayProfile.objects.filter(Q(user__email__iexact=email), ~Q(id=session_gateway_profile.id),\
							Q(gateway=session_gateway_profile.gateway),Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS','ONE TIME PASSWORD']))
				if existing_gateway_profile.exists():
					payload['response'] = 'Profile With Email Already exists'
					payload['response_status'] = '26'
				else:
					session_gateway_profile.user.email = email
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


	def update_msisdn(self, payload, node_info):
		try:
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			if 'msisdn' in payload.keys() and self.get_msisdn(payload):
				msisdn = self.get_msisdn(payload)

				existing_gateway_profile = GatewayProfile.objects.filter(
					Q(msisdn__phone_number=msisdn),
					~Q(id=session_gateway_profile.id),
					Q(gateway=session_gateway_profile.gateway),
					Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS','ONE TIME PASSWORD'])
				)
				if existing_gateway_profile.exists():
					payload['response'] = 'Profile With Phone Number Already exists'
					payload['response_status'] = '26'
				else:
					session_gateway_profile.msisdn.phone_number = msisdn
					session_gateway_profile.msisdn.save()

					payload['response'] = 'Phone Number Updated'
					payload['response_status'] = '00'
			else:
				lgr.info('Invalid Phone Number:%s' % payload)
				payload['response'] = 'No Valid Phone Number Found'
				payload['response_status'] = '25'
		except Exception, e:
			lgr.info('Error on Update Profile Phone Number: %s' % e)
			payload['response_status'] = '96'
		return payload


	def set_profile_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			new_pin = payload['new_pin'] if 'new_pin' in payload.keys() else payload['pin']
			if new_pin == payload['confirm_pin']:

				salt = str(session_gateway_profile.id)
				salt = '0%s' % salt if len(salt) < 2 else salt

				hash_pin = crypt.crypt(str(new_pin), salt)
				session_gateway_profile.pin = hash_pin
				session_gateway_profile.save()
				payload['response'] = 'New PIN isSet'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '95'
				payload['response'] = 'Confirm PIN did not match New PIN'

		except Exception, e:
			lgr.info('Error on Set Profile Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def validate_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			salt = str(session_gateway_profile.id)
			salt = '0%s' % salt if len(salt) < 2 else salt

			hash_pin = crypt.crypt(str(payload['pin']), salt)

			if hash_pin == session_gateway_profile.pin:
				session_gateway_profile.pin_retries = 0
				session_gateway_profile.save()
				payload['response'] = 'Valid PIN'
				payload['response_status'] = '00'
			else:
				if session_gateway_profile.pin_retries >= gateway_profile.gateway.max_pin_retries:
					session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
				session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
				session_gateway_profile.save()
				payload['response_status'] = '55'
				payload['response'] = 'Invalid PIN'

		except Exception, e:
			lgr.info('Error on Validating Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def reset_profile_pushnotification(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			profile = session_gateway_profile.user.profile
			profile.pn = False
			profile.save()
			payload['response'] = 'Profile Push Notification Reset'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on Reset Profile Push Notification: %s' % e)
			payload['response_status'] = '96'
		return payload

	def set_profile_expired_passport(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='EXPIRED PASSPORT')
			session_gateway_profile.save()
			payload['response'] = 'Profile is on Expired Passport'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on set profile Expired Passport: %s' % e)
			payload['response_status'] = '96'
		return payload


	def set_profile_for_terms(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='FOR TERMS')
			session_gateway_profile.save()
			payload['response'] = 'Profile is on For Terms'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on set profile For Terms: %s' % e)
			payload['response_status'] = '96'
		return payload


	def set_profile_for_update(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='FOR UPDATE')
			session_gateway_profile.save()
			payload['response'] = 'Profile is on For Update'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on set profile For Update: %s' % e)
			payload['response_status'] = '96'
		return payload



	def set_profile_first_access(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='FIRST ACCESS')
			session_gateway_profile.save()
			payload['response'] = 'Profile is on First Access'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on set profile First Access: %s' % e)
			payload['response_status'] = '96'
		return payload



	def set_profile_pending(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='PENDING')
			session_gateway_profile.save()
			payload['response'] = 'Profile is Pending Activation'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on set profile pending: %s' % e)
			payload['response_status'] = '96'
		return payload


	def set_profile_deactivated(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='DEACTIVATED')
			session_gateway_profile.save()
			payload['response'] = 'Profile DeActivated'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on Validating One Time Pin: %s' % e)
			payload['response_status'] = '96'
		return payload



	def set_profile_activated(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			session_gateway_profile.status = ProfileStatus.objects.get(name='ACTIVATED')
			session_gateway_profile.save()
			payload['response'] = 'Profile Activated'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on Validating One Time Pin: %s' % e)
			payload['response_status'] = '96'
		return payload

	def update_profile_institution(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			if 'institution_id' in payload.keys():
				session_gateway_profile.institution = Institution.objects.get(id=payload['institution_id'])
				session_gateway_profile.save()

				payload['response'] = 'Profile Institution Updated'
				payload['response_status'] = '00'
			elif gateway_profile.institution:
				session_gateway_profile.institution = gateway_profile.institution
				session_gateway_profile.save()

				payload['response'] = 'Profile Institution Updated'
				payload['response_status'] = '00'

			else:
				payload['response'] = 'Institution not Submitted'
				payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on Updating Profile Institution: %s' % e)
			payload['response_status'] = '96'
		return payload



	def validate_one_time_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			salt = str(session_gateway_profile.id)
			salt = '0%s' % salt if len(salt) < 2 else salt

			hash_pin = crypt.crypt(str(payload['one_time_pin']), salt)

			if hash_pin == session_gateway_profile.pin:
				session_gateway_profile.pin_retries = 0
				session_gateway_profile.save()
				payload['response'] = 'Valid One Time PIN'
				payload['response_status'] = '00'
			else:
				if session_gateway_profile.pin_retries >= gateway_profile.gateway.max_pin_retries:
					session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
				session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
				session_gateway_profile.save()
				payload['response_status'] = '55'
				payload['response'] = 'Invalid One Time PIN'

		except Exception, e:
			lgr.info('Error on Validating One Time Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def validate_one_time_password(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			if gateway_profile.user.is_active and gateway_profile.user.check_password(payload['one_time_password']):
				payload['response'] = 'Password Verified'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'

		except Exception, e:
			lgr.info('Error on Validating One Time Pin: %s' % e)
			payload['response_status'] = '96'
		return payload

	def one_time_password(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			chars = string.ascii_letters + string.digits
			rnd = random.SystemRandom()
			password = ''.join(rnd.choice(chars) for i in range(8))

			session_gateway_profile.user.set_password(password)
			session_gateway_profile.user.save()
			session_gateway_profile.status = ProfileStatus.objects.get(name='ONE TIME PASSWORD')
			session_gateway_profile.save()

			payload['one_time_password'] = password
			payload['response'] = 'One Time Password Set'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on One Time Password: %s' % e)
			payload['response_status'] = '96'
		return payload


	def reset_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			chars = string.digits
			rnd = random.SystemRandom()
			pin = ''.join(rnd.choice(chars) for i in range(0,4))


			salt = str(session_gateway_profile.id)
			salt = '0%s' % salt if len(salt) < 2 else salt

			hash_pin = crypt.crypt(str(pin), salt)

			session_gateway_profile.pin = hash_pin
			session_gateway_profile.status = ProfileStatus.objects.get(name='RESET PIN')
			session_gateway_profile.save()

			payload['reset_pin'] = pin
			payload['response'] = 'Reset Pin'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on Reset Pin: %s' % e)
			payload['response_status'] = '96'
		return payload


	def one_time_pin(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			chars = string.digits
			rnd = random.SystemRandom()
			pin = ''.join(rnd.choice(chars) for i in range(0,4))


			salt = str(session_gateway_profile.id)
			salt = '0%s' % salt if len(salt) < 2 else salt

			hash_pin = crypt.crypt(str(pin), salt)

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
			confirm_password = payload['confirm_password']

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

			session_gateway_profile = GatewayProfile.objects.filter(Q(user__username=payload['username'])|Q(user__email__iexact=payload['username']),\
								Q(gateway=gateway_profile.gateway),Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS']))
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

	def create_institution(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			lgr.info('Gateway Profile : %s|%s' % (gateway_profile, payload))

			#logo, if exists
			#Create co-ordinates if dont exist
			# lng = payload['lng'] if 'lng' in payload.keys() else 0.0
			# lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	         #        trans_point = Point(float(lng), float(lat))

			institution = Institution()
			institution.name = payload['institution_name']


			def createBusinessNumber(original):
				i = Institution.objects.filter(business_number__iexact=original)
				if i.exists():
					chars = str(payload['institution_name'].replace(' ',''))
					rnd = random.SystemRandom()
					append_char = ''.join(rnd.choice(chars) for i in range(1,4))
					new_original = original+append_char
					return createBusinessNumber(new_original)
				else:
					return original.upper()


			institution.business_number = createBusinessNumber(str(payload['institution_name'].replace(' ','')[:4]))

			if 'institution_reg_number' in payload.keys(): institution.registration_number = payload['institution_reg_number']
			if 'institution_tax_pin' in payload.keys(): institution.tax_pin = payload['institution_tax_pin']

			if 'institution_address' in payload.keys(): institution.address = payload['institution_address']
			if 'institution_physical_address' in payload.keys(): institution.physical_address = payload['institution_physical_address']
			if 'institution_location' in payload.keys():
				coordinates = payload['institution_location']
				longitude,latitude = coordinates.split(',', 1)
				# institution.geometry = Point(x=longitude, y=latitude)
				trans_point = Point(float(longitude), float(latitude))

			if 'institution_description' in payload.keys(): institution.description = payload['institution_description']
			else: institution.description = payload['institution_name']

			if 'institution_status' in payload.keys(): institution.status = InstitutionStatus.objects.get(name=payload['institution_status'])
			else: institution.status = InstitutionStatus.objects.get(name='ACTIVE') 

			if 'institution_tagline' in payload.keys(): institution.tagline = payload['institution_tagline']
			else: institution.tagline=payload['institution_name']

			try:
				filename = payload['institution_logo']
				fromdir_name = settings.MEDIA_ROOT + '/tmp/uploads/'
				from_file = fromdir_name + str(filename)
				with open(from_file, 'r') as f:
					myfile = File(f)
					institution.logo.save(filename, myfile, save=False)
			except Exception, e:
				lgr.info('Error on saving Institution Logo: %s' % e)

		
			if 'institution_default_color' in payload.keys(): institution.default_color = payload['institution_default_color']
			else: institution.default_color = '#fff'
			if 'institution_country' in payload.keys(): institution.country = Country.objects.get(name=payload['institution_country'])
			else: institution.country = Country.objects.get(iso2='KE')
			if 'institution_theme' in payload.keys(): institution.theme = Theme.objects.get(name=payload['institution_theme'])
			else: institution.theme = Theme.objects.get(name='polymer2.0')
			institution.geometry = trans_point

			institution.save()

			if 'industry_class_id' in payload.keys():
				institution.industries.add(IndustryClass.objects.get(id=payload['industry_class_id']))

			institution.gateway.add(gateway_profile.gateway)
			institution.currency.add(Currency.objects.get(code=payload['institution_currency']))

			payload['institution_id'] = institution.id

			payload['response'] = 'Institution Created'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on Creating Institution: %s' % e)
			payload['response_status'] = '96'

		return payload


	def payload_exclude_institution(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			del payload['institution_id']

			payload['response'] = 'Institution Excluded from Payload'
			payload['response_status'] = '00'
		except Exception as e:
			lgr.info('Error on Deleting Institution: %s' % e)
			payload['response_status'] = '96'

		return payload


	def delete_institution(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			institution = Institution.objects.get(pk=payload['institution_id'])
			institution.status = InstitutionStatus.objects.get(name='DELETED')
			institution.save()

			payload['response'] = 'Institution Deleted'
			payload['response_status'] = '00'
		except Exception as e:
			lgr.info('Error on Deleting Institution: %s' % e)
			payload['response_status'] = '96'

		return payload


	def update_institution_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			institution = Institution.objects.get(pk=payload['institution_id'])
			institution.name = payload['institution_name']

			if 'institution_reg_number' in payload.keys(): institution.registration_number = payload['institution_reg_number']
			if 'institution_tax_pin' in payload.keys(): institution.tax_pin = payload['institution_tax_pin']

			if 'institution_address' in payload.keys(): institution.address = payload['institution_address']
			if 'institution_physical_address' in payload.keys(): institution.physical_address = payload['institution_physical_address']
			if 'institution_location' in payload.keys():
				coordinates = payload['institution_location']
				longitude,latitude = coordinates.split(',', 1)
				# institution.geometry = Point(x=longitude, y=latitude)
				trans_point = Point(float(longitude), float(latitude))

			if 'institution_description' in payload.keys(): institution.description = payload['institution_description']
			else: institution.description = payload['institution_name']

			if 'institution_tagline' in payload.keys(): institution.tagline = payload['institution_tagline']
			else: institution.tagline=payload['institution_name']

			try:
				filename = payload['institution_logo']
				fromdir_name = settings.MEDIA_ROOT + '/tmp/uploads/'
				from_file = fromdir_name + str(filename)
				with open(from_file, 'r') as f:
					myfile = File(f)
					institution.logo.save(filename, myfile, save=False)
			except Exception, e:
				lgr.info('Error on saving Institution Logo: %s' % e)

			if 'institution_default_color' in payload.keys(): institution.default_color = payload['institution_default_color']
			else: institution.default_color = '#fff'
			if 'institution_country' in payload.keys(): institution.country = Country.objects.get(name=payload['institution_country'])
			else: institution.country = Country.objects.get(iso2='KE')
			institution.geometry = trans_point

			institution.save()
			payload['response'] = 'Institution Updated'
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on Updating Institution: %s' % e)
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
				details['profile']['notification_channel'] = '{}/notifications/{}'.format(gateway.pk, gateway_profile.user.profile.pk)

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

	def get_institution_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			gateway = gateway_profile.gateway
			details = {}

			institution = None
			if 'institution_id' in payload.keys() and payload['institution_id'] not in ["",None,'None']:
				institution_list = Institution.objects.filter(status__name='ACTIVE',id=payload['institution_id']).prefetch_related('gateway')
				if len(institution_list)>0:
					institution = institution_list[0]
			elif gateway_profile.institution is not None:
				institution = gateway_profile.institution
			if institution is not None:
				details['institution_logo'] =institution.logo.name
				details['institution_name'] =institution.name
				details['institution_reg_number'] =institution.registration_number
				details['institution_tax_pin'] = institution.tax_pin
				details['institution_physical_address'] =institution.physical_address
				details['institution_tagline'] =institution.tagline
				details['institution_address'] =institution.address
				details['background_image'] = institution.background_image

				details['institution_default_color'] = institution.default_color
				details['institution_primary_color'] = institution.primary_color
				details['institution_secondary_color'] = institution.secondary_color
				details['institution_accent_color'] = institution.accent_color

				details['institution_location'] = institution.geometry

			payload.update(details)

			payload['response'] = 'Got Institution Details'
			payload['response_status'] = '00'
			# lgr.info('\n\n\n\t#####Host: %s' % gateway_profile)
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
			existing_gateway_profile, payload, profile_error = self.profile_state(existing_gateway_profile, payload, profile_error)

			if profile_error: pass
			elif existing_gateway_profile.exists():

				payload['response'] = 'Profile Error: Gateway Profile Exists'
				payload['response_status'] = '63'

			else:
				def createUsername(original):
					u = User.objects.filter(username__iexact=original)
					if u.exists():
						chars = string.ascii_letters + string.digits
						rnd = random.SystemRandom()
						append_char = ''.join(rnd.choice(chars) for i in range(1,6))
						new_original = original+append_char
						return createUsername(new_original)
					else:
						return original.lower()


				username = ''

				if 'national_id' in payload.keys():
					username = createUsername(payload["national_id"].replace(' ','').strip())
				elif 'passport_number' in payload.keys():
					username = createUsername(payload["passport_number"].replace(' ','').strip())
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
				elif "role_id" in payload.keys() and create_gateway_profile.institution in [None,'']:
					role = Role.objects.get(id=payload["role_id"])
					access_level = role.access_level
					create_gateway_profile.role = role
					if 'institution_id' in payload.keys():
						create_gateway_profile.institution = Institution.objects.get(id=payload['institution_id'])
					elif 'institution_id' not in payload.keys() and access_level.name not in ['CUSTOMER','SUPER ADMINISTRATOR'] and gateway_profile.institution:
						create_gateway_profile.institution = gateway_profile.institution 
				elif "access_level" in payload.keys() and create_gateway_profile.institution in [None,'']:
					access_level = AccessLevel.objects.get(name=payload["access_level"])
					if 'institution_id' in payload.keys():
						create_gateway_profile.institution = Institution.objects.get(id=payload['institution_id'])
					elif 'institution_id' not in payload.keys() and access_level.name not in ['CUSTOMER','SUPER ADMINISTRATOR'] and gateway_profile.institution:
						create_gateway_profile.institution = gateway_profile.institution 
				elif "role" in payload.keys() and create_gateway_profile.institution in [None,'']:
					role = Role.objects.get(name=payload["role"])
					access_level = role.access_level
					create_gateway_profile.role = role
					if 'institution_id' in payload.keys():
						create_gateway_profile.institution = Institution.objects.get(id=payload['institution_id'])
					elif 'institution_id' not in payload.keys() and access_level.name not in ['CUSTOMER','SUPER ADMINISTRATOR'] and gateway_profile.institution:
						create_gateway_profile.institution = gateway_profile.institution 

				else:
					access_level = AccessLevel.objects.get(name="CUSTOMER")

				'''
				if create_gateway_profile.access_level in [None,''] or (create_gateway_profile.access_level not in \
				 [None,''] and create_gateway_profile.access_level.hierarchy>access_level.hierarchy):
					create_gateway_profile.access_level = access_level
				'''
				if access_level.name == 'SYSTEM': create_gateway_profile.access_level = AccessLevel.objects.get(name="CUSTOMER")
				else: create_gateway_profile.access_level = access_level
				#if create_gateway_profile.created_by in [None,'']:create_gateway_profile.created_by = gateway_profile.user.profile 
				create_gateway_profile.save()

				payload["profile_id"] = create_gateway_profile.user.profile.id
				payload['response'] = 'User Profile Created'
				payload['response_status'] = '00'
				payload['session_gateway_profile_id'] = create_gateway_profile.id

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
			session_gateway_profile, payload, profile_error = self.profile_state(session_gateway_profile, payload, profile_error)

			if profile_error: pass
			elif session_gateway_profile.exists():
				payload['session_gateway_profile_id'] = session_gateway_profile[0].id
				user, payload = self.profile_update_if_null(session_gateway_profile[0].user, payload)

				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if 'first_name' in payload.keys()  else user.first_name
				payload['last_name'] = payload['last_name'] if 'last_name' in payload.keys()  else user.last_name
				payload['gender'] = user.profile.gender.code if user.profile.gender else None
				payload['middle_name'] = payload['middle_name'] if 'middle_name' in payload.keys()  else user.profile.middle_name

				if user.profile.national_id: payload['national_id'] = user.profile.national_id
				if user.profile.passport_number: 
					payload['passport_number'] = user.profile.passport_number
					if user.profile.passport_expiry_date: payload['passport_expiry_date'] = user.profile.passport_expiry_date.isoformat()
				if user.profile.postal_address: payload['postal_address'] = user.profile.postal_address
				if user.profile.address: payload['address'] = user.profile.address
				if user.profile.postal_code: payload['postal_code'] = user.profile.postal_code

				if user.profile.dob: payload['dob'] = user.profile.dob.isoformat()
				if user.profile.tax_pin: payload['tax_pin'] = user.profile.tax_pin

				if 'msisdn' not in payload.keys() and session_gateway_profile[0].msisdn:
					payload['msisdn'] = session_gateway_profile[0].msisdn.phone_number
				
				if user.email and self.validateEmail(user.email): payload['email'] = user.email
				elif 'email' in payload.keys(): del payload['email']

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
			session_gateway_profile, payload, profile_error = self.profile_state(session_gateway_profile, payload, profile_error)

			if profile_error: pass
			elif session_gateway_profile.exists():
				payload['session_gateway_profile_id'] = session_gateway_profile[0].id
				user, payload = self.profile_update(session_gateway_profile[0].user, payload)

				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if 'first_name' in payload.keys()  else user.first_name
				payload['last_name'] = payload['last_name'] if 'last_name' in payload.keys()  else user.last_name
				payload['gender'] = user.profile.gender.code if user.profile.gender else None
				payload['middle_name'] = payload['middle_name'] if 'middle_name' in payload.keys()  else user.profile.middle_name

				if user.profile.national_id: payload['national_id'] = user.profile.national_id
				if user.profile.passport_number: 
					payload['passport_number'] = user.profile.passport_number
					if user.profile.passport_expiry_date: payload['passport_expiry_date'] = user.profile.passport_expiry_date.isoformat()
				if user.profile.postal_address: payload['postal_address'] = user.profile.postal_address
				if user.profile.address: payload['address'] = user.profile.address
				if user.profile.postal_code: payload['postal_code'] = user.profile.postal_code
				if user.profile.dob: payload['dob'] = user.profile.dob.isoformat()
				if user.profile.tax_pin: payload['tax_pin'] = user.profile.tax_pin

				if 'msisdn' not in payload.keys() and session_gateway_profile[0].msisdn:
					payload['msisdn'] = session_gateway_profile[0].msisdn.phone_number

				if 'role_id' in payload.keys():
					role = Role.objects.get(id=payload["role_id"])
					access_level = role.access_level
					session_gateway_profile[0].role = role
					#session_gateway_profile[0].access_level = access_level
					session_gateway_profile[0].save()

				if user.email and self.validateEmail(user.email): payload['email'] = user.email
				elif 'email' in payload.keys(): del payload['email']

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


	def get_change_identity_profile(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			profile_error = None
			session_gateway_profile, payload, profile_error = self.profile_capture(gateway_profile, payload, profile_error)
			session_gateway_profile, payload, profile_error = self.profile_state(session_gateway_profile, payload, profile_error)

			if profile_error: pass
			elif session_gateway_profile.exists():
				payload['session_gateway_profile_id'] = session_gateway_profile[0].id

				#Delete Any Exisiting Identity Info
				profile = session_gateway_profile[0].user.profile
				profile.passport_number = ''
				profile.passport_expiry_date = None
				profile.national_id = ''
				profile.save()

				user, payload = self.profile_update(session_gateway_profile[0].user, payload)

				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if 'first_name' in payload.keys()  else user.first_name
				payload['last_name'] = payload['last_name'] if 'last_name' in payload.keys()  else user.last_name
				payload['gender'] = user.profile.gender.code if user.profile.gender else None
				payload['middle_name'] = payload['middle_name'] if 'middle_name' in payload.keys()  else user.profile.middle_name

				if user.profile.national_id: payload['national_id'] = user.profile.national_id
				if user.profile.passport_number: 
					payload['passport_number'] = user.profile.passport_number
					if user.profile.passport_expiry_date: payload['passport_expiry_date'] = user.profile.passport_expiry_date.isoformat()
				if user.profile.postal_address: payload['postal_address'] = user.profile.postal_address
				if user.profile.address: payload['address'] = user.profile.address
				if user.profile.postal_code: payload['postal_code'] = user.profile.postal_code
				if user.profile.dob: payload['dob'] = user.profile.dob.isoformat()
				if user.profile.tax_pin: payload['tax_pin'] = user.profile.tax_pin

				if 'msisdn' not in payload.keys() and session_gateway_profile[0].msisdn:
					payload['msisdn'] = session_gateway_profile[0].msisdn.phone_number

				if user.email and self.validateEmail(user.email): payload['email'] = user.email
				elif 'email' in payload.keys(): del payload['email']

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
			if ('email_msisdn' in payload.keys() or 'username' in payload.keys() or ('email' in payload.keys() and self.validateEmail(payload['email']))) and 'password' in payload.keys():
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
				elif 'email_msisdn' in payload.keys() and  self.validateEmail(payload['email_msisdn'].strip()):
					gateway_login_profile = GatewayProfile.objects.filter(user__email__iexact=payload['email_msisdn'].strip(), gateway=gateway_profile.gateway)
				elif  'email_msisdn' in payload.keys() and  self.simple_get_msisdn(payload['email_msisdn'].strip(), payload):
					gateway_login_profile = GatewayProfile.objects.filter(msisdn__phone_number=self.simple_get_msisdn(payload['email_msisdn'].strip(), payload), gateway=gateway_profile.gateway)
				elif  'email_msisdn' in payload.keys() and  GatewayProfile.objects.filter(gateway=gateway_profile.gateway, user__username__iexact=payload['email_msisdn'].strip()).exists():
					gateway_login_profile = GatewayProfile.objects.filter(user__username__iexact=payload['email_msisdn'].strip(), gateway=gateway_profile.gateway)

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

			elif ('email_msisdn' in payload.keys() or 'msisdn' in payload.keys()) and 'fingerprint' in payload.keys() and 'pin' in payload.keys():
				if  'email_msisdn' in payload.keys() and  self.simple_get_msisdn(payload['email_msisdn'].strip(), payload):
					gateway_login_profile = GatewayProfile.objects.filter(msisdn__phone_number=self.simple_get_msisdn(payload['email_msisdn'].strip(), payload), gateway=gateway_profile.gateway)
					gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile__msisdn__phone_number=self.simple_get_msisdn(payload['email_msisdn'].strip(), payload), \
							gateway_profile__gateway=gateway_profile.gateway, device_id = payload['fingerprint'],\
							channel__id=payload['chid'])

				else:
					gateway_profile_device_list = GatewayProfileDevice.objects.filter(gateway_profile__msisdn__phone_number= self.get_msisdn(payload), \
							gateway_profile__gateway=gateway_profile.gateway, device_id = payload['fingerprint'],\
							channel__id=payload['chid'])

				lgr.info('Gateway Profile Device: %s' % gateway_profile_device_list)
				if gateway_profile_device_list.exists():
					session_gateway_profile = gateway_profile_device_list[0].gateway_profile
		
					salt = str(session_gateway_profile.id)
					salt = '0%s' % salt if len(salt) < 2 else salt

					hash_pin = crypt.crypt(str(payload['pin']), salt)
					if hash_pin == session_gateway_profile.pin:
						session_gateway_profile.pin_retries = 0
						session_gateway_profile.save()
						authorized_gateway_profile = session_gateway_profile

					else:
						if session_gateway_profile.pin_retries >= gateway_profile.gateway.max_pin_retries:
							session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
						session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
						session_gateway_profile.save()


					lgr.info('Authorized Gateway Profile: %s' % authorized_gateway_profile)
			if authorized_gateway_profile is not None and authorized_gateway_profile.status.name not in ['DELETED']:
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


