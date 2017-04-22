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

from bridge.models import *
from vcs.models import *

import logging
lgr = logging.getLogger('upc')

from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app


class Wrappers:
        def validateEmail(self, email):
                try:
                        validate_email(str(email))
                        return True
                except ValidationError:
                        return False

	@app.task(filter=task_method, ignore_result=True)
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
	def verify_msisdn(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Ensure session Gateway Profile is not used as it would use a profile of an existing account with MSISDN

			lng = payload['lng'] if 'lng' in payload.keys() else 0.0
			lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	                trans_point = Point(float(lng), float(lat))
			g = GeoIP()

			msisdn = None
			if "msisdn" in payload.keys():
	 			msisdn = str(payload['msisdn'])
				msisdn = msisdn.strip()
				if len(msisdn) >= 9 and msisdn[:1] == '+':
					msisdn = str(msisdn)
				elif len(msisdn) >= 7 and len(msisdn) <=10 and msisdn[:1] == '0':
					country_list = Country.objects.filter(mpoly__intersects=trans_point)
					ip_point = g.geos(str(payload['ip_address']))
					if country_list.exists() and country_list[0].ccode:
						msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
					elif ip_point:
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

			lng = payload['lng'] if 'lng' in payload.keys() else 0.0
			lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	                trans_point = Point(float(lng), float(lat))
			g = GeoIP()

			msisdn = None
			if "msisdn" in payload.keys():
	 			msisdn = str(payload['msisdn'])
				msisdn = msisdn.strip()
				if len(msisdn) >= 9 and msisdn[:1] == '+':
					msisdn = str(msisdn)
				elif len(msisdn) >= 7 and len(msisdn) <=10 and msisdn[:1] == '0':
					country_list = Country.objects.filter(mpoly__intersects=trans_point)
					ip_point = g.geos(str(payload['ip_address']))
					if country_list.exists() and country_list[0].ccode:
						msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
					elif ip_point:
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
						till_currency=till_currency,description=description,physical_addr=payload["till_location"],\
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

	def event_status(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			lgr.info('Gateway Profile in Event Status: %s' % gateway_profile)
			if gateway_profile.access_level.name in ['SYSTEM']:
				lgr.info('User is System User')
				payload['response'] = 'System User'
			else:
       	                        payload['profile_photo'] = gateway_profile.user.profile.photo.name
       	                        payload['first_name'] = gateway_profile.user.first_name
       	                       	payload['last_name'] = gateway_profile.user.last_name
       	                       	payload['access_level'] = gateway_profile.access_level.name
				if gateway_profile.institution:
					payload['institution_id'] = gateway_profile.institution.id
				payload['response'] = 'Gateway Profile Exists'
			
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error on Event Status: %s' % e)
			payload['response_status'] = '96'

		return payload

	def create_user_profile(self, payload, node_info):
		try:
			#Clean MSISDN for lookup
			if 'msisdn' in payload.keys():
				payload["msisdn"] = '+%s' % payload["msisdn"] if '+' not in payload["msisdn"] else payload["msisdn"]

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			host = Host.objects.get(host=payload['gateway_host'], status__name='ENABLED')



			if ('email' in payload.keys() and self.validateEmail(payload["email"]) ) and \
			('msisdn' in payload.keys() and len(payload["msisdn"])>=9 and len(payload["msisdn"])<=15):
				existing_gateway_profile = GatewayProfile.objects.filter(Q(msisdn__phone_number=payload["msisdn"]),Q(gateway=gateway_profile.gateway))
				if existing_gateway_profile.exists():
					pass
				else:
					existing_gateway_profile = GatewayProfile.objects.filter(Q(user__email=payload["email"]),Q(gateway=gateway_profile.gateway))
			elif 'email' in payload.keys() and self.validateEmail(payload["email"]):
				existing_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,user__email=payload["email"])
			elif 'msisdn' in payload.keys() and len(payload["msisdn"])>=9 and len(payload["msisdn"])<=15:
				existing_gateway_profile = GatewayProfile.objects.filter(gateway=gateway_profile.gateway,msisdn__phone_number=payload["msisdn"])
			elif 'session_gateway_profile_id' in payload.keys():
				existing_gateway_profile = GatewayProfile.objects.filter(id=payload['session_gateway_profile_id'])
			else:
				existing_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)


			if existing_gateway_profile.exists():
				user = existing_gateway_profile[0].user

				if 'full_names' in payload.keys():
					full_names = payload["full_names"].split(" ")
					if len(full_names) == 1:
						payload['first_name'] = full_names[0]
					if len(full_names) == 2:
						payload['first_name'],payload['last_name'] = full_names
					elif len(full_names) == 3:
						payload['first_name'],payload['middle_name'],payload['last_name'] = full_names

				if 'email' in payload.keys() and user.email in [None,""] and self.validateEmail(payload["email"]):user.email = payload["email"]
				if 'first_name' in payload.keys() and user.first_name in [None,""]: user.first_name = payload['first_name']
				if 'last_name' in payload.keys() and user.last_name in [None,""]: user.last_name = payload['last_name']
				user.save()

				profile = Profile.objects.get(user=user) #User is a OneToOne field
				if 'middle_name' in payload.keys() and profile.middle_name in [None,""]: profile.middle_name = payload['middle_name']
				if 'national_id' in payload.keys() and profile.national_id in [None,""]: profile.national_id = payload['national_id']
				if 'physical_addr' in payload.keys() and profile.physical_addr in [None,""]: profile.physical_addr = payload['physical_addr']
				if 'city' in payload.keys() and profile.city in [None,""]: profile.city = payload['city']
				if 'region' in payload.keys() and profile.region in [None,""]: profile.region = payload['region']
				if 'address' in payload.keys() and profile.address in [None,""]: profile.address = payload['address']
				if 'gender' in payload.keys() and profile.gender in [None,""]:
					try: gender = Gender.objects.get(name=payload['gender']); profile.gender = gender
					except Exception, e: lgr.info('Error on Gender: %s' % e)
				if 'dob' in payload.keys() and profile.dob in [None,""]: 
					try: profile.dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()
					except Exception, e: lgr.info('Error on DOB: %s' % e)


				profile.save()

				create_gateway_profile = existing_gateway_profile[0]
			else:
				def createUsername(original):
					u = User.objects.filter(username=original)
					if len(u)>0:
						chars = string.digits
						rnd = random.SystemRandom()
						append_char = ''.join(rnd.choice(chars) for i in range(1,6))
						new_original = original+append_char
						return createUsername(new_original)
					else:
						return original


				username = ''
				if 'email' in payload.keys() and self.validateEmail(payload["email"]):
					username = createUsername(payload["email"].split('@')[0])
				elif 'msisdn' in payload.keys() and len(payload["msisdn"])>=9 and len(payload["msisdn"])<=15:
					#username = '%s' % (time.time()*1000)
					username = '%s' % payload["msisdn"]
					username = createUsername(username)

				payload['username'] = username
				username = username.lower()[:100]
				user = User.objects.create_user(username, '','')#username,email,password
				lgr.info("Created User: %s" % user)
				if 'full_names' in payload.keys():
					full_names = payload["full_names"].split(" ")
					if len(full_names) == 1:
						payload['first_name'] = full_names[0]
					if len(full_names) == 2:
						payload['first_name'],payload['last_name'] = full_names
					elif len(full_names) == 3:
						payload['first_name'],payload['middle_name'],payload['last_name'] = full_names

				if 'email' in payload.keys() and user.email in [None,""] and self.validateEmail(payload["email"]):user.email = payload["email"]
				if 'first_name' in payload.keys() and user.first_name in [None,""]: user.first_name = payload['first_name']
				if 'last_name' in payload.keys() and user.last_name in [None,""]: user.last_name = payload['last_name']
				user.save()

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
				if 'middle_name' in payload.keys() and profile.middle_name in [None,""]: profile.middle_name = payload['middle_name']
				if 'national_id' in payload.keys() and profile.national_id in [None,""]: profile.national_id = payload['national_id']
				if 'physical_addr' in payload.keys() and profile.physical_addr in [None,""]: profile.physical_addr = payload['physical_addr']
				if 'city' in payload.keys() and profile.city in [None,""]: profile.city = payload['city']
				if 'region' in payload.keys() and profile.region in [None,""]: profile.region = payload['region']
				if 'address' in payload.keys() and profile.address in [None,""]: profile.address = payload['address']
				if 'gender' in payload.keys() and profile.gender in [None,""]:
					try: gender = Gender.objects.get(name=payload['gender']); profile.gender = gender
					except Exception, e: lgr.info('Error on Gender: %s' % e)
				if 'dob' in payload.keys() and profile.dob in [None,""]: 
					try: profile.dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()
					except Exception, e: lgr.info('Error on DOB: %s' % e)


				profile.save()
				lgr.info('Saved Profile')
				create_gateway_profile = GatewayProfile(user=user, gateway=gateway_profile.gateway, status=profile_status)

			###################################################################################################################################
			#Create Gateway Profile Attributes to be added

			lng = payload['lng'] if 'lng' in payload.keys() else 0.0
			lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	                trans_point = Point(float(lng), float(lat))
			g = GeoIP()

			msisdn = None
			if "msisdn" in payload.keys():
	 			msisdn = str(payload['msisdn'])
				msisdn = msisdn.strip()
				if len(msisdn) >= 9 and msisdn[:1] == '+':
					msisdn = str(msisdn)
				elif len(msisdn) >= 7 and len(msisdn) <=10 and msisdn[:1] == '0':
					country_list = Country.objects.filter(mpoly__intersects=trans_point)
					ip_point = g.geos(str(payload['ip_address']))
					if country_list.exists() and country_list[0].ccode:
						msisdn = '+%s%s' % (country_list[0].ccode,msisdn[1:])
					elif ip_point:
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


				if msisdn is not None:
					try:msisdn = MSISDN.objects.get(phone_number=msisdn)
					except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();
					if create_gateway_profile.msisdn in [None,'']:
						create_gateway_profile.msisdn = msisdn

			if "access_level_id" in payload.keys() and create_gateway_profile.institution in [None,'']:
				access_level = AccessLevel.objects.get(id=payload["access_level_id"])
				if 'institution_id' in payload.keys():
					create_gateway_profile.institution = Institution.objects.get(id=payload['institution_id'])
				elif gateway_profile.institution not in [None, '']:
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

		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Creating User Profile: %s" % e)
		return payload

	def get_profile(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if ('email' in payload.keys() and self.validateEmail(payload["email"]) ) and \
			('msisdn' in payload.keys() and len(payload["msisdn"])>=9 and len(payload["msisdn"])<=15):
				payload["msisdn"] = '+%s' % payload["msisdn"] if '+' not in payload["msisdn"] else payload["msisdn"]
				session_gateway_profile = GatewayProfile.objects.filter(Q(msisdn__phone_number=payload["msisdn"]),Q(gateway=gateway_profile.gateway))
				if session_gateway_profile.exists():
					pass
				else:
					session_gateway_profile = GatewayProfile.objects.filter(Q(user__email=payload["email"]),Q(gateway=gateway_profile.gateway))
			elif 'email' in payload.keys() and self.validateEmail(payload["email"]):
				session_gateway_profile = GatewayProfile.objects.filter(user__email=payload["email"],\
						 gateway=gateway_profile.gateway)
			elif 'msisdn' in payload.keys() and len(payload["msisdn"])>=9 and len(payload["msisdn"])<=15:
				payload["msisdn"] = '+%s' % payload["msisdn"] if '+' not in payload["msisdn"] else payload["msisdn"]

				session_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=payload["msisdn"],\
						 gateway=gateway_profile.gateway)
			elif 'session_gateway_profile_id' in payload.keys():
				session_gateway_profile = GatewayProfile.objects.filter(id=payload['session_gateway_profile_id'])
			else:
				session_gateway_profile = GatewayProfile.objects.filter(id=gateway_profile.id)


			if session_gateway_profile.exists() and session_gateway_profile[0].access_level.name == 'SYSTEM':
				payload['response'] = 'System User Not Allowed'
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
					if 'physical_addr' in payload.keys() and profile.physical_addr in [None,""]: profile.physical_addr = payload['physical_addr']
					if 'city' in payload.keys() and profile.city in [None,""]: profile.city = payload['city']
					if 'region' in payload.keys() and profile.region in [None,""]: profile.region = payload['region']
					if 'address' in payload.keys() and profile.address in [None,""]: profile.address = payload['address']
					if 'gender' in payload.keys() and profile.gender in [None,""]:
						try: gender = Gender.objects.get(name=payload['gender']); profile.gender = gender
						except Exception, e: lgr.info('Error on Gender: %s' % e)
					if 'dob' in payload.keys() and profile.dob in [None,""]: 
						try: profile.dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()
						except Exception, e: lgr.info('Error on DOB: %s' % e)


					profile.save()


				payload['username'] = user.username 
				payload['first_name'] = payload['first_name'] if user.first_name in ['',None] and 'first_name' in payload.keys() and payload['first_name'] not in ['',None] else user.first_name
				payload['last_name'] = payload['last_name'] if user.last_name in ['',None] and 'last_name' in payload.keys() and payload['last_name'] not in ['',None] else user.last_name

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
			if 'username' in payload.keys() and 'password' in payload.keys():
				lgr.info("Returning User")
				#CHECK CREDENTIALS and 
				gateway_login_profile = GatewayProfile.objects.filter(Q(gateway=gateway_profile.gateway),Q(user__username=payload['username'].strip())|\
							Q(user__email=payload['username'].strip()))

				for p in gateway_login_profile: #Loop through all profils matching username
					if p.user.is_active and p.user.check_password(payload['password']):
						authorized_gateway_profile = p
						break

			elif 'sec' in payload.keys() and 'gpid' in payload.keys():
				session_id = base64.urlsafe_b64decode(payload['sec'])
				lgr.info('Session Got: %s' % session_id.decode('hex'))
				session = SessionHop.objects.filter(session_id=session_id.decode('hex'),gateway_profile__id=payload['gpid'],\
						gateway_profile__gateway=gateway_profile.gateway,\
						date_created__gte=timezone.localtime(timezone.now())-timezone.timedelta(hours=12))
				lgr.info('Fectch Existing session: %s' % session)
				if len(session) > 0:
					authorized_gateway_profile = session[0].gateway_profile
					#payload['trigger'] = "SET PASSWORD"
			if authorized_gateway_profile is not None and authorized_gateway_profile.status.name in ['ACTIVATED','ONE TIME PIN']:
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
