from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from pos.models import *
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import time, json
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.files import File

import logging
lgr = logging.getLogger('regix')

class ImageProcessor:
	@app.task(ignore_result=True)
	def saveProductImage(self, payload, product):
		lgr = get_task_logger(__name__)
		try:

			fromdir_name = '/home/system/tmp/uploads/'
			def pimage(product, filename):
				from_file = fromdir_name + str(filename)
				lgr.info('Filename: %s' % filename)

				product_status = ProductStatus.objects.get(name='ACTIVE')
				image = ProductImage(product=product, status=product_status)
				with open(from_file, 'r') as f:
					myfile = File(f)
					image.photo.save(filename, myfile, save=False)

				image.save()
				myfile.close()
				f.close()
			if 'FRONT IMAGE' in payload.keys() and payload['FRONT IMAGE'] <> '':
				pimage(product, payload['FRONT IMAGE'])
			if 'BACK IMAGE' in payload.keys() and payload['BACK IMAGE'] <> '':
				pimage(product, payload['BACK IMAGE'])
			if 'LEFT IMAGE' in payload.keys() and payload['LEFT IMAGE'] <> '':
				pimage(product, payload['LEFT IMAGE'])
			if 'RIGHT IMAGE' in payload.keys() and payload['RIGHT IMAGE'] <> '':
				pimage(product, payload['RIGHT IMAGE'])
			if 'TOP IMAGE' in payload.keys() and payload['TOP IMAGE'] <> '':
				pimage(product, payload['TOP IMAGE'])
			if 'BOTTOM IMAGE' in payload.keys() and payload['BOTTOM IMAGE'] <> '':
				pimage(product, payload['BOTTOM IMAGE'])

		except Exception, e:
			lgr.info('Error On Saving Default Image: %s' % e)

