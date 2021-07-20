from __future__ import absolute_import, unicode_literals
from celery import shared_task
from celery import group, chain
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

from django.template import Context, loader
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.contrib.gis.geoip2 import GeoIP2

import simplejson as json
from functools import reduce
from django.db import IntegrityError, DatabaseError
import pytz, time, pycurl
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.validators import validate_email
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
#import urllib, urllib2
from django.db import transaction
from xml.sax.saxutils import escape, unescape
from django.utils.encoding import smart_text
from django.db.models import Q, F
from django.db.models import Count, Sum, Max, Min, Avg
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers
from django.db.models.functions import TruncTime
import operator, string
from itertools import islice
from django.core.mail import EmailMultiAlternatives
from primary.core.upc.tasks import Wrappers as UPCWrappers
import numpy as np
import pandas as pd
from django.conf import settings
from collections import defaultdict

from primary.core.administration.views import WebService
from .models import *

import logging
lgr = logging.getLogger('secondary.channels.notify')

class Wrappers:
	def batch_product_send(self, payload, df_data, date_obj, notifications, ext_outbound_id, gateway_profile):
		profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
		scheduled_send = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
		state = OutBoundState.objects.get(name='CREATED')

		df_list = []
		obj_list = []
		r, c = df_data.shape
		for key, value in notifications.items():
			contact = Contact.objects.get(id=value['contact_id'])
			if contact.product.notification.code.channel.name == 'EMAIL':
				df_email=df_data['recipient'].astype(str).str.extract(r'(?P<email>^[\w\.\+\-]+\@[\w\.]+\.[a-z]{2,3}$)')
				df_email = df_email[~df_email['email'].isnull()]
				_recipient = df_email['email'].values
			elif contact.product.notification.code.channel.name == 'WHATSAPP':
				df_msisdn=df_data['recipient'].astype(str).str.extract(r'(?P<msisdn>^\+(:?[\d]*)$|(?:[\d]*)$)')
				df_msisdn = df_msisdn[~df_msisdn['msisdn'].isnull()]
				_recipient = df_msisdn['msisdn'].values
			else:
				mno = contact.product.notification.code.mno
				mno_prefix = MNOPrefix.objects.filter(mno=mno).values_list('prefix', flat=True)
				ccode=contact.product.notification.code.mno.country.ccode
				code = [re.findall(r'^\+'+ccode+'([\d]*)$', p)[0] for p in mno_prefix]
				prefix = '|'.join(code)
				fprefix = '|'.join(mno_prefix).replace('+','')

				df_prefix=df_data['recipient'].astype(str).str.extract(r'(?P<msisdn>^(?:('+prefix+')([\d]*)$)|^0(?:('+prefix+')([\d]*)$))')
				df_fprefix=df_data['recipient'].astype(str).str.extract(r'(?P<msisdn>^\+(?:('+fprefix+')[\d]*)$|^(?:('+fprefix+')([\d]*)$))')

				df_prefix = df_prefix[~df_prefix['msisdn'].isnull()]
				df_prefix['msisdn']=df_prefix['msisdn'].str.lstrip('0')
				df_prefix['msisdn']=ccode+df_prefix['msisdn'].astype(str)

				df_fprefix = df_fprefix[~df_fprefix['msisdn'].isnull()]

				_recipient = np.concatenate([df_prefix['msisdn'].values, df_fprefix['msisdn'].values])

			#Capture Recipients
			_recipient = np.unique(_recipient)
			lgr.info('\n\n\n\n\n\tRecipient: %s' % _recipient)
			_recipient_count = _recipient.size


			heading, template = None, None
			if 'notification_template_id' in payload.keys():
				template = NotificationTemplate.objects.get(id=payload['notification_template_id'])

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

			elif 'subject' in payload.keys():
				heading = payload['subject'].strip()[:512]

			#lgr.info('Message and Contact Captured: %s | %s | %s' % (mno.name, prefix, _recipient_count) )
			if r >= 100:
				df = pd.DataFrame({'recipient': _recipient})
				if template: df['template'] = template
				df['heading'] = heading
				df['message'] = payload['message']
				df['scheduled_send'] = scheduled_send
				df['contact'] = value['contact_id']
				df['state'] = state.id
				df['date_modified'] = timezone.now()
				df['date_created'] = timezone.now()
				df['sends'] = 0
				if 'contact_group' in payload.keys(): df['contact_group'] = payload['contact_group'] 
				df['pn'] = False
				df['pn_ack'] = False
				df['ext_outbound_id'] = ext_outbound_id
				df['inst_notified'] = False
				df['message_len'] = value['message_len'] if 'message_len' in value.keys() else 1

				df_list.append(df)
			else:
				contact = Contact.objects.get(id=value['contact_id'])
				contact_group = payload['contact_group'] if 'contact_group' in payload.keys() else None
				message_len =  value['message_len'] if 'message_len' in value.keys() else 1
				#Append by adding
				obj_list = obj_list+[Outbound(contact=contact, template=template, heading=heading, \
								message=payload['message'], scheduled_send=scheduled_send,\
								state=state, recipient=r, sends=0, ext_outbound_id=ext_outbound_id,\
								 contact_group=contact_group, message_len=message_len) for r in _recipient]

				lgr.info('\n\n\n\n\n\tObject List: %s' % obj_list)
		outbound_log = None

		if df_list:
			from django.core.files.base import ContentFile

			#lgr.info('DataFrame List: %s' % df_list)
			_df = pd.concat(df_list)

			#lgr.info('Recipient Outbound Bulk Logger Started: %s' % _df)
			f1 = ContentFile(_df.to_csv(index=False))

			outbound_log = Outbound.objects.from_csv(f1)

		if obj_list:
			outbound_log = Outbound.objects.bulk_create(obj_list)

		return outbound_log

	def batch_product_notifications(self, payload, df, product, message, gateway_profile):
		notifications = {}
		notifications_preview = {}
		lgr.info('Product: %s' % product)

		contact = Contact.objects.filter(product=product, gateway_profile=gateway_profile)
		status = ContactStatus.objects.get(name='ACTIVE') #User is active to receive notification
		if not len(contact):
			new_contact = Contact(status=status,product=product,subscription_details=json.dumps({}),\
					subscribed=True, gateway_profile=gateway_profile)
			new_contact.save()
		else:
			new_contact = contact[0]
			new_contact.status = status
			new_contact.subscribed=True
			new_contact.save()
		if product.notification.code.channel.name == 'EMAIL':
			df_email=df['recipient'].astype(str).str.extract(r'(?P<email>^[\w\.\+\-]+\@[\w\.]+\.[a-z]{2,3}$)')
			df_email = df_email[~df_email['email'].isnull()]
			_recipient = df_email['email'].values
			message_len = 1
		elif product.notification.code.channel.name == 'WHATSAPP':
			df_msisdn=df['recipient'].astype(str).str.extract(r'(?P<msisdn>^\+(:?[\d]*)$|(?:[\d]*)$)')
			df_msisdn = df_msisdn[~df_msisdn['msisdn'].isnull()]
			_recipient = df_msisdn['msisdn'].values
			message_len = 1
		else:
			#For SMS
			chunks, chunk_size = len(message), 160  # SMS Unit is 160 characters (NB: IN FUTURE!!, pick message_len from DB - notification_product)
			messages = [message[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
			message_len = len(messages)

			mno_prefix = MNOPrefix.objects.filter(mno=product.notification.code.mno).values_list('prefix', flat=True)

			ccode=product.notification.code.mno.country.ccode

			code = [re.findall(r'^\+'+ccode+'([\d]*)$', p)[0] for p in mno_prefix]

			prefix = '|'.join(code)

			fprefix = '|'.join(mno_prefix).replace('+','')

			lgr.info('Full Prefix: %s' % fprefix)
			lgr.info('Prefix: %s' % prefix)

			#df_prefix=df['recipient'].str.extract(r'(?P<msisdn>^(?:('+prefix+')([\d]*)$))')
			df_prefix=df['recipient'].astype(str).str.extract(r'(?P<msisdn>^(?:('+prefix+')([\d]*)$)|^0(?:('+prefix+')([\d]*)$))')
			df_fprefix=df['recipient'].astype(str).str.extract(r'(?P<msisdn>^\+(?:('+fprefix+')[\d]*)$|^(?:('+fprefix+')([\d]*)$))')

			df_prefix = df_prefix[~df_prefix['msisdn'].isnull()]
			df_prefix['msisdn']=df_prefix['msisdn'].str.lstrip('0')
			df_prefix['msisdn']=ccode+df_prefix['msisdn'].astype(str)

			df_fprefix = df_fprefix[~df_fprefix['msisdn'].isnull()]

			_recipient = np.concatenate([df_prefix['msisdn'].values, df_fprefix['msisdn'].values])

		#Capture Recipients
		_recipient = np.unique(_recipient)
		_recipient_count = _recipient.size

		if _recipient_count:
			unit_charge = (product.unit_credit_charge) #Pick the notification product cost
			product_charge = (unit_charge*Decimal(_recipient_count)*message_len)

			notifications[product.id] = {'float_amount': float(product_charge), 'float_product_type_id': product.notification.product_type.id, 
							'contact_id': new_contact.id, 'message_len':message_len }

			if product.notification.code.institution:
				notifications[product.id]['institution_id'] = product.notification.code.institution.id

			notifications_preview[product.notification.code.mno.name if product.notification.code.mno \
						else product.notification.code.channel.name] = {'float_amount': float(product_charge),
												'recipient_count':_recipient_count,
												'message_len':message_len,
												'alias':product.notification.code.alias}

		return notifications, notifications_preview

	def recipient_payload(self, payload):
		new_payload, transaction, count = {}, None, 1

		exempt_keys = ['card','credentials','new_pin','validate_pin','confirm_password','password','pin',\
					   'access_level','response_status','sec_hash','ip_address','service' ,'lat','lng',\
					   'chid','session','session_id','csrf_token','csrfmiddlewaretoken' , 'gateway_host' ,'gateway_profile' ,\
					   'transaction_timestamp' ,'action_id' , 'bridge__transaction_id','merchant_data', 'signedpares',\
					   'gpid','sec','fingerprint','vpc_securehash','currency','amount',\
					   'institution_id','response','input','trigger','send_minutes_period','send_hours_period',\
					   'send_days_period','send_years_period','token','repeat_bridge_transaction','transaction_auth',\
					   'gateway_id','file_upload','recipient','contact_group_id','gateway_profile_id','contact_group_name',\
					   'contact_group_description']

		for k, v in payload.items():
			try:
				value = json.loads(v)
				if isinstance(value, list) or isinstance(value, dict):continue
			except: pass
			key = k.lower()
			if key not in exempt_keys:
				if count <= 100:
					new_payload[str(k)[:30] ] = str(v)[:500]
				else:
					break
				count = count+1

		return new_payload



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
			payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))

			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception as e:
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
		except ValidationError as e:
			lgr.info("URL Validation Error: %s" % e)
			return False

