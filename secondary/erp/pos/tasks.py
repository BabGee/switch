from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
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

from django.db.models import Q, F
import operator
#from secondary.channels.notify.mqtt import MqttServerClient
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers


from secondary.erp.pos.models import *

import logging
lgr = logging.getLogger('pos')


class Wrappers:
	def bill_entry(self, item, purchase_order, balance_bf, payload):
		purchase_order.cart_item.add(item)


		transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None

		#ADD to Bill Manager for Payment deductions
		bill_manager = BillManager(credit=False,transaction_reference=transaction_reference,\
				action_reference=payload['action_id'],order=purchase_order,amount=item.total,\
				balance_bf=balance_bf)

		bill_manager.save()

		return bill_manager


	def get_balance_bf(self, item, purchase_order, balance_bf):
		if item.currency == purchase_order.currency:
			balance_bf = balance_bf + item.total
		else:
			forex = Forex.objects.filter(base_currency=purchase_order.currency, quote_currency=item.currency)
			total = Decimal(0)
			if forex.exists():
				total = item.total/forex[0].exchange_rate

			balance_bf = balance_bf + total
			lgr.info('Forex Calculate balance_bf to %s|from: %s| %s' % (purchase_order.currency, item.currency, balance_bf) )

		return balance_bf


	def cart_update(self, cart_item, payload, quantity, sub_total, total):

		cart_item.quantity=quantity
		cart_item.sub_total=sub_total
		cart_item.total=total
		cart_item.details=self.transaction_payload(payload)

		cart_item.save()

		return cart_item


	def cart_entry(self, product_item, payload, quantity, sub_total, total):
		session_gateway_profile = None
		status = CartStatus.objects.get(name='UNPAID')

		channel = Channel.objects.get(id=payload['chid'])

		cart_item = CartItem(product_item=product_item,currency=product_item.currency,\
			status=status,quantity=quantity,price=product_item.unit_cost,sub_total=sub_total,total=total,\
			details=self.transaction_payload(payload), channel=channel)

		if 'session_gateway_profile_id' in payload.keys():
			session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
		else:
			session_gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])


		cart_item.gateway_profile = session_gateway_profile
		if session_gateway_profile.institution == product_item.institution:
			cart_item.cart_type = CartType.objects.get(name='POS')
		else:
			cart_item.cart_type = CartType.objects.get(name='SHOP')

		if 'csrf_token' in payload.keys():
			cart_item.token = payload['csrf_token']
		elif 'csrfmiddlewaretoken' in payload.keys():
			cart_item.token = payload['csrfmiddlewaretoken']
		elif "token" in payload.keys():
			cart_item.token = payload['token']

		cart_item.save()

		return cart_item

	def sale_charge_item(self, balance_bf, item, payload, gateway):
		#Sale Charge Item Bill entry
		sale_charge_item = None
		sale_charge = SaleCharge.objects.filter(Q(min_amount__lt=balance_bf,max_amount__gt=balance_bf,credit=False),\
						Q(Q(product_type=item.product_item.product_type)|Q(product_type=None)),\
						Q(Q(institution=item.product_item.institution)|Q(institution=None)),\
						Q(Q(gateway=gateway)|Q(gateway=None)))
		for sc in sale_charge:
			product_item = sc.sale_charge_type.product_item
			charge = Decimal(0)
			if sc.is_percentage:
				charge = charge + ((sc.charge_value/100)*Decimal(item.total))
			else:
				charge = charge+sc.charge_value

			if sc.per_item:
				sale_charge_item = self.cart_entry(sc.sale_charge_type.product_item, payload, 1, charge, charge)
				#sale_charge_item = CartItem.objects.get(id=cart_item_id)

			else:
				sale_charge_exists = False
				if item.gateway_profile:
					sale_charge_items = CartItem.objects.filter(gateway_profile=item.gateway_profile, product_item=product_item)
					sale_charge_exists = sale_charge_items.exists()
				else:
					sale_charge_items = CartItem.objects.filter(token=item.token, product_item=product_item)
					sale_charge_exists = sale_charge_items.exists()

				if sale_charge_exists:
					#sale_charge_item = sale_charge_items[0]
					sale_charge_item = self.cart_update(sale_charge_items[0], payload, 1, charge, charge)
				else:
					sale_charge_item = self.cart_entry(sc.sale_charge_type.product_item, payload, 1, charge, charge)
					#sale_charge_item = CartItem.objects.get(id=cart_item_id)

		return sale_charge_item


	def sale_charge_bill_entry(self, balance_bf, item, payload, purchase_order, gateway):
		sale_charge_item = self.sale_charge_item(balance_bf, item, payload, gateway)
		if sale_charge_item:
			balance_bf = self.get_balance_bf(sale_charge_item, purchase_order, balance_bf)
			bill_manager = self.bill_entry(sale_charge_item, purchase_order, balance_bf, payload)
		return balance_bf


	def sale_charge_bill(self, balance_bf, item, payload, purchase_order, gateway):
		#Sale Charge Item Bill entry
		sale_charge = SaleCharge.objects.filter(Q(min_amount__lt=balance_bf,max_amount__gt=balance_bf,credit=False),\
						Q(Q(product_type=item.product_item.product_type)|Q(product_type=None)),\
						Q(Q(institution=item.product_item.institution)|Q(institution=None)),\
						Q(Q(gateway=gateway)|Q(gateway=None)))

		for sc in sale_charge:
			product_item = sc.sale_charge_type.product_item
			charge = Decimal(0)
			if sc.is_percentage:
				charge = charge + ((sc.charge_value/100)*Decimal(item.total))
			else:
				charge = charge+sc.charge_value

			if sc.per_item:
				sale_charge_item = self.cart_entry(sc.sale_charge_type.product_item, payload, 1, charge, charge)
				#item = CartItem.objects.get(id=cart_item_id)
				balance_bf = self.get_balance_bf(sale_charge_item, purchase_order, balance_bf)
				bill_manager = self.bill_entry(sale_charge_item, purchase_order, balance_bf, payload)

			else:
				if bill_manager.order.cart_item.filter(product_item=product_item).exists():
					lgr.info('Sale Charge Already Exists')
				else:
					sale_charge_item = self.cart_entry(sc.sale_charge_type.product_item, payload, 1, charge, charge)
					#item = CartItem.objects.get(id=cart_item_id)
					balance_bf = self.get_balance_bf(sale_charge_item, purchase_order, balance_bf)
					bill_manager = self.bill_entry(sale_charge_item, purchase_order, balance_bf, payload)

		return balance_bf

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
	def delete_cart_item_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			cart_item = CartItem.objects.get(id=payload['cart_item_id'],\
						 product_item__institution__gateway=gateway_profile.gateway)

			payload['total'] = cart_item.total
			payload['sub_total'] = cart_item.sub_total
			payload['quantity'] = cart_item.quantity
			payload['price'] = cart_item.price
			payload['product_item_id'] = cart_item.product_item.id
			payload['cat_item_status'] = cart_item.status.name
			payload['details'] = json.loads(cart_item.details)


			if cart_item.product_item.uneditable:
				payload['trigger'] = 'uneditable_item%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
			else:
				payload['trigger'] = 'editable_item%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

			payload["response_status"] = "00"
			payload["response"] = "Cart Item Details"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Cart Items: %s" % e)
		return payload


	def update_cart_item_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			cart_item = CartItem.objects.get(id=payload['cart_item_id'],\
						 product_item__institution__gateway=gateway_profile.gateway)

			payload['total'] = cart_item.total
			payload['sub_total'] = cart_item.sub_total
			payload['quantity'] = cart_item.quantity
			payload['price'] = cart_item.price
			payload['product_item_id'] = cart_item.product_item.id
			payload['cat_item_status'] = cart_item.status.name
			payload['details'] = json.loads(cart_item.details)


			if cart_item.product_item.product_type.name == 'Location':
				payload['trigger'] = 'location_item%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
			else:
				payload['trigger'] = 'quantity_item%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

			payload["response_status"] = "00"
			payload["response"] = "Cart Item Details"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Cart Items: %s" % e)
		return payload

	def update_cart_item(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			cart_item = CartItem.objects.get(id=payload['cart_item_id'],\
						 product_item__institution__gateway=gateway_profile.gateway)

			product_item = cart_item.product_item

			quantity = Decimal(payload['quantity']) if 'quantity' in payload.keys() else Decimal(1)
			sub_total = Decimal(product_item.unit_cost*quantity).quantize(Decimal('.01'), rounding=ROUND_DOWN)
			total = sub_total

			if 'quantity' not in payload.keys() and product_item.variable_unit and 'amount' in payload.keys():
				quantity = Decimal(Decimal(payload['amount'])/product_item.unit_cost).quantize(Decimal('.01'), rounding=ROUND_DOWN)
				sub_total = Decimal(product_item.unit_cost*quantity).quantize(Decimal('.01'), rounding=ROUND_DOWN)
				total = sub_total

			cart_item.quantity = quantity
			cart_item.sub_total = sub_total
			cart_item.total = total
			cart_item.pn = False
			cart_item.save()


			payload["response_status"] = "00"
			payload["response"] = "Updated Cart Item"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Update Cart Item: %s" % e)
		return payload

	def delete_cart_item(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			cart_item = CartItem.objects.get(id=payload['cart_item_id'],\
						 product_item__institution__gateway=gateway_profile.gateway)

			cart_item.status = CartStatus.objects.get(name='DELETED')
			cart_item.pn = False
			cart_item.save()

			payload["response_status"] = "00"
			payload["response"] = "Deleted Cart Item"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Delete Cart Item: %s" % e)
		return payload

	def window_event(self, payload, node_info):
		try:
			payload["response_status"] = "00"
			payload["response"] = "Window Event"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on window event: %s" % e)
		return payload


	def allow_cash_on_delivery(self, payload, node_info):
		try:
			if 'purchase_order_id' in payload.keys() and 'amount' in payload.keys() and 'currency' in payload.keys():
				payload['balance_bf'] = payload['amount']
				payload["response_status"] = "00"
				payload["response"] = "Allowed: %s %s to cash on delivery" % (payload['currency'], payload['amount'])
			else:
				payload["response_status"] = "25"
				payload["response"] = "Bill Detail(s) missing"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on allowing cash on delivery: %s" % e)
		return payload


	def get_bill(self, payload, node_info):
		try:
			if 'reference' in payload.keys():

				#An order will ALWAYS have an initial bill manager, hence

				bill_manager_list = BillManager.objects.filter(order__reference__iexact=payload['reference'],order__status__name='UNPAID').order_by("-date_created")
				if bill_manager_list.exists():
					cart_items = bill_manager_list[0].order.cart_item.all()
					if cart_items.exists():
						#Takes up the institution with the most products
						product_institution = cart_items.values('product_item__institution__id').annotate(Count('product_item__institution__id')).order_by('-product_item__institution__id__count')
						if product_institution.count() == 1:
							payload['institution_id'] = product_institution[0]['product_item__institution__id']
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
			if 'purchase_order_id' in payload.keys():
				purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])

				#Update as unpaid in all cases
				status = OrderStatus.objects.get(name='UNPAID')
				cart_status = CartStatus.objects.get(name='UNPAID')

				purchase_order.status = status
				purchase_order.save()
				purchase_order.cart_item.all().update(status=cart_status)

				#Reverse if a credit (Pay Bill) Exists
				bill_manager_list = BillManager.objects.filter(order=purchase_order).order_by("-date_created")[:1]
				if bill_manager_list.exists() and bill_manager_list[0].credit:
					order = bill_manager_list[0].order
					balance_bf = bill_manager_list[0].amount + bill_manager_list[0].balance_bf

					transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None
					bill_manager = BillManager(credit=False,transaction_reference=transaction_reference,\
							action_reference=payload['action_id'],order=order,\
							amount=balance_bf,\
							balance_bf=balance_bf)

					bill_manager.save()

					payload['amount'] = bill_manager.amount
					payload['purchase_order_id'] = order.id
					payload["response"] = "Bill Reversed. Balance: %s" % bill_manager.balance_bf
				else:
					#!!IMPORTANT - Or Account would be debitted on no bill
					payload['amount'] = Decimal(0)
					payload["response"] = "No Bill to Reverse"
			else:
				payload['response'] = "No Order to Reverse"
			#All are successes
			payload["response_status"] = "00"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on reverse pay bill: %s" % e)
		return payload


	def pay_bill(self, payload, node_info):
		try:
			if 'reference' in payload.keys():
				#An order will ALWAYS have an initial bill manager, hence

				bill_manager_list = BillManager.objects.filter(order__reference__iexact=payload['reference'],order__status__name='UNPAID').order_by("-date_created")
				if bill_manager_list.exists():
					order = bill_manager_list[0].order
					amount = Decimal(payload['balance_bf'])

					#If currency does not match purchase_order currency (FOREX) and replace amount & currency in payload
					currency = Currency.objects.get(code=payload['currency'])
					if currency <> order.currency:
						order_currency = order.currency
						forex = Forex.objects.filter(base_currency=order_currency, quote_currency=currency)
						if forex.exists():
							amount = (amount/forex[0].exchange_rate).quantize(Decimal('.01'), rounding=ROUND_UP)
						lgr.info('Forex Calculate balance_bf to %s|from: %s| %s' % (order_currency, currency, amount) )

					if amount > 0:

						if bill_manager_list[0].balance_bf <= amount:
							#payment balance_bf is greater than outstanding bill
							balance_bf = 0
							#transacting amount refers to the deduction for bill amount only
							transacting_amount = bill_manager_list[0].balance_bf
							#Resets query so transacting amount must have been captured
							status = OrderStatus.objects.get(name='PAID')
							order.status = status
							order.save()
							order.cart_item.all().update(status=CartStatus.objects.get(name='PAID'))

						else:

							#payment balance_bf is less than outstanding bill
							balance_bf = bill_manager_list[0].balance_bf - amount

							#transacting amount refers to the deduction for bill amount only
							transacting_amount = amount

						transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None
						bill_manager = BillManager(credit=True,transaction_reference=transaction_reference,\
								action_reference=payload['action_id'],order=order,\
								amount=transacting_amount,\
								balance_bf=Decimal(balance_bf).quantize(Decimal('.01'), rounding=ROUND_DOWN))
						bill_manager.payment_method = PaymentMethod.objects.get(name=payload['payment_method'])
						bill_manager.save()


						amount = bill_manager.amount
						if currency <> order.currency:
							order_currency = order.currency
							forex = Forex.objects.filter(base_currency=order_currency, quote_currency=currency)
							if forex.exists():
								amount = Decimal(amount*forex[0].exchange_rate).quantize(Decimal('.01'), rounding=ROUND_DOWN)
							lgr.info('Forex Calculate amount to %s|from: %s| %s' % (order_currency, currency, amount) )

						payload['amount'] = amount
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

			#Ensure cart product items tills match, and cart item is not added to any other purchase order
			cart_items = CartItem.objects.filter(id__in=str(payload['cart_items'].strip()).split(','),purchaseorder=None)

			if cart_items.exists():
				#get greates reference from un-expired/unpaid list (expiry after 15days)
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

				bill_manager = BillManager.objects.filter(order__gateway_profile=session_gateway_profile).order_by('-date_created')

				if 'purchase_order_id' in payload.keys():
					bill_manager = bill_manager.filter(order__id=payload['purchase_order_id'])
				elif 'transaction_reference' in payload.keys() and 'purchase_order_id' not in payload.keys():
					bill_manager_extract = bill_manager.filter(transaction_reference = payload['transaction_reference'])
					bill_manager = bill_manager.filter(order=bill_manager_extract[0].order)



				elif 'reference' in payload.keys() and 'purchase_order_id' not in payload.keys():
					bill_manager = bill_manager.filter(order__reference__iexact=payload['reference'])
				else:
					bill_manager = bill_manager.none()
				if bill_manager.exists():
					balance_bf = bill_manager[0].balance_bf
					for item in cart_items:
						purchase_order = bill_manager[0].order
						balance_bf = self.get_balance_bf(item, purchase_order, balance_bf)
						#Primary Item Bill Entry
						bill_manager = self.bill_entry(item, purchase_order, balance_bf, payload)

						balance_bf = self.sale_charge_bill_entry(balance_bf, item, payload, purchase_order, gateway_profile.gateway)

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
			cart_items = CartItem.objects.filter(id__in=str(payload['cart_items'].strip()).split(','),\
					 status=CartStatus.objects.get(name='UNPAID'))

			if cart_items.exists():

				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

				#creates reference from un-expired&unpaid list (expiry after 15days)

				def reference(pre_reference):
					chars = string.ascii_letters 
					nums = string.digits
					rnd = random.SystemRandom()
					prefix = ''.join(rnd.choice(chars) for i in range(3))
					suffix = ''.join(rnd.choice(nums) for i in range(2,4))
					trial = '%s-%s%s' % (pre_reference.upper()[:8], prefix.upper(), suffix)
					#reference_list = PurchaseOrder.objects.filter(reference=trial,status__name='UNPAID',\
					#		expiry__gte=timezone.now()).order_by('-reference')[:1]

					reference_list = PurchaseOrder.objects.filter(reference=trial).order_by('-reference')[:1]
					if reference_list.exists():
						return reference(pre_reference)
					else:
						return trial

				if 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					reference = reference(institution.business_number)
				else:
					reference = reference(gateway_profile.gateway.name)

				expiry = timezone.localtime(timezone.now())+timezone.timedelta(days=45)
				status = OrderStatus.objects.get(name='UNPAID')
				currency = cart_items[0].currency

				purchase_order = PurchaseOrder(reference=reference,\
						currency=currency,\
						status=status,expiry=expiry, gateway_profile=session_gateway_profile)

				if 'description' in payload.keys():
					purchase_order.description = payload['description']
				elif 'description' not in payload.keys() and 'comment' in payload.keys():
					purchase_order.description = payload['comment']
		
				purchase_order.save()	

				balance_bf = Decimal(0)
				for item in cart_items:
					balance_bf = self.get_balance_bf(item, purchase_order, balance_bf)
					#Primary Item Bill Entry
					bill_manager = self.bill_entry(item, purchase_order, balance_bf, payload)

					balance_bf = self.sale_charge_bill_entry(balance_bf, item, payload, purchase_order, gateway_profile.gateway)

				payload['reference'] = purchase_order.reference
				payload['purchase_order_id'] = purchase_order.id

				payload["response_status"] = "00"
				payload["response"] = "Purchase Order Created"
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on creating purchase order: %s" % e)
		return payload

	def add_product_to_cart(self, payload, node_info):
		try:

			product_item = ProductItem.objects.get(id=payload['product_item_id'])
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])




			quantity = Decimal(payload['quantity']) if 'quantity' in payload.keys() and payload['quantity'] not in ["",None] else Decimal(1)
			sub_total = Decimal(product_item.unit_cost*quantity).quantize(Decimal('.01'), rounding=ROUND_DOWN)
			total = sub_total

			if 'quantity' not in payload.keys() and product_item.variable_unit and 'amount' in payload.keys():
				quantity = Decimal(Decimal(payload['amount'])/product_item.unit_cost).quantize(Decimal('.01'), rounding=ROUND_DOWN)
				sub_total = Decimal(product_item.unit_cost*quantity).quantize(Decimal('.01'), rounding=ROUND_DOWN)
				total = sub_total


			primary_item = self.cart_entry(product_item, payload, quantity, sub_total, total)

			payload['cart_items'] = '%s%s' % (primary_item.id, ','+payload['cart_items'] if 'cart_items' in payload.keys() else '')

			sale_charge_item = self.sale_charge_item(total, primary_item, payload, gateway_profile.gateway)
			if sale_charge_item:
				payload['cart_items'] = '%s%s' % (sale_charge_item.id, ','+payload['cart_items'] if 'cart_items' in payload.keys() else '')

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
				for c in purchase_order:
					c.update(status=CartStatus.objects.get(name='CANCELLED'))

				payload['response'] = 'Sale Order Cancelled'
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
						payload["response"] = payload['reference']
					else:
						payload["response"] = "Sale Order"

		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Order: %s" % e)
		return payload



	def bulk_sale_order(self, payload, node_info):
		try:
			product_item_list = payload['product_item_list']
			purchase_order_id = None
			for i in product_item_list:
				payload = self.add_product_to_cart(i, node_info)
				if 'response_status' in payload.keys() and payload['response_status'] == '00':
					if purchase_order_id:
						payload['purchase_order_id'] = purchase_order_id
						payload = self.add_to_purchase_order(payload, node_info)

					else:
						payload = self.create_purchase_order(payload, node_info)
						purchase_order_id = payload['purchase_order_id']

					if 'response_status' in payload.keys() and payload['response_status'] == '00':
						payload["response_status"] = "00"
						if 'reference' in payload.keys():
							payload["response"] = payload['reference']
						else:
							payload["response"] = "Sale Order"
				else:
					break

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
						payload["response"] = payload['reference']
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


			#transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None
			transaction = Transaction.objects.get(id=payload["bridge__transaction_id"])

			primary_contact_profile = Profile.objects.get(id=payload['profile_id'])
			lgr.info("Starting Generating Till Number")
			all_contacts = SaleContact.objects.filter(institution=gateway_profile.institution).order_by("-sale_contact_number")[:1]
			if len(all_contacts)>0:
				sale_contact_number = all_contacts[0].sale_contact_number+1
			else:
				sale_contact_number = 1

			try:details = json.loads(transaction.request)
			except: details = json.loads({})

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

	def delivery_notification(self, payload, node_info):
		'''
		add model pos.DeliveryContact
			profile (upc.Profile)
			institution (upc.Institution)
			status AVAILABLE DELIVERING
		add model pos.DeliveryActivity
			delivery (pos.Delivery)
			contact (pos.DeliveryContact)
			status NOTIFIED ACCEPTED REJECTED
		'''
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			try:
				delivery_contact = DeliveryContact.objects.get(gateway_profile = gateway_profile)
			except:
				delivery_contact = DeliveryContact()
				delivery_contact.gateway_profile = gateway_profile
				delivery_contact.save()

			delivery_activity = DeliveryActivity()
			delivery_activity.delivery_id = payload['delivery']
			delivery_activity.contact = delivery_contact
			delivery_activity.status = DeliveryActivityStatus.objects.get(name='NOTIFIED')
			delivery_activity.save()

			# TODO : send delivery notification


			payload["response_status"] = "00"
			payload["response"] = "Sale Contact Created"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Contact: %s" % e)

		return payload

	def create_delivery(self, payload, node_info):
		try:
			# gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])
			cart_item = CartItem.objects.get(id=payload['cart_item_id'])
			product_item = cart_item.product_item
			institution = product_item

			delivery_types = DeliveryType.objects.filter(institution=institution)
			if delivery_types.exists():
				deliveries = Delivery.objects.filter(delivery_type__institution=institution,order=purchase_order)
				if not deliveries.exists():
					delivery = Delivery()
					delivery_type = DeliveryType.objects.get(id=payload['delivery_type'])
					delivery.order_id = payload['purchase_order_id']
					delivery.status = DeliveryStatus.objects.get(name='WAITTING')

					delivery.save()
					delivery.delivery_type.add(delivery_type)

					payload["delivery_id"] = delivery.pk

			payload["response_status"] = "00"
			payload["response"] = "Delivery Created"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Delivery: %s" % e)

		return payload


	def create_delivery_activities(self, payload, node_info):
		try:
			profiles_id_list = payload['profiles'].split(',')
			delivery = Delivery.objects.get(pk=payload['delivery_id'])
			g_profiles = GatewayProfile.objects.filter(id__in=profiles_id_list)

			for g_profile in g_profiles:
				delivery_activity = DeliveryActivity()
				delivery_activity.delivery = delivery
				delivery_activity.profile = g_profile.user.profile
				delivery_activity.status = DeliveryActivityStatus.objects.get(name='NOTIFIED')
				delivery_activity.save()

				# payload["delivery_activity"] = delivery_activity.pk
			delivery.status = DeliveryStatus.objects.get(name='ASSIGNED')
			delivery.save()

			payload["response_status"] = "00"
			payload["response"] = "Delivery Activities Created"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Delivery Activities: %s" % e)

		return payload


	def order_status(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if gateway_profile.access_level == AccessLevel.objects.get(name='DELIVERY'):
				delivery_activity = DeliveryActivity.objects.get(id=payload['delivery_activity_id'])

				purchase_order = delivery_activity.delivery.order

				payload['purchase_order_id'] = purchase_order.pk

				delivery_activities = DeliveryActivity.objects.filter(delivery__order=purchase_order)
				# accepted_by_me
				if delivery_activities.filter(profile=gateway_profile.user.profile,status__name='ACCEPTED').exists():
					payload['trigger'] = 'accepted_by_me%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				# accepted_by_else
				elif delivery_activities.filter(status__name='ACCEPTED').exists():
					payload['trigger'] = 'accepted_by_else%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')
				else:
					payload['trigger'] = 'accepted_by_none%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')

			else:
				# purchase_order = PurchaseOrder.objects.get(id = payload['purchase_order_id'])
				delivery = Delivery.objects.get(id=payload['delivery_id'])
				purchase_order = delivery.order

				payload['purchase_order_id'] = purchase_order.pk
				if delivery.status.name =='WAITTING CONFIRMATION':
					payload['trigger'] = 'should_confirm%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')


			payload["response_status"] = "00"
			payload["response"] = "Got Purchase Order Details"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on getting Purchase Order Details: %s" % e)

		return payload


	def accept_delivery_activity(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			delivery_activity = DeliveryActivity.objects.get(id=payload['delivery_activity_id'])

			purchase_order = delivery_activity.delivery.order
			payload['purchase_order_id'] = purchase_order.pk

			delivery_activity.delivery.status =  DeliveryStatus.objects.get(name='IN_PROCESS')
			delivery_activity.delivery.save()


			DeliveryActivity.objects.filter(delivery__order=purchase_order)\
				.update(status = DeliveryActivityStatus.objects.get(name='REJECTED'))

			delivery_activity.status = DeliveryActivityStatus.objects.get(name='ACCEPTED')
			delivery_activity.save()

			payload["response_status"] = "00"
			payload["response"] = "Delivery Activity Accepted"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on accepting Delivery Activity: %s" % e)

		return payload

	def delivery_done(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			delivery_activity = DeliveryActivity.objects.get(id=payload['delivery_activity_id'])

			purchase_order = delivery_activity.delivery.order
			payload['purchase_order_id'] = purchase_order.pk

			delivery_activity.delivery.status =  DeliveryStatus.objects.get(name='WAITTING CONFIRMATION')
			delivery_activity.delivery.save()

			delivery_activity.status = DeliveryActivityStatus.objects.get(name='COMPLETED')
			delivery_activity.save()

			payload["response_status"] = "00"
			payload["response"] = "Delivery Activity COMPLETED"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Completing Delivery Activity: %s" % e)

		return payload

	def delivery_confirm(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#purchase_order = PurchaseOrder.objects.get()
			delivery = Delivery.objects.get(id=payload['delivery_id'])

			delivery.status = DeliveryStatus.objects.get(name='DELIVERED')
			delivery.save()

			payload["response_status"] = "00"
			payload["response"] = "Delivery Activity confirmed"
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Confirming Delivery Activity: %s" % e)

		return payload




class Trade(System):
	pass


class Payments(System):
	pass


@app.task(ignore_result=True)
def order_service_call(order):
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		o = PurchaseOrder.objects.get(id=order)
		lgr.info('Captured Order: %s' % o)
		cart_item = o.cart_item.all()
		for c in cart_item:
			lgr.info('Captured Cart Item: %s' % c)
			product_item = c.product_item
			payload = json.loads(c.details)	

			gateway_profile = c.gateway_profile
			service = c.product_item.product_type.service

			payload['cart_item_id'] = c.id
			payload['purchase_order_id'] = o.id
			payload['product_item_id'] = c.product_item.id
			payload['item'] = c.product_item.name
			payload['product_type'] = c.product_item.product_type.name
			payload['quantity'] = c.quantity
			payload['currency'] = c.currency.code
			payload['amount'] = c.total
			payload['reference'] = o.reference
			#payload['institution_id'] = c.product_item.institution.id
			payload['chid'] = c.channel.id
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = '127.0.0.1'

			payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception, e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload



@app.task(ignore_result=True)
def service_call(payload):
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		payload = json.loads(payload)
		payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))

		service = Service.objects.get(id=payload['service_id'])
		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)
		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception, e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_paid_order():
	lgr = get_task_logger(__name__)
	try:
		orig_order = PurchaseOrder.objects.select_for_update().filter(Q(status__name='PAID'),Q(cart_processed=False),\
					Q(cart_item__status__name='PAID'),~Q(cart_item__product_item__product_type__service=None),\
					Q(date_modified__lte=timezone.now()-timezone.timedelta(seconds=1)))
		order = list(orig_order.values_list('id',flat=True)[:500])

		processing = orig_order.filter(id__in=order).update(cart_processed=True, date_modified=timezone.now())
		for od in order:
			order_service_call.delay(od)
	except Exception, e: lgr.info('Error on process paid order')



	'''
	order = PurchaseOrder.objects.select_for_update().filter(status__name='PAID',cart_processed=False,\
		 date_modified__lte=timezone.now()-timezone.timedelta(seconds=10))[:10]

	for o in order:
		try:
			o.cart_processed = True
			o.save()
			lgr.info('Captured Order: %s' % o)
			cart_item = o.cart_item.filter(status__name='PAID')
			for c in cart_item:
				lgr.info('Captured Cart Item: %s' % c)
				product_item = c.product_item
				payload = json.loads(c.details)	

				service = c.product_item.product_type.service
				payload['service_id'] = service.id
				payload['purchase_order_id'] = o.id
				payload['product_item_id'] = c.product_item.id
				payload['item'] = c.product_item.name
				payload['product_type'] = c.product_item.product_type.name
				payload['gateway_profile_id'] = c.gateway_profile.id
				payload['quantity'] = c.quantity
				payload['currency'] = c.currency.code
				payload['amount'] = c.total
				payload['reference'] = o.reference
				#payload['institution_id'] = c.product_item.institution.id
				payload['chid'] = c.channel.id
				payload['ip_address'] = '127.0.0.1'
				payload['gateway_host'] = '127.0.0.1'

	    			payload = json.dumps(payload, cls=DjangoJSONEncoder)
				
				lgr.info('Product Item: %s | Payload: %s' % (product_item, payload))
				if service is None:
					lgr.info('No Service to process for product: %s' % product_item)
				else:
					try:service_call(payload)
					except Exception, e: lgr.info('Error on Service Call: %s' % e)
		except Exception, e:
			lgr.info('Error processing paid order item: %s | %s' % (o,e))
	'''