class System:
	def create_transaction(self, payload, node_info):
		try:
			transaction = Transaction.objects.get(id=payload['bridge__transaction_id'])
			transaction_type = ProductTransactionType.objects.get(id=payload['TRANSACTION TYPE'])
			transaction_status = ProductTransactionStatus.objects.get(name='CREATED')
			created_by = User.objects.get(id=payload['user_id'])
			product_transaction = ProductTransaction(transaction=transaction, transaction_type=transaction_type, reference='reference',\
					 status=transaction_status, created_by=created_by)
			if 'QUANTITY' in payload.keys() and payload['QUANTITY'] <> "":
				quantity = ("".join(re.findall("\d+.", str(payload['QUANTITY']))).replace(" ","")).replace('k','')
				if quantity <> "":
					product_transaction.quantity = quantity

			if 'COMMENT' in payload.keys() and payload['COMMENT'] <> "":
				product_transaction.comment = payload['COMMENT']

			product_transaction.save()
			lgr.info('Purchase Order: %s' % product_transaction)

			user = []
			if 'msisdn' in payload.keys() and payload['msisdn'] <>"":
				msisdn = str(payload['msisdn'])
				msisdn = msisdn.strip()
				if len(msisdn) == 9:
					msisdn = '+254' + msisdn
				elif len(msisdn) == 10:
					msisdn = '+254' + msisdn[-9:]
				elif len(msisdn) == 12:
					msisdn = '+' + msisdn
				elif len(msisdn) == 13 and msisdn[:-12] == '+':
					msisdn = str(payload['msisdn'])
				lgr.info('\n\n\n\n\t#######Final MSISDN: %s\n\n\n\n' % msisdn)
				user = User.objects.filter(profile__msisdn__phone_number=msisdn)
				lgr.info('\n\n\n\t#######User: %s\n\n\n\n' % user)
			if (len(user)>0):
				product_transaction.user = user[0]
				product_transaction.save()
				names = '%s %s' % (user[0].first_name, user[0].last_name)
				payload['response'] = '%s | Transaction: %s' % (names.title(), product_transaction.reference)
				payload['response_status']= '00'
			else:
				payload['response'] = 'Unregistered User Transaction: %s' % (product_transaction.reference)
				payload['response_status']= '00'

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Registry Transaction: %s" % e)
		return payload

	def create_registry_product(self, payload, node_info):
		try:

			username = None
			if 'msisdn' in payload.keys():
	 			msisdn = str(payload['msisdn'])
				msisdn = msisdn.strip()
				if len(msisdn) == 9:
					msisdn = '+254' + msisdn
				elif len(msisdn) == 10:
					msisdn = '+254' + msisdn[-9:]
				elif len(msisdn) == 12:
					msisdn = '+' + msisdn
				elif len(msisdn) == 13 and msisdn[:-12] == '+':
					msisdn = str(payload['msisdn'])
				else:
					msisdn = None
				lgr.info('\n\n\n\n\t#######Final MSISDN: %s\n\n\n\n' % msisdn)
				username = msisdn
			elif 'email' in payload.keys() and self.validateEmail(payload['email']):
				username = payload['email']

			user = User.objects.filter(username=username)
			lgr.info('\n\n\n\t#######User: %s\n\n\n\n' % user)
			if len(user) > 0:
				names = '%s %s' % (user[0].first_name, user[0].last_name)
				product = Product.objects.get(id=payload['SELECT PRODUCT'])
				created_by = User.objects.get(id=payload['user_id'])
				reg_prod = RegistryProduct(user=user[0],product=product, created_by=created_by)
				reg_prod.save()
				payload['response'] = 'Registry Product Added'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '13' #Record not Found

			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Registry: %s" % e)
		return payload

	def add_product(self, payload, node_info):
		try:
			#Name, Trading Status
			cost_status = CostStatus.objects.get(id=payload['COST STATUS'])
			product_status = ProductStatus.objects.get(name='ACTIVE')
			trading_status = TradingStatus.objects.get(id=payload['PRODUCT TRADING'])
			institution_till = InstitutionTill.objects.get(id=payload['PRODUCT TILL'])
			product_type = ProductType.objects.get(id=payload['PRODUCT TYPE'])
			product = Product(name=payload['NAME'],trading=trading_status, status=product_status, institution_till=institution_till,\
				unit_cost=payload['UNIT COST'], cost_status=cost_status, product_type=product_type)
			if 'KIND' in payload.keys() and payload['KIND'] <> '':
				product.kind = payload['KIND']
			if 'DETAILS' in payload.keys() and payload['DETAILS'] <> '':
				product.details = json.dumps(payload['DETAILS'])
			if 'DEFAULT IMAGE' in payload.keys() and payload['DEFAULT IMAGE'] <> '':
				fromdir_name = '/home/system/tmp/uploads/'
				filename = '%s' % payload['DEFAULT IMAGE']
				from_file = fromdir_name + str(filename)
				lgr.info('Filename: %s' % filename)
				with open(from_file, 'r') as f:
					myfile = File(f)
					product.photo.save(filename, myfile, save=False)

			product.save()
			#Save Product Extra Images
			ImageProcessor().saveProductImage.delay(payload, product)

			payload['response'] = 'Product Added| ID: %s' % product.id 
			payload['response_status'] = '00'
		except Exception, e:
			lgr.info('Error Adding Product: %s' % e)
			payload['response_status'] = '96'
		return payload

	def product_price(self, payload, node_info):
		try:
			lgr.info('Product Price Payload: %s ' % payload)
			trf = Product.objects.filter(product_type__name=payload['PRODUCT TYPE'], institution_till__city=payload['CITY'], institution_till__name=payload['TILL'])
			lgr.info('Transaction Reference: %s' % trf)
			if len(trf)>0:
				lgr.info('Transaction Reference Select: %s' % trf[0])

				cost = trf[0].unit_cost
				currency = trf[0].institution_till.till_currency.currency
				if cost > 0:
					currency = '%ss' % currency	
				payload['response'] = '%s %s.' % (cost, currency)

			else:
				payload['response'] = 'No Product Price Found'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Querying Registry: %s" % e)
		return payload


class Trade(System):
	pass


class Payments(System):
	pass
