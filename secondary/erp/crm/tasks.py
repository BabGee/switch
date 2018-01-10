from __future__ import absolute_import

from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from secondary.erp.pos.models import *
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.db import transaction

import time, json
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re, pytz
from django.core.files import File

from primary.core.administration.models import Currency
from django.conf import settings

from switch.celery import app
from switch.celery import single_instance_task

import logging
lgr = logging.getLogger('crm')

class Wrappers:
	pass

class System(Wrappers):
	def bulk_product_item_details(self, payload, node_info):
		try:
			product_items = payload['product_items']
			product_items_list = product_items.split(',')

			new_payload = payload.copy()
			payload['product_item_list'] = []


			for product in product_items_list:

				lgr.info('Product: %s' % product)
				product_list = product.split('|')
				product = new_payload.copy()
				lgr.info('Product List: %s' % product_list)
				product_item_id, quantity = product_list

				quantity = quantity if quantity not in ["",None] else Decimal(1)
				product['quantity'] = str(quantity)

				lgr.info('Product: %s' % product)
				product_item = ProductItem.objects.filter(id=product_item_id,status__name='ACTIVE')

				if 'product_type' in payload.keys():
					product_item = product_item.filter(product_type__name=payload['product_type'])


				if 'product_type_id' in payload.keys():
					product_item = product_item.filter(product_type__id=payload['product_type_id'])

				if 'institution_id' in payload.keys():
					product_item = product_item.filter(institution__id=payload['institution_id'])

				if product_item.exists():
					product['product_item_id'] = product_item[0].id
					product['product_item_name'] = product_item[0].name
					product['product_item_kind'] = product_item[0].kind
					product['product_item_image'] = product_item[0].default_image if product_item[0].default_image else ''
					product['institution_id'] = product_item[0].institution.id
					#product['till_number'] = product_item[0].product_type.institution_till.till_number
					product['currency'] = product_item[0].currency.code
					if  product_item[0].variable_unit and 'quantity' in product.keys() and product['quantity'] not in ["",None]:
						lgr.info('Variable Unit with Quantity')
						product['amount'] = str(product_item[0].unit_cost*Decimal(product['quantity']))
						payload['response'] = 'Successful'
						payload['response_status'] = '00'
					elif product_item[0].variable_unit and 'amount' in payload.keys():
						if product_item[0].unit_limit_min is not None and Decimal(payload['amount']) < product_item[0].unit_limit_min:
							payload['response'] = 'Min Amount: %s' % product_item[0].unit_limit_min
							payload['response_status'] = '13'
							break #Stop Loop
						elif product_item[0].unit_limit_max is not None and Decimal(payload['amount']) > product_item[0].unit_limit_max:
							payload['response'] = 'Max Amount: %s' % product_item[0].unit_limit_max
							payload['response_status'] = '13'
							break #Stop Loop
						else:
							lgr.info('Variable Unit with Amount')
							payload['response'] = 'Successful'
							payload['response_status'] = '00'
					else:
						lgr.info('not variable unit with amount or quantity')
						product['amount'] = str(product_item[0].unit_cost)
						payload['response'] = 'Successful'
						payload['response_status'] = '00'

					#Append product
					payload['product_item_list'].append(product)
				else:
					payload['response_status'] = '25'


			lgr.info('Product Item Details: %s' % payload)
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on product item details: %s" % e)
		return payload



	def product_item_details(self, payload, node_info):
		try:
			#payload['ext_service_id'] = payload['Payment']
			#Ensure product name uniqueness under an institution is enforced on code on creation of product
			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.filter(id=payload['product_item_id'],status__name='ACTIVE').order_by('id')
			elif 'item' in payload.keys() and 'institution_id' in payload.keys():
				product_item = ProductItem.objects.filter(name=payload["item"], institution__id=payload['institution_id'], status__name='ACTIVE').order_by('id')
			else:
				product_item = ProductItem.objects.none()	

			if 'product_type' in payload.keys():
				product_item = product_item.filter(product_type__name=payload['product_type'])


			if 'product_type_id' in payload.keys():
				product_item = product_item.filter(product_type__id=payload['product_type_id'])


			if 'institution_id' in payload.keys():
				product_item = product_item.filter(institution__id=payload['institution_id'])


			if product_item.exists():
				payload['product_item_id'] = product_item[0].id
				payload['product_item_name'] = product_item[0].name
				payload['product_item_kind'] = product_item[0].kind
				payload['product_item_image'] = product_item[0].default_image if product_item[0].default_image else ''
				payload['institution_id'] = product_item[0].institution.id
				#payload['till_number'] = product_item[0].product_type.institution_till.till_number
				payload['currency'] = product_item[0].currency.code
				if  product_item[0].variable_unit and 'quantity' in payload.keys():
					lgr.info('Variable Unit with Quantity')
					payload['amount'] = str(product_item[0].unit_cost*Decimal(payload['quantity']))
					payload['response'] = 'Successful'
					payload['response_status'] = '00'
				elif product_item[0].variable_unit and 'amount' in payload.keys():
					if product_item[0].unit_limit_min is not None and Decimal(payload['amount']) < product_item[0].unit_limit_min:
						payload['response'] = 'Min Amount: %s' % product_item[0].unit_limit_min
						payload['response_status'] = '13'
					elif product_item[0].unit_limit_max is not None and Decimal(payload['amount']) > product_item[0].unit_limit_max:
						payload['response'] = 'Max Amount: %s' % product_item[0].unit_limit_max
						payload['response_status'] = '13'
					else:
						lgr.info('Variable Unit with Amount')
						payload['response'] = 'Successful'
						payload['response_status'] = '00'
				else:
					lgr.info('not variable unit with amount or quantity')
					payload['amount'] = str(product_item[0].unit_cost)
					payload['response'] = 'Successful'
					payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'

			lgr.info('Product Item Details: %s' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on product item details: %s" % e)
		return payload


	def event_ticket(self, payload, node_info):
		try:
			#payload['ext_service_id'] = payload['Payment']

			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.filter(id=payload['product_item_id'],status__name='ACTIVE').order_by('id')
			elif 'item' in payload.keys() and 'institution_id' in payload.keys():
				product_item = ProductItem.objects.filter(name=payload["item"],product_type__name='Event Ticket', institution__id=payload['institution_id'], status__name='ACTIVE').order_by('id')
			else:
				product_item = ProductItem.objects.none()	

			if 'institution_id' in payload.keys():
				product_item = product_item.filter(institution__id=payload['institution_id'])


			if product_item.exists():
				payload['product_item_id'] = product_item[0].id
				payload['institution_id'] = product_item[0].institution.id
				#payload['till_number'] = product_item[0].product_type.institution_till.till_number
				payload['currency'] = product_item[0].currency.code
				payload['amount'] = product_item[0].unit_cost
				payload['response'] = 'Successful'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on event ticket: %s" % e)
		return payload


	def investor_enrollment(self, payload, node_info):
		try:
			#payload['ext_service_id'] = payload['Payment']

			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.filter(id=payload['product_item_id'],status__name='ACTIVE').order_by('id')
			elif 'item' in payload.keys() and 'institution_id' in payload.keys():
				product_item = ProductItem.objects.filter(name=payload["item"],product_type__name='Investor Enrollment', institution__id=payload['institution_id'], status__name='ACTIVE').order_by('id')
			else:
				product_item = ProductItem.objects.none()	

			if 'institution_id' in payload.keys():
				product_item = product_item.filter(institution__id=payload['institution_id'])


			if product_item.exists():
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				enrollment = Enrollment.objects.filter(enrollment_type__product_item=product_item[0],profile=session_gateway_profile.user.profile, status__name='ACTIVE')
				if enrollment.exists():
					payload['response'] = 'Record Exists'
					payload['response_status'] = '26'
				else:
					payload['product_item_id'] = product_item[0].id
					payload['institution_id'] = product_item[0].institution.id
					#payload['till_number'] = product_item[0].product_type.institution_till.till_number
					payload['currency'] = product_item[0].currency.code
					payload['amount'] = product_item[0].unit_cost
					payload['response'] = 'Successful'
					payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on awards registration: %s" % e)
		return payload


	def member_registration(self, payload, node_info):
		try:
			#payload['ext_service_id'] = payload['Payment']

			if 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.filter(id=payload['product_item_id'],status__name='ACTIVE').order_by('id')
			elif 'item' in payload.keys() and 'institution_id' in payload.keys():
				product_item = ProductItem.objects.filter(name=payload["item"],product_type__name='Membership Plan', institution__id=payload['institution_id'], status__name='ACTIVE').order_by('id')
			else:
				product_item = ProductItem.objects.none()	

			if 'institution_id' in payload.keys():
				product_item = product_item.filter(institution__id=payload['institution_id'])


			if product_item.exists():
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				enrollment = Enrollment.objects.filter(enrollment_type__product_item=product_item[0],profile=session_gateway_profile.user.profile, status__name='ACTIVE')
				if enrollment.exists():
					payload['response'] = 'Record Exists'
					payload['response_status'] = '26'
				else:
					payload['product_item_id'] = product_item[0].id
					payload['institution_id'] = product_item[0].institution.id
					#payload['till_number'] = product_item[0].product_type.institution_till.till_number
					payload['currency'] = product_item[0].currency.code
					payload['amount'] = product_item[0].unit_cost
					payload['response'] = 'Successful'
					payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on awards registration: %s" % e)
		return payload

	def get_details(self, payload, node_info):
		try:
			enrollment = Enrollment.objects.get(id=payload['id'])
			profile = enrollment.profile

			pks = payload.keys()

			if 'first_name' in pks \
					and 'middle_name' in pks \
					and 'last_name' in pks \
					and 'gender' in pks \
					and 'id_number' in pks:

				profile.user.first_name = payload['first_name']
				profile.user.last_name = payload['last_name']
				profile.user.save()

				profile.middle_name = payload['middle_name']
				profile.gender_id = int(payload['gender'])
				profile.national_id = payload['id_number']
				profile.save()

			
			payload['first_name'] = profile.user.first_name
			m_n = profile.middle_name
			payload['middle_name'] = m_n if m_n else ''
			payload['last_name'] = profile.user.last_name
			gnd = profile.gender
			payload['gender'] = gnd if gnd else 'Not Set'
			payload['id_number'] = profile.national_id
			#payload['phone_number'] = gateway_profile.msisdn.phone_number
			payload['registration_date'] = enrollment.enrollment_date

			payload['response'] = 'Details Captured'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on getting Profile Details: %s" % e)
		return payload

	def create_enrollment(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			institution = None
			if 'institution_id' in payload.keys():
				institution = Institution.objects.get(id=payload['institution_id'])
			elif 'institution_id' not in payload.keys() and gateway_profile.institution is not None:
				institution = gateway_profile.institution

			enrollment_type = None
			if 'record' not in payload.keys():
				lgr.info('Record not in paylod')
				enrollment_type_list = EnrollmentType.objects.filter(product_item__institution=institution)

	                        if 'product_item_id' in payload.keys():
					lgr.info('Product Item Found')
       		                        enrollment_type_list = enrollment_type_list.filter(product_item__id=payload['product_item_id'])

				if enrollment_type_list.exists():
					enrollment_type = enrollment_type_list[0]
					all_enrollments = Enrollment.objects.filter(enrollment_type__).\
							extra(
							    select={'int_record': "CAST(substring(record FROM '^[0-9]+') AS INTEGER)"}
								).\
							order_by("-int_record")
				else:
					all_enrollments = Enrollment.objects.none()


				if all_enrollments.exists():
					lgr.info('All Enrollment Found')
					record = all_enrollments[0].record
				else:
					lgr.info('All Enrollment Not found, does institution')
					all_enrollments = Enrollment.objects.filter(enrollment_type__product_item__institution=institution).\
						extra(
						    select={'int_record': "CAST(substring(record FROM '^[0-9]+') AS INTEGER)"}
							).\
						order_by("-int_record")

		                        if 'product_item_id' in payload.keys():
						lgr.info('All Enrollment for inst got product')
       			                        all_enrollments = all_enrollments.filter(enrollment_type__product_item__id=payload['product_item_id']).\
								extra(
								    select={'int_record': "CAST(substring(record FROM '^[0-9]+') AS INTEGER)"}
									).\
								order_by("-int_record")


					if all_enrollments.exists():
						lgr.info('All Enrollment for inst exists gives new record (+1) or allocates 1: %s|%s' % (all_enrollments[0],all_enrollments[0].record))
						try:record = int(all_enrollments[0].record)+1
						except: record = 1
					else:
						lgr.info('All enrollment for inst does not exists allocates 1')
						record = 1
			else:
				record = payload['record']

			lgr.info('Record: %s' % record)
                        #Check if enrollment exists
			if 'session_gateway_profile_id' in payload.keys():
				lgr.info('Session Gateway Found')
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

                        enrollment_list = Enrollment.objects.filter(status__name='ACTIVE',record=record,\
                                                                enrollment_type__product_item__institution=institution)

			lgr.info('Enrollment List: %s' % enrollment_list)
                        if 'product_item_id' in payload.keys():
				lgr.info('Product Item Found')
                                enrollment_list = enrollment_list.filter(enrollment_type__product_item__id=payload['product_item_id'])

                        if enrollment_list.exists():
				lgr.info('Enrollment with record exists')
				enrollment = enrollment_list[0]
				if 'session_gateway_profile_id' in payload.keys():
					session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
					enrollment_profile = enrollment_list.filter(profile=session_gateway_profile.user.profile)
					if enrollment_profile.exists():
						enrollment = enrollment_profile[0]
					else:
						enrollment = enrollment_list[0]
						enrollment.profile = session_gateway_profile.user.profile
						enrollment.save()

				payload['record'] = enrollment.record
                        else:
				lgr.info('Enrollment with record does not exist')

				enrollment_type = EnrollmentType.objects.filter(product_item__institution=institution)

				if 'product_item_id' in payload.keys():
					enrollment_type = enrollment_type.filter(product_item__id=payload['product_item_id'])

				if enrollment_type.exists():
	                                status = EnrollmentStatus.objects.get(name='ACTIVE')

        	                        enrollment = Enrollment(record=record, status=status, enrollment_type=enrollment_type[0])

                	                if 'alias' in payload.keys():
                        	                enrollment.alias = payload['alias']
                                	else:
						alias = institution.name if institution else ''
						if 'full_names' in payload.keys():
							alias = payload['full_names']
						elif 'first_name' in payload.keys() or 'last_name' in payload.keys() or 'middle_name' in payload.keys():
							alias = ''
							if 'first_name' in payload.keys():
								alias = '%s %s' % (alias, payload['first_name'])
							if 'middle_name' in payload.keys():
								alias = '%s %s' % (alias, payload['middle_name'])
							if 'last_name' in payload.keys():
								alias = '%s %s' % (alias, payload['last_name'])

                        	                enrollment.alias = alias.strip()

					if 'enrollment_date' in payload.keys():
						#enrollment.enrollment_date = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(payload['enrollment_date'], '%d/%m/%Y')).date()
						enrollment.enrollment_date = datetime.strptime(payload['enrollment_date'], '%d/%m/%Y').date()
					else:
						enrollment.enrollment_date = timezone.now().date()

					if 'session_gateway_profile_id' in payload.keys():
						session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
						enrollment.profile = session_gateway_profile.user.profile
					else:
						enrollment.profile = gateway_profile.profile

					if 'expiry' in payload.keys():
						#enrollment.expiry = pytz.timezone(gateway_profile.user.profile.timezone).localize(datetime.strptime(payload['expiry'], '%d/%m/%Y'))
						enrollment.expiry = datetime.strptime(payload['expiry'], '%d/%m/%Y')
					elif 'expiry_days_period' in payload.keys():
						enrollment.expiry = timezone.now()+timezone.timedelta(days=(int(payload['expiry_days_period'])))
					elif 'expiry_years_period' in payload.keys():
						enrollment.expiry = timezone.now()+timezone.timedelta(days=(365*int(payload['expiry_years_period'])))
					else:
						enrollment.expiry = timezone.now()+timezone.timedelta(days=(365*20))

	                                enrollment.save()

					payload['record'] = enrollment.record
					payload['response_status'] = '00'
					payload['response'] = 'Enrollment Captured'

				else:
					payload['response_status'] = '00'
					payload['response'] = 'Enrollment Type Does Not Exist'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Programs: %s" % e)
		return payload


	def get_programs(self, payload, node_info):
		try:
			payload['response_status'] = '00'
			payload['response'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Programs: %s" % e)
		return payload


	def add_product_type(self,payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			try:
				product_type = ShopProductType.objects.get(name=payload['product_type_name'])
			except ShopProductType.DoesNotExist:
				product_type = ShopProductType()
				product_type.name = payload['product_type_name']

				try:
					shop_product_category = ShopProductCategory.objects.get(name=payload['product_type_category'])
				except ShopProductCategory.DoesNotExist:
					shop_product_category = ShopProductCategory()
					shop_product_category.name = payload['product_type_category']
					shop_product_category.description = payload['product_type_category_description']
					shop_product_category.status = ProductStatus.objects.get(name='ACTIVE')
					shop_product_category.save()

				product_type.product_category = shop_product_category
				product_type.description = payload['product_type_description']
				product_type.status = ProductStatus.objects.get(name='ACTIVE')
				product_type.institution = gateway_profile.institution

				product_type.save()

			payload['response_status'] = '00'
			payload['response'] = 'Product Type Added Succefully'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Add Product Type: %s" % e)
		return payload

	def add_product(self,payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			product = ProductItem()
			product.name = payload['product_name']
			product.description = payload['product_description']
			product.status =  ProductStatus.objects.get(name=payload['product_status']) # ACTIVE
			product.shop_product_type_id = payload['shop_product_type']
                        product.product_type_id = payload['product_type_id']
			product.buying_cost = payload['product_buying_cost']
			product.unit_cost = payload['product_selling_cost']
			product.institution = gateway_profile.institution
			product.currency = Currency.objects.get(code=payload['product_currency']) # KES
			product.product_display = ProductDisplay.objects.get(name=payload['product_display']) # DEFAULT

			product.vat = payload['product_vat']
			product.discount = payload['product_discount']
			product.barcode = payload['product_barcode']
			# product.unit_limit_min = payload['product_current_stok']

			product.kind = payload['product_kind']
			try:
				filename = payload['product_default_image']
				fromdir_name = settings.MEDIA_ROOT + '/tmp/uploads/'
				from_file = fromdir_name + str(filename)
				with open(from_file, 'r') as f:
					myfile = File(f)
					product.default_image.save(filename, myfile, save=False)
			except Exception, e:
				lgr.info('Error on saving Product default Image: %s' % e)


			product.save()


			payload['response_status'] = '00'
			payload['response'] = 'Product Added Succefully'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Add Product: %s" % e)
		return payload

class Trade(System):
	pass

class Payments(System):
	pass

#lgr = get_task_logger(__name__)
#Celery Tasks Here

@app.task(ignore_result=True, soft_time_limit=259200) #Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
def add_enrollment_type():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	e=Enrollment.objects.all()

	for i in e:
		if i.enrollment_type == None:
			enrollment_type = EnrollmentType.objects.get(product_item__institution=i.institution,product_item=i.product_item)
			i.enrollment_type = enrollment_type
			i.save()





