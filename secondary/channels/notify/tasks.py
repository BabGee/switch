from __future__ import absolute_import, unicode_literals
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

from django.template import Context, loader
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.contrib.gis.geoip import GeoIP

from django.db import IntegrityError
import pytz, time, json, pycurl
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.validators import validate_email
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
import urllib, urllib2
from django.db import transaction
from xml.sax.saxutils import escape, unescape
from django.utils.encoding import smart_str, smart_unicode
from django.db.models import Q, F
from django.db.models import Count, Sum, Max, Min, Avg
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers

import operator, string
from django.core.mail import EmailMultiAlternatives
from primary.core.upc.tasks import Wrappers as UPCWrappers
import numpy as np
from django.conf import settings

from primary.core.administration.views import WebService
from .models import *

import logging
lgr = logging.getLogger('secondary.channels.notify')


class Wrappers:
	def trigger_notification_template(self, payload,notification_template):
		#Check if trigger Exists
		if 'trigger' in payload.keys():
			triggers = str(payload['trigger'].strip()).split(',')
			trigger_list = Trigger.objects.filter(name__in=triggers)
			lgr.info('Triggers: %s' % trigger_list)
			notification_template = notification_template.filter(Q(trigger__in=trigger_list)|Q(trigger=None)).distinct()
			#Eliminate none matching trigger list
			for i in notification_template:
				if i.trigger.all().exists():
					if i.trigger.all().count() == trigger_list.count():
						if False in [i.trigger.filter(id=t.id).exists() for t in trigger_list.all()]:
							lgr.info('Non Matching: %s' % i)
							notification_template = notification_template.filter(~Q(id=i.id))
					else:
						lgr.info('Non Matching: %s' % i)
						notification_template = notification_template.filter(~Q(id=i.id))
		else:
			notification_template = notification_template.filter(Q(trigger=None))

		return notification_template

	@app.task(ignore_result=True)
	def service_call(self, service, gateway_profile, payload):
		#from celery.utils.log import get_task_logger
		lgr = get_task_logger(__name__)

		from primary.core.api.views import ServiceCall
		try:
			payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload


	def validateEmail(self, email):
		try:
			validate_email(str(email))
			return True
		except ValidationError:
			return False

	def validate_url(self, url):
		val = URLValidator()
		try:
			val(url)
			return True
		except ValidationError, e:
			lgr.info("URL Validation Error: %s" % e)
			return False

	def post_request(self, payload, node):
		try:
			if self.validate_url(node):
				jdata = json.dumps(payload)
				#response = urllib2.urlopen(node, jdata, timeout = timeout)
				#jdata = response.read()
				#payload = json.loads(jdata)
				c = pycurl.Curl()
				#Timeout in 30 seconds
				c.setopt(pycurl.CONNECTTIMEOUT, 20)
				c.setopt(pycurl.TIMEOUT, 20)
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

