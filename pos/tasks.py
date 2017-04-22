from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import pytz, time, os, random, string, json
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import base64, re
from django.core.files import File
from django.db.models import Count
from django.db import transaction

from pos.models import *
from django.db.models import Q, F
import operator

import logging
lgr = logging.getLogger('vbs')


class Wrappers:
	@app.task(filter=task_method, ignore_result=True)
	def service_call(self, service, gateway_profile, payload):
		lgr = get_task_logger(__name__)
		from api.views import ServiceCall
		try:
			payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info('Unable to make service call: %s' % e)
		return payload

	def transaction_payload(self, payload):
		new_payload, transaction, count = {}, None, 1
		for k, v in payload.items():
			key = k.lower()
			if 'card' not in key and 'credentials' not in key and 'new_pin' not in key and \
			 'validate_pin' not in key and 'password' not in key and 'confirm_password' not in key and \
			 'pin' not in key and 'access_level' not in key and \
			 'response_status' not in key and 'sec_hash' not in key and 'ip_address' not in key and \
			 'service' not in key and key <> 'lat' and key <> 'lng' and \
			 key <> 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and 'transaction_timestamp' not in key and \
			 'action_id' not in key and 'bridge__transaction_id' not in key and \
			 'merchant_data' not in key and 'signedpares' not in key and \
			 key <> 'gpid' and key <> 'sec' and \
			 key not in ['ext_product_id','vpc_securehash','ext_inbound_id','currency','amount'] and \
			 'institution_id' not in key and key <> 'response' and key <> 'input':

				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:40]
				else:
					break
				count = count+1

		return json.dumps(new_payload)



