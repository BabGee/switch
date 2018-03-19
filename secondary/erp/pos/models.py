from django.contrib.gis.db import models
from secondary.erp.crm.models import *
from secondary.finance.paygate.models import *

class SaleChargeType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=256)
	product_item = models.ForeignKey(ProductItem) #ProductItem Institution can be different from the institution exerting the charge
	def __unicode__(self):
		return u'%s' % (self.name)


class SaleCharge(models.Model):
        date_modified = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	sale_charge_type = models.ForeignKey(SaleChargeType)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	expiry = models.DateTimeField(null=True, blank=True)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	base_charge = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=256, null=True, blank=True)
	main_location = models.PointField(srid=4326,blank=True,null=True)
	min_distance = models.IntegerField(null=True, blank=True)
	max_distance = models.IntegerField(null=True, blank=True)
	charge_per_km = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	per_item = models.BooleanField(default=False)
	product_display = models.ManyToManyField(ProductDisplay, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
        def __unicode__(self):
                return u'%s %s %s' % (self.id, self.sale_charge_type, self.charge_value)
	def product_display_list(self):
		return "\n".join([a.name for a in self.product_display.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])


class CartType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class CartStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)


class CartItem(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	product_item = models.ForeignKey(ProductItem)
	gateway_profile = models.ForeignKey(GatewayProfile, blank=True, null=True) #Purchasing Institution has institution profile to manage|If not logged in, NULL & use IP
	currency = models.ForeignKey(Currency)
	status = models.ForeignKey(CartStatus)
	quantity = models.DecimalField(max_digits=19, decimal_places=2)
	expiry = models.DateTimeField(null=True, blank=True)
	price = models.DecimalField(max_digits=19, decimal_places=2)
	sub_total = models.DecimalField(max_digits=19, decimal_places=2)
	vat = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	other_tax = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	discount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	other_relief = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	total = models.DecimalField(max_digits=19, decimal_places=2)
	details = models.CharField(max_length=1920)
	token = models.CharField(max_length=200, null=True, blank=True)
	channel = models.ForeignKey(Channel)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	cart_type = models.ForeignKey(CartType)
	def __unicode__(self):
		return u'%s %s %s' % (self.product_item, self.gateway_profile, self.quantity)


class OrderStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class PurchaseOrder(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	cart_item = models.ManyToManyField(CartItem)
	reference = models.CharField(max_length=45)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	currency = models.ForeignKey(Currency)
	description = models.CharField(max_length=200, blank=True, null=True)
	status = models.ForeignKey(OrderStatus)
	expiry = models.DateTimeField()
	cart_processed = models.BooleanField(default=False)
	gateway_profile = models.ForeignKey(GatewayProfile) #Gateway Profile to Match Cart Items for checkout
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	def __unicode__(self):
		return u'%s %s' % (self.reference, self.status.name)
	def cart_item_list(self):
		return "\n".join([a.product_item.name for a in self.cart_item.all()])

class BillManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	action_reference = models.CharField(max_length=45, null=True, blank=True) #Action ID
	order = models.ForeignKey(PurchaseOrder)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	payment_method = models.ForeignKey(PaymentMethod, null=True, blank=True)
	incoming_payment = models.ForeignKey(Incoming, null=True, blank=True)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	def __unicode__(self):
		return u'%s %s' % (self.id, self.credit)

class DeliveryStatus(models.Model):
	# CREATED
	# ASSIGNED
	# IN PROGRESS
	# COMPLETED
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)



class Delivery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)

	order = models.ForeignKey(PurchaseOrder)
	status = models.ForeignKey(DeliveryStatus)

	schedule = models.DateTimeField(default=timezone.now)
	delivery_profile = models.ForeignKey(GatewayProfile,null=True)

	origin_name = models.CharField(max_length=200,blank=True,null=True)
	origin_coord = models.PointField(srid=4326,blank=True,null=True)

	destination_name = models.CharField(max_length=200)
	destination_coord = models.PointField(srid=4326)

	follow_on = models.ForeignKey('self',null=True)

	def __unicode__(self):
		return u'%s %s' % (self.order, self.status)




