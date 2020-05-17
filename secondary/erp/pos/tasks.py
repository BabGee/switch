from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task, group, chain
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import simplejson as json
import pytz, time, os, random, string
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import base64, re
from django.core.files import File
from django.db.models import Count, Sum
from django.db import transaction
import numpy as np
from django.db.models import Q, F
import operator
#from secondary.channels.notify.mqtt import MqttServerClient
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers

from primary.core.administration.views import WebService
from primary.core.api.views import Authorize

from secondary.erp.pos.models import *

import logging
lgr = logging.getLogger('secondary.erp.pos')


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

		if 'callback_url' in payload.keys():
			cart_item.api_callback_url = payload['callback_url']
			cart_item.api_callback_status = APICallBackStatus.objects.get(name='CREATED')
			cart_item.api_gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

		cart_item.save()

		return cart_item

	def sale_charge_item(self, balance_bf, item, payload, gateway):
		#Sale Charge Item Bill entry
		sale_charge_item = None
		sale_charge = SaleCharge.objects.filter(Q(min_amount__lt=balance_bf,max_amount__gt=balance_bf,credit=False),\
						Q(Q(product_display=item.product_item.product_display)|Q(product_display=None)),\
						Q(Q(product_type=item.product_item.product_type)|Q(product_type=None)),\
						Q(Q(institution=item.product_item.institution)|Q(institution=None)),\
						Q(Q(gateway=gateway)|Q(gateway=None)))
		for sc in sale_charge:

			charge = Decimal(0)

			if 'delivery_location_coord' in payload.keys():
				coordinates = payload['delivery_location_coord']
				longitude, latitude = coordinates.split(',', 1)
				trans_point = Point(float(longitude), float(latitude))
				distance = sc.main_location.distance(trans_point)
				distance_in_km = Decimal(distance) * Decimal(100)
				if sc.min_distance<=distance_in_km and sc.max_distance>distance_in_km:
					charge = (sc.charge_per_km * distance_in_km) + sc.charge_value

			product_item = sc.sale_charge_type.product_item

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
						Q(Q(product_display=item.product_item.product_display)|Q(product_display=None)),\
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
			 'service' not in key and key != 'lat' and key != 'lng' and \
			 key != 'chid' and 'session' not in key and 'csrf_token' not in key and \
			 'csrfmiddlewaretoken' not in key and 'gateway_host' not in key and \
			 'gateway_profile' not in key and 'transaction_timestamp' not in key and \
			 'action_id' not in key and 'bridge__transaction_id' not in key and \
			 'merchant_data' not in key and 'signedpares' not in key and \
			 key != 'gpid' and key != 'sec' and \
			 key not in ['ext_product_id','vpc_securehash','currency','amount'] and \
			 'institution_id' not in key and key != 'response' and key != 'input' and \
			 key != 'repeat_bridge_transaction' and key != 'transaction_auth':

				if count <= 30:
					new_payload[str(k)[:30] ] = str(v)[:40]
				else:
					break
				count = count+1

		return json.dumps(new_payload)


