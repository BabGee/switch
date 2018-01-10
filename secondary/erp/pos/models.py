from django.contrib.gis.db import models
from secondary.erp.crm.models import *


class SaleContactType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	institution = models.ForeignKey(Institution)
	def __unicode__(self):
		return u'%s' % (self.name)

class SaleContact(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)	
	sale_contact_type = models.ForeignKey(SaleContactType)
	location = models.CharField(max_length=200, blank=True, null=True)
	geometry = models.PointField(srid=4326)
	objects = models.GeoManager()
	sale_contact_number = models.IntegerField()
	institution = models.ForeignKey(Institution)
	primary_contact_profile = models.ForeignKey(Profile)
	comment = models.CharField(max_length=256, null=True, blank = True)
	details = models.CharField(max_length=1280)
	created_by = models.ForeignKey(GatewayProfile, related_name="salecontact_created_by")
	def __unicode__(self):
		return u'%s' % (self.name)

class SaleChargeType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
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
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=200, null=True, blank=True)
	per_item = models.BooleanField(default=False)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
        def __unicode__(self):
                return u'%s %s %s' % (self.id, self.sale_charge_type, self.charge_value)
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
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	def __unicode__(self):
		return u'%s %s' % (self.id, self.credit)

class DeliveryStatus(models.Model):
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
	def __unicode__(self):
		return u'%s %s' % (self.order, self.status)

class DeliveryActivityStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)
  
class DeliveryTypeStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class DeliveryType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	status = models.ForeignKey(DeliveryTypeStatus)
	channel = models.ForeignKey(Channel)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, blank=True, null=True)
	def __unicode__(self):
		return u'%s %s' % (self.gateway,self.channel)

class DeliveryActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	delivery = models.ForeignKey(Delivery)
	delivery_type = models.ManyToManyField(DeliveryType)
	status = models.ForeignKey(DeliveryActivityStatus)
	profile = models.ForeignKey(Profile)
	def __unicode__(self):
		return u'%s %s' % (self.delivery, self.profile)
	def delivery_type_list(self):
		return "\n".join(['%s %s' % (a.channel,a.gateway) for a in self.delivery_type.all()])

