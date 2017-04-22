from __future__ import absolute_import
from celery import shared_task

from django.shortcuts import render
from regix.models import *
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import time
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

import logging
lgr = logging.getLogger('regix')

class System:
	@shared_task
	def is_registered(self, payload, node_info):
		try:
			registry = Registry.objects.get(id_number__iexact=payload['ID NUMBER'])
			names = '%s %s %s' % (registry.first_name, registry.middle_name, registry.last_name)
			payload['response'] = 'Registry Profile Is Registered: %s' % names.title()
			payload['response_status']= '00'
		except Registry.DoesNotExist:
			payload['response'] = 'Registry Profile does NOT exist'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Querying Registry: %s" % e)
		return payload

	@shared_task
	def create_registry_transaction(self, payload, node_info):
		try:
			metric = Metric.objects.filter(si_unit=payload['SELECT METRICS'])
			lgr.info('Got Metric: %s' % metric)
			status = TransactionStatus.objects.get(name='CREATED')
			#Get Reference and Costing
			reference = OrderReference.objects.get(id=payload['REFERENCE'])
			lgr.info('Reference: %s' % reference)
			cost_amount = Decimal(payload['QUANTITY']) * Decimal(reference.unit_cost)
			cost_amount = cost_amount.quantize(Decimal('.01'), rounding=ROUND_DOWN)
			lgr.info('Cost Amount: %s' % cost_amount)
			transaction = RegistryTransaction(id_number=payload['ID NUMBER'], product=reference.product, reference=reference,quantity=payload['QUANTITY'],\
				metric=metric[0], amount=cost_amount, currency=reference.currency, institution=reference.institution,\
				comment = payload['COMMENT'], status=status)
			lgr.info('Transaction: %s' % transaction)
			transaction.save()
			lgr.info("Payload: %s" % payload)
			payload['response'] = transaction.id
			payload['response_status'] = '00'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Registry Transaction: %s" % e)
		return payload

	@shared_task
	def create_registry_product(self, payload, node_info):
		try:
			registry = Registry.objects.get(id_number__icontains=payload['ID NUMBER'].lower())
			product_source_metric = ProductSourceMetric.objects.get(id=payload['PRODUCT SOURCE METRIC'])
			product_source_capacity= Decimal(payload['PRODUCT SOURCE CAPACITY'])
			quantity_per_production = Decimal(payload['QUANTITY PER PRODUCTION'])
			production_frequency = ProductionFrequency.objects.get(id=payload['PRODUCTION FREQUENCY'])
			production_metric = Metric.objects.get(id=payload['PRODUCTION METRICS'])

			product = RegistryProduct(registry = registry, product_source_metric = product_source_metric,\
				product_source_capacity = product_source_capacity,quantity_per_production = quantity_per_production,\
				production_frequency = production_frequency, production_metric=production_metric)
			product.save()
			lgr.info("Payload: %s" % payload)
			payload['response'] = product.id
			payload['response_status'] = '00'


		except Exception, e:
			if str(e) == 'ID NUMBER':
				payload['response_status'] = '15'
				lgr.info('Exception: %s' % e)
			else:
				payload['response_status'] = '96'
			lgr.info("Error on Creating Product: %s" % e)
		return payload

	@shared_task
	def create_registry_profile(self, payload, node_info):
		try:

			pnt = Point(float(payload['lng']), float(payload['lat']))
			country = Country.objects.get(mpoly__intersects=pnt)
			status = RegistryStatus.objects.get(name='ACTIVE')
			created_by = Profile.objects.get(id=payload['profile_id'])
			reg = Registry(first_name=payload['FIRST NAME'],middle_name=payload['MIDDLE NAME'],last_name=payload['LAST NAME'],\
                                                country=country,id_number=payload['ID NUMBER'],status=status,created_by=created_by)
                        reg.save()

			lgr.info('Reg: %s' % reg)
                        dob = payload['DATE OF BIRTH']
                        lgr.info('DOB: %s' % dob)
                        dob = datetime.strptime(dob, '%Y-%m-%dT%H:%M:%S.%fZ')
			lgr.info('DOB dt After TZ: %s' % dob)
			marital_status = MaritalStatus.objects.get(name=payload['MARITAL STATUS'])
                        reg_details = RegistryDetails(registry=reg, physical_addr=payload['PHYSICAL ADDRESS'],\
                                                 msisdn=payload['msisdn'], dob=dob, gender=payload['GENDER'], marital_status=marital_status,\
						 number_of_dependents=payload['NUMBER OF DEPENDENTS'])
                        reg_details.save()

			lgr.info('Details: %s' % reg_details)

			lgr.info("Payload: %s" % payload)
			payload['response'] = reg.id
			payload['response_status'] = '00'
		except IntegrityError:
			lgr.info('Registry already exist')
			payload['response_status'] = '94'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Registry: %s" % e)
		return payload