class System(Wrappers):
	@transaction.atomic
	def session_subscription_send(self, payload, node_info):
		try:
			lgr.info('Log Outbound Contact Group Send: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if payload.get('scheduled_date') and payload.get('scheduled_time'):
				date_string = payload['scheduled_date']+' '+payload['scheduled_time']
				date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
			else:
				date_obj = datetime.now()
		
			lgr.info('Payload: %s' % payload)

			notifications = json.loads(payload['notifications_object'])

			lgr.info('Notifications: %s' % notifications)

			ext_outbound_id = None
			if "ext_outbound_id" in payload.keys():
				ext_outbound_id = payload['ext_outbound_id']
			elif 'bridge__transaction_id' in payload.keys():
				ext_outbound_id = payload['bridge__transaction_id']

			session_subscription = SessionSubscription.objects.select_for_update(nowait=True).filter(status__name='ACTIVE', 
							expiry__gte=timezone.now(),
							enrollment_type__product_item__institution=gateway_profile.institution,
							last_access__gte=timezone.now()-timezone.timedelta(seconds=1)*F('session_subscription_type__session_expiration'))

			if payload.get('session_subscription_type'):
				session_subscription = session_subscription.filter(session_subscription_type__name=payload['session_subscription_type'])

			if payload.get('expiry_hours_max'):
				session_subscription = session_subscription.filter(
							last_access__lte=timezone.now()-(
								(timezone.timedelta(seconds=1)*F('session_subscription_type__session_expiration'))-(
											timezone.timedelta(hours=1)*float(payload['expiry_hours_max'])
									)
								)
							)

			if payload.get('product_item'):
				session_subscription = session_subscription.filter(
							enrollment__enrollment_type__product_item__name=payload['product_item'])
			
			recipient=np.asarray(session_subscription.values_list('recipient', flat=True))
			#Update query after numpy capture
			session_subscription.update(sends=F('sends')+1)

			recipient = np.unique(recipient)

			df_data  = pd.DataFrame({'recipient': recipient})

			lgr.info(f'Recipient Contact Captured Data: {df_data.shape[0]}')
			if payload.get('message') and df_data.shape[0] and len(notifications):
				outbound_log = self.batch_product_send(payload, df_data, date_obj, notifications, ext_outbound_id, gateway_profile)
				lgr.info('Recipient Outbound Bulk Logger Completed Task')

				payload['response'] = 'Outbound Message Processed'
				payload['response_status']= '00'
			elif not payload.get('message') and df_data.shape[0]:
				payload['response'] = 'No Message to Send'
				payload['response_status']= '00'
			else:
				payload['response'] = 'No Contact/Message to Send'
				payload['response_status']= '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Session Subscription Send: %s" % e)
		return payload



	def session_subscription_details(self, payload, node_info):
		try:
			lgr.info('Get Product Outbound Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			session_subscription = SessionSubscription.objects.filter(status__name='ACTIVE', 
							expiry__gte=timezone.now(),
							enrollment_type__product_item__institution=gateway_profile.institution,
							last_access__gte=timezone.now()-timezone.timedelta(seconds=1)*F('session_subscription_type__session_expiration'))

			if payload.get('session_subscription_type'):
				session_subscription = session_subscription.filter(session_subscription_type__name=payload['session_subscription_type'])

			if payload.get('expiry_hours_max'):
				session_subscription = session_subscription.filter(
							last_access__lte=timezone.now()-(
								(timezone.timedelta(seconds=1)*F('session_subscription_type__session_expiration'))-(
											timezone.timedelta(hours=1)*float(payload['expiry_hours_max'])
									)
								)
							)

			if payload.get('product_item'):
				session_subscription = session_subscription.filter(
							enrollment__enrollment_type__product_item__name=payload['product_item'])

			recipient=np.asarray(session_subscription.values_list('recipient', flat=True))

			recipient = np.unique(recipient)

			df = pd.DataFrame({'recipient': recipient})

			notifications = dict()
			notifications_preview = dict()
			product_list = NotificationProduct.objects.filter(Q(notification__code__institution=gateway_profile.institution),\
									Q(notification__code__alias__iexact=payload['alias']),
									Q(notification__status__name='ACTIVE'), \
									Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
									 Q(service__name=payload['SERVICE'])).distinct('notification__code__mno__id')

			#Service is meant to send to unique MNOs with same alias, hence returns one product per MNO (distinct MNO)
			#lgr.info('Product List: %s' % product_list)
			# Message Len
			message = payload.get('message')
			notifications_preview['message'] = {'text': message, 'scheduled_date':payload.get('scheduled_date'),'scheduled_time':payload.get('scheduled_time')}

			if len(product_list):

				for product in product_list:
					ns,nsp = self.batch_product_notifications(payload, df, product, message, gateway_profile)
					if ns: notifications.update(ns)
					if nsp: notifications_preview.update(nsp)

				payload['notifications_object'] = json.dumps(notifications)
				payload['notifications_preview'] = json.dumps(notifications_preview)
				payload['response'] = 'Session Subscription Details Captured'
				payload['response_status']= '00'
			else:
				payload['response'] = 'Notification Product not Found'
				payload['response_status']= '25'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Session Subscription Details: %s" % e)
		return payload

	def update_session_subscription(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			enrollment = Enrollment.objects.get(id=payload['enrollment_id'])

			session_subscription_type_list = SessionSubscriptionType.objects.filter(service__name=payload['SERVICE'])

			status = SessionSubscriptionStatus.objects.get(name='ACTIVE')
			session_sub = SessionSubscription.objects.filter(gateway_profile=gateway_profile, expiry__gte=timezone.now(),
									enrollment_type=enrollment.enrollment_type,
									status=status)

			if len(session_sub):
				session_subscription.expiry = enrollment.expiry
				session_subscription = session_sub.last()
				session_subscription.last_access = timezone.now()
			else:
				session_subscription_type = session_subscription_type_list.first()
				session_subscription = SessionSubscription(gateway_profile=gateway_profile,expiry=enrollment.expiry,
									enrollment_type=enrollment.enrollment_type,
									session_subscription_type=session_subscription_type,
									last_access=timezone.now(), 
									status=status, sends=0)

				if session_subscription_type.channel.name in ['WHATSAPP','SMS']:
					msisdn = UPCWrappers().get_msisdn(payload)
					if msisdn: session_subscription.recipient = msisdn

			#Save either
			session_subscription.save()

			payload['response'] = 'Session Subscription Update'
			payload['response_status'] = '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on update session subscription: %s" % e)
		return payload

	def notification_template_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			notification_template = NotificationTemplate.objects.get(id=payload['notification_template_id'])

			payload['template_heading'] = notification_template.template_heading
			payload['template_message'] = notification_template.template_message

			payload['response'] = 'Notification Template Details Captured'
			payload['response_status'] = '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Notification Template Details: %s" % e)
		return payload


	def edit_notification_template_message(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			notification_template = NotificationTemplate.objects.get(id=payload['notification_template_id'])

			if 'template_message' in payload.keys() and payload['template_message'] not in ['',None]:
				notification_template.template_message = payload['template_message']
				notification_template.save()

				payload['response'] = 'Message Updated'
				payload['response_status'] = '00'
			else:
				payload['response'] = 'No Message to Update'
				payload['response_status'] = '25'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Editing Notification Template Message: %s" % e)
		return payload


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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Updating Notification Template: %s" % e)
		return payload

	def create_contact_group(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			status = ContactGroupStatus.objects.get(name='ACTIVE')
			contact_group = ContactGroup(name=payload['contact_group_name'].strip(), \
					description=payload['contact_group_description'], status=status,\
					institution=gateway_profile.institution,gateway=gateway_profile.gateway)

			contact_group.save()
			payload['contact_group_id'] = contact_group.id
			payload['response'] = 'Contact Group Created'
			payload['response_status'] = '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Updating Notification Template: %s" % e)

		return payload


	def delete_recipient_contact_group(self, payload, node_info):
		try:
			# gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			status = ContactGroupStatus.objects.get(name='DELETED')
			contact_group = ContactGroup.objects.get(pk=payload['contact_group_id'])
			contact_group.status = status
			contact_group.save()

			## Delete recipients
			#recipient_deleted_status = ContactStatus.objects.get(name='DELETED')
			#contact_group.recipient_set.update(status=recipient_deleted_status)

			payload['response'] = 'Recipient Contact Group Deleted'
			payload['response_status'] = '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Deleting Contact Group: %s" % e)

		return payload


	def delete_contact_group(self, payload, node_info):
		try:
			# gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			status = ContactGroupStatus.objects.get(name='DELETED')
			contact_group = ContactGroup.objects.get(pk=payload['contact_group_id'])
			contact_group.status = status
			contact_group.save()

			# Delete recipients
			recipient_deleted_status = ContactStatus.objects.get(name='DELETED')
			contact_group.recipient_set.update(status=recipient_deleted_status)

			payload['response'] = 'Contact Group Deleted'
			payload['response_status'] = '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Deleting Contact Group: %s" % e)

		return payload


	def contact_group_details(self, payload, node_info):
		try:
			contact_group = ContactGroup.objects.get(pk=payload['contact_group_id'])
			payload['contact_group_name'] = contact_group.name
			payload['contact_group_description'] = contact_group.description

			payload['response'] = 'Got Contact Group Details'
			payload['response_status'] = '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Contact Group Details: %s" % e)

		return payload


	def create_notification_template(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			service = Service.objects.get(name='TEMPLATE NOTIFICATION')
			status = TemplateStatus.objects.get(name='ACTIVE')

			product_list = NotificationProduct.objects.filter(Q(notification__code__institution=gateway_profile.institution),\
									Q(notification__code__alias__iexact=payload['alias']),
									Q(notification__status__name='ACTIVE'), \
									Q(notification__channel__id=payload['chid'])|Q(notification__channel=None))

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

			notification_template.product.add(*product_list)

			payload['response'] = 'Template Saved'
			payload['response_status'] = '00'

		except Exception as e:
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

		except Exception as e:
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

		except Exception as e:

			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Notification Template Details: %s" % e)

		return payload

	def add_recipient(self, payload, node_info):
		try:
			lgr.info("Add Recipient: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if 'recipient' in payload.keys() and (  UPCWrappers().simple_get_msisdn(str(payload['recipient']).strip()) or UPCWrappers.validateEmail(None,str(payload['recipient']).strip()) ):
				status = ContactStatus.objects.get(name='ACTIVE')
				contact_group = ContactGroup.objects.get(id=str(payload['contact_group_id']).strip())
				if not Recipient.objects.filter(recipient=str(payload['recipient']).strip(),contact_group=contact_group).exists():
					recipient = Recipient(status=status,subscribed=True,recipient=str(payload['recipient']).strip(),\
							details=json.dumps(self.recipient_payload(payload)),\
							contact_group=contact_group)
					recipient.save()

					payload['response_status'] = '00'
					payload['response'] = 'Recipient Added'
				else:
					payload['response_status'] = '26'
					payload['response'] = 'Recipient Exists'
			else:
					payload['response_status'] = '12'
					payload['response'] = 'Invalid Recipient'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Add Recipient: %s" % e)
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

			if contact.exists():
				#Change status to INACTIVE but leave subscribed=True. Celery service would check for INACTIVE contact purpoting to be subscribed and unsubscribe
				contact_status = ContactStatus.objects.get(name='INACTIVE')
				c = contact[0]
				c.status = contact_status
				c.save()

				payload['response'] = 'Contact Deactiated'
				payload["response_status"] = "00"
			else:
				payload['response_status'] = "25"
		except Exception as e:
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
				g = GeoIP2()



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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Notification: %s" % e)
		return payload

	def init_notification(self, payload, node_info):
		try:

			if 'alias' in payload.keys():
				del payload['alias'] #

			if 'notification_template_id' in payload.keys():
				del payload['notification_template_id'] #

			if 'notification_product_id' in payload.keys():
				del payload['notification_product_id'] #

			if 'message' in payload.keys():
				del payload['message']
			payload['response_status'] = '00'
			payload['response'] = 'Notification Initialized'
		except Exception as e:
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Init Notification: %s" % e)
		return payload


	def get_notification(self, payload, node_info):
		try:

			lgr.info("Payload: %s" % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if payload.get('alias'):
				notification_product = NotificationProduct.objects.filter(Q(notification__status__name='ACTIVE'), 
									Q(notification__code__gateway=gateway_profile.gateway),
									Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
									Q(notification__code__alias__iexact=payload['alias'].strip()),
									 Q(service__name=payload['SERVICE'])).\
									prefetch_related('notification__code','product_type')

			else:

				notification_product = NotificationProduct.objects.filter(Q(notification__status__name='ACTIVE'), \
									Q(notification__code__gateway=gateway_profile.gateway),\
									Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
									 Q(service__name=payload['SERVICE'])).\
									prefetch_related('notification__code','product_type')

			lgr.info('Notification Product: %s' % notification_product)
			msisdn = UPCWrappers().get_msisdn(payload)
			if msisdn is not None:
				#Get/Filter MNO
				code1=(len(msisdn) -7)
				code2=(len(msisdn) -6)
				code3=(len(msisdn) -5)

				prefix = MNOPrefix.objects.filter(prefix=msisdn[:code3])
				if not len(prefix):
					prefix = MNOPrefix.objects.filter(prefix=msisdn[:code2])
					if not len(prefix):
						prefix = MNOPrefix.objects.filter(prefix=msisdn[:code1])

				#lgr.info('MNO Prefix: %s|%s' % (prefix,msisdn))
				#Get Notification product
				if len(prefix): notification_product = notification_product.filter(Q(notification__code__mno=prefix[0].mno)|Q(notification__code__mno=None))
				else: notification_product = notification_product.none()
			elif 'session_gateway_profile_id' in payload.keys():
				contact = Contact.objects.filter(product__in=[p for p in notification_product],gateway_profile__id=payload['session_gateway_profile_id'])
				if 'notification_delivery_channel' in payload.keys():
					contact = contact.filter(product__notification__code__channel__name=payload['notification_delivery_channel'])

				if len(contact):
					lgr.info(contact)
					notification_product = notification_product.filter(id__in=[c.product.id for c in contact])

			lgr.info('Notification Product: %s ' % notification_product)

			if 'ext_product_id' in payload.keys():
				notification_product = notification_product.filter(Q(ext_product_id=payload['ext_product_id'])|Q(ext_product_id=None))

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
			institution = None
			if payload.get('institution_id'):
				institution = Institution.objects.get(id=payload['institution_id'])
			elif gateway_profile.institution:
				institution = gateway_profile.institution

			if institution:
				#Filter to send an institution notification or otherwise a gateway if institution does not exist (gateway only has institution as None)
				institution_notification_product = notification_product.filter(notification__code__institution=institution)
				if institution_notification_product.exists(): notification_product = institution_notification_product
				else:
					gateway_notification_product = notification_product.filter(notification__code__institution=None, institution_allowed=True)
					notification_product = gateway_notification_product
			else:
				notification_product = notification_product.filter(notification__code__institution=None)

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
				notification_template = notification_template_list[0] if len(notification_template_list) else None


			lgr.info('Notification Product: %s ' % notification_product)
			if len(notification_product):
				def get_template(mapTags=True):
					#Construct Message to send
					if 'message' not in payload.keys():
						if notification_template:
							payload['notification_template_id'] = notification_template.id
							message = notification_template.template_message
							if mapTags:
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
				#lgr.info('Payload: %s' % payload)
				if 'product_item_id' in payload.keys(): del payload['product_item_id'] #Avoid deduction of float

				if notification_product[0].notification.code.institution:
					payload['institution_id'] = notification_product[0].notification.code.institution.id
				else:
					if 'institution_id' in payload.keys(): del payload['institution_id'] #User gateway Float if exists, if not, fail


				float_amount = (notification_product[0].unit_credit_charge) #Pick the notification product cost
				if 'recipient_count' in payload.keys():
					float_amount = float_amount*Decimal(payload['recipient_count'])

				payload_d = defaultdict(lambda: "...")
				payload_d.update(payload)

				#Calculate price per SMS per each 160 characters
				if notification_product[0].notification.code.channel.name == 'SMS':
					_ = get_template()
					payload['message'] = payload['message'].strip().format_map(payload_d)
					message = payload['message']
					message = unescape(message)
					message = smart_text(message)
					message = escape(message)
					chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
					messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
					payload['message_len'] = len(messages)
					float_amount = float_amount*len(messages)
				elif notification_product[0].notification.code.channel.name == 'WHATSAPP':
					_ = get_template(False)
					message = json.loads(payload['message']) if payload.get('message') else dict()
					if message.get('type') == 'interactive':
						message['interactive']['body']['text'] = message['interactive']['body']['text'].\
											strip().format_map(payload_d)
					elif message.get('type') == 'text':
						message['text']['body'] = message['text']['body'].\
											strip().format_map(payload_d)
					elif message.get('type') == 'image' and message['image'].get('caption'):
						message['image']['caption'] = message['video']['caption'].\
											strip().format_map(payload_d)
					elif message.get('type') == 'video' and message['video'].get('caption'):
						message['video']['caption'] = message['video']['caption'].\
											strip().format_map(payload_d)
					if message: payload['message'] = json.dumps(message)
				else:
					_ = get_template()
					payload['message'] = payload['message'].strip().format_map(payload_d)

				#Finally
				payload['alias'] = notification_product[0].notification.code.alias
				payload['float_product_type_id'] = notification_product[0].notification.product_type.id
				payload['float_amount'] = float_amount
				payload['response'] = "Notification Captured : %s" % notification_product[0].id 
				payload['response_status']= '00'
			elif len(notification_product)<1 and 'notification_product_id' in payload.keys():
				del payload['notification_product_id'] #Avoid send SMS
				if 'product_item_id' in payload.keys(): del payload['product_item_id'] #Avoid deduction of float
				payload['response'] = 'Notification Product not found'
				payload["response_status"] = "00"
				
			else:
				payload['response'] = 'Notification Product Not found'
				payload["response_status"] = "25"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Notification: %s" % e,exc_info=True)
		return payload

	def get_email_notification(self, payload, node_info):
		payload['notification_delivery_channel'] = 'EMAIL'
		return self.get_notification(payload, node_info)

	def get_sms_notification(self, payload, node_info):
		payload['notification_delivery_channel'] = 'SMS'
		return self.get_notification(payload, node_info)

	def get_batch_notification(self, payload, node_info):

		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			lgr.info('Payload: %s' % payload)
			notification_product = NotificationProduct.objects.filter(Q(notification__status__name='ACTIVE'), \
						Q(notification__code__gateway=gateway_profile.gateway),\
						Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
						 Q(service__name=payload['SERVICE'])).\
						prefetch_related('notification__code','product_type')




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
				gateway_notification_product = notification_product.filter(notification__code__institution=None, institution_allowed=True)
				notification_product =  institution_notification_product if len(institution_notification_product) else gateway_notification_product
			else:
				notification_product = notification_product.filter(notification__code__institution=None)

			lgr.info('Notification Product: %s ' % notification_product)
			if "keyword" in payload.keys():
				notification_product=notification_product.filter(keyword__iexact=payload['keyword'])

			lgr.info('Notification Product: %s ' % notification_product)
			
			#Distinct is meant to send to unique MNOs with same alias, hence returns one notification_product per MNO (distinct MNO)
			notification_product.distinct('notification__code__alias','notification__code__mno__id','notification__code__channel__name')

			lgr.info('Product List: %s' % notification_product)

			if 'notification_template_id' in payload.keys():
				notification_template = NotificationTemplate.objects.get(id=payload['notification_template_id'])
				notification_product = notification_product.filter(id__in=[t.id for t in notification_template.product.all()])
			else:
				#get notification_template using service
				notification_template_list = NotificationTemplate.objects.filter(product__in=notification_product,service__name=payload['SERVICE'])

				notification_template_list = self.trigger_notification_template(payload,notification_template_list)
				notification_template = notification_template_list[0] if len(notification_template_list) else None

			lgr.info('Notification Product: %s ' % notification_product)

			recipient_list = json.loads(payload['recipients'])

			recipient=np.asarray(recipient_list)
			recipient = np.unique(recipient)

			if len(notification_product) and len(recipient)<=100:
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


				# Message Len

				payload['message'] = payload['message'].strip().format(**payload)
				message = payload['message']
				message = unescape(message)
				message = smart_text(message)
				message = escape(message)


				df = pd.DataFrame({'recipient': recipient})

				notifications = dict()
				notifications_preview = dict()

				notifications_preview['message'] = {
									'text':message,
									'scheduled_date':payload['scheduled_date'] if 'scheduled_date' in payload.keys() else None,
									'scheduled_time':payload['scheduled_time'] if 'scheduled_time' in payload.keys() else None
									}

				#lgr.info('Recipients: %s' % recipient)
				for product in notification_product:
					ns,nsp = self.batch_product_notifications(payload, df, product, message, gateway_profile)
					if ns: notifications.update(ns)
					if nsp: notifications_preview.update(nsp)
				payload['notifications_object'] = json.dumps(notifications)
				payload['notifications_preview'] = json.dumps(notifications_preview)
				payload['response'] = 'Batch Request Captured'
				payload['response_status']= '00'
			elif not notification_product.exists():
				payload["response_status"] = "25"
				payload['response'] = 'Notification Product not Found'
			else:	
				payload["response_status"] = "25"
				payload['response'] = 'No Recipients Found'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Get Batch Notification: %s" % e,exc_info=True)
		return payload


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
					if "linkid" in payload.keys():
						contact = contact.filter(linkid=payload['linkid'])

					status = ContactStatus.objects.get(name='ACTIVE') #User is active to receive notification
					if not len(contact):
						details = json.dumps({})
						new_contact = Contact(status=status,product=notification_product,subscription_details=details,\
								gateway_profile=session_gateway_profile)

						#On create Contact, apply create_subscribe. Existing contacts, do not apply
						if notification_product.subscribable:
							new_contact.subscribed=notification_product.create_subscribe
						else:
							new_contact.subscribed=True

						if "linkid" in payload.keys():
							new_contact.linkid=payload['linkid']
						new_contact.save()
					else:
						new_contact = contact[0]
						new_contact.status = status
						if not notification_product.subscribable and not new_contact.subscribed: #Subscribe Unsubscribed where not subscribable on send
							new_contact.subscribed=True

						new_contact.save()
					state = OutBoundState.objects.get(name='CREATED')

					message = payload['message']
					message = unescape(message)
					message = smart_text(message)
					message = escape(message)

					outbound = Outbound(contact=new_contact,message=message,scheduled_send=scheduled_send,state=state, sends=0)
					if ext_outbound_id is not None:
						outbound.ext_outbound_id = ext_outbound_id

					if new_contact.product.notification.code.channel.name in ['SMS','WHATSAPP']:
						msisdn = UPCWrappers().get_msisdn(payload)
						if msisdn:
							outbound.recipient = msisdn
						elif new_contact.gateway_profile.msisdn:
							outbound.recipient = new_contact.gateway_profile.msisdn.phone_number
					elif new_contact.product.notification.code.channel.name == 'EMAIL':
						if 'email' in payload.keys() and self.validateEmail(payload["email"]):
							outbound.recipient = payload['email']
						elif new_contact.gateway_profile.user.email:
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
					elif 'subject' in payload.keys():
						outbound.heading = payload['subject'].strip()[:512]

					if 'message_len' in payload.keys(): outbound.message_len = payload['message_len'] 

					outbound.save()

					#Ensure there's a unique value for ext_outbound_id
					if not outbound.ext_outbound_id: 
						outbound.ext_outbound_id = outbound.id
						outbound.save()
					'''
					if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:

						template_file = NotificationAttachment()

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
					'''

					payload['response'] = "Notification Sent. Please check %s" % notification_product.notification.code.channel.name
					payload['response_status']= '00'
				else:

					payload['response'] = 'No message to send'
					payload['response_status'] = '25'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Send Notification: %s" % e)
		return payload

	def send_batch_notification(self, payload, node_info):

		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			lgr.info('Payload: %s' % payload)
			notifications = json.loads(payload['notifications_object'])
			lgr.info('Notifications: %s' % notifications)
			try:date_obj = datetime.strptime(payload["scheduled_send"], '%d/%m/%Y %I:%M %p')
			except: date_obj = datetime.now()

			ext_outbound_id = None
			if "ext_outbound_id" in payload.keys():
				ext_outbound_id = payload['ext_outbound_id']
			elif 'bridge__transaction_id' in payload.keys():
				ext_outbound_id = payload['bridge__transaction_id']

			recipient_list = json.loads(payload['recipients'])

			recipient=np.asarray(recipient_list)
			recipient = np.unique(recipient)

			df_data = pd.DataFrame({'recipient': recipient})

			if 'message' in payload.keys() and payload['message'] not in ['',None] and recipient.size and len(notifications):
				outbound_log = self.batch_product_send(payload, df_data, date_obj, notifications, ext_outbound_id, gateway_profile)
				lgr.info('Recipient Outbound Bulk Logger Completed Task')
				payload['response'] = 'Batch Notification Sent'
				payload['response_status']= '00'
			elif len(recipient_list):
				payload['response'] = 'No Message to Send'
				payload['response_status']= '00'
			else:
				payload['response'] = 'No Recipient/Message to Send'
				payload['response_status']= '00'


		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Send Batch Notification: %s" % e,exc_info=True)
		return payload



	def process_delivery_status(self, payload, node_info):
		try:
			#lgr.info("Process Delivery Status: %s" % payload)

			outbound_id = payload['outbound_id']
			delivery_status = payload['delivery_status']
			outbound = Outbound.objects.select_related('contact').filter(ext_outbound_id=outbound_id.strip())
			if 'recipient' in payload.keys():
				outbound = outbound.filter(recipient=payload['recipient'].strip())
			if 'ext_service_id' in payload.keys() and payload['ext_service_id'] not in [None,'']:
				outbound = outbound.filter(contact__product__notification__ext_service_id=payload['ext_service_id'])

			#lgr.info('Outbound List: %s' % outbound)
			if len(outbound):
				this_outbound = outbound[0]
				#lgr.info("This outbound: %s|Delivery Status: %s" % (this_outbound, delivery_status) )
				if delivery_status in ['RESEND']:
					#lgr.info('Delivery Status: To retry in an hour')
					state = OutBoundState.objects.get(name='CREATED')
					this_outbound.state = state
					this_outbound.scheduled_send=timezone.now()+timezone.timedelta(hours=1)
					this_outbound.save()
				elif delivery_status in ['UNSUBSCRIBED'] and this_outbound.contact.product.subscribable:
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

				elif delivery_status in ['UNSUBSCRIBED']:
					#lgr.info('Delivery Status: Unsubscribed User, UNSUBSCRIBED on unsubscribable')
					state = OutBoundState.objects.get(name='UNSUBSCRIBED')
					this_outbound.state = state
					this_outbound.save()
				elif delivery_status in ['DELIVERED']:
					#lgr.info('Delivery Status: Succesfully Delivered')
					state = OutBoundState.objects.get(name='DELIVERED')
					this_outbound.state = state
					this_outbound.save()
				elif delivery_status in ['INVALID']:
					#lgr.info('Delivery Status: Failed')
					state = OutBoundState.objects.get(name='INVALID')
					this_outbound.state = state
					this_outbound.save()
				elif delivery_status in ['UNDELIVERED']:
					#lgr.info('Delivery Status: Failed')
					state = OutBoundState.objects.get(name='UNDELIVERED')
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
		except Exception as e:
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
				if not len(contact):
					new_contact = Contact(status=status,product=notification_product[0],subscription_details=details[:1920],\
							gateway_profile=session_gateway_profile)

					#On create Contact, apply create_subscribe. Existing contacts, do not apply
					if notification_product[0].subscribable:
						new_contact.subscribed=notification_product[0].create_subscribe
					else:
						if not notification_product.subscribable and not new_contact.subscribed: #Subscribe Unsubscribed where not subscribable on send
							new_contact.subscribed=True

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

				message = message.strip().format(**payload)

				outbound = Outbound(contact=new_contact, message=message, scheduled_send=timezone.now()+timezone.timedelta(seconds=5), state=state, sends=0)

				if new_contact.product.notification.code.channel.name in ['SMS','WHATSAPP']:
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
				elif 'subject' in payload.keys():
					outbound.heading = payload['subject'].strip()[:512]

				if 'message_len' in payload.keys(): outbound.message_len = payload['message_len'] 

				outbound.save()

				payload['response'] = 'Notification Sent. Subscription: %s' % outbound.contact.product.name
			else:
				payload['response'] = "Notification Not Found"
			payload['response_status']= '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on creating Notification: %s" % e)
		return payload



	def unsubscribe_recipient(self, payload, node_info):
		try:
			recipient = Recipient.objects.get(id=payload['recipient_id'])
			recipient.subscribed = False
			recipient.save()
			
			payload['response'] = 'Recipient UnSubscribed'
			payload['response_status']= '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on UnSubscribing Recipient: %s" % e,exc_info=True)
		return payload

	def subscribe_recipient(self, payload, node_info):
		try:
			recipient = Recipient.objects.get(id=payload['recipient_id'])
			recipient.subscribed = True
			recipient.save()
			
			payload['response'] = 'Recipient Subscribed'
			payload['response_status']= '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Subscribing Recipient: %s" % e,exc_info=True)
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Message: %s" % e)
		return payload


	def recipient_contact_group_send_details(self, payload, node_info):
		try:
			lgr.info('Get Product Outbound Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			def pandas_factory(colnames, rows):
				return pd.DataFrame(rows, columns=colnames)

			#Session required within task 
			from cassandra.cqlengine.connection import session
			session.row_factory = pandas_factory
			session.default_fetch_size = 150000 #needed for large queries, otherwise driver will do pagination. Default is 50000.

			#query=f"select * from switch.notify_recipient where contact_group_id in ? and status=?"
			query=f"select * from switch.notify_recipient where contact_group_id in ?"
			#_bound = dict(contact_group_id=[a for a in payload['contact_group_id'].split(',') if a], status=str('ACTIVE'))
			#_bound = tuple(([int(a) for a in payload['contact_group_id'].split(',') if a], 'ACTIVE'))
			_bound = tuple(([int(a) for a in payload['contact_group_id'].split(',') if a],))
			prepared_query = session.prepare(query)
			bound = prepared_query.bind(_bound) 
			rows = session.execute(bound)
			df = rows._current_rows
			df = df[['recipient']]

			notifications = dict()
			notifications_preview = dict()
			product_list = NotificationProduct.objects.filter(Q(notification__code__institution=gateway_profile.institution),\
									Q(notification__code__alias__iexact=payload['alias']),
									Q(notification__status__name='ACTIVE'), \
									Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
									 Q(service__name=payload['SERVICE'])).distinct('notification__code__mno__id')

			#Service is meant to send to unique MNOs with same alias, hence returns one product per MNO (distinct MNO)
			#lgr.info('Product List: %s' % product_list)
			# Message Len

			message = payload['message'].strip()
			message = unescape(message)
			message = smart_text(message)
			message = escape(message)
			notifications_preview['message'] = {'text':message,'scheduled_date':payload['scheduled_date'],'scheduled_time':payload['scheduled_time']}

			if len(product_list):

				for product in product_list:
					ns,nsp = self.batch_product_notifications(payload, df, product, message, gateway_profile)
					if ns: notifications.update(ns)
					if nsp: notifications_preview.update(nsp)

				payload['notifications_object'] = json.dumps(notifications)
				payload['notifications_preview'] = json.dumps(notifications_preview)
				payload['contact_group'] = '\n'.join(ContactGroup.objects.filter(id__in=[a for a in payload['contact_group_id'].split(',') if a]).values_list('name', flat=True))
				payload['response'] = 'Contact Group Send Details Captured'
				payload['response_status']= '00'
			else:
				payload['response'] = 'Notification Product not Found'
				payload['response_status']= '25'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Contact Group Send Details: %s" % e)
		return payload


	def contact_group_send_details(self, payload, node_info):
		try:
			lgr.info('Get Product Outbound Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			recipient_list = Recipient.objects.filter(subscribed=True,status__name='ACTIVE',\
							contact_group__id__in=[a for a in payload['contact_group_id'].split(',') if a],\
							contact_group__institution=gateway_profile.institution,\
							contact_group__gateway=gateway_profile.gateway).values_list('recipient', flat=True)

			#recipient_count = recipient.count()

			recipient=np.asarray(recipient_list)
			recipient = np.unique(recipient)

			df = pd.DataFrame({'recipient': recipient})

			notifications = dict()
			notifications_preview = dict()
			product_list = NotificationProduct.objects.filter(Q(notification__code__institution=gateway_profile.institution),\
									Q(notification__code__alias__iexact=payload['alias']),
									Q(notification__status__name='ACTIVE'), \
									Q(notification__channel__id=payload['chid'])|Q(notification__channel=None),
									 Q(service__name=payload['SERVICE'])).distinct('notification__code__mno__id')

			#Service is meant to send to unique MNOs with same alias, hence returns one product per MNO (distinct MNO)
			#lgr.info('Product List: %s' % product_list)
			# Message Len

			message = payload['message'].strip()
			message = unescape(message)
			message = smart_text(message)
			message = escape(message)
			notifications_preview['message'] = {'text':message,'scheduled_date':payload['scheduled_date'],'scheduled_time':payload['scheduled_time']}

			if len(product_list):

				for product in product_list:
					ns,nsp = self.batch_product_notifications(payload, df, product, message, gateway_profile)
					if ns: notifications.update(ns)
					if nsp: notifications_preview.update(nsp)

				payload['notifications_object'] = json.dumps(notifications)
				payload['notifications_preview'] = json.dumps(notifications_preview)
				payload['contact_group'] = '\n'.join(ContactGroup.objects.filter(id__in=[a for a in payload['contact_group_id'].split(',') if a]).values_list('name', flat=True))
				payload['response'] = 'Contact Group Send Details Captured'
				payload['response_status']= '00'
			else:
				payload['response'] = 'Notification Product not Found'
				payload['response_status']= '25'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Contact Group Send Details: %s" % e)
		return payload


	def contact_group_list_details(self, payload, node_info):
		try:
			lgr.info('Get Product Outbound Notification: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			recipient_list = Recipient.objects.filter(subscribed=True,status__name='ACTIVE',\
							contact_group__id__in=[a for a in payload['contact_group_id'].split(',') if a],\
							contact_group__institution=gateway_profile.institution,\
							contact_group__gateway=gateway_profile.gateway).values_list('recipient', flat=True)

			#recipient_count = recipient.count()

			recipient=np.asarray(recipient_list)
			recipient = np.unique(recipient)
			recipient_count = recipient.size
			payload['recipient_count'] = recipient_count
			payload['contact_group'] = '\n'.join(ContactGroup.objects.filter(id__in=[a for a in payload['contact_group_id'].split(',') if a]).values_list('name', flat=True))

			product = NotificationProduct.objects.get(id=payload['notification_product_id'])
			contact = Contact.objects.filter(product=product, gateway_profile=gateway_profile)
			status = ContactStatus.objects.get(name='ACTIVE') #User is active to receive notification
			if not len(contact):
				new_contact = Contact(status=status,product=product,subscription_details=json.dumps({}),\
						subscribed=True, gateway_profile=gateway_profile)
				new_contact.save()
			else:
				new_contact = contact[0]
				new_contact.status = status
				new_contact.subscribed=True
				new_contact.save()

			#Message Len

			message = payload['message'].strip()
			message = unescape(message)
			message = smart_text(message)
			message = escape(message)
			chunks, chunk_size = len(message), 160 #SMS Unit is 160 characters
			messages = [ message[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
			message_len = len(messages)

			payload['recipient_count'] = recipient_count
			payload['message_len'] = message_len
			payload['contact_id'] = new_contact.id
			payload['response'] = 'Contact Group of %d Recipient(s) to receive %s message(s)' % (recipient_count, message_len)
			payload['response_status']= '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Contact Group List Details: %s" % e)
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

					message = payload['message']
					message = unescape(message)
					message = smart_text(message)
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Notification Charges: %s" % e)
		return payload


	def log_recipient_contact_group_send(self, payload, node_info):
		try:
			lgr.info('Log Outbound Contact Group Send: %s' % payload)

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			date_string = payload['scheduled_date']+' '+payload['scheduled_time']
			date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
		
			lgr.info('Payload: %s' % payload)

			notifications = json.loads(payload['notifications_object'])

			lgr.info('Notifications: %s' % notifications)

			ext_outbound_id = None
			if "ext_outbound_id" in payload.keys():
				ext_outbound_id = payload['ext_outbound_id']
			elif 'bridge__transaction_id' in payload.keys():
				ext_outbound_id = payload['bridge__transaction_id']

			def pandas_factory(colnames, rows):
				return pd.DataFrame(rows, columns=colnames)

			#Session required within task 
			from cassandra.cqlengine.connection import session
			session.row_factory = pandas_factory
			session.default_fetch_size = 150000 #needed for large queries, otherwise driver will do pagination. Default is 50000.

			#query=f"select * from switch.notify_recipient where contact_group_id in ? and status=?"
			query=f"select * from switch.notify_recipient where contact_group_id in ?"
			#_bound = dict(contact_group_id=[a for a in payload['contact_group_id'].split(',') if a], status=str('ACTIVE'))
			lgr.info(f'Query: {query}')
			#_bound = tuple(([int(a) for a in payload['contact_group_id'].split(',') if a], 'ACTIVE'))
			_bound = tuple(([int(a) for a in payload['contact_group_id'].split(',') if a],))
			lgr.info(f'Bound: {_bound}')
			prepared_query = session.prepare(query)
			lgr.info(f'Prepared: {prepared_query}')
			bound = prepared_query.bind(_bound) 
			lgr.info(f'Bound 2: {bound}')
			rows = session.execute(bound)
			lgr.info(f'Rows: {rows}')
			df = rows._current_rows
			lgr.info(f'DF: {df.head()}')
			df_data = df[['recipient']]
			lgr.info(f'Recipient Contact Captured Data: {df.shape[0]}')
			if 'message' in payload.keys() and df.shape[0] and len(notifications):
				outbound_log = self.batch_product_send(payload, df_data, date_obj, notifications, ext_outbound_id, gateway_profile)
				lgr.info('Recipient Outbound Bulk Logger Completed Task')

				payload['response'] = 'Outbound Message Processed'
				payload['response_status']= '00'
			elif 'message' not in payload.keys() and len(recipient_list):
				payload['response'] = 'No Message to Send'
				payload['response_status']= '00'
			else:
				payload['response'] = 'No Contact/Message to Send'
				payload['response_status']= '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Log Recipient Contact Group Send: %s" % e)
		return payload



	def log_contact_group_send(self, payload, node_info):
		try:
			lgr.info('Log Outbound Contact Group Send: %s' % payload)

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			date_string = payload['scheduled_date']+' '+payload['scheduled_time']
			date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
		
			lgr.info('Payload: %s' % payload)

			notifications = json.loads(payload['notifications_object'])

			lgr.info('Notifications: %s' % notifications)

			ext_outbound_id = None
			if "ext_outbound_id" in payload.keys():
				ext_outbound_id = payload['ext_outbound_id']
			elif 'bridge__transaction_id' in payload.keys():
				ext_outbound_id = payload['bridge__transaction_id']

			recipient_list = Recipient.objects.filter(subscribed=True,status__name='ACTIVE',\
							contact_group__id__in=[a for a in payload['contact_group_id'].split(',') if a],\
							contact_group__institution=gateway_profile.institution,\
							contact_group__gateway=gateway_profile.gateway).values_list('recipient', flat=True)

			#recipient_count = recipient.count()

			recipient=np.asarray(recipient_list)
			recipient = np.unique(recipient)

			df_data = pd.DataFrame({'recipient': recipient})


			if 'message' in payload.keys() and recipient.size and len(notifications):
				outbound_log = self.batch_product_send(payload, df_data, date_obj, notifications, ext_outbound_id, gateway_profile)
				lgr.info('Recipient Outbound Bulk Logger Completed Task')

				payload['response'] = 'Outbound Message Processed'
				payload['response_status']= '00'
			elif 'message' not in payload.keys() and len(recipient_list):
				payload['response'] = 'No Message to Send'
				payload['response_status']= '00'
			else:
				payload['response'] = 'No Contact/Message to Send'
				payload['response_status']= '00'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Log Contact Group Send: %s" % e)
		return payload


	def log_contact_group_message(self, payload, node_info):
		try:
			lgr.info('Log Outbound Message: %s' % payload)

			date_string = payload['scheduled_date']+' '+payload['scheduled_time']
			date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
		
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
			scheduled_send = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

			notification_product = NotificationProduct.objects.get(id=payload['notification_product_id'])

			'''

			recipient_list = Recipient.objects.filter(Q(subscribed=True,status__name='ACTIVE',\
							contact_group__id__in=[a for a in payload['contact_group_id'].split(',') if a],\
							contact_group__institution=gateway_profile.institution,\
							contact_group__gateway=gateway_profile.gateway),\
							~Q(recipient__in=Outbound.objects.filter(date_created__gte=timezone.now()-timezone.timedelta(hours=2),message__icontains='TONIGHT SURE FIXED 108 ODDS ARE IN! ID:XX97').values_list('recipient',flat=True)))\
							.values_list('recipient', flat=True)



			'''

			recipient_list = Recipient.objects.using('read').filter(subscribed=True,status__name='ACTIVE',\
							contact_group__id__in=[a for a in payload['contact_group_id'].split(',') if a],\
							contact_group__institution=gateway_profile.institution,\
							contact_group__gateway=gateway_profile.gateway)\
							.values_list('recipient', flat=True)

			if 'message' in payload.keys() and len(recipient_list):

				lgr.info('Message and Contact Captured')
				#Bulk Create Outbound
				recipient=np.asarray(recipient_list)
				recipient = np.unique(recipient)
				#recipient_outbound_bulk_logger.delay(payload, recipient, scheduled_send)

				#recipient_outbound_bulk_logger(payload, recipient, scheduled_send)

				lgr.info('Recipient Outbound Bulk Logger Started')

				df = pd.DataFrame({'recipient': recipient})
				df['message'] = payload['message']
				df['scheduled_send'] = scheduled_send
				df['contact'] = payload['contact_id']
				df['state'] = OutBoundState.objects.get(name='CREATED').id
				df['date_modified'] = timezone.now()
				df['date_created'] = timezone.now()
				df['sends'] = 0
				if 'contact_group' in payload.keys(): df['contact_group'] = payload['contact_group'] 
				df['pn'] = False
				df['pn_ack'] = False
				df['ext_outbound_id'] = payload['bridge__transaction_id']
				df['inst_notified'] = False
				from django.core.files.base import ContentFile

				f1 = ContentFile(df.to_csv(index=False))

				outbound_log = Outbound.objects.from_csv(f1)

				lgr.info('Recipient Outbound Bulk Logger Completed Task')



				'''
				df = pd.DataFrame({'recipient': recipient})
				df['message'] = payload['message']
				df['scheduled_send'] = scheduled_send
				df['contact'] = payload['contact_id']
				df['state'] = OutBoundState.objects.get(name='CREATED').id
				df['date_modified'] = timezone.now()
				df['date_created'] = timezone.now()
				df['sends'] = 0
				df['pn'] = False
				df['pn_ack'] = False
				df['inst_notified'] = False

				from django.core.files.base import ContentFile
				f1 = ContentFile(df.to_csv(index=False))
				outbound_log = Outbound.objects.from_csv(f1)
				'''

				payload['response'] = 'Outbound Message Processed'
				payload['response_status']= '00'
			elif 'message' not in payload.keys() and len(recipient_list):
				payload['response'] = 'No Message to Send'
				payload['response_status']= '00'
			else:
				payload['response'] = 'No Contact/Message to Send'
				payload['response_status']= '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Log Outbound Message: %s" % e)
		return payload


	def log_notification_message(self, payload, node_info):
		try:
			lgr.info('Log Outbound Message: %s' % payload)

			try:
				date_string = payload['scheduled_date']+' '+payload['scheduled_time']
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
					contact_outbound_bulk_logger.apply_async((payload, contact_list, scheduled_send), serializer='json')

					payload['response'] = 'Outbound Message Processed'
					payload['response_status']= '00'
				elif 'message' not in payload.keys() and len(contact_list)>0:
					payload['response'] = 'No Message to Send'
					payload['response_status']= '00'
				else:
					payload['response'] = 'No Contact/Message to Send'
					payload['response_status']= '00'
		except Exception as e:
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
				if contact.product.notification.code.channel.name in ['SMS','WHATSAPP']:
					msisdn = UPCWrappers().get_msisdn(payload)
					if msisdn:
						inbound.recipient = msisdn
					elif contact.gateway_profile.msisdn:
						inbound.recipient = contact.gateway_profile.msisdn.phone_number
				elif contact.product.notification.code.channel.name == 'EMAIL':
					if 'email' in payload.keys() and self.validateEmail(payload["email"]):
						inbound.recipient = payload['email']
					else:
						inbound.recipient = contact.gateway_profile.user.email
				elif contact.product.notification.code.channel.name == 'MQTT':
					if 'pn_notification_id' in payload.keys() and payload['pn_notification_id'] not in ['',None]:
						inbound.recipient = payload['pn_notification_id']
					else:
						inbound.recipient = contact.gateway_profile.user.profile.id

				inbound.save()
				#notify institution
				if inbound.contact.product.notification.institution_url not in [None, ""]:
					node = {}
					node['institution_url'] = inbound.contact.product.notification.institution_url
					#self.notify_institution.delay(payload, node)
					notify_institution.delay(self, payload, node)

			payload['response'] = 'Inbox Message Successful'
			payload['response_status']= '00'
		except Exception as e:
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
			if not len(prefix):
				prefix = MNOPrefix.objects.filter(prefix=msisdn[:code2])
				if not len(prefix):
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
						if not contact.exists()  or 'linkid' in payload.keys():
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
					elif 'notification_action' in payload.keys() and payload['notification_action'] == 'Deletion' and contact.exists():
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
					except Exception as e:
						lgr.info('Error On creating gateway contact: %s' % e)
			else:
				payload['response'] = 'Notification Product Does not Exist'
				payload['response_status'] = '25'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Subscribe: %s" % e)
		return payload

class Payments(System):
	pass

class Trade(System):
	pass

@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def update_credentials():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for inactive contacts that are still subscribed and have an unsubscription_endpoint
	credential = Credential.objects.select_for_update().filter(updated=True, token_expiration__lte=timezone.now())
	lgr.info('Credentials: %s' % credential)
	for i in credential:
		try:
			i.updated = False
			i.save()

			payload = {}
			payload['name'] = i.name
			payload['description'] = i.description
			payload['api_key'] = i.api_key
			payload['api_secret'] = i.api_secret
			payload['api_token'] = i.api_token
			payload['access_token'] = i.access_token

			lgr.info('Request: %s' % payload)
			#Send SMS
			node = i.url
			lgr.info('Endpoint: %s' % node)

			payload = WebService().post_request(payload, node, timeout=5)
			lgr.info('Response: %s' % payload)

			########If response status not a success, the contact will remain processing
			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				i.api_token = payload['response']['api_token']
				if 'access_token' in payload['response'].keys():
					i.access_token = payload['response']['access_token']
			else: lgr.info('Credentials Response not a success')

		except Exception as e:
			lgr.info('Error update credentials: %s | %s' % (i,e))

		#Reset to retry in validity period whether succesful or not
		i.token_expiration = timezone.now() + timezone.timedelta(seconds=i.token_validity)
		i.updated = True
		i.save()

@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def update_delivery_status(data):
	try:
		df = pd.DataFrame(data)
		#df['recipient'] = df['recipient'].apply(lambda x: '+%s' % x.strip() if x.strip()[:1] != '+' else x)
		for status in df['delivery_status'].unique():
			status_df = df[df['delivery_status']==status]
			state = OutBoundState.objects.get(name=status)
			q_list = map(lambda n: Q(recipient__endswith=n[1]['recipient'],ext_outbound_id=n[1]['outbound_id']), status_df.iterrows())
			#q_list = map(lambda n: Q(recipient__contains=n[1]['recipient'],ext_outbound_id=n[1]['outbound_id']), status_df.iterrows())
			q_list = reduce(lambda a, b: a | b, q_list)
			Outbound.objects.filter(~Q(state__name=status), q_list).update(state=state)

	except Exception as e:
		lgr.info('Error on Update Delivery Status')
	


@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def get_delivery_status():
	try:
		#df = pd.DataFrame(WebService().post_request({"module":"sdp", "function":"getSmsDeliveryStatusResponse",  "limit":10000, "min_duration": {"seconds": 60}, "max_duration": {"seconds": 0}}, 'http://192.168.137.28:732/data/request/')['response']['data'])
		#df = pd.DataFrame(WebService().post_request({"module":"sdp", "function":"dtsvc",  "limit":10000, "min_duration": {"seconds": 123}, "max_duration": {"seconds": 120}}, 'http://192.168.137.28:732/data/request/')['response']['data'])
		#data = WebService().post_request({"module":"sdp", "function":"dtsvc",  "limit":10000, "min_duration": {"seconds": 125}, "max_duration": {"seconds": 120}}, 'http://192.168.137.28:7321/data/request/', timeout=5)['response']['data']
		data = WebService().post_request({"module":"sdp", "function":"dtsvc",  "limit":10000, "min_duration": {"seconds": 125}, "max_duration": {"seconds": 120}}, 'https://integrator.interintel.co/data/request/', timeout=5)['response']['data']

		if data:
			dchunks, dchunk_size = len(data), 125
			tasks = [update_delivery_status.s(data[i:i+dchunk_size]) for i in range(0, dchunks, dchunk_size)]
			#lgr.info('Tasks: %s' % tasks)

			chunks, chunk_size = len(tasks), 100
			status_tasks = [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]

	except Exception as e:
		lgr.info('Error on Get Delivery Status')
	

@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def get_delivery_status_test():
	try:
		#df = pd.DataFrame(WebService().post_request({"module":"sdp", "function":"getSmsDeliveryStatusResponse",  "limit":10000, "min_duration": {"seconds": 60}, "max_duration": {"seconds": 0}}, 'http://192.168.137.28:732/data/request/')['response']['data'])
		#df = pd.DataFrame(WebService().post_request({"module":"sdp", "function":"dtsvc",  "limit":10000, "min_duration": {"seconds": 123}, "max_duration": {"seconds": 120}}, 'http://192.168.137.28:732/data/request/')['response']['data'])
		#data = WebService().post_request({"module":"sdp", "function":"dtsvc",  "limit":20000, "min_duration": {"seconds": 123}, "max_duration": {"seconds": 120}}, 'http://192.168.137.28:732/data/request/', timeout=5)['response']['data']
		data = WebService().post_request({"module":"sdp", "function":"dtsvc",  "limit":20000, "min_duration": {"seconds": 123}, "max_duration": {"seconds": 120}}, 'https://integrator.interintel.co/data/request/', timeout=5)['response']['data']

		if data:
			df = pd.DataFrame(data)
			#df['recipient'] = df['recipient'].apply(lambda x: '+%s' % x.strip() if x.strip()[:1] != '+' else x)
			for status in df['delivery_status'].unique():
				status_df = df[df['delivery_status']==status]
				state = OutBoundState.objects.get(name=status)
				#q_list = map(lambda n: Q(recipient__contains=n[1]['recipient'],ext_outbound_id=n[1]['outbound_id']), status_df.iterrows())
				q_list = map(lambda n: Q(recipient__endswith=n[1]['recipient'],ext_outbound_id=n[1]['outbound_id']), status_df.iterrows())
				q_list = reduce(lambda a, b: a | b, q_list)
				Outbound.objects.filter(~Q(state__name=status), q_list).update(state=state)

	except Exception as e:
		lgr.info('Error on Get Delivery Status')
	

@app.task(ignore_result=True)
def send_contact_subscription(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node: %s" % (payload, node) )

		i = Contact.objects.get(id=payload['id'])
		if i.status.name != 'PROCESSING':
			i.status = ContactStatus.objects.get(name='PROCESSING')
			i.save()

		payload = WebService().post_request(payload, node, timeout=5)
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

	except Exception as e:
		lgr.info("Error on Sending Contact Subscription: %s" % e)

@app.task(ignore_result=True)
def send_contact_unsubscription(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node: %s" % (payload, node) )
		i = Contact.objects.get(id=payload['id'])
		if i.status.name != 'PROCESSING':
			i.status = ContactStatus.objects.get(name='PROCESSING')
			i.save()


		payload = WebService().post_request(payload, node, timeout=5)
		lgr.info('Response: %s' % payload)

		########If response status not a success, the contact will remain processing
		if 'response_status' in payload.keys() and payload['response_status'] == '00':
			i.status = ContactStatus.objects.get(name="INACTIVE")
			i.subscribed = False

		else:
			i.status = ContactStatus.objects.get(name="PROCESSING")
			i.subscribed = False

		i.save()

	except Exception as e:
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
			payload = WebService().post_request(payload, endpoint, timeout=5)
		lgr.info("Response||Payload: %s| Node Info: %s" % (payload, node) )

		payload['response'] = 'Institution Notified'
		payload['response_status']= '00'
	except Exception as e:
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
	contact = Contact.objects.select_for_update().filter(Q(subscribed=True),Q(status__name='INACTIVE'),Q(product__subscribable=True),\
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

		except Exception as e:
			lgr.info('Error unsubscribing item: %s | %s' % (i,e))



#PAUSED not used
@app.task(ignore_result=True, serializer='pickle', time_limit=1000, soft_time_limit=900)
@transaction.atomic
def outbound_bulk_logger(batch):
	try:
		outbound = Outbound.objects.bulk_create(batch)
		lgr.info('Succesfully Logged to Outbound')
	except Exception as e:
		lgr.info("Error on Outbound Bulk Logger: %s" % e)


@app.task(ignore_result=True, serializer='pickle', time_limit=1000, soft_time_limit=900)
def recipient_outbound_bulk_logger(payload, recipient, scheduled_send):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		import time
		start_time = time.time()
		lgr.info('Recipient Outbound Bulk Logger Started')

		df = pd.DataFrame({'recipient': recipient})
		df['message'] = payload['message']
		df['scheduled_send'] = scheduled_send
		df['contact'] = payload['contact_id']
		df['state'] = OutBoundState.objects.get(name='CREATED').id
		df['date_modified'] = timezone.now()
		df['date_created'] = timezone.now()
		df['sends'] = 0
		df['pn'] = False
		df['pn_ack'] = False
		df['inst_notified'] = False

		from django.core.files.base import ContentFile

		f1 = ContentFile(df.to_csv(index=False))

		outbound_log = Outbound.objects.from_csv(f1)

		lgr.info('Recipient Outbound Bulk Logger Completed Task')
	except Exception as e:
		lgr.info("Error on Outbound Bulk Logger: %s" % e)


@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
@transaction.atomic
def recipient_outbound_bulk_logger_deprecated(payload, recipient_list, scheduled_send):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		lgr.info('Recipient Outbound Bulk Logger Started')

		state = OutBoundState.objects.get(name='CREATED')
		contact = Contact.objects.get(id=payload['contact_id'])
		#'''
		objs = [Outbound(contact=contact,message=payload['message'],scheduled_send=scheduled_send,state=state, recipient=r, sends=0) for r in recipient_list]
		outbound = Outbound.objects.bulk_create(objs, 10000)

		'''

		objs = (Outbound(contact=contact,message=payload['message'],scheduled_send=scheduled_send,state=state, recipient=r, sends=0) for r in recipient_list)
		batch_size = 10000
		start = 0
		tasks = []
		while True:
			batch = list(islice(objs, start, start+batch_size))
			start+=batch_size
			if not batch: break
			tasks.append(outbound_bulk_logger.s(batch))

		chunks, chunk_size = len(tasks), 500
		outbound_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]

		'''
		lgr.info('Recipient Outbound Bulk Logger Completed Task')
	except Exception as e:
		lgr.info("Error on Outbound Bulk Logger: %s" % e)



@app.task(ignore_result=True)
def contact_outbound_bulk_logger(payload, contact_list, scheduled_send):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		lgr.info('Outbound Bulk Logger Started')
		state = OutBoundState.objects.get(name='CREATED')
		#For Bulk Create, do not save each model in loop
		outbound_list = []
		for c in contact_list:
			contact = Contact.objects.get(id=c[0])
			message_len =  payload['message_len'] if 'message_len' in payload.keys() else 1
			outbound = Outbound(contact=contact,message=payload['message'],scheduled_send=scheduled_send,state=state, sends=0, message_len=message_len)
			#Notification for bulk uses contact records only for recipient
			if contact.product.notification.code.channel.name in ['SMS','WHATSAPP'] and contact.gateway_profile.msisdn:
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
			elif 'subject' in payload.keys():
				outbound.heading = payload['subject'].strip()[:512]

			outbound_list.append(outbound)
		if len(outbound_list)>0:
			lgr.info('Outbound Bulk Logger Captured')
			Outbound.objects.bulk_create(outbound_list)
	except Exception as e:
		lgr.info("Error on Outbound Bulk Logger: %s" % e)



@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def contact_subscription():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) one hour ago
	contact = Contact.objects.select_for_update().filter(Q(subscribed=False),Q(product__subscribable=True),\
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
		except Exception as e:
			lgr.info('Error subscribing item: %s | %s' % (i,e))

def _send_outbound_batch(message_list):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		i = Outbound.objects.filter(id__in=message_list)

		#add a valid phone number check
		message = i.first().message
		message = unescape(message)
		message = smart_text(message)
		message = escape(message)
		payload = {}

		i.update(ext_outbound_id = i.first().id)

		payload['kmp_correlator'] = i.first().id

		payload['kmp_correlator'] = i.first().id
		#payload['kmp_correlator'] = 'e'.join(message_list)
		payload['outbound_id'] = i.first().id

		payload['kmp_service_id'] = i.first().contact.product.notification.ext_service_id
		payload['kmp_code'] = i.first().contact.product.notification.code.code
		payload['kmp_message'] = message

		payload['kmp_recipients'] = np.unique(np.asarray(i.values_list('recipient', flat=True))).tolist()

		if i.first().contact.product.notification.endpoint:
			if i.first().contact.product.notification.endpoint.request not in [None, ""]:
				try:payload.update(i.first().contact.product.notification.endpoint.request)
				except:pass

			payload['kmp_spid'] = i.first().contact.product.notification.endpoint.account_id
			payload['kmp_password'] = i.first().contact.product.notification.endpoint.password

			payload['node_account_id'] = i.first().contact.product.notification.endpoint.account_id
			payload['node_username'] = i.first().contact.product.notification.endpoint.username
			payload['node_password'] = i.first().contact.product.notification.endpoint.password
			payload['node_api_key'] = i.first().contact.product.notification.endpoint.api_key
			if i.first().contact.product.notification.endpoint.credential:
				payload['api_key'] = i.first().contact.product.notification.endpoint.credential.api_key
				payload['api_secret'] = i.first().contact.product.notification.endpoint.credential.api_secret
				payload['api_token'] = i.first().contact.product.notification.endpoint.credential.api_token
				payload['access_token'] = i.first().contact.product.notification.endpoint.credential.access_token

			payload['contact_info'] = json.loads(i.first().contact.subscription_details)

			#Send SMS
			node = i.first().contact.product.notification.endpoint.url
			lgr.info("Payload: %s| Node: %s" % (payload, node) )
			payload = WebService().post_request(payload, node, timeout=5)
			lgr.info('Batch Response: %s' % payload)

			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				updates = {}
				updates['state'] = OutBoundState.objects.get(name='SENT')
				if 'response' in payload.keys(): updates['response'] = payload['response'][:200]
				
				i.update(**updates)
			else:
				updates = {}
				updates['state'] = OutBoundState.objects.get(name='FAILED')
				if 'response' in payload.keys(): updates['response'] = payload['response'][:200]

				i.update(**updates)
		else:
			lgr.info('No Endpoint')
			i.update(state = OutBoundState.objects.get(name='SENT'))

	except Exception as e:
		lgr.info("Error on Sending Outbound Batch: %s" % e)

def _send_outbound(message):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		i = Outbound.objects.get(id=message)
		#add a valid phone number check
		message = i.message
		message = unescape(message)
		message = smart_text(message)
		message = escape(message)

		payload = {}

		if not i.ext_outbound_id:
			i.ext_outbound_id = i.id
			i.save()

		payload['kmp_correlator'] = i.ext_outbound_id
		payload['outbound_id'] = i.id

		payload['kmp_service_id'] = i.contact.product.notification.ext_service_id
		payload['kmp_code'] = i.contact.product.notification.code.code
		payload['kmp_message'] = message


		payload['kmp_recipients'] = [str(i.recipient)]

		if i.contact.product.notification.endpoint:
			if i.contact.product.notification.endpoint.request not in [None, ""]:
				try:payload.update(i.contact.product.notification.endpoint.request)
				except:pass

			payload['kmp_spid'] = i.contact.product.notification.endpoint.account_id
			payload['kmp_password'] = i.contact.product.notification.endpoint.password

			payload['node_account_id'] = i.contact.product.notification.endpoint.account_id
			payload['node_username'] = i.contact.product.notification.endpoint.username
			payload['node_password'] = i.contact.product.notification.endpoint.password
			payload['node_api_key'] = i.contact.product.notification.endpoint.api_key
			if i.contact.product.notification.endpoint.credential:
				payload['api_key'] = i.contact.product.notification.endpoint.credential.api_key
				payload['api_secret'] = i.contact.product.notification.endpoint.credential.api_secret
				payload['api_token'] = i.contact.product.notification.endpoint.credential.api_token
				payload['access_token'] = i.contact.product.notification.endpoint.credential.access_token

			payload['contact_info'] = json.loads(i.contact.subscription_details)

			#Not always available
			payload['linkid'] = i.contact.linkid

			#Send SMS
			node = i.contact.product.notification.endpoint.url
			lgr.info("Payload: %s| Node: %s" % (payload, node) )
			payload = WebService().post_request(payload, node, timeout=5)
			lgr.info('Response: %s' % payload)


			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				i.state = OutBoundState.objects.get(name='SENT')

				#lgr.info('Product Expires(On-demand): %s' % i.contact.product.expires)
				if i.contact.product.expires:
					#lgr.info('Unsubscribe On-Demand Contact')
					i.contact.status = ContactStatus.objects.get(name='INACTIVE')
					i.contact.subscribed = False
					i.contact.save()

			else:
				i.state = OutBoundState.objects.get(name='FAILED')
			#lgr.info('SMS Sent')
			###############################
			if 'response' in payload.keys(): i.response = payload['response'][:200]
			#Save all actions
			i.save()

		else:
			lgr.info('No Endpoint')
			i.state = OutBoundState.objects.get(name='SENT')
			###############################
			#Save all actions
			i.save()


	except Exception as e:
		lgr.info("Error on Sending Outbound: %s" % e)


def _send_outbound_list(payload):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		#Send SMS
		node = payload['node_url']
		lgr.info("Payload: %s| Node: %s" % (payload, node) )
		payload = WebService().post_request(payload, node, timeout=5)
		lgr.info('Response: %s' % payload)

	except Exception as e:
		lgr.info("Error on Sending Outbound: %s" % e)


@app.task(ignore_result=True)
def send_outbound_batch_list(payload):
	_send_outbound_list(payload)

@app.task(ignore_result=True)
def send_outbound_list(payload):
	_send_outbound_list(payload)


@app.task(ignore_result=True)
def bulk_send_outbound_batch_list(payload):
	_send_outbound_list(payload)

@app.task(ignore_result=True)
def bulk_send_outbound_list(payload):
	_send_outbound_list(payload)



@app.task(ignore_result=True)
def send_outbound_batch(message):
	_send_outbound_batch(message)

@app.task(ignore_result=True)
def send_outbound(message):
	_send_outbound(message)


@app.task(ignore_result=True)
def bulk_send_outbound_batch(message):
	_send_outbound_batch(message)

@app.task(ignore_result=True)
def bulk_send_outbound(message):
	_send_outbound(message)


@app.task(ignore_result=True)
def send_outbound2(payload, node):
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	try:
		payload = json.loads(payload)
		lgr.info("Payload: %s| Node: %s" % (payload, node) )
		payload = WebService().post_request(payload, node, timeout=5)
		lgr.info('Response: %s' % payload)

		outbound = Outbound.objects.get(id=payload['outbound_id'])
		if 'response_status' in payload.keys() and payload['response_status'] == '00':
			outbound.state = OutBoundState.objects.get(name='SENT')

			lgr.info('Product Expires(On-demand): %s' % outbound.contact.product.expires)
			if outbound.contact.product.expires:
				lgr.info('Unsubscribe On-Demand Contact')
				outbound.contact.status = ContactStatus.objects.get(name='INACTIVE')
				outbound.contact.subscribed = False
				outbound.contact.save()

		else:
			outbound.state = OutBoundState.objects.get(name='FAILED')
		outbound.save()
	except Exception as e:
		lgr.info("Error on Sending Outbound: %s" % e)

def _send_outbound_sms_messages_list(is_bulk, limit_batch):
	try:
		#from celery.utils.log import get_task_logger
		lgr = get_task_logger(__name__)
		orig_outbound = Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='SMS'),\
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),contact__product__trading_box__close_time__gte=timezone.localtime().time())),\
					~Q(recipient=None),~Q(recipient=''),~Q(contact__product__notification__endpoint__url=None),~Q(contact__product__notification__endpoint__url=''),\
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=96)),\
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk)).order_by('contact__product__priority').select_related('contact')



		lgr.info('Orig Outbound: %s' % orig_outbound)

		outbound = orig_outbound[:limit_batch].values_list('id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',\
                                                'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',\
                                                'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',\
                                                'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url')
	
		lgr.info('Outbound: %s' % outbound)
		if len(outbound):
			messages=np.asarray(outbound)

			lgr.info('Messages: %s' % messages)
			#Update State
			processing = orig_outbound.filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

			df = pd.DataFrame({'kmp_recipients':messages[:,1], 'product':messages[:,2], 'batch':messages[:,3],'kmp_correlator':messages[:,4],'kmp_service_id':messages[:,5],'kmp_code':messages[:,6],\
				'kmp_message':messages[:,7],'kmp_spid':messages[:,8],'kmp_password':messages[:,9],'node_account_id':messages[:,8],'node_password':messages[:,9],'node_username':messages[:,10],\
				'node_api_key':messages[:,11],'contact_info':messages[:,12],'linkid':messages[:,13],'node_url':messages[:,14]})

			lgr.info('DF: %s' % df)
			df['batch'] = pd.to_numeric(df['batch'])
			df = df.dropna(axis='columns',how='all')
			cols = df.columns.tolist()
			#df.set_index(cols, inplace=True)
			#df = df.sort_index()
			cols.remove('kmp_recipients')
			grouped_df = df.groupby(cols)

			tasks = []
			for name,group_df in grouped_df:
				batch_size = group_df['batch'].unique()[0]
				kmp_recipients = group_df['kmp_recipients'].unique().tolist()
				payload = dict()    
				for c in cols: payload[c] = str(group_df[c].unique()[0])
				#lgr.info('MULTI: %s \n %s' % (group_df.shape,group_df.head()))
				if batch_size>1 and len(group_df.shape)>1 and group_df.shape[0]>1:
					objs = kmp_recipients
					lgr.info('Got Here (multi): %s' % objs)
					start = 0
					while True:
						batch = list(islice(objs, start, start+batch_size))
						start+=batch_size
						if not batch: break
						payload['kmp_recipients'] = batch
						lgr.info(payload)
						if is_bulk: tasks.append(bulk_send_outbound_batch_list.s(payload))
						else: tasks.append(send_outbound_batch_list.s(payload))
				elif len(group_df.shape)>1 :
					lgr.info('Got Here (list of singles): %s' % kmp_recipients)
					for d in kmp_recipients:
						payload['kmp_recipients'] = [d]       
						lgr.info(payload)
						if is_bulk: tasks.append(bulk_send_outbound_list.s(payload))
						else: tasks.append(send_outbound_list.s(payload))
				else:
					lgr.info('Got Here (single): %s' % kmp_recipients)
					payload['kmp_recipients'] = kmp_recipients
					lgr.info(payload)
					if is_bulk: tasks.append(bulk_send_outbound_list.s(payload))
					else: tasks.append(send_outbound_list.s(payload))

			lgr.info('Got Here 10: %s' % tasks)

			chunks, chunk_size = len(tasks), 100
			sms_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]

	except Exception as e:
		lgr.info('Error on Send Outbound SMS Messages: %s ' % e)


@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_outbound_sms_messages_list():
	_send_outbound_sms_messages_list(is_bulk=False, limit_batch=240)

@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def bulk_send_outbound_sms_messages_list():
	_send_outbound_sms_messages_list(is_bulk=True, limit_batch=240)



def _send_outbound_sms_messages(is_bulk, limit_batch):
	try:
		#from celery.utils.log import get_task_logger
		lgr = get_task_logger(__name__)
		#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
		'''
		orig_outbound = Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='SMS'),\
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),contact__product__trading_box__close_time__gte=timezone.localtime().time())),\
					~Q(recipient=None),~Q(recipient=''),\
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
					|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
					|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)),\
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk)).order_by('contact__product__priority').select_related('contact','template','state')
		'''

		#.order_by('contact__product__priority').select_related('contact','template','state')
		orig_outbound = Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='SMS'),~Q(recipient=None),
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk),
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),
					contact__product__trading_box__close_time__gte=timezone.localtime().time())),
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
					|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
					|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)))\
					.select_related('contact','template','state')

		outbound = orig_outbound[:limit_batch].values_list('id','recipient','state__name','message','contact__product__id','contact__product__notification__endpoint__batch')
		if len(outbound):
			messages=np.asarray(outbound)

			#if messages.size > 0 and outbound.exists():
			#lgr.info('Here 3: %s' % messages.size)
			#if messages.size > 0:

			#Update State
			processing = orig_outbound.filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

			df = pd.DataFrame({'ID':messages[:,0], 'MSISDN':messages[:,1], 'STATE':messages[:,2], 'MESSAGE':messages[:,3], 'PRODUCT':messages[:,4], 'BATCH':messages[:,5]  })

			df['BATCH'] = pd.to_numeric(df['BATCH'])

			df.set_index(['MESSAGE','PRODUCT','BATCH'], inplace=True)
			df = df.sort_index()

			tasks = []
			for x in df.index.unique():
				batch_size = x[2]
				ID= df.loc[(x),:]['ID']
				lgr.info('MULTI: %s \n %s' % (df.loc[(x),:].shape,df.loc[(x),:].head()))
				if batch_size>1 and len(df.loc[(x),:].shape)>1 and df.loc[(x),:].shape[0]>1:
					objs = ID.values
					#lgr.info('Got Here (multi): %s' % x[0])
					start = 0
					while True:
						#lgr.info('Objs: %s | start: %s | batch_size: %s |' % (objs, start, batch_size))
						batch = list(islice(objs, start, start+batch_size))
						start+=batch_size

						#lgr.info('Finished Adding Batch')
						if not batch: break
						if is_bulk: tasks.append(bulk_send_outbound_batch.s(batch))
						else: tasks.append(send_outbound_batch.s(batch))
				elif len(df.loc[(x),:].shape)>1 :
					#lgr.info('Got Here (list of singles): %s' % x[0])
					for d in ID: 
						if is_bulk: tasks.append(bulk_send_outbound.s(d))
						else: tasks.append(send_outbound.s(d))
				else:
					#lgr.info('Got Here (single): %s' % x[0])
					if is_bulk: tasks.append(bulk_send_outbound.s(ID))
					else: tasks.append(send_outbound.s(ID))

			#lgr.info('Got Here 10: %s' % tasks)

			chunks, chunk_size = len(tasks), 100
			sms_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]

	except Exception as e:
		lgr.info('Error on Send Outbound SMS Messages: %s ' % e)