class System(Wrappers):
	def update_notification_template(self, payload, node_info):
		try:

			if 'notification_product_id' not in payload.keys():
				payload['response'] = "Notification not found"
				payload['response_status']= '25'
			else:
				gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
				notification_template = NotificationTemplate.objects.filter(product__id=payload['notification_product_id'],\
							service__name='TEMPLATE NOTIFICATION', status__name='ACTIVE')

				notification_template = self.trigger_notification_template(payload,notification_template)

				if notification_template.exists() and 'message' in payload.keys() and payload['message'] not in ['',None]:
					template = notification_template[0]
					template.template_message = payload['message']
					template.save()

					payload['response'] = 'Template Updated'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'No Template to Update'
					payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Updating Notification Template: %s" % e)
		return payload

	def create_notification_template(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			service = Service.objects.get(name='TEMPLATE NOTIFICATION')
			status = TemplateStatus.objects.get(name='ACTIVE')

			n_p_ids = [np for np in payload['notification_products'].split(',') if np ]
			notification_products = NotificationProduct.objects.filter(id__in=n_p_ids)

			notification_template = NotificationTemplate()
			notification_template.template_heading = payload['template_heading']
			notification_template.template_message = payload['template_message']

			notification_template.service = service
			notification_template.description = payload['template_heading']
			notification_template.status = status

			if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:

				template_file = TemplateFile()

				template_file.name = notification_template.template_heading
				template_file.description = notification_template.template_heading

				template_file.save()
				##########################
				media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'


				filename = payload['attachment']

				tmp_file = media_temp + str(filename)
				with open(tmp_file, 'r') as f:
					template_file.file_path.save(filename, File(f), save=False)
				f.close()
				#######################
				notification_template.template_file = template_file


			notification_template.save()

			notification_template.product.add(*notification_products)

			payload['response'] = 'Template Saved'
			payload['response_status'] = '00'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Updating Notification Template: %s" % e)

		return payload

	def edit_notification_template(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			notification_template = NotificationTemplate.objects.get(pk=payload['notification_template_id'])

			notification_template.template_heading = payload['template_heading']
			notification_template.template_message = payload['template_message']

			# notification_template.description = payload['template_heading']


			##########################
			media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

			if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:
				filename = payload['attachment']
				template_file = TemplateFile()

				template_file.name = notification_template.template_heading
				template_file.description = notification_template.template_heading
				template_file.save()
				notification_template.template_file = template_file

				tmp_file = media_temp + str(filename)
				with open(tmp_file, 'r') as f:
					template_file.file_path.save(filename, File(f), save=False)
				f.close()
			#######################

			notification_template.save()

			n_p_ids = [np for np in payload['notification_products'].split(',') if np]
			notification_products = NotificationProduct.objects.filter(id__in=n_p_ids)

			new_levels = n_p_ids
			current_levels = notification_template.product.values_list('pk', flat=True)

			remove_levels = list(set(current_levels).difference(new_levels))
			add_levels = list(set(new_levels).difference(current_levels))

			notification_template.product.add(*NotificationProduct.objects.filter(pk__in=add_levels))
			notification_template.product.remove(*NotificationProduct.objects.filter(pk__in=remove_levels))

			payload['response'] = 'Template Saved'
			payload['response_status'] = '00'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Updating Notification Template: %s" % e)

		return payload

	def notification_template_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			notification_template = NotificationTemplate.objects.get(pk=payload['notification_template_id'])
			payload['template_heading'] = notification_template.template_heading
			payload['template_message'] = notification_template.template_message

			# notification_template.description = payload['template_heading']

			if notification_template.template_file and notification_template.template_file.file_path:
				payload['template_file'] = notification_template.template_file.file_path.url

			notification_product_list = NotificationProduct.objects.filter(Q(notification__code__institution=gateway_profile.institution)\
							|Q(notification__code__institution=None),Q(notification__code__gateway=gateway_profile.gateway)\
							|Q(notification__code__gateway=None))

			#payload['template_products'] = ','.join([product.id for product in notification_template.product.all()])

			payload['template_products'] = json.dumps([dict(id=p.id, name=p.name, selected=notification_template.product.filter(id=p.id).exists()) for p in notification_product_list])

			payload['response'] = 'Template Details Captured'
			payload['response_status'] = '00'

		except Exception, e:

			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Notification Template Details: %s" % e)

		return payload

	def add_notification_contact(self, payload, node_info):
		try:
		
			lgr.info("Get Notification: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			notification_product = NotificationProduct.objects.filter(notification__status__name='ACTIVE', \
						notification__code__gateway=gateway_profile.gateway,\
						 service__name=payload['SERVICE'])


			'''
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
			'''
			msisdn = UPCWrappers().get_msisdn(payload)

			if msisdn is not None:
				#Get/Filter MNO
				code1=(len(msisdn) -7)
				code2=(len(msisdn) -6)
				code3=(len(msisdn) -5)

				prefix = MNOPrefix.objects.filter(prefix=msisdn[:code3])
				if len(prefix)<1:
					prefix = MNOPrefix.objects.filter(prefix=msisdn[:code2])
					if len(prefix)<1:
						prefix = MNOPrefix.objects.filter(prefix=msisdn[:code1])

				lgr.info('MNO Prefix: %s|%s' % (prefix,msisdn))
				#Get Notification product
				notification_product = notification_product.filter(Q(notification__code__mno=prefix[0].mno)|Q(notification__code__mno=None))

			if 'notification_delivery_channel' in payload.keys():
				notification_product = notification_product.filter(notification__code__channel__name=payload['notification_delivery_channel'])

			if 'notification_product_id' in payload.keys():
				notification_product = notification_product.filter(id=payload['notification_product_id'])
			if 'product_item_id' in payload.keys():
				product_type = ProductItem.objects.get(id=payload['product_item_id']).product_type
				notification_product = notification_product.filter(product_type=product_type)
			if 'product_type_id' in payload.keys():
				notification_product = notification_product.filter(product_type__id=payload['product_type_id'])
			if 'payment_method' in payload.keys():
				notification_product = notification_product.filter(payment_method__name=payload['payment_method'])
			if 'code' in payload.keys():
				notification_product = notification_product.filter(notification__code__code=payload['code'])

			if 'institution_id' in payload.keys():
				#Filter to send an institution notification or otherwise a gateway if institution does not exist (gateway only has institution as None)
				institution_notification_product = notification_product.filter(notification__code__institution__id=payload['institution_id'])
				gateway_notification_product = notification_product.filter(notification__code__institution=None)
				notification_product =  institution_notification_product if institution_notification_product.exists() else gateway_notification_product

			if "keyword" in payload.keys():
				lgr.info("Keyword to filter found: %s" % payload['keyword'])
				notification_product=notification_product.filter(keyword__iexact=payload['keyword'])

			if len(notification_product)>0:
				notification_product = notification_product[0]
				status = ContactStatus.objects.get(name='ACTIVE') #User is active to receive notification

				if 'session_gateway_profile_id' in payload.keys():
					session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				else:
					session_gateway_profile_list = GatewayProfile.objects.filter(msisdn=msisdn, gateway=gateway_profile.gateway)
					session_gateway_profile = session_gateway_profile_list[0]


				contact = Contact.objects.filter(product=notification_product, gateway_profile=session_gateway_profile)
				

				if len(contact)<1:
					details = json.dumps({})
					new_contact = Contact(status=status,product=notification_product,subscription_details=details,\
							gateway_profile=session_gateway_profile)
					if notification_product.subscribable:
						new_contact.subscribed=False
					else:
						new_contact.subscribed=True

					if "linkid" in payload.keys():
						new_contact.linkid=payload['linkid']
					new_contact.save()
					payload['contact_id'] = new_contact.id
					payload['response'] = 'Contact Added'

				else:
					new_contact = contact[0]
					payload['contact_id'] = new_contact.id
					payload['response'] = 'Contact Exists'


				if 'contact_group' in payload.keys():
					#check if contact_group exists if not create
					contact_group_list = ContactGroup.objects.filter(name=payload['contact_group'],institution=new_contact.product.notification.code.institution)
					if len(contact_group_list)<1:
						contact_group = ContactGroup(name=payload['contact_group'],description=payload['contact_group'],institution=new_contact.product.notification.code.institution)
						contact_group.save()
					else:
						contact_group = contact_group_list[0]

					#check if contact's contact_group is added, if not, create
					contact_with_group = new_contact.contact_group.filter(id=contact_group.id)
					if len(contact_with_group)<1:
						new_contact.contact_group.add(contact_group)

				payload['response_status'] = '00'
			else:
				payload['response_status'] = "25"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Notification: %s" % e)
		return payload


	def deactivate_contact(self, payload, node_info):
		try:
			lgr.info("Get Payload: %s" % payload)

			msisdn = UPCWrappers().get_msisdn(payload)

			contact = Contact.objects.filter(gateway_profile__msisdn__phone_number=msisdn,\
				product__notification__code__institution__id=payload['institution_id'],\
				product__subscribable=True,status__name='ACTIVE', subscribed=True)
			if 'notification_product' in payload.keys():
				contact = contact.filter(product__name=payload['notification_product'])
			lgr.info('Contact: %s' % contact)

			if len(contact)>0:
				#Change status to INACTIVE but leave subscribed=True. Celery service would check for INACTIVE contact purpoting to be subscribed and unsubscribe
				contact_status = ContactStatus.objects.get(name='INACTIVE')
				c = contact[0]
				c.status = contact_status
				c.save()

				payload['response'] = 'Contact Deactiated'
				payload["response_status"] = "00"
			else:
				payload['response_status'] = "25"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Notification: %s" % e)
		return payload


	def change_to_recipient(self, payload, node_info):
		try:
			lgr.info("Get Payload: %s" % payload)
			if 'recipient_msisdn' in payload.keys() and payload['recipient_msisdn'] not in ["",None] or \
			'recipient_email' in payload.keys() and payload['recipient_email'] not in ["",None]:


				lng = payload['lng'] if 'lng' in payload.keys() else 0.0
				lat = payload['lat'] if 'lat' in payload.keys() else 0.0
	        	        trans_point = Point(float(lng), float(lat))
				g = GeoIP()



				if 'msisdn' in payload.keys():
					payload['original_msisdn'] = payload['msisdn']
					del payload['msisdn']
				if 'national_id' in payload.keys():
					payload['original_national_id'] = payload['national_id']
					del payload['national_id']
				if 'document_number' in payload.keys():
					payload['original_document_number'] = payload['document_number']
					del payload['document_number']
				if 'passport_number' in payload.keys():
					payload['original_passport_number'] = payload['passport_number']
					del payload['passport_number']
				if 'first_name' in payload.keys():
					payload['original_first_name'] = payload['first_name']
					del payload['first_name']
				if 'middle_name' in payload.keys():
					payload['original_middle_name'] = payload['middle_name']
					del payload['middle_name']
				if 'last_name' in payload.keys():
					payload['original_last_name'] = payload['last_name']
					del payload['last_name']
				if 'full_names' in payload.keys():
					payload['original_full_names'] = payload['full_names']
					del payload['full_names']
				if 'email' in payload.keys():
					payload['original_email'] = payload['email']
					del payload['email']
				if 'postal_address' in payload.keys():
					payload['original_postal_address'] = payload['postal_address']
					del payload['postal_address']
				if 'postal_code' in payload.keys():
					payload['original_postal_code'] = payload['postal_code']
					del payload['postal_code']

				if 'session_gateway_profile_id' in payload.keys():
					payload['original_session_gateway_profile_id'] = payload['session_gateway_profile_id']
					del payload['session_gateway_profile_id']


				if 'recipient_national_id' in payload.keys():
					payload['national_id'] = payload['recipient_national_id']
				if 'recipient_document_number' in payload.keys():
					payload['document_number'] = payload['recipient_document_number']
				if 'recipient_passport_number' in payload.keys():
					payload['passport_number'] = payload['recipient_passport_number']
				if 'recipient_postal_address' in payload.keys():
					payload['postal_address'] = payload['recipient_postal_address']
				if 'recipient_postal_code' in payload.keys():
					payload['postal_code'] = payload['recipient_postal_code']

				if 'recipient_msisdn' in payload.keys():
			 		payload['msisdn'] = str(payload['recipient_msisdn'])
					msisdn = UPCWrappers().get_msisdn(payload)

					if msisdn is not None:
						payload['msisdn'] = msisdn
						payload['response'] = 'MSISDN Changed to recipient'
						payload["response_status"] = "00"
				                payload['trigger'] = 'change_to_recipient%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					else:
						payload['response_status'] = '00'
						payload['response'] = 'No Recipient Found'
				elif 'recipient_email' in payload.keys() and self.validateEmail(payload["recipient_email"]):
					payload['email'] = payload['recipient_email'].strip()
					payload['response'] = 'EMAIL Changed to recipient'
					payload["response_status"] = "00"
					payload['trigger'] = 'change_to_recipient%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				else:
					payload['response_status'] = '00'
					payload['response'] = 'No Recipient Found'
			else:
				payload['response_status'] = '00'
				payload['response'] = 'No Recipient Found'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Notification: %s" % e)
		return payload

	def init_notification(self, payload, node_info):
		try:

			if 'notification_template_id' in payload.keys():
				del payload['notification_template_id'] #

			if 'notification_product_id' in payload.keys():
				del payload['notification_product_id'] #

			if 'message' in payload.keys():
				del payload['message']
			payload['response_status'] = '00'
			payload['response'] = 'Notification Initialized'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Init Notification: %s" % e)
		return payload

	def should_send_sms(self, payload, node_info):
		'''
		Adds a trigger `send_sms_notification` used on next service commands to run
		is added if str(payload['send_sms']) == 'True'

		'''
		try:
			lgr.info(payload['send_sms'])
			if 'send_sms' in payload.keys() and str(payload['send_sms']) == 'True':
				payload['trigger'] = 'send_sms_notification%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')
			else:
				# TODO remove send_sms_notification trigger if exists
				pass

			if 'trigger' in payload.keys():
				lgr.info(payload['trigger'])
			else:
				lgr.info('no trigger added')

			payload['response_status'] = '00'
			payload['response'] = 'Notification Initialized'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Init Notification: %s" % e)
		return payload


	def get_notification(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			notification_product = NotificationProduct.objects.filter(Q(notification__status__name='ACTIVE'), \
						Q(notification__code__gateway=gateway_profile.gateway),\
						Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
						 Q(service__name=payload['SERVICE'])).\
						prefetch_related('notification__code','product_type')

			msisdn = UPCWrappers().get_msisdn(payload)
			if msisdn is not None:
				#Get/Filter MNO
				code1=(len(msisdn) -7)
				code2=(len(msisdn) -6)
				code3=(len(msisdn) -5)

				prefix = MNOPrefix.objects.filter(prefix=msisdn[:code3])
				if len(prefix)<1:
					prefix = MNOPrefix.objects.filter(prefix=msisdn[:code2])
					if len(prefix)<1:
						prefix = MNOPrefix.objects.filter(prefix=msisdn[:code1])

				lgr.info('MNO Prefix: %s|%s' % (prefix,msisdn))
				#Get Notification product
				notification_product = notification_product.filter(Q(notification__code__mno=prefix[0].mno)|Q(notification__code__mno=None))
			elif 'session_gateway_profile_id' in payload.keys():
				contact = Contact.objects.filter(product__in=[p for p in notification_product],gateway_profile__id=payload['session_gateway_profile_id'])
				if contact.exists():
					notification_product = notification_product.filter(id__in=[c.product.id for c in contact])

			lgr.info('Notification Product: %s ' % notification_product)

			if 'notification_delivery_channel' in payload.keys():
				notification_product = notification_product.filter(notification__code__channel__name=payload['notification_delivery_channel'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'notification_product_id' in payload.keys():
				notification_product = notification_product.filter(id=payload['notification_product_id'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'product_item_id' in payload.keys():
				product_type = ProductItem.objects.get(id=payload['product_item_id']).product_type
				notification_product = notification_product.filter(product_type=product_type)

			lgr.info('Notification Product: %s ' % notification_product)
			if 'product_type_id' in payload.keys():
				notification_product = notification_product.filter(product_type__id=payload['product_type_id'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'product_type' in payload.keys():
				notification_product = notification_product.filter(product_type__name=payload['product_type'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'payment_method' in payload.keys():
				notification_product = notification_product.filter(payment_method__name=payload['payment_method'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'code' in payload.keys():
				notification_product = notification_product.filter(notification__code__code=payload['code'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'alias' in payload.keys():
				notification_product = notification_product.filter(notification__code__alias=payload['alias'])

			lgr.info('Notification Product: %s ' % notification_product)
			if 'institution_id' in payload.keys():
				#Filter to send an institution notification or otherwise a gateway if institution does not exist (gateway only has institution as None)
				institution_notification_product = notification_product.filter(notification__code__institution__id=payload['institution_id'])
				gateway_notification_product = notification_product.filter(notification__code__institution=None)
				notification_product =  institution_notification_product if institution_notification_product.exists() else gateway_notification_product

			lgr.info('Notification Product: %s ' % notification_product)
			if "keyword" in payload.keys():
				notification_product=notification_product.filter(keyword__iexact=payload['keyword'])

			lgr.info('Notification Product: %s ' % notification_product)


			if 'notification_template_id' in payload.keys():
				notification_template = NotificationTemplate.objects.get(id=payload['notification_template_id'])
				notification_product = notification_product.filter(id__in=[t.id for t in notification_template.product.all()])
			else:
				#get notification_template using service
				notification_template_list = NotificationTemplate.objects.filter(product__in=notification_product,service__name=payload['SERVICE'])

				notification_template_list = self.trigger_notification_template(payload,notification_template_list)
				notification_template = notification_template_list[0] if notification_template_list.exists() else None



			lgr.info('Notification Product: %s ' % notification_product)

			if notification_product.exists():
				#Construct Message to send
				if 'message' not in payload.keys():
					if notification_template:
						payload['notification_template_id'] = notification_template.id
						message = notification_template.template_message
						variables = re.findall("\[(.*?)\]", message)
						for v in variables:
							variable_key, variable_val = None, None
							n = v.find("=")
							if n >=0:
								variable_key = v[:n]
								variable_val = str(v[(n+1):]).strip()
							else:
								variable_key = v
							message_item = ''
							if variable_key in payload.keys():
								message_item = payload[variable_key]
								if variable_val is not None:
									if '|' in variable_val:
										prefix, suffix = variable_val.split('|')
										message_item = '%s %s %s' % (prefix, message_item, suffix)
									else:
										message_item = '%s %s' % (variable_val, message_item)
							message = message.replace('['+v+']',str(message_item).strip())
						#Message after loop
						payload['message'] = message
					else:
						payload['message'] = ''
				payload['notification_product_id'] = notification_product[0].id
				lgr.info('Payload: %s' % payload)
				#product_item = ProductItem.objects.filter(institution_till=notification_product[0].notification.institution_till,\
				#		product_type=notification_product[0].notification.product_type)
				#payload['product_item_id'] = product_item[0].id #Pick the notification product, product item used in sales and purchases of credits etc| *****@@Will throw error if no product item!!!!
				if 'product_item_id' in payload.keys(): del payload['product_item_id'] #Avoid deduction of float
				payload['float_product_type_id'] = notification_product[0].notification.product_type.id
				payload['float_amount'] = (notification_product[0].unit_credit_charge) #Pick the notification product cost

				#if 'institution_id' not in payload.keys() and notification_product[0].notification.code.institution:
				#	payload['institution_id'] = notification_product[0].notification.code.institution.id
				if notification_product[0].notification.code.institution:
					payload['institution_id'] = notification_product[0].notification.code.institution.id
				else:
					if 'institution_id' in payload.keys(): del payload['institution_id'] #User gateway Float if exists, if not, fail
				payload['response'] = "Notification Captured : %s" % notification_product[0].id 
				payload['response_status']= '00'
				#Calculate price per SMS per each 160 characters
				if notification_product[0].notification.code.channel.name == 'SMS':
					message = payload['message'].strip()
			                message = unescape(message)
					message = smart_str(message)
		                	message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					payload['float_amount'] = (notification_product[0].unit_credit_charge)*len(messages)

			elif len(notification_product)<1 and 'notification_product_id' in payload.keys():
				del payload['notification_product_id'] #Avoid send SMS
				if 'product_item_id' in payload.keys(): del payload['product_item_id'] #Avoid deduction of float
				payload['response'] = 'Notification Product not found'
				payload["response_status"] = "00"
				
			else:
				payload['response'] = 'Notification Product Not found'
				payload["response_status"] = "25"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Notification: %s" % e)
		return payload

	def get_email_notification(self, payload, node_info):
		payload['notification_delivery_channel'] = 'EMAIL'
		return self.get_notification(payload, node_info)

	def get_sms_notification(self, payload, node_info):
		payload['notification_delivery_channel'] = 'SMS'
		return self.get_notification(payload, node_info)


	def send_notification(self, payload, node_info):
		try:

			if 'notification_product_id' not in payload.keys():
				payload['response'] = "Notification not found"
				payload['response_status']= '25'

			else:
				gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

				ext_outbound_id = None
				if "ext_outbound_id" in payload.keys():
					ext_outbound_id = payload['ext_outbound_id']
                                elif 'bridge__transaction_id' in payload.keys():
					ext_outbound_id = payload['bridge__transaction_id']

				try:date_obj = datetime.strptime(payload["scheduled_send"], '%d/%m/%Y %I:%M %p')
				except: date_obj = None
				if date_obj is not None:		
					profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
					scheduled_send = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
				else:
					scheduled_send = timezone.now()
				notification_product = NotificationProduct.objects.get(id=payload['notification_product_id'])

				if 'session_gateway_profile_id' in payload.keys():
					session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				else:
					session_gateway_profile = gateway_profile

				#Check if Contact exists in notification product
				contact = Contact.objects.filter(product=notification_product, gateway_profile=session_gateway_profile) 

				#Construct Message to send
				if 'message' in payload.keys() and payload['message'] not in ['',None]:
					message = payload['message']

					if "linkid" in payload.keys():
						contact = contact.filter(linkid=payload['linkid'])

					status = ContactStatus.objects.get(name='ACTIVE') #User is active to receive notification
					if len(contact)<1:
						details = json.dumps({})
						new_contact = Contact(status=status,product=notification_product,subscription_details=details,\
								gateway_profile=session_gateway_profile)
						if notification_product.subscribable:
							new_contact.subscribed=False
						else:
							new_contact.subscribed=True

						if "linkid" in payload.keys():
							new_contact.linkid=payload['linkid']
						new_contact.save()
					else:
						new_contact = contact[0]
						new_contact.status = status
						if notification_product.subscribable == False and new_contact.subscribed == False: #Subscribe Unsubscribed Bulk(subscribable = False)
							new_contact.subscribed=True

						new_contact.save()
					state = OutBoundState.objects.get(name='CREATED')

					message = payload['message'].strip()
					message = unescape(message)
					message = smart_str(message)
					message = escape(message)

					outbound = Outbound(contact=new_contact,message=message,scheduled_send=scheduled_send,state=state, sends=0)
					if ext_outbound_id is not None:
						outbound.ext_outbound_id = ext_outbound_id

					if new_contact.product.notification.code.channel.name == 'SMS':
						msisdn = UPCWrappers().get_msisdn(payload)
						if msisdn:
							outbound.recipient = msisdn
						elif new_contact.gateway_profile.msisdn:
							outbound.recipient = new_contact.gateway_profile.msisdn.phone_number
					elif new_contact.product.notification.code.channel.name == 'EMAIL':
						if 'email' in payload.keys() and self.validateEmail(payload["email"]):
							outbound.recipient = payload['email']
						else:
							outbound.recipient = new_contact.gateway_profile.user.email
					elif new_contact.product.notification.code.channel.name == 'MQTT':
						if 'pn_notification_id' in payload.keys() and payload['pn_notification_id'] not in ['',None]:
							outbound.recipient = payload['pn_notification_id']
						else:
							outbound.recipient = new_contact.gateway_profile.user.profile.id

					if 'notification_template_id' in payload.keys():
						template = NotificationTemplate.objects.get(id=payload['notification_template_id'])
						outbound.template = template

						heading = template.template_heading
						variables = re.findall("\[(.*?)\]", heading)
						for v in variables:
							variable_key, variable_val = None, None
							n = v.find("=")
							if n >=0:
								variable_key = v[:n]
								variable_val = str(v[(n+1):]).strip()
							else:
								variable_key = v
							heading_item = ''
							if variable_key in payload.keys():
								heading_item = payload[variable_key]
								if variable_val is not None:
									if '|' in variable_val:
										prefix, suffix = variable_val.split('|')
										heading_item = '%s %s %s' % (prefix, heading_item, suffix)
									else:
										heading_item = '%s %s' % (variable_val, heading_item)
							heading = heading.replace('['+v+']',str(heading_item).strip())

						outbound.heading = heading

					outbound.save()

					payload['response'] = "Notification Sent. Please check %s" % notification_product.notification.code.channel.name
					payload['response_status']= '00'
				else:
					payload['response'] = 'No message to send'
					payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Send Notification: %s" % e)
		return payload


	def process_delivery_status(self, payload, node_info):
		try:
			lgr.info("Process Delivery Status: %s" % payload)
			msisdn = UPCWrappers().get_msisdn(payload)

			outbound_id = payload['outbound_id']
			delivery_status = payload['delivery_status']
			outbound = Outbound.objects.select_related('contact').filter(id=outbound_id,recipient=msisdn)
			if 'ext_service_id' in payload.keys() and payload['ext_service_id'] not in [None,'']:
				outbound = outbound.filter(contact__product__notification__ext_service_id=payload['ext_service_id'])

			lgr.info('Outbound List: %s' % outbound)
			if outbound.exists():
				this_outbound = outbound[0]
				#lgr.info("This outbound: %s|Delivery Status: %s" % (this_outbound, delivery_status) )
				if delivery_status in ['RESEND']:
					#lgr.info('Delivery Status: To retry in an hour')
					state = OutBoundState.objects.get(name='CREATED')
					this_outbound.state = state
					this_outbound.scheduled_send=timezone.now()+timezone.timedelta(hours=1)
					this_outbound.save()
				elif delivery_status in ['UNSUBSCRIBED']:
					#lgr.info('Delivery Status: Unsubscribed User, Initiating Subscription')

					if this_outbound.sends >= 2:
						status = ContactStatus.objects.get(name='INACTIVE')
					else:
						status = ContactStatus.objects.get(name='ACTIVE')
					this_outbound.contact.status = status
					this_outbound.contact.subscribed = False
					this_outbound.contact.save()
					state = OutBoundState.objects.get(name='CREATED')
					this_outbound.state = state
					this_outbound.save()
				elif delivery_status in ['DELIVERED']:
					#lgr.info('Delivery Status: Succesfully Delivered')
					state = OutBoundState.objects.get(name='DELIVERED')
					this_outbound.state = state
					this_outbound.save()
				elif delivery_status in ['FAILED']:
					#lgr.info('Delivery Status: Failed')
					state = OutBoundState.objects.get(name='FAILED')
					this_outbound.state = state
					this_outbound.save()
				else:
					pass
				this_outbound.save()
				#Notify Institution
				if this_outbound.contact.product.notification.institution_url not in [None, ""]:
					node = {}
					node['institution_url'] = this_outbound.contact.product.notification.institution_url
					#self.notify_institution.delay(payload, node)
					notify_institution.delay(payload, node)

				payload['ext_outbound_id'] = this_outbound.ext_outbound_id
				payload['response'] = "Delivery Status Processed"
			else:
				payload['response'] = 'Message not Found'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Processing Delivery Status: %s" % e)
		return payload


	def create_sms_notification(self, payload, node_info):
		try:
			lgr.info('Create Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			institution_id = payload['institution_id']
			service = payload['SERVICE']

			notification_product = NotificationProduct.objects.filter(product_type__id=payload['product_type_id'],\
							 notification__code__institution__id=payload['institution_id'])

			'''
			session_gateway_profile = None
			if 'session_gateway_profile_id' in payload.keys():
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			elif 'msisdn' in payload.keys():
				#Check if MSISDN Exists
				msisdn = UPCWrappers().get_msisdn(payload)
				if msisdn is not None:
					try:msisdn = MSISDN.objects.get(phone_number=msisdn)
					except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();

					session_gateway_profile = GatewayProfile.objects.filter(msisdn=msisdn, gateway=gateway_profile.gateway)
			'''

			if 'session_gateway_profile_id' in payload.keys():
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			else:
				session_gateway_profile = gateway_profile


			#Check if Contact exists in notification product
			contact = Contact.objects.filter(product=notification_product[0], gateway_profile=session_gateway_profile) 
			lgr.info('Contact: %s' % contact)
			#get notification_template using service & get/create contact
			notification_template = NotificationTemplate.objects.filter(product=notification_product[0],service__name=payload['SERVICE'])

			notification_template = self.trigger_notification_template(payload,notification_template)

			if notification_template.exists():
				payload['notification_template_id'] = notification_template[0].id
				details = json.dumps({})
				status = ContactStatus.objects.get(name='ACTIVE') #User is active to receive notification
				if len(contact)<1:
					new_contact = Contact(status=status,product=notification_product[0],subscription_details=details[:1920],\
							subscribed=False, gateway_profile=session_gateway_profile)
					new_contact.save()
				else:
					new_contact = contact[0]
					new_contact.status = status
					new_contact.save()

				#Create Outbound notification
				state = OutBoundState.objects.get(name='CREATED')
				message = notification_template[0].template_message

				variables = re.findall("\[(.*?)\]", message)
				lgr.info("Found Variables: %s" % variables)
				for v in variables:
					variable_key, variable_val = None, None
					n = v.find("=")
					if n >=0:
						variable_key = v[:n]
						variable_val = str(v[(n+1):]).strip()
					else:
						variable_key = v
					lgr.info('Variable Found: Key:%s|Val: %s' % (variable_key, variable_val))
					message_item = ''
					if variable_key in payload.keys():
						message_item = payload[variable_key]
						if variable_val is not None:
							if '|' in variable_val:
								prefix, suffix = variable_val.split('|')
								message_item = '%s %s %s' % (prefix, message_item, suffix)
							else:
								message_item = '%s %s' % (variable_val, message_item)
					lgr.info('Message ITEM: %s' % message_item)
					message = message.replace('['+v+']',str(message_item).strip())

				#if '[URL]' in message and 'URL' in payload.keys():
				#	message = message.replace('[URL]', str(payload['URL']))

				outbound = Outbound(contact=new_contact, message=message, scheduled_send=timezone.now()+timezone.timedelta(seconds=5), state=state, sends=0)

				if new_contact.product.notification.code.channel.name == 'SMS':
					msisdn = UPCWrappers().get_msisdn(payload)
					if msisdn:
						outbound.recipient = msisdn
					else:
						outbound.recipient = new_contact.gateway_profile.msisdn.phone_number
				elif new_contact.product.notification.code.channel.name == 'EMAIL':
					if 'email' in payload.keys() and self.validateEmail(payload["email"]):
						outbound.recipient = payload['email']
					else:
						outbound.recipient = new_contact.gateway_profile.user.email
				elif new_contact.product.notification.code.channel.name == 'MQTT':
					if 'pn_notification_id' in payload.keys() and payload['pn_notification_id'] not in ['',None]:
						outbound.recipient = payload['pn_notification_id']
					else:
						outbound.recipient = new_contact.gateway_profile.user.profile.id

				if 'notification_template_id' in payload.keys():
					notification_template = NotificationTemplate.objects.get(id=payload['notification_template_id'])
					outbound.template = notification_template
					outbound.heading = notification_template.template_heading
				outbound.save()

				payload['response'] = 'Notification Sent. Subscription: %s' % outbound.contact.product.name
			else:
				payload['response'] = "Notification Not Found"
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating Notification: %s" % e)
		return payload

	def get_message(self, payload, node_info):
		try:
			response = "No Message"
			lgr.info('Get Message: %s' % payload)
			inbound = Inbound.objects.filter(id__in=json.loads(payload['inbound']))
			for i in inbound:
				response = "From: %s | %s" % (i.contact.msisdn.phone_number, i.message)
			
			payload['inbound_message'] = response
			payload['response'] = 'Message Got Got'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Message: %s" % e)
		return payload


	def contact_group_charges(self, payload, node_info):
		try:
			lgr.info('Get Product Outbound Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			contact_group_list = ContactGroup.objects.filter(id__in=[a for a in payload['contact_group'].split(',') if a],\
							institution=gateway_profile.institution,\
							gateway=gateway_profile.gateway)

			lgr.info('Contact Group List: %s' % contact_group_list)
			contact = Contact.objects.filter(subscribed=True,status__name='ACTIVE',\
							contact_group__in=[c for c in contact_group_list],\
							product__notification__code__institution=gateway_profile.institution,\
							product__notification__code__gateway=gateway_profile.gateway).select_related('product')

			lgr.info('Contact: %s' % contact)
			contact_product_list = contact.values('product__id','product__unit_credit_charge').annotate(product_count=Count('product__id'))

			lgr.info('Contact Group List: %s' % contact_group_list)
			#Get Amount
			response = ''
			if contact_product_list.exists():
				for contact_product in contact_product_list:
					contact_list_count = contact.filter(product__id=contact_product['product__id']).distinct('gateway_profile__msisdn__phone_number').count()

					lgr.info('Contact List Count: %s' % contact_list_count)
					message = payload['message'].strip()
		        	        message = unescape(message)
					message = smart_str(message)
		                	message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					messages_count = len(messages)
 					float_amount = Decimal(contact_list_count * contact_product['product__unit_credit_charge'] * messages_count)
					response = '%s | @ %s' % (response, float_amount)

				payload['response'] = response
				payload['response_status']= '00'
			else:
				payload['response'] = 'Notification Product Not Found'
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Notification Charges: %s" % e)
		return payload



	def notification_charges(self, payload, node_info):
		try:
			lgr.info('Get Product Outbound Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			notification_product_list = NotificationProduct.objects.filter(id__in=[a for a in payload['notification_product'].split(',') if a],\
							notification__code__institution=gateway_profile.institution,\
							notification__code__gateway=gateway_profile.gateway)
			#Get Amount
			response = ''
			if notification_product_list.exists():
				for notification_product in notification_product_list:
					contact_list_count = Contact.objects.filter(product=notification_product,subscribed=True,status__name='ACTIVE').count()
					message = payload['message'].strip()
					message = unescape(message)
					message = smart_str(message)
					message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					messages_count = len(messages)
 					float_amount = Decimal(contact_list_count * notification_product.unit_credit_charge * messages_count)
					response = '%s | @ %s' % (response, float_amount)

				payload['response'] = response
				payload['response_status']= '00'
			else:
				payload['response'] = 'Notification Product Not Found'
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Notification Charges: %s" % e)
		return payload


	def log_contact_group_message(self, payload, node_info):
		try:
			lgr.info('Log Outbound Message: %s' % payload)

			date_string = payload['scheduled _date']+' '+payload['scheduled_time']
			date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
		
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
			scheduled_send = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)




			contact_group_list = ContactGroup.objects.filter(id__in=[a for a in payload['contact_group'].split(',') if a],\
							institution=gateway_profile.institution,\
							gateway=gateway_profile.gateway)

			lgr.info('Contact Group List: %s' % contact_group_list)
			contact = Contact.objects.filter(subscribed=True,status__name='ACTIVE',\
							contact_group__in=[c for c in contact_group_list],\
							product__notification__code__institution=gateway_profile.institution,\
							product__notification__code__gateway=gateway_profile.gateway).select_related('product')

			lgr.info('Contact: %s' % contact)
			contact_product_list = contact.values('product__id','product__unit_credit_charge').annotate(product_count=Count('product__id'))

			lgr.info('Contact Group List: %s' % contact_group_list)
			#Get Amount
			response = ''
			for contact_product in contact_product_list:
				contact_list = contact.filter(product__id=contact_product['product__id']).values_list('id').distinct('gateway_profile__msisdn__phone_number')
				if 'message' in payload.keys() and len(contact_list)>0:
					lgr.info('Message and Contact Captured')
					#Bulk Create Outbound
					#self.outbound_bulk_logger.delay(payload, contact_list, scheduled_send)
					contact_list = np.asarray(contact_list).tolist()
					lgr.info('Contact List: %s' % len(contact_list))
					#outbound_bulk_logger.apply_async((payload, contact_list, scheduled_send), serializer='json')

					outbound_bulk_logger(payload, contact_list, scheduled_send)

					payload['response'] = 'Outbound Message Processed'
					payload['response_status']= '00'
				elif 'message' not in payload.keys() and len(contact_list)>0:
					payload['response'] = 'No Message to Send'
					payload['response_status']= '00'
				else:
					payload['response'] = 'No Contact/Message to Send'
					payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Log Outbound Message: %s" % e)
		return payload


	def log_notification_message(self, payload, node_info):
		try:
			lgr.info('Log Outbound Message: %s' % payload)

			try:
				date_string = payload['scheduled _date']+' '+payload['scheduled_time']
				date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
		
				gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
				profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
				scheduled_send = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
			except: scheduled_send = timezone.now()
			#notification_product = NotificationProduct.objects.get(id=payload['notification_product'])
			notification_product_list = NotificationProduct.objects.filter(id__in=[a for a in payload['notification_product'].split(',') if a])

			for notification_product in notification_product_list:
				contact_list = Contact.objects.filter(product=notification_product,subscribed=True,status__name='ACTIVE').values_list('id')
				if 'message' in payload.keys() and len(contact_list)>0:
					lgr.info('Message and Contact Captured')
					#Bulk Create Outbound
					#self.outbound_bulk_logger.delay(payload, contact_list, scheduled_send)

					contact_list = np.asarray(contact_list).tolist()
					lgr.info('Contact List: %s' % len(contact_list))
					#outbound_bulk_logger.apply_async((payload, contact_list, scheduled_send), serializer='json')

					outbound_bulk_logger(payload, contact_list, scheduled_send)

					payload['response'] = 'Outbound Message Processed'
					payload['response_status']= '00'
				elif 'message' not in payload.keys() and len(contact_list)>0:
					payload['response'] = 'No Message to Send'
					payload['response_status']= '00'
				else:
					payload['response'] = 'No Contact/Message to Send'
					payload['response_status']= '00'
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Log Outbound Message: %s" % e)
		return payload


	def inbound_message(self, payload, node_info):
		try:
			lgr.info('Inbound Message: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if 'message' in payload.keys() and 'contact_id' in payload.keys():
				contact = Contact.objects.get(id=payload['contact_id'])
				state = InBoundState.objects.get(name='CREATED')
				inbound = Inbound(contact=contact,message=str(payload['message'][:3839]),state=state)
				inbound.save()
				#notify institution
				if inbound.contact.product.notification.institution_url not in [None, ""]:
					node = {}
					node['institution_url'] = inbound.contact.product.notification.institution_url
					#self.notify_institution.delay(payload, node)
					notify_institution.delay(self, payload, node)

			payload['response'] = 'Inbox Message Successful'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Subscribe: %s" % e)
		return payload


	def subscribe(self, payload, node_info):
		try:
			lgr.info('Subscription: %s' % payload)

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			#Get MNO from Prefix
			#prefix = MNOPrefix.objects.filter(prefix=payload["msisdn"][4:][:3], mno__country_code__code=payload["msisdn"][1:][:3])

			msisdn = UPCWrappers().get_msisdn(payload)

			code1=(len(msisdn) -7)
			code2=(len(msisdn) -6)
			code3=(len(msisdn) -5)

			prefix = MNOPrefix.objects.filter(prefix=msisdn[:code3])
			if len(prefix)<1:
				prefix = MNOPrefix.objects.filter(prefix=msisdn[:code2])
				if len(prefix)<1:
					prefix = MNOPrefix.objects.filter(prefix=msisdn[:code1])

			lgr.info('MNO Prefix: %s' % prefix)
			#Get Notification product
			notification_product = NotificationProduct.objects.filter(notification__code__code=payload['accesspoint'],\
					notification__code__mno=prefix[0].mno)

			if 'ext_service_id' in payload.keys() and payload['ext_service_id'] not in [None,'']:
				notification_product = notification_product.filter(notification__ext_service_id=payload['ext_service_id'])
			if 'ext_product_id' in payload.keys() and payload['ext_product_id'] not in [None,'']:
				notification_product = notification_product.filter(ext_product_id=payload['ext_product_id'])

			if len(notification_product)>0:
				#Get Action
				lgr.info('Action: %s' % payload['notification_action'])
				#Check if MSISDN Exists
				try:msisdn = MSISDN.objects.get(phone_number=msisdn)
				except MSISDN.DoesNotExist: msisdn = MSISDN(phone_number=msisdn);msisdn.save();

				lgr.info('MSISDN: %s' % msisdn)

				def contact_entry_subscription(payload, session_gateway_profile, notification_product, msisdn):
					#Check if Contact exists in notification product
					contact = Contact.objects.filter(product=notification_product[0],gateway_profile__msisdn=msisdn, \
						gateway_profile__gateway=notification_product[0].notification.code.gateway)

					lgr.info('Contact: %s' % contact)
					#Subscription Details
					details = json.dumps( payload['subscription_details'] )
					lgr.info("Subscription Details: %s" % details)
					if 'notification_action' in payload.keys() and payload['notification_action'] == 'Addition':
						status = ContactStatus.objects.get(name='ACTIVE')
						if len(contact)<1 or 'linkid' in payload.keys():
							new_contact = Contact(status=status,product=notification_product[0],subscription_details=details[:1920],\
									subscribed=True, gateway_profile=session_gateway_profile)
							if 'linkid' in payload.keys():new_contact.linkid = payload['linkid'] 
							new_contact.save()
						else:
							new_contact = contact[0]
							new_contact.subscribed = True
							new_contact.subscription_details = details[:1920]
							new_contact.status = status
							new_contact.save()
						payload['contact_id'] = new_contact.id
						payload['response'] = '%s Subscription Successful' % new_contact.product.name
						payload['response_status']= '00'
					elif 'notification_action' in payload.keys() and payload['notification_action'] == 'Deletion' and len(contact)>0:
						status = ContactStatus.objects.get(name='INACTIVE')
						if 'linkid' in payload.keys(): contact.filter(linkid=payload['linkid'])
						new_contact = contact[0]
						new_contact.subscribed = False
						new_contact.subscription_details = details[:1920]
						new_contact.status = status
						new_contact.save()
						payload['contact_id'] = new_contact.id
						payload['response'] = '%s UnSubscription Successful' % new_contact.product.name
						payload['response_status']= '00'
					else:
						payload['response_status'] = '05'
					payload = self.inbound_message(payload,{})
					return payload


				#check for profile gateway, capture or create gateway profile before subscribe | get session gateway profile for the gateway profile within the product gateway
				session_gateway_profile_list = GatewayProfile.objects.filter(msisdn=msisdn,\
							 gateway=notification_product[0].notification.code.gateway)
				if len(session_gateway_profile_list)>0:
					session_gateway_profile = session_gateway_profile_list[0]

					lgr.info('Session Gateway Profile: %s' % session_gateway_profile)
					payload = contact_entry_subscription(payload, session_gateway_profile, notification_product, msisdn)
				else:
					from primary.core.upc.tasks import System
					#Loop through code gateways and create msisdn profile for all gateways for the code and add each to contacts
					gateway = notification_product[0].notification.code.gateway
					try:
						gateway_profile_user = gateway_profile.user
						new_gateway_profile = GatewayProfile.objects.get(user=gateway_profile_user, gateway=gateway)
						payload['gateway_profile_id'] = new_gateway_profile.id
						payload = System().get_profile(payload, {})
						session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
						payload = contact_entry_subscription(payload, session_gateway_profile, notification_product, msisdn)
					except Exception, e:
						lgr.info('Error On creating gateway contact: %s' % e)
			else:
				payload['response'] = 'Notification Product Does not Exist'
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Subscribe: %s" % e)
		return payload

class Payments(System):
	pass

class Trade(System):
	pass


@app.task(ignore_result=True)
def send_contact_subscription(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node: %s" % (payload, node) )

		i = Contact.objects.get(id=payload['id'])
		if i.status.name <> 'PROCESSING':
			i.status = ContactStatus.objects.get(name='PROCESSING')
			i.save()

		payload = WebService().post_request(payload, node)
		lgr.info('Response: %s' % payload)

		########
		if 'response_status' in payload.keys() and payload['response_status'] == '00':
			if 'response' in payload.keys() and payload['response'] == 'EXISTS':
				status = ContactStatus.objects.get(name='ACTIVE')
				i.status = status
				i.subscribed = True
				i.save()
			elif 'response' in payload.keys() and payload['response'] == 'UNKNOWN':
				i.state = ContactStatus.objects.get(name='PROCESSING')
				i.save()
	
			else:
				status = ContactStatus.objects.get(name='INACTIVE')
				i.status = status
				i.save()
		else:
			i.state = ContactStatus.objects.get(name='FAILED')
			i.save()

	except Exception, e:
		lgr.info("Error on Sending Contact Subscription: %s" % e)

@app.task(ignore_result=True)
def send_contact_unsubscription(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node: %s" % (payload, node) )
		i = Contact.objects.get(id=payload['id'])
		if i.status.name <> 'PROCESSING':
			i.status = ContactStatus.objects.get(name='PROCESSING')
			i.save()


		payload = WebService().post_request(payload, node)
		lgr.info('Response: %s' % payload)

		########If response status not a success, the contact will remain processing
		if 'response_status' in payload.keys() and payload['response_status'] == '00':
			i.status = ContactStatus.objects.get(name="INACTIVE")
			i.subscribed = False

		else:
			i.status = ContactStatus.objects.get(name="PROCESSING")
			i.subscribed = False

		i.save()

	except Exception, e:
		lgr.info("Error on Sending Contact: %s" % e)

@app.task(ignore_result=True)
def notify_institution(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node Info: %s" % (payload, node) )
		if 'institution_url' in node.keys():
			endpoint = node['institution_url']
			lgr.info('Endpoint: %s' % endpoint)
			payload = WebService().post_request(payload, endpoint)
		lgr.info("Response||Payload: %s| Node Info: %s" % (payload, node) )

		payload['response'] = 'Institution Notified'
		payload['response_status']= '00'
	except Exception, e:
		payload['response_status'] = '96'
		lgr.info("Error on Notifying Institution: %s" % e)
	return payload


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def contact_unsubscription():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for inactive contacts that are still subscribed and have an unsubscription_endpoint
	contact = Contact.objects.select_for_update().filter(Q(subscribed=True),Q(status__name='INACTIVE'),\
			~Q(product__unsubscription_endpoint=None))[:10]

	for i in contact:
		try:
			i.status = ContactStatus.objects.get(name="PROCESSING")
			i.save()

			payload = {}
			payload['kmp_correlator'] = 'C%s' % i.id
			payload['kmp_recipients'] = [str(i.gateway_profile.msisdn.phone_number)]
			payload['kmp_spid'] = i.product.unsubscription_endpoint.account_id
			payload['kmp_password'] = i.product.unsubscription_endpoint.password
			payload['kmp_code'] = i.product.notification.code.code
			payload['kmp_service_id'] = i.product.notification.ext_service_id

			payload['kmp_product_id'] = i.product.ext_product_id
			payload['kmp_keyword'] = i.product.keyword
			payload['node_account_id'] = i.product.unsubscription_endpoint.account_id
			payload['node_username'] = i.product.unsubscription_endpoint.username
			payload['node_password'] = i.product.unsubscription_endpoint.password
			payload['node_api_key'] = i.product.unsubscription_endpoint.api_key


			#Send SMS
			node = i.product.unsubscription_endpoint.url
			lgr.info('Endpoint: %s' % node)
			payload['id'] = i.id

			payload = json.dumps(payload, cls=DjangoJSONEncoder)
			send_contact_unsubscription.delay(payload, node)

		except Exception, e:
			lgr.info('Error unsubscribing item: %s | %s' % (i,e))


@app.task(ignore_result=True)
def outbound_bulk_logger(payload, contact_list, scheduled_send):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		lgr.info('Outbound Bulk Logger Started')
		state = OutBoundState.objects.get(name='CREATED')
		#For Bulk Create, do not save each model in loop
		outbound_list = []
		for c in contact_list:
			contact = Contact.objects.get(id=c[0])
			outbound = Outbound(contact=contact,message=payload['message'],scheduled_send=scheduled_send,state=state, sends=0)
			#Notification for bulk uses contact records only for recipient
			if contact.product.notification.code.channel.name == 'SMS' and contact.gateway_profile.msisdn:
				outbound.recipient = contact.gateway_profile.msisdn.phone_number
			elif contact.product.notification.code.channel.name == 'EMAIL' and self.validateEmail(contact.gateway_profile.user.email):
				outbound.recipient = contact.gateway_profile.user.email
			elif contact.product.notification.code.channel.name == 'MQTT':
				outbound.recipient = contact.gateway_profile.user.profile.id
			else:
				lgr.info('Contact not matched to email or sms: %s' % contact)

			if 'notification_template_id' in payload.keys():
				template = NotificationTemplate.objects.get(id=payload['notification_template_id'])
				outbound.template = template
				outbound.heading = template.template_heading
			outbound_list.append(outbound)
		if len(outbound_list)>0:
			lgr.info('Outbound Bulk Logger Captured')
			Outbound.objects.bulk_create(outbound_list)
	except Exception, e:
		lgr.info("Error on Outbound Bulk Logger: %s" % e)



@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def contact_subscription():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) one hour ago
	contact = Contact.objects.select_for_update().filter(Q(subscribed=False),\
			Q(status__name='ACTIVE')|Q(status__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(hours=1)))[:10]

	for i in contact:
		try:
			i.status = ContactStatus.objects.get(name="PROCESSING")

			lgr.info('Subscription Status: False')
			if i.product.subscription_endpoint is not None:
				payload = {}
				payload['kmp_correlator'] = 'C%s' % (i.id)
				payload['kmp_recipients'] = [str(i.gateway_profile.msisdn.phone_number)]
				payload['kmp_spid'] = i.product.subscription_endpoint.account_id
				payload['kmp_password'] = i.product.subscription_endpoint.password
				payload['kmp_code'] = i.product.notification.code.code
				payload['kmp_service_id'] = i.product.notification.ext_service_id
	
				payload['kmp_product_id'] = i.product.ext_product_id
				payload['kmp_keyword'] = i.product.keyword
				payload['node_account_id'] = i.product.subscription_endpoint.account_id
				payload['node_username'] = i.product.subscription_endpoint.username
				payload['node_password'] = i.product.subscription_endpoint.password
				payload['node_api_key'] = i.product.subscription_endpoint.api_key

				#Send Subscription Request
				node = i.product.subscription_endpoint.url
				lgr.info('Endpoint: %s' % node)

				#No response is required on celery use (ignore results)
				payload['id'] = i.id

				payload = json.dumps(payload, cls=DjangoJSONEncoder)
				send_contact_subscription.delay(payload, node)

			elif i.product.subscription_endpoint is None and i.product.subscribable:
				status = ContactStatus.objects.get(name='ACTIVE')
				i.status = status
				i.subscribed = True
			else:
				status = ContactStatus.objects.get(name='INACTIVE')
				i.status = status
			i.save()
		except Exception, e:
			lgr.info('Error subscribing item: %s | %s' % (i,e))


@app.task(ignore_result=True)
def send_outbound(message):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		i = Outbound.objects.get(id=message)

		#add a valid phone number check
		message = i.message
                message = unescape(message)
		message = smart_str(message)
		message = escape(message)

		payload = {}
		payload['kmp_correlator'] = i.id
		payload['outbound_id'] = i.id

		payload['kmp_service_id'] = i.contact.product.notification.ext_service_id
		payload['kmp_code'] = i.contact.product.notification.code.code
		payload['kmp_message'] = message


		#USE A CHANGE PROFILE MSISDN
		try:
			payload['kmp_recipients'] = [str(i.recipient)]
			'''
			if i.contact.gateway_profile.changeprofilemsisdn and i.contact.gateway_profile.changeprofilemsisdn.status.name == 'ACTIVE' and i.contact.gateway_profile.changeprofilemsisdn.expiry >= timezone.now():
				payload['kmp_recipients'] = [str(i.contact.gateway_profile.changeprofilemsisdn.msisdn.phone_number)]

				#Disable Contact as it is temprorary awaiting confirmation
				i.contact.status = ContactStatus.objects.get(name='INACTIVE')
				i.contact.subscribed = False
				i.contact.save()
				#Change the Change MSISDN profile status to PROCESSING
				i.contact.gateway_profile.changeprofilemsisdn.status = ChangeProfileMSISDNStatus.objects.get(name='PROCESSED')
				i.contact.gateway_profile.changeprofilemsisdn.save()

			else:
				payload['kmp_recipients'] = [str(i.recipient)]
			'''
		except ObjectDoesNotExist:
			payload['kmp_recipients'] = [str(i.recipient)]

		if i.contact.product.notification.endpoint:
			payload['kmp_spid'] = i.contact.product.notification.endpoint.account_id
			payload['kmp_password'] = i.contact.product.notification.endpoint.password

			payload['node_account_id'] = i.contact.product.notification.endpoint.account_id
			payload['node_username'] = i.contact.product.notification.endpoint.username
			payload['node_password'] = i.contact.product.notification.endpoint.password
			payload['node_api_key'] = i.contact.product.notification.endpoint.api_key

			payload['contact_info'] = json.loads(i.contact.subscription_details)

			#Not always available
			payload['linkid'] = i.contact.linkid

			#Send SMS
			node = i.contact.product.notification.endpoint.url
			#No response is required on celery use (ignore results)
			#Wrappers().send_outbound.delay(payload, node)

			############################


			#lgr.info("Payload: %s| Node: %s" % (payload, node) )
			payload = WebService().post_request(payload, node)
			#lgr.info('Response: %s' % payload)


			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				i.state = OutBoundState.objects.get(name='SENT')

				#lgr.info('Product Expires(On-demand): %s' % i.contact.product.expires)
				if i.contact.product.expires == True:
					#lgr.info('Unsubscribe On-Demand Contact')
					i.contact.status = ContactStatus.objects.get(name='INACTIVE')
					i.contact.subscribed = False
					i.contact.save()

			else:
				i.state = OutBoundState.objects.get(name='FAILED')
			i.save()
			###############################
			#lgr.info('SMS Sent')
		else:
			lgr.info('No Endpoint')
			i.state = OutBoundState.objects.get(name='SENT')
			i.save()

	except Exception, e:
		lgr.info("Error on Sending Outbound: %s" % e)


@app.task(ignore_result=True)
def send_outbound2(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node: %s" % (payload, node) )
		payload = WebService().post_request(payload, node)
		lgr.info('Response: %s' % payload)

		outbound = Outbound.objects.get(id=payload['outbound_id'])
		if 'response_status' in payload.keys() and payload['response_status'] == '00':
			outbound.state = OutBoundState.objects.get(name='SENT')

			lgr.info('Product Expires(On-demand): %s' % outbound.contact.product.expires)
			if outbound.contact.product.expires == True:
				lgr.info('Unsubscribe On-Demand Contact')
				outbound.contact.status = ContactStatus.objects.get(name='INACTIVE')
				outbound.contact.subscribed = False
				outbound.contact.save()

		else:
			outbound.state = OutBoundState.objects.get(name='FAILED')
		outbound.save()
	except Exception, e:
		lgr.info("Error on Sending Outbound: %s" % e)


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_outbound_sms_messages():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)

	#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
	orig_outbound = Outbound.objects.select_for_update().filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='SMS'),\
				~Q(recipient=None),~Q(recipient=''),\
				Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=96))\
				|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(hours=6),date_created__gte=timezone.now()-timezone.timedelta(hours=96))\
				|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(hours=2),date_created__gte=timezone.now()-timezone.timedelta(hours=6)),\
				Q(contact__status__name='ACTIVE'))
	outbound = list(orig_outbound.values_list('id',flat=True)[:500])

	processing = orig_outbound.filter(id__in=outbound).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)
	for ob in outbound:
		send_outbound.delay(ob)

@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_outbound_email_messages():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
	outbound = Outbound.objects.select_for_update().filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='EMAIL'),\
				Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=96))\
				|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(hours=6),date_created__gte=timezone.now()-timezone.timedelta(hours=96))\
				|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(hours=2),date_created__gte=timezone.now()-timezone.timedelta(hours=6)),\
				Q(contact__status__name='ACTIVE')).\
				prefetch_related('contact').select_related('contact__gateway_profile','contact__product','contact__product__notification','contact__product__notification__code')[:500]

	for i in outbound:
		try:
			i.state = OutBoundState.objects.get(name='PROCESSING')
			i.sends = i.sends + 1
			i.save()

			channel = i.contact.product.notification.code.channel.name
			endpoint = i.contact.product.notification.endpoint
			email = i.recipient if i.recipient not in [None, ""] else i.contact.gateway_profile.user.email
			lgr.info('Before Sender')
			sender = '<%s>' % i.contact.product.notification.code.code
	
			lgr.info('Sender: %s' % sender)	
			if i.contact.product.notification.code.alias not in ['',None]:
				sender = '%s %s' % (i.contact.product.notification.code.alias, sender)
			lgr.info('Sender: %s' % sender)	
			if email not in [None,''] and Wrappers().validateEmail(email):
				try:
					gateway = i.contact.product.notification.code.gateway
					#subject, from_email, to = gateway.name +': '+str(i.heading), sender, email
					subject, from_email, to = str(i.heading), sender, email

					text_content = i.message 

					if i.template.template_file.file_path:
						html_content = loader.get_template(i.template.template_file.file_path.name) #html template with utf-8 charset
					else:
						html_content = loader.get_template('default_send_mail.html') #html template with utf-8 charset
					#d = Context({'message':unescape(i.message), 'gateway':gateway})
					d = {'message':unescape(i.message), 'gateway':gateway}
					html_content = html_content.render(d)
					html_content = smart_str(html_content)
					msg = EmailMultiAlternatives(subject, text_content, from_email, [to.strip()], headers={'Reply-To': from_email})

					msg.attach_alternative(html_content, "text/html")
					msg.send()              

					i.state = OutBoundState.objects.get(name='SENT')

				except Exception, e:
					lgr.info('Error Sending Mail: %s' % e)
					i.state = OutBoundState.objects.get(name='FAILED')

				except BadHeaderError:
					lgr.info('Bad Header: Error Sending Mail')
					i.state = OutBoundState.objects.get(name='FAILED')

			else:
				lgr.info('No Valid Email')

			i.save()
		except Exception, e:
			lgr.info('Error Sending item: %s | %s' % (i, e))



@app.task(ignore_result=True, soft_time_limit=259200) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
def send_bulk_sms():
	import csv, time
	with open('/var/www/html/eagle_africa1.csv', 'rb') as f:
		reader = csv.reader(f)
		your_list = map(tuple, reader)

	for c in your_list:
		try:
			service = 'SEND SMS'
			payload = {}
			payload['chid'] = '5'
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = '127.0.0.1'

			if c[0] not in ['',None] and '+' not in c[0]:
				payload['MSISDN'] = '+%s' % c[0].strip()
			elif c[0] not in ['',None]:
				payload['MSISDN'] = '%s' % c[0].strip()

			if c[1] not in ['',None]:
				payload['FULL_NAMES'] = c[1].strip()
			if c[5] not in ['',None]:
				payload['message'] = c[5].strip()[:160]
			outbound = Outbound.objects.filter(contact__gateway_profile__msisdn__phone_number=payload['MSISDN'],message__contains='Your 2015 Op Bal')
			if outbound.exists():
				lgr.info('Pass Exists: %s' % payload['MSISDN'])
			else:
				gateway_profile = GatewayProfile.objects.get(id=223057)
				service = Service.objects.get(name=service)
				w = Wrappers()
				try:w.service_call(w, service, gateway_profile, payload) #No async as float deduction needs sync
				except Exception, e: lgr.info('Error on Service Call: %s' % e)
		except Exception, e: lgr.info('Error On Send Bulk SMS: %s' % e)


'''
@app.task(ignore_result=True, soft_time_limit=259200) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
def add_gateway_bulk_contact():

	#g = GatewayProfile.objects.filter(~Q(gateway=Gateway.objects.get(id=14))).distinct('msisdn__phone_number')
	g = GatewayProfile.objects.filter(~Q(gateway=Gateway.objects.get(id=14))).values('msisdn__phone_number').annotate(Count('msisdn__phone_number')).order_by('-id')
	for c in g:
		try:
			service = 'ADD NOTIFICATION CONTACT'
			payload = {}
			payload['chid'] = '5'
			payload['lat'] = 0.0
			payload['lng'] = 0.0
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = 'nikobizz.com'
			payload['institution_id'] = '58'
			#payload['MSISDN'] = c.msisdn.phone_number
			payload['MSISDN'] = c['msisdn__phone_number']
			gateway_profile = GatewayProfile.objects.get(id=295739)
			service = Service.objects.get(name=service)
			try:Wrappers().service_call.delay(service, gateway_profile, payload) #No async as float deduction needs sync
			except Exception, e: lgr.info('Error on Service Call: %s' % e)
		except Exception, e: lgr.info('Error On Add Notification Contact: %s' % e)

'''

@app.task(ignore_result=True, soft_time_limit=259200) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
def add_bulk_contact():
	import csv, time
	with open('/var/www/html/NUNUA/customers.csv', 'rb') as f:
		reader = csv.reader(f)
		your_list = map(tuple, reader)

	for c in your_list:
		try:
			service = 'ADD NOTIFICATION CONTACT'
			payload = {}
			payload['chid'] = '5'
			payload['lat'] = 0.0
			payload['lng'] = 0.0
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = 'nunur.nikobizz.com'
			payload['institution_id'] = '58'
			payload['contact_group'] = 'CUSTOMERS'

			if c[0] not in ['',None] and '+' not in c[0]:
				payload['MSISDN'] = '+%s' % c[0].strip()
			elif c[0] not in ['',None]:
				payload['MSISDN'] = '%s' % c[0].strip()
			if c[2] not in ['',None]:
				payload['FULL_NAMES'] = c[2].strip()
			'''
			if c[3] not in ['',None]:
				payload['dob'] = c[3].strip()
			if c[4] not in ['',None]:
				payload['enrollment_date'] = c[4].strip()
			'''
			gateway_profile = GatewayProfile.objects.get(id=489061)
			service = Service.objects.get(name=service)
			'''
			try:Wrappers().service_call.delay(service, gateway_profile, payload) #No async as float deduction needs sync
			except Exception, e: lgr.info('Error on Service Call: %s' % e)
			'''

			w = Wrappers()
			try:w.service_call.apply_async((w, service, gateway_profile, payload), serializer='pickle')
			except Exception, e: lgr.info('Error on Service Call: %s' % e)

		except Exception, e: lgr.info('Error On Add Notification Contact: %s' % e)



'''

import billiard
from multiprocessing.util import Finalize

_finalizers = []

def show(timer):
	print timer
	return timer


@app.task
def f():
	p = billiard.Pool(3)
	_finalizers.append(Finalize(p, p.terminate))
	try:
		#p.map_async(time.sleep, [1000, 1000, 1000])
		p.apply_async(show, (1000,))
		p.close()
		p.join()
	finally:
		p.terminate()

'''