class System(Wrappers):

	def update_outgoing_payment(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])
			purchase_order.outgoing_payment=Outgoing.objects.get(id=payload['paygate_outgoing_id'])
			purchase_order.save()

			payload['response'] = 'Outgoing Payment Updated'
			payload['response_status'] = '00'
		except Exception as e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Update Outgoing Payment: %s" % e)

		return payload



	def log_order_activity(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			try:
				order_product = OrderProduct.objects.filter(service__name=payload['SERVICE'])

				lgr.info('Got HEre')
				if 'currency' in payload.keys():
					order_product = order_product.filter(Q(currency__code=payload['currency'])|Q(currency=None))

				if 'payment_method' in payload.keys():
					order_product = order_product.filter(Q(payment_method__name=payload['payment_method'])\
								|Q(payment_method=None))

				if 'product_type_id' in payload.keys():
					order_product = order_product.filter(Q(product_type__id=payload['product_type_id'])\
								|Q(product_type=None))

				if 'product_item_id' in payload.keys():
					product_item = ProductItem.objects.get(id=payload['product_item_id'])
					order_product = order_product.filter(Q(product_type=product_item.product_type)\
								|Q(product_type=None))

				if 'ext_product_id' in payload.keys():
					order_product = order_product.filter(ext_product_id=payload['ext_product_id'])

				lgr.info('Got HEre')
				if order_product.exists():
					#log 
					response_status = ResponseStatus.objects.get(response='DEFAULT')
					status = TransactionStatus.objects.get(name="CREATED")
					order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])
					channel = Channel.objects.get(id=payload['chid'])
					lgr.info('Got HEre')

					reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else ''
					
					order_activity = OrderActivity(order_product=order_product[0], order=order, transaction_reference=reference,\
							gateway_profile=gateway_profile, request=self.transaction_payload(payload),\
							response_status=response_status, sends=0, status=status, \
							channel=channel, gateway=gateway_profile.gateway)

					lgr.info('Got HEre')
					if 'scheduled_send' in payload.keys() and payload['scheduled_send'] not in ["",None]:
						try:date_obj = datetime.strptime(payload["scheduled_send"], '%d/%m/%Y %I:%M %p')
						except: date_obj = None
						if date_obj is not None:		
							profile_tz = pytz.timezone(gateway_profile.profile.timezone)
							scheduled_send = pytz.timezone(gateway_profile.profile.timezone).localize(date_obj)
							lgr.info("Send Scheduled: %s" % scheduled_send)
						else:
							scheduled_send = timezone.now()+timezone.timedelta(seconds=1)
					else:
						scheduled_send = timezone.now()+timezone.timedelta(seconds=1)

					order_activity.scheduled_send = scheduled_send

					lgr.info('Got HEre')
					if 'ext_inbound_id' in payload.keys() and payload['ext_inbound_id'] not in ["",None]:
						order_activity.ext_inbound_id = payload['ext_inbound_id']
					elif 'bridge__transaction_id' in payload.keys():
						order_activity.ext_inbound_id = payload['bridge__transaction_id']

					if 'currency' in payload.keys() and payload['currency'] not in ["",None]:
						order_activity.currency = Currency.objects.get(code=payload['currency'])
					if 'amount' in payload.keys() and payload['amount'] not in ["",None]:
						order_activity.amount = Decimal(payload['amount'])
					if 'charge' in payload.keys() and payload['charge'] not in ["",None]:
						order_activity.charge = Decimal(payload['charge'])

					order_activity.save()

					lgr.info('Got HEre')
					payload['response'] = 'Order Activity Logged'
					payload['response_status'] = '00'
				else:
					payload['response'] = 'Order Activity product not found'
					payload['response_status'] = '92'

			except ProductItem.DoesNotExist:
				lgr.info("ProdutItem Does not Exist")
				payload['response_status'] = '25'

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Order Activity: %s" % e)
		return payload


	def settle_order_charges(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			amount = Decimal(payload['amount'])
			charge = Decimal(0)

			if 'institution_id' in payload.keys():
				charge_list = OrderCharge.objects.filter(institution__id=payload['institution_id'], min_amount__lte=Decimal(amount), order_product__service__name=payload['SERVICE'],\
						max_amount__gte=Decimal(amount))
			elif 'product_item_id' in payload.keys():
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				payload['institution_id'] = product_item.institution.id
				charge_list = OrderCharge.objects.filter(institution=product_item.institution, min_amount__lte=Decimal(amount), order_product__service__name=payload['SERVICE'],\
						max_amount__gte=Decimal(amount))
			else:
				charge_list = OrderCharge.objects.none()


			if 'payment_method' in payload.keys():
				charge_list = charge_list.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			for c in charge_list:
				if c.is_percentage:
					charge = charge + ((c.charge_value/100)*Decimal(amount))
				else:
					charge = charge+c.charge_value		

			payload['amount'] = amount - charge
			payload['charge'] = charge

			payload["response_status"] = "00"
			payload['response'] = "Order Charges Settled"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("error settle order charges: %s" % e)

		return payload


	def settle_paid_orders(self, payload, node_info):
		try:
			
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			bill_manager_list = BillManager.objects.filter(order__status__name='PAID',order__cart_item__status__name='PAID')
			if gateway_profile.institution:
				bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution=gateway_profile.institution)
			elif 'institution_id' in payload.keys():
				bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution__id=payload['institution_id'])
			else:
				bill_manager_list = bill_manager_list.none()

			if 'product_type_list' in payload.keys():
				#product_type_list = '23,65,123,35,563,34,42'
				bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__product_type__id__in=[p for p in payload['product_type_list'].split(',') if p])

			settled_amount = Decimal(0)
			if bill_manager_list.exists():
				settled_amount = bill_manager_list.aggregate(Sum('balance_bf'))['balance_bf__sum']
				settle_orders.delay(np.unique(np.asarray(bill_manager_list.values_list('order__id',flat=True))).tolist())

			payload['settled_amount'] = settled_amount
			payload["response_status"] = "00"
			payload['response'] = "Settled: %s" % settled_amount

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("error settling paid ordes: %s" % e)

		return payload

	def create_sale_charge(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			product_item = ProductItem.objects.get(id=payload['product_item_id'])

			sale_charge_type = SaleChargeType(name=product_item.name, description=product_item.description,\
							product_item=product_item)
			sale_charge_type.save()
			sale_charge = SaleCharge(sale_charge_type=sale_charge_type,description=product_item.description)
			if 'credit' in payload.keys() and payload['credit']:
				sale_charge.credit = True

			sale_charge.min_amount = payload['min_amount'] if 'min_amount' in payload.keys() else 0
			sale_charge.max_amount = payload['max_amount'] if 'max_amount' in payload.keys() else 999999
			sale_charge.charge_value = payload['charge_value'] if 'charge_value' in payload.keys() else 0

			if 'is_percentage' in payload.keys() and payload['is_percentage']:
				sale_charge.is_percentage = True
			if 'main_location' in payload.keys():
				coordinates = payload['main_location']
				longitude, latitude = coordinates.split(',', 1)
				trans_point = Point(float(longitude), float(latitude))
				sale_charge.main_location = trans_point

			if 'min_distance' in payload.keys(): sale_charge.min_distance = payload['min_distance']
			if 'max_distance' in payload.keys(): sale_charge.max_distance = payload['max_distance']
			if 'charge_per_km' in payload.keys(): sale_charge.charge_per_km = payload['charge_per_km']
			if 'per_item' in payload.keys() and payload['per_item']:
				sale_charge.max_distance = payload['max_distance']

			sale_charge.save()

			sale_charge.product_display.add(ProductDisplay.objects.get(name='SHOP'))
			sale_charge.product_type.add(ProductType.objects.get(id=111))
			sale_charge.institution.add(gateway_profile.institution)
			sale_charge.gateway.add(gateway_profile.gateway)

			payload["response_status"] = "00"
			payload["response"] = "Sale Charge Created"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Charge: %s" % e)
		return payload


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
		except Exception as e:
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
		except Exception as e:
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
		except Exception as e:
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Delete Cart Item: %s" % e)
		return payload

	def window_event(self, payload, node_info):
		try:
			payload["response_status"] = "00"
			payload["response"] = "Window Event"
		except Exception as e:
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on allowing cash on delivery: %s" % e)
		return payload


	def check_order_status(self, payload, node_info):
		try:
			if 'reference' in payload.keys():

				#An order will ALWAYS have an initial bill manager, hence
				reference = payload['reference'].strip()
				bill_manager_list = BillManager.objects.filter(order__reference__iexact=reference,order__status__name__in=['UNPAID','PAID']).order_by("-date_created")
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
					if bill_manager_list.filter(order__status__name='UNPAID').exists():
						payload['trigger'] = 'unpaid_order%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload["response"] = "Unpaid Order"
					else:
						payload['trigger'] = 'paid_order%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
						payload["response"] = "Paid Order"
				else:
					payload["response_status"] = "25"
					payload["response"] = "No Purchase Order with given reference"
			else:
				payload["response_status"] = "25"
				payload["response"] = "No Purchase Order reference was given"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on pay bill: %s" % e)
		return payload



	def get_bill(self, payload, node_info):
		try:
			if 'reference' in payload.keys():

				#An order will ALWAYS have an initial bill manager, hence
				reference = payload['reference'].strip()
				bill_manager_list = BillManager.objects.filter(order__reference__iexact=reference,order__status__name='UNPAID').order_by("-date_created")
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
		except Exception as e:
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on reverse pay bill: %s" % e)
		return payload


	def pay_bill(self, payload, node_info):
		try:
			if 'reference' in payload.keys():
				#An order will ALWAYS have an initial bill manager, hence
				reference = payload['reference'].strip()

				bill_manager_list = BillManager.objects.filter(order__reference__iexact=reference,order__status__name='UNPAID').order_by("-date_created")
				if bill_manager_list.exists():
					order = bill_manager_list[0].order
					amount = Decimal(payload['balance_bf'])

					#If currency does not match purchase_order currency (FOREX) and replace amount & currency in payload
					currency = Currency.objects.get(code=payload['currency'])
					if currency != order.currency:
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

						if 'paygate_incoming_id' in payload.keys():
							bill_manager.incoming_payment = Incoming.objects.get(id=payload['paygate_incoming_id'])

						bill_manager.save()


						amount = bill_manager.amount
						if currency != order.currency:
							order_currency = order.currency
							forex = Forex.objects.filter(base_currency=order_currency, quote_currency=currency)
							if forex.exists():
								amount = Decimal(amount*forex[0].exchange_rate).quantize(Decimal('.01'), rounding=ROUND_DOWN)
							lgr.info('Forex Calculate amount to %s|from: %s| %s' % (order_currency, currency, amount) )

						payload['bill_manager_id'] = bill_manager.id
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


		except Exception as e:
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
				if 'session_gateway_profile_id' in payload.keys():
					session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				else:
					session_gateway_profile = gateway_profile

				bill_manager = BillManager.objects.filter(order__gateway_profile=session_gateway_profile).order_by('-date_created')

				if 'purchase_order_id' in payload.keys():
					bill_manager = bill_manager.filter(order__id=payload['purchase_order_id'])
				elif 'reference' in payload.keys():
					reference = payload['reference'].strip()
					bill_manager = bill_manager.filter(order__reference__iexact=reference)
				elif 'transaction_reference' in payload.keys():
					bill_manager_extract = bill_manager.filter(transaction_reference = payload['transaction_reference'])
					if bill_manager_extract.exists(): bill_manager = bill_manager.filter(order=bill_manager_extract[0].order)
					else: bill_manager = bill_manager.none()
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

		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on creating purchase order: %s" % e,exc_info=True)
		return payload


	def create_purchase_order(self, payload, node_info):
		try:

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			#Ensure cart product items tills match
			cart_items = CartItem.objects.filter(id__in=str(payload['cart_items'].strip()).split(','),\
					 status=CartStatus.objects.get(name='UNPAID'))

			if cart_items.exists():
				if 'session_gateway_profile_id' in payload.keys():
					session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				else:
					session_gateway_profile = gateway_profile
					session_gateway_profile_system = GatewayProfile.objects.get(gateway=gateway_profile.gateway,
																		 user__username='System@User',status__name='ACTIVATED')

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

				if 'reference' in payload.keys():
					reference_order = PurchaseOrder.objects.filter(status__name='UNPAID', reference__iexact=payload['reference'],
								cart_item__product_item__institution__id__in=[i['product_item__institution__id'] \
								for i in cart_items.values('product_item__institution__id').distinct('product_item__institution__id')])
					if reference_order.exists(): reference_order.update(status=OrderStatus.objects.get(name='CANCELLED'))			
					reference = payload['reference']
				elif 'institution_id' in payload.keys():
					institution = Institution.objects.get(id=payload['institution_id'])
					reference = reference(institution.business_number)
				else:
					reference = reference(gateway_profile.gateway.name)

				if 'expiry' in payload.keys():
					expiry = datetime.strptime(payload['expiry'], '%Y-%m-%d')
				elif 'expiry_days_period' in payload.keys():
					expiry = timezone.now()+timezone.timedelta(days=(int(payload['expiry_days_period'])))
				elif 'expiry_years_period' in payload.keys():
					expiry = timezone.now()+timezone.timedelta(days=(365*int(payload['expiry_years_period'])))
				elif 'expiry_seconds_period' in payload.keys():
					expiry = timezone.now()+timezone.timedelta(seconds=(int(payload['expiry_seconds_period'])))
				else:
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
		except Exception as e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on creating purchase order: %s" % e,exc_info=True)
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
		except Exception as e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on Adding product to cart: %s" % e,exc_info=True)
		return payload

	def cancel_sale_order(self, payload, node_info):
		try:

			reference = payload['reference'].strip() if 'reference' in payload.keys() else ""
			purchase_order = PurchaseOrder.objects.filter(reference=reference, status__name='UNPAID')

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
		except Exception as e:
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

		except Exception as e:
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

		except Exception as e:
			payload['response'] = str(e)
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

		except Exception as e:
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
		except Exception as e:
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Sale Contact: %s" % e)

		return payload

	def create_delivery(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])

			if 'delivery_location_coord' not in payload.keys() and 'delivery_location_name' not in payload.keys():
				payload["response_status"] = "00"
				payload["response"] = "Delivery Not Created, No Location Specified"
				return payload

			# delivery_types = DeliveryType.objects.filter(institution=institution)
			# if delivery_types.exists():
			deliveries = Delivery.objects.filter(order=purchase_order)
			if not deliveries.exists():
				delivery = Delivery()
				delivery.order_id = payload['purchase_order_id']
				delivery.status = DeliveryStatus.objects.get(name='CREATED')
				# TODO

				try:
					date_string = payload['scheduled_date'] + ' ' + payload['scheduled_time']
					date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
					scheduled_send = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)
					delivery.schedule = scheduled_send

				except:pass
				lgr.info("Delivery schedule : {}".format(delivery.schedule))

				if 'delivery_location_coord' in payload.keys():
					coordinates = payload['delivery_location_coord']
					longitude, latitude = coordinates.split(',', 1)
					trans_point = Point(float(longitude), float(latitude))
					delivery.destination_coord = trans_point
				if 'delivery_location_name' in payload.keys():
					delivery.destination_name = payload['delivery_location_name']


				delivery.save()

				payload["delivery_id"] = delivery.pk

			payload["response_status"] = "00"
			payload["response"] = "Delivery Created"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Delivery: %s" % e)

		return payload


	def create_delivery_type(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			institution = gateway_profile.institution
			channel = Channel.objects.get(name=payload['channel'])

			delivery_types = DeliveryType.objects.filter(institution=institution,channel=channel,gateway=gateway_profile.gateway)
			if delivery_types.exists():
				pass
			else:
				delivery_type = DeliveryType()
				delivery_type.channel = channel
				delivery_type.institution = institution
				delivery_type.status = DeliveryTypeStatus.objects.get(name='ACTIVE')
				delivery_type.gateway = gateway_profile.gateway
				delivery_type.save()
				payload["delivery_id"] = delivery_type.pk

			payload["response_status"] = "00"
			payload["response"] = "Delivery Type Created"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Creating Delivery Type: %s" % e)

		return payload


	def assign_order(self, payload, node_info):
		try:
			delivery = Delivery.objects.get(pk=payload['delivery_id'])
			delivery_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])

			delivery.delivery_profile = delivery_profile
			delivery.status = DeliveryStatus.objects.get(name='ASSIGNED')
			delivery.save()

			# used for sending notifications
			payload['msisdn'] = delivery_profile.msisdn.phone_number

			payload["response_status"] = "00"
			payload["response"] = "Delivery Assigned"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Assigning Delivery: %s" % e)

		return payload

	def order_has_delivery(self, payload, node_info):
		'''
		Adds a trigger `has_delivery` if the purchaser_order has a Delivery
		'''
		try:
			deliveries = Delivery.objects.filter(order_id=payload['purchase_order_id'])
			if deliveries.exists():
				payload['delivery_id'] = deliveries[0].pk
				payload['trigger'] = 'has_delivery%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')
			else:
				payload['trigger'] = 'no_delivery%s' % (
					',' + payload['trigger'] if 'trigger' in payload.keys() else '')

			payload['response_status'] = '00'
			payload['response'] = 'Checked Delivery'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Checking Delivery: %s" % e)
		return payload


	def order_status(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if 'delivery_id' in payload.keys():
				delivery = Delivery.objects.get(id=payload['delivery_id'])
			elif 'purchase_order_id' in payload.keys():
				purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])
				delivery = Delivery.objects.filter(order=purchase_order).first()
			# delivery = Delivery.objects.get(id=payload['delivery_id'])

			purchase_order = delivery.order
			payload['purchase_order_id'] = purchase_order.pk
			if gateway_profile.access_level == AccessLevel.objects.get(name='DELIVERY'):
				# accepted_by_me
				if delivery.delivery_profile == gateway_profile:
					if delivery.status.name == 'IN PROGRESS':
						payload['trigger'] = 'accepted_by_me%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
					elif delivery.status.name == 'ASSIGNED':
						payload['trigger'] = 'accepted_by_none%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')
			else:
				if delivery.status.name =='WAITTING CONFIRMATION':
					payload['trigger'] = 'should_confirm%s' % (',' + payload['trigger'] if 'trigger' in payload.keys() else '')

			payload['delivery_status'] = delivery.status.name
			payload["response_status"] = "00"
			payload["response"] = "Got Purchase Order Details"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on getting Purchase Order Details: %s" % e)

		return payload


	def accept_order(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			delivery = Delivery.objects.get(id=payload['delivery_id'])

			purchase_order = delivery.order
			payload['purchase_order_id'] = purchase_order.pk

			#coordinates = payload['delivery_origin']
			#longitude, latitude = coordinates.split(',', 1)
			#trans_point = Point(float(longitude), float(latitude))
			#delivery.origin_name = coordinates
			#delivery.origin_coord = trans_point
			delivery.status =  DeliveryStatus.objects.get(name='IN PROGRESS')
			delivery.save()


			payload["response_status"] = "00"
			payload["response"] = "Delivery Accepted Accepted"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on accepting Delivery: %s" % e)

		return payload

	def delivery_done(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			delivery = Delivery.objects.get(id=payload['delivery_id'])

			delivery.status =  DeliveryStatus.objects.get(name='WAITTING CONFIRMATION')
			delivery.save()

			payload["response_status"] = "00"
			payload["response"] = "Delivery DELIVERED"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Completing Delivery: %s" % e)

		return payload

	def delivery_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if 'delivery_id' in payload.keys():
				delivery = Delivery.objects.get(id=payload['delivery_id'])

			elif 'purchase_order_id' in payload.keys():
				purchase_order = PurchaseOrder.objects.get(id=payload['purchase_order_id'])
				delivery = Delivery.objects.filter(order=purchase_order).first()

			purchase_order = delivery.order
			payload['purchase_order_id'] = purchase_order.pk
			payload['delivery_status'] = delivery.status.name

			if delivery.delivery_profile:
				if delivery.delivery_profile.msisdn: payload['delivery_profile_phone'] = delivery.delivery_profile.msisdn.phone_number
				delivery_user = delivery.delivery_profile.user
				payload['delivery_profile_name'] = delivery_user.first_name +' '+delivery_user.last_name

			payload['delivery_origin_name'] = delivery.origin_name
			if delivery.origin_coord:
				payload['delivery_origin_coord'] = '{},{}'.format(delivery.origin_coord.x,delivery.origin_coord.y)
			payload['delivery_destination_name'] = delivery.destination_name
			if delivery.destination_coord:
				payload['delivery_destination_coord'] = '{},{}'.format(delivery.destination_coord.x, delivery.destination_coord.y)

			delivery_recipient = purchase_order.gateway_profile
			payload['delivery_recipient_name'] = delivery_recipient.user.first_name+' '+delivery_recipient.user.last_name
			if delivery_recipient.msisdn:payload['delivery_recipient_phone'] = delivery_recipient.msisdn.phone_number

			payload['delivery_schedule'] = delivery.schedule

			payload["response_status"] = "00"
			payload["response"] = "Got Delivery Details"
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error Getting Delivery Details: %s" % e)
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
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Confirming Delivery Activity: %s" % e)

		return payload




class Trade(System):
	pass


class Payments(System):
	pass



@app.task(ignore_result=True)
def callback_url_call(bill, cart):
	lgr = get_task_logger(__name__)
	try:
		bill_manager = BillManager.objects.get(id=bill)
		cart_item = CartItem.objects.get(id=cart)

		payload = json.loads(cart_item.details)

		payload.update(json.loads(bill_manager.incoming_payment.request))
		payload['quantity'] = cart_item.quantity
		payload['currency'] = cart_item.currency.code
		payload['amount'] = cart_item.total

		payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))

		API_KEY = cart_item.api_gateway_profile.user.profile.api_key
		payload = Authorize().return_hash(payload, API_KEY)
		node = cart_item.api_callback_url

		lgr.info("Payload: %s| Node: %s" % (payload, node) )

		payload = WebService().post_request(payload, node)

		lgr.info('CallBack Response: %s' % payload)
		if 'response' in payload.keys(): cart_item.api_message = payload['response'][:128]
		if 'response_status' in payload.keys() and payload['response_status'] == '00':
			cart_item.api_callback_status = APICallBackStatus.objects.get(name='SENT')
		else:
			cart_item.api_callback_status = APICallBackStatus.objects.get(name='FAILED')

		cart_item.save()

	except Exception as e:
		lgr.info('Error on CallBack URL Call: %s' % e)