class System(Wrappers):
	def window_event(self, payload, node_info):
		try:
			payload["response_status"] = "00"
			payload["response"] = "Window Event"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on window event: %s" % e)
		return payload


	def get_bill(self, payload, node_info):
		try:
			if 'reference' in payload.keys():

				#An order will ALWAYS have an initial bill manager, hence

				bill_manager_list = BillManager.objects.filter(order__reference=payload['reference'],order__status__name='UNPAID').order_by("-date_created")
				if len(bill_manager_list)>0:
					payload['amount'] = str(bill_manager_list[0].balance_bf)
                                        payload['currency'] = bill_manager_list[0].order.currency.code
					payload['purchase_order_id'] = bill_manager_list[0].order.id
					payload["response_status"] = "00"
					payload["response"] = "Bill Balance: %s" % bill_manager_list[0].balance_bf
				else:
					payload["response_status"] = "25"
					payload["response"] = "No Purchase Order with given reference"
			else:
				payload["response_status"] = "25"
				payload["response"] = "No Purchase Order reference was given"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on pay bill: %s" % e)
		return payload



	def reverse_pay_bill(self, payload, node_info):
		try:
			purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])
			status = OrderStatus.objects.get(name='UNPAID')
			purchase_order.status = status
			purchase_order.save()
			bill_manager_list = BillManager.objects.filter(order=purchase_order).order_by("-date_created")[:1]
			if bill_manager_list.exists():
				order = bill_manager_list[0].order
				balance_bf = bill_manager_list[0].amount+bill_manager_list[0].balance_bf
				bill_manager = BillManager(credit=False,transaction_reference=payload['bridge__transaction_id'],\
						action_reference=payload['action_id'],order=order,\
						amount=bill_manager_list[0].amount,\
						balance_bf=Decimal(balance_bf).quantize(Decimal('.01'), rounding=ROUND_DOWN))

				bill_manager.save()

				payload['amount'] = bill_manager.amount
				payload['purchase_order_id'] = order.id
				payload["response"] = "Bill Reversed. Balance: %s" % bill_manager.balance_bf
			else:
				#!!IMPORTANT - Or Account would be debitted on no bill
				payload['amount'] = Decimal(0)
				payload["response"] = "No Bill to Reverse"
			payload["response_status"] = "00"

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on reverse pay bill: %s" % e)
		return payload


	def pay_bill(self, payload, node_info):
		try:
			if 'reference' in payload.keys():

				#An order will ALWAYS have an initial bill manager, hence

				bill_manager_list = BillManager.objects.filter(order__reference=payload['reference'],order__status__name='UNPAID').order_by("-date_created")
				if len(bill_manager_list)>0:
					order = bill_manager_list[0].order
					#If currency does not much purchase_order currency (FOREX) and replace amount & currency in payload
					if 'balance_bf' in payload.keys() and Decimal(payload['balance_bf']) >= 0:
						if bill_manager_list[0].balance_bf <= Decimal(payload['balance_bf']):
							#payment balance_bf is greater than outstanding bill
							balance_bf = 0
							status = OrderStatus.objects.get(name='PAID')
							order.status = status
							order.save()

							#transacting amount refers to the deduction for bill amount only
							transacting_amount = bill_manager_list[0].balance_bf
						else:
							#payment balance_bf is less than outstanding bill
							balance_bf = Decimal(bill_manager_list[0].balance_bf) - Decimal(payload['balance_bf'])
							#transacting amount refers to the deduction for bill amount only
							transacting_amount = Decimal(payload['balance_bf']).quantize(Decimal('.01'), rounding=ROUND_DOWN)  

						bill_manager = BillManager(credit=True,transaction_reference=payload['bridge__transaction_id'],\
								action_reference=payload['action_id'],order=order,\
								amount=transacting_amount,\
								balance_bf=Decimal(balance_bf).quantize(Decimal('.01'), rounding=ROUND_DOWN))
						bill_manager.payment_method = PaymentMethod.objects.get(name=payload['payment_method'])
						bill_manager.save()

						payload['amount'] = bill_manager.amount
						payload['purchase_order_id'] = order.id
						payload["response_status"] = "00"
						payload["response"] = "Bill Payment Accepted. Balance: %s" % bill_manager.balance_bf
					else:
						payload['amount'] = Decimal(0)
						payload["response_status"] = "00"
						payload["response"] = "No Amount to pay outstanding bill"
				else:
					#!!IMPORTANT - Or Account would be debitted on no bill
					payload['amount'] = Decimal(0)
					payload["response_status"] = "00"
					payload["response"] = "No Purchase Order with given reference"
			else:
				#!!IMPORTANT - Or Account would be debitted on no bill
				payload['amount'] = Decimal(0)
				payload["response_status"] = "00"
				payload["response"] = "No Purchase Order reference was given"


		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on pay bill: %s" % e)
		return payload


	def add_to_purchase_order(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			#Ensure cart product items tills match
			cart_items = CartItem.objects.filter(id__in=payload['cart_items'],\
					 product_item__institution_till__id=payload['institution_till_id'])

			if len(cart_items)>0:
				#get greates reference from un-expired/unpaid list (expiry after 15days)
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

				bill_manager = BillManager.objects.filter(order__gateway_profile=session_gateway_profile).order_by('-date_created')


				if 'purchase_order_id' in payload.keys():
					bill_manager = bill_manager.filter(order__id=payload['purchase_order_id'])
				elif 'transaction_reference' in payload.keys() and 'purchase_order_id' not in payload.keys():
					bill_manager_extract = bill_manager.filter(transaction_reference = payload['transaction_reference'])
					bill_manager = bill_manager.filter(order=bill_manager_extract[0].order)



				elif 'reference' in payload.keys() and 'purchase_order_id' not in payload.keys():
					bill_manager = bill_manager.filter(order__reference=payload['reference'])
				else:
					bill_manager = bill_manager.none()
				if bill_manager.exists():
					amount = Decimal(0)
					for c in cart_items:
						purchase_order = bill_manager[0].order
						purchase_order.cart_item.add(c)
						if c.currency == purchase_order.currency:
							amount = amount + c.total
						else:
							lgr.info('Forex Calculate amount to %s|from: %s' % (purchase_order.currency,c.currency) )

						#ADD to Bill Manager for Payment deductions
						bill_manager = BillManager(credit=False,transaction_reference=payload['bridge__transaction_id'],\
								action_reference=payload['action_id'],order=purchase_order,amount=c.total,\
								balance_bf=amount)

						bill_manager.save()

					payload['reference'] = purchase_order.reference

					payload['purchase_order_id'] = purchase_order.id

					payload["response_status"] = "00"
					payload["response"] = "Purchase Order Created"
				else:
					payload["response_status"] = "25"
					payload["response"] = "No order Found"

			else:
				payload["response_status"] = "25"
				payload["response"] = "No Cart Items Found"

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating purchase order: %s" % e)
		return payload


	def create_purchase_order(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


			#Ensure cart product items tills match
			cart_items = CartItem.objects.filter(id__in=payload['cart_items'],\
					 product_item__institution_till__id=payload['institution_till_id'])

			if len(cart_items)>0:
				#get greates reference from un-expired/unpaid list (expiry after 15days)

				def reference(pre_reference):
					chars = string.ascii_letters 
					nums = string.digits
					rnd = random.SystemRandom()
					prefix = ''.join(rnd.choice(chars) for i in range(3))
					suffix = ''.join(rnd.choice(nums) for i in range(2,4))
					trial = '%s-%s%s' % (pre_reference, prefix.upper(), suffix)
					reference_list = PurchaseOrder.objects.filter(reference=trial,status__name='UNPAID',\
							expiry__gte=timezone.now()).order_by('-reference')[:1]
					if len(reference_list)>0:
						return reference(pre_reference)
					else:
						return trial

				if 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					pre_reference = '%s-%s' % (payload['institution_till_id'], institution.business_number)
					reference = reference(pre_reference)
				else:
					pre_reference = '%s' % (payload['institution_till_id'])
					reference = reference(pre_reference)

				expiry = timezone.localtime(timezone.now())+timezone.timedelta(days=45)
				status = OrderStatus.objects.get(name='UNPAID')
				currency = cart_items[0].currency
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

				purchase_order = PurchaseOrder(reference=reference,\
						currency=currency,\
						status=status,expiry=expiry, gateway_profile=session_gateway_profile)

				if 'description' in payload.keys():
					purchase_order.description = payload['description']
				elif 'description' not in payload.keys() and 'comment' in payload.keys():
					purchase_order.description = payload['comment']
		
				purchase_order.save()	

				amount = Decimal(0)
				for c in cart_items:
					purchase_order.cart_item.add(c)
					if c.currency == purchase_order.currency:
						amount = amount + c.total
					else:
						lgr.info('Forex Calculate amount to %s|from: %s' % (purchase_order.currency,c.currency) )

					#ADD to Bill Manager for Payment deductions
					bill_manager = BillManager(credit=False,transaction_reference=payload['bridge__transaction_id'],\
							action_reference=payload['action_id'],order=purchase_order,amount=c.total,\
							balance_bf=amount)

					bill_manager.save()

				payload['reference'] = purchase_order.reference

				payload['purchase_order_id'] = purchase_order.id

			payload["response_status"] = "00"
			payload["response"] = "Purchase Order Created"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on creating purchase order: %s" % e)
		return payload

	def add_product_to_cart(self, payload, node_info):
		try:
			product_item = ProductItem.objects.get(id=payload['product_item_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			session_gateway_profile = None
			status = CartStatus.objects.get(name='ACTIVE')

			quantity = Decimal(payload['quantity']) if 'quantity' in payload.keys() else Decimal(1)
			sub_total = Decimal(product_item.unit_cost*quantity).quantize(Decimal('.01'), rounding=ROUND_UP)
			total = sub_total

			if 'quantity' not in payload.keys() and product_item.variable_unit and 'amount' in payload.keys():
				quantity = Decimal(Decimal(payload['amount'])/product_item.unit_cost).quantize(Decimal('.01'), rounding=ROUND_UP)
				sub_total = Decimal(product_item.unit_cost*quantity).quantize(Decimal('.01'), rounding=ROUND_UP)
				total = sub_total

			if 'institution_till_id' in payload.keys():
				till = product_item.institution_till.filter(id=payload['institution_till_id'])[0]
			else:
				till = product_item.institution_till.all()[0]

			channel = Channel.objects.get(id=payload['chid'])

			cart_item = CartItem(product_item=product_item,currency=product_item.currency,\
				status=status,quantity=quantity,price=product_item.unit_cost,sub_total=sub_total,total=total,\
				details=self.transaction_payload(payload), till=till, channel=channel)

			if 'session_gateway_profile_id' in payload.keys():
				cart_item.gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			if 'csrf_token' in payload.keys():
				cart_item.token = payload['csrf_token']

			cart_item.save()

			payload['cart_items'] = [cart_item.id]
			payload["response_status"] = "00"
			payload["response"] = "Product Added to Cart"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Adding product to cart: %s" % e)
		return payload

	def cancel_sale_order(self, payload, node_info):
		try:

			purchase_order = PurchaseOrder.objects.filter(reference=payload['reference'], status__name='UNPAID')
			if 'purchase_order_id' in payload.keys():
				purchase_order = purchase_order.filter(id=payload['purchase_order_id'])

			if purchase_order.exists():
				purchase_order.update(status=OrderStatus.objects.get(name='CANCELLED'))
				payload['response'] = 'Sale Order Reversed'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Reversing Sale Order: %s" % e)
		return payload


	def add_to_order(self, payload, node_info):
		try:
			payload = self.add_product_to_cart(payload, node_info)
			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				payload = self.add_to_purchase_order(payload, node_info)
				if 'response_status' in payload.keys() and payload['response_status'] == '00':
					payload["response_status"] = "00"
					if 'reference' in payload.keys():
						payload["response"] = "Sale Order: %s" % payload['reference']
					else:
						payload["response"] = "Sale Order"

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Order: %s" % e)
		return payload



	def sale_order(self, payload, node_info):
		try:
			payload = self.add_product_to_cart(payload, node_info)
			if 'response_status' in payload.keys() and payload['response_status'] == '00':
				payload = self.create_purchase_order(payload, node_info)
				if 'response_status' in payload.keys() and payload['response_status'] == '00':
					payload["response_status"] = "00"
					if 'reference' in payload.keys():
						payload["response"] = "Sale Order: %s" % payload['reference']
					else:
						payload["response"] = "Sale Order"

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Order: %s" % e)
		return payload


	def create_sale_contact(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			sale_contact_type = SaleContactType.objects.get(id=payload["sale_contact_type"])
			transaction = Transaction.objects.get(id=payload["bridge__transaction_id"])

			primary_contact_profile = Profile.objects.get(id=payload['profile_id'])
			lgr.info("Starting Generating Till Number")
			all_contacts = SaleContact.objects.filter(institution=gateway_profile.institution).order_by("-sale_contact_number")[:1]
			if len(all_contacts)>0:
				sale_contact_number = all_contacts[0].sale_contact_number+1
			else:
				sale_contact_number = 1

			details = json.loads(transaction.request)
			if "sale_contact_name" in details.keys(): del details["sale_contact_name"]
			if "sale_contact_type" in details.keys(): del details["sale_contact_type"]
			if "comment" in details.keys(): del details["comment"]

			sale_contact = SaleContact(name=payload['sale_contact_name'],description=payload['sale_contact_name'],\
					sale_contact_type=sale_contact_type,geometry=transaction.geometry,\
					sale_contact_number=sale_contact_number,institution=gateway_profile.institution,\
					primary_contact_profile=primary_contact_profile,details=details,created_by=gateway_profile)

			if 'sale_contact_location' in payload.keys():
				sale_contact.location=payload['sale_contact_location'],
			if "comment" in payload.keys():
				sale_contact.comment = payload["comment"]
			sale_contact.save()

			payload['sale_contact_id'] = sale_contact.id
			payload['sale_contact_number'] = sale_contact.sale_contact_number

			payload["response_status"] = "00"
			payload["response"] = "Sale Contact Created"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Contact: %s" % e)
		return payload


class Trade(System):
	pass


class Payments(System):
	pass

@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_paid_order():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)

	order = PurchaseOrder.objects.select_for_update().filter(status__name='PAID',cart_processed=False,\
		 date_modified__lte=timezone.now()-timezone.timedelta(seconds=10))[:10]

	for o in order:
		try:
			o.cart_processed = True
			o.save()
			lgr.info('Captured Order: %s' % o)
			cart_item = o.cart_item.all()
			for c in cart_item:
				lgr.info('Captured Cart Item: %s' % c)
				product_item = c.product_item
				service = c.product_item.product_type.service
				payload = json.loads(c.details)	
				payload['purchase_order_id'] = o.id
				payload['product_item_id'] = c.product_item.id
				payload['item'] = c.product_item.name
				payload['product_type'] = c.product_item.product_type.name
				gateway_profile = c.gateway_profile
				payload['quantity'] = c.quantity
				payload['currency'] = c.currency.code
				payload['amount'] = c.total
				payload['reference'] = o.reference
				payload['institution_id'] = c.product_item.institution.id
				payload['institution_till_id'] = c.till.id
				payload['chid'] = c.channel.id
				payload['ip_address'] = '127.0.0.1'
				payload['gateway_host'] = '127.0.0.1'


				lgr.info('Product Item: %s | Payload: %s' % (product_item, payload))
				if service is None:
					lgr.info('No Service to process for product: %s' % product_item)
				else:
					try:Wrappers().service_call(service, gateway_profile, payload)
					except Exception, e: lgr.info('Error on Service Call: %s' % e)
		except Exception, e:
			lgr.info('Error processing paid order item: %s | %s' % (o,e))
