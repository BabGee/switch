from django.db import models
from django.contrib.gis.db.models import MultiPolygonField, PointField, Manager as GeoManager
from secondary.erp.crm.models import *
from secondary.finance.paygate.models import *

class SaleChargeType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=256)
	product_item = models.ForeignKey(ProductItem, on_delete=models.CASCADE) #ProductItem Institution can be different from the institution exerting the charge
	def __str__(self):
		return u'%s' % (self.name)


class SaleCharge(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	sale_charge_type = models.ForeignKey(SaleChargeType, on_delete=models.CASCADE)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	expiry = models.DateTimeField(null=True, blank=True)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=256, null=True, blank=True)
	main_location = PointField(srid=4326,blank=True,null=True)
	objects = GeoManager()
	min_distance = models.IntegerField(null=True, blank=True)
	max_distance = models.IntegerField(null=True, blank=True)
	charge_per_km = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	per_item = models.BooleanField(default=False)
	product_display = models.ManyToManyField(ProductDisplay, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __str__(self):
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
	def __str__(self):
		return u'%s' % (self.name)

class CartStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class APICallBackStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)



class CartItem(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	product_item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, blank=True, null=True, on_delete=models.CASCADE) #Purchasing Institution has institution profile to manage|If not logged in, NULL & use IP
	currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
	status = models.ForeignKey(CartStatus, on_delete=models.CASCADE)
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
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	cart_type = models.ForeignKey(CartType, on_delete=models.CASCADE)
	api_callback_url = models.CharField(max_length=512, null=True, blank=True)
	api_gateway_profile = models.ForeignKey(GatewayProfile, related_name='api_gateway_profile', blank=True, null=True, on_delete=models.CASCADE)
	api_callback_status = models.ForeignKey(APICallBackStatus, blank=True, null=True, on_delete=models.CASCADE)
	api_message = models.CharField(max_length=128, null=True, blank=True)
	def __str__(self):
		return u'%s %s %s' % (self.product_item, self.gateway_profile, self.quantity)


class OrderStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class PurchaseOrder(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	cart_item = models.ManyToManyField(CartItem)
	reference = models.CharField(max_length=45)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
	description = models.CharField(max_length=200, blank=True, null=True)
	status = models.ForeignKey(OrderStatus, on_delete=models.CASCADE)
	expiry = models.DateTimeField()
	cart_processed = models.BooleanField(default=False)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE) #Gateway Profile to Match Cart Items for checkout
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	outgoing_payment = models.ForeignKey(Outgoing, null=True, blank=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s' % (self.id, self.reference, self.status.name)
	def cart_item_list(self):
		return "\n".join([a.product_item.name for a in self.cart_item.all()])

class BillManagerStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class BillManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	action_reference = models.CharField(max_length=45, null=True, blank=True) #Action ID
	order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	payment_method = models.ForeignKey(PaymentMethod, null=True, blank=True, on_delete=models.CASCADE)
	incoming_payment = models.ForeignKey(Incoming, null=True, blank=True, on_delete=models.CASCADE)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	status = models.ForeignKey(BillManagerStatus, null=True, blank=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s' % (self.id, self.credit)

class OrderProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True) #Add all products that process service on account number
	service = models.ManyToManyField(Service, blank=True)
	details = models.CharField(max_length=512, default=json.dumps({}))
	realtime = models.BooleanField(default=False)
	show_message = models.BooleanField(default=False)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
	trigger = models.ManyToManyField(Trigger, blank=True)
	def __str__(self):
		return u'%s %s' % (self.name, self.description)
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])
	def trigger_list(self):
		return "\n".join([a.name for a in self.trigger.all()])

class OrderCharge(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
	expiry = models.DateTimeField(null=True, blank=True)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=256, null=True, blank=True)
	order_product = models.ManyToManyField(OrderProduct)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __str__(self):
		return u'%s %s %s' % (self.id, self.institution, self.charge_value)
	def order_product_list(self):
		return "\n".join([a.name for a in self.order_product.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])

class OrderActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	order_product = models.ForeignKey(OrderProduct, on_delete=models.CASCADE)
	order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
	status = models.ForeignKey(TransactionStatus, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	request = models.CharField(max_length=10240)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	transaction_reference = models.CharField(max_length=256, null=True, blank=True) #Transaction ID
	currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	scheduled_send = models.DateTimeField(blank=True, null=True)
	message = models.CharField(max_length=3840, blank=True, null=True)
	sends = models.IntegerField()
	ext_inbound_id = models.CharField(max_length=256, blank=True, null=True)
	def __str__(self):
		return u'%s %s' % (self.order_type, self.gateway_profile)

class DeliveryStatus(models.Model):
	# CREATED
	# ASSIGNED
	# IN PROGRESS
	# COMPLETED
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)



class Delivery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)

	order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
	status = models.ForeignKey(DeliveryStatus, on_delete=models.CASCADE)

	schedule = models.DateTimeField(default=timezone.now)
	delivery_profile = models.ForeignKey(GatewayProfile,null=True, on_delete=models.CASCADE)

	origin_name = models.CharField(max_length=200,blank=True,null=True)
	origin_coord = PointField(srid=4326,blank=True,null=True)

	destination_name = models.CharField(max_length=200)
	destination_coord = PointField(srid=4326)

	follow_on = models.ForeignKey('self',null=True, on_delete=models.CASCADE)

	def __str__(self):
		return u'%s %s' % (self.order, self.status)