@app.task(ignore_result=True)
@transaction.atomic
def settle_orders(order_list):
	for o in order_list:
		order = PurchaseOrder.objects.get(id=o)
		order.status = OrderStatus.objects.get(name='SETTLED')
		order.cart_processed = False
		order.save()

		order.cart_item.update(status=CartStatus.objects.get(name='SETTLED'))


@app.task(ignore_result=True)
def order_background_service_call(order, status):
	lgr = get_task_logger(__name__)
	try:
		from primary.core.bridge.tasks import Wrappers as BridgeWrappers
		#o = PurchaseOrder.objects.get(id=order)
		lgr.info('Started Order Service Call: %s' % order)
		bill = BillManager.objects.filter(order__id=order).last()
		o = bill.order
		lgr.info('Captured Order: %s' % o)
		cart_item = o.cart_item.filter(Q(status__name=status), ~Q(Q(product_item__product_type__service=None),Q(product_item__product_type__settlement_service=None)))
		lgr.info('Cart Item: %s' % cart_item)
		for c in cart_item:
			lgr.info('Captured Cart Item: %s | %s | %s' % (c,c.product_item.product_type.service, c.product_item.product_type.settlement_service))
			product_item = c.product_item
			payload = json.loads(c.details)	

			gateway_profile = c.gateway_profile
			service = product_item.product_type.settlement_service if status == 'SETTLED' else product_item.product_type.service 

			payload['cart_item_id'] = c.id
			payload['purchase_order_id'] = o.id
			payload['product_item_id'] = c.product_item.id
			payload['item'] = c.product_item.name
			payload['product_type'] = c.product_item.product_type.name
			payload['quantity'] = c.quantity
			payload['currency'] = c.currency.code
			payload['amount'] = c.total
			payload['reference'] = o.reference
			payload['institution_id'] = c.product_item.institution.id
			payload['chid'] = c.channel.id
			payload['ip_address'] = '127.0.0.1'
			payload['gateway_host'] = '127.0.0.1'


			if bill.incoming_payment:
				payload['paygate_incoming_id'] = bill.incoming_payment.id
				payload['ext_inbound_id'] = bill.incoming_payment.ext_inbound_id
				payload.update(bill.incoming_payment.request)

			payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))

			payload = BridgeWrappers().background_service_call(service, gateway_profile, payload)

			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception as e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload

