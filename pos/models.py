from django.contrib.gis.db import models
from crm.models import *


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
	created_by = models.ForeignKey(GatewayProfile, related_name="salecontact__created_by")
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
	till = models.ForeignKey(InstitutionTill)
	token = models.CharField(max_length=200, null=True, blank=True)
	channel = models.ForeignKey(Channel)
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
	def __unicode__(self):
		return u'%s %s' % (self.id, self.credit)
     