@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_outbound_sms_messages():
	_send_outbound_sms_messages(is_bulk=False, limit_batch=240)


@app.task(ignore_result=True, time_limit=1000, soft_time_limit=900)
#@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def bulk_send_outbound_sms_messages():
	_send_outbound_sms_messages(is_bulk=True, limit_batch=240)


@app.task(ignore_result=True, soft_time_limit=3600) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def send_outbound_email_messages():
	#from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	#Check for created outbounds or processing and gte(last try) 4 hours ago within the last 3 days| Check for failed transactions within the last 10 minutes
	outbound = Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='EMAIL'),\
				Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=96))\
				|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(hours=6),date_created__gte=timezone.now()-timezone.timedelta(hours=96))\
				|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(hours=2),date_created__gte=timezone.now()-timezone.timedelta(hours=6)),\
				Q(contact__status__name='ACTIVE')).\
				select_related('contact')[:100]

	if len(outbound):
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

						if i.template and i.template.template_file.file_path:
							html_content = loader.get_template(i.template.template_file.file_path.name) #html template with utf-8 charset
							#d = Context({'message':unescape(i.message), 'gateway':gateway})
							d = {'message':unescape(i.message), 'gateway':gateway}
							html_content = html_content.render(d)
							html_content = smart_text(html_content)

							text_content = smart_text(text_content)
							msg = EmailMultiAlternatives(subject, text_content, from_email, [to.strip()], headers={'Reply-To': from_email})

							msg.attach_alternative(html_content, "text/html")
							msg.send()	      
						else:
							html_content = unescape(i.message)

							text_content = smart_text(text_content)
							msg = EmailMultiAlternatives(subject, text_content, from_email, [to.strip()], headers={'Reply-To': from_email})

							msg.attach_alternative(html_content, "text/html")
							msg.send()	      


						i.state = OutBoundState.objects.get(name='SENT')

					except Exception as e:
						lgr.info('Error Sending Mail: %s' % e)
						i.state = OutBoundState.objects.get(name='FAILED')

					except BadHeaderError:
						lgr.info('Bad Header: Error Sending Mail')
						i.state = OutBoundState.objects.get(name='FAILED')

				else:
					lgr.info('No Valid Email')
					i.state = OutBoundState.objects.get(name='FAILED')

				i.save()
			except Exception as e:
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
				except Exception as e: lgr.info('Error on Service Call: %s' % e)
		except Exception as e: lgr.info('Error On Send Bulk SMS: %s' % e)


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
			except Exception as e: lgr.info('Error on Service Call: %s' % e)
		except Exception as e: lgr.info('Error On Add Notification Contact: %s' % e)

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
			except Exception as e: lgr.info('Error on Service Call: %s' % e)
			'''

			w = Wrappers()
			try:w.service_call.apply_async((w, service, gateway_profile, payload), serializer='pickle')
			except Exception as e: lgr.info('Error on Service Call: %s' % e)

		except Exception as e: lgr.info('Error On Add Notification Contact: %s' % e)



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