@app.task(ignore_result=True)
def order_service_call(order):
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		lgr.info('OrderID: %s' % order)
		o = PurchaseOrder.objects.get(id=order)
		lgr.info('Captured Order: %s' % o)
		cart_item = o.cart_item.all()
		for c in cart_item:
			lgr.info('Captured Cart Item: %s | %s' % (c,c.product_item.product_type.service))
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

			payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))

			payload = ServiceCall().api_service_call(service, gateway_profile, payload)
			lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception as e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload



@app.task(ignore_result=True)
def service_call(payload):
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		payload = json.loads(payload)

		payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))
		service = Service.objects.get(id=payload['service_id'])
		gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)
		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
	except Exception as e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_settled_order():
	lgr = get_task_logger(__name__)
	try:
		orig_order = PurchaseOrder.objects.select_for_update(nowait=True).filter(Q(status__name='SETTLED'),Q(cart_processed=False))
		order = list(orig_order.values_list('id',flat=True)[:500])

		processing = orig_order.filter(id__in=order).update(cart_processed=True, date_modified=timezone.now())
		for od in order:
			lgr.info('Order: %s' % od)
			order_background_service_call.delay(od, 'SETTLED')
	except DatabaseError as e:
		lgr.info('Transaction Rolled Back')
		transaction.set_rollback(True)

	except Exception as e: lgr.info('Error on process settled order: %s' % e)


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_paid_order():
	lgr = get_task_logger(__name__)
	try:
		orig_order = PurchaseOrder.objects.select_for_update(nowait=True).filter(Q(status__name='PAID'),Q(cart_processed=False))
		order = list(orig_order.values_list('id',flat=True)[:500])

		processing = orig_order.filter(id__in=order).update(cart_processed=True, date_modified=timezone.now())
		for od in order:
			lgr.info('Order: %s' % od)
			order_background_service_call.delay(od, 'PAID')
	except DatabaseError as e:
		lgr.info('Transaction Rolled Back')
		transaction.set_rollback(True)

	except Exception as e: lgr.info('Error on process paid order: %s' % e)


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_callback_url():
	lgr = get_task_logger(__name__)
	try:
		lgr.info('Process CallBack URL')

		all_bill = BillManager.objects.filter(Q(order__status__name='PAID',order__cart_item__api_callback_status__name='CREATED'),\
					~Q(order__cart_item__api_gateway_profile=None),~Q(incoming_payment=None),\
					~Q(order__cart_item__api_callback_url__in=[None,''])).values_list('id','order__cart_item__id').distinct()[:500]

		lgr.info('Bill %s' % all_bill)
		bill = np.asarray(all_bill)

		lgr.info('BillL %s' % bill.size)
		lgr.info('BillL %s' % bill)
		if bill.size>0:
			orig_cart  = CartItem.objects.select_for_update(nowait=True).filter(id__in=bill[:,1])

			lgr.info('Cart Items List %s' % bill[:,1])
			processing = orig_cart.filter(id__in=bill[:,1].tolist()).update(api_callback_status=APICallBackStatus.objects.get(name='PROCESSING'), date_modified=timezone.now())
			tasks = []
			for b, c in bill.tolist():
				lgr.info('Call Back: %s | %s' % (b, c))
				tasks.append(callback_url_call.s(b, c))

			chunks, chunk_size = len(tasks), 500
			callback_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]


	except Exception as e: lgr.info('Error on process callback url: %s' % e)
	#except DatabaseError as e:
	#	lgr.info('Transaction Rolled Back')
	#	transaction.set_rollback(True)



