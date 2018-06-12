from django.db import models
from secondary.erp.crm.models import *

class FloatType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	product_type = models.ManyToManyField(ProductType, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	service = models.ManyToManyField(Service, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	float_product_type = models.ForeignKey(ProductType, blank=True, null=True, related_name='float_product_type')
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.name, self.float_product_type)
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])


class FloatCharge(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	float_type = models.ForeignKey(FloatType)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	expiry = models.DateTimeField(null=True, blank=True)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=200, null=True, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.float_type, self.charge_value)
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])


class FloatManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	float_amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	expiry = models.DateTimeField(null=True, blank=True)
	float_type = models.ForeignKey(FloatType)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, blank=True, null=True)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.float_type, self.balance_bf)


class Endpoint(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = models.CharField(max_length=1920, null=True, blank=True)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=512, null=True, blank=True)
	username = models.CharField(max_length=128, null=True, blank=True)
	password = models.CharField(max_length=1024, null=True, blank=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class RemittanceStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Remittance(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(RemittanceStatus)
	ext_service_id = models.CharField(max_length=250)
	ext_service_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_details = models.CharField(max_length=1920, null=True, blank=True)
	service = models.ForeignKey(Service, null=True, blank=True) #Service for processing outgoing tasks
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.ext_service_id)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])


class RemittanceProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	remittance = models.ForeignKey(Remittance)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	endpoint = models.ForeignKey(Endpoint, null=True, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True) #Add all products that process service on account number
	service = models.ManyToManyField(Service, blank=True)
	realtime = models.BooleanField(default=False)
	show_message = models.BooleanField(default=False)
	fail_continues = models.BooleanField(default=False)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
        currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
	def __unicode__(self):
		return u'%s %s' % (self.name, self.remittance)
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])


class PollerFrequency(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Poller(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = models.CharField(max_length=1920)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=128)
	username = models.CharField(max_length=128)
	password = models.CharField(max_length=256)
	remittance_product = models.ForeignKey(RemittanceProduct)
	frequency = models.ForeignKey(PollerFrequency)
	def __unicode__(self):
		return u'%s' % (self.name)

class InstitutionNotification(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ForeignKey(Institution)
	remittance_product = models.ForeignKey(RemittanceProduct)
	description = models.CharField(max_length=100)
	request = models.CharField(max_length=1920, null=True, blank=True)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=512, null=True, blank=True)
	username = models.CharField(max_length=128, null=True, blank=True)
	password = models.CharField(max_length=1024, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.institution, self.remittance_product)


class InstitutionIncomingService(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	service = models.ForeignKey(Service)
	description = models.CharField(max_length=100)
	keyword = models.CharField(max_length=50, unique=True, blank=True, null=True)
	product_item = models.ForeignKey(ProductItem)
	gateway = models.ForeignKey(Gateway)
	details = models.CharField(max_length=512, default=json.dumps({}))
	process_order = models.NullBooleanField(help_text='Null=Both Order & None-Order, True=Only Order, False=Only Non-Orders')
	def __unicode__(self):
		return u'%s %s' % (self.product_item.institution, self.service)

class IncomingState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Incoming(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	remittance_product = models.ForeignKey(RemittanceProduct)
	reference = models.CharField(max_length=200, blank=True, null=True) #Transaction ID
	request = models.CharField(max_length=3840)
	amount = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	charge = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	currency = models.ForeignKey(Currency, blank=True, null=True)
	response_status = models.ForeignKey(ResponseStatus)
	message = models.CharField(max_length=3840, blank=True, null=True)
	ext_inbound_id = models.CharField(max_length=200, blank=True, null=True) #External Transaction ID for use in duplicate transactions check
	ext_first_name = models.CharField(max_length=200, blank=True, null=True)
	ext_middle_name = models.CharField(max_length=200, blank=True, null=True)
	ext_last_name = models.CharField(max_length=200, blank=True, null=True)
	inst_notified = models.NullBooleanField(default=False)
	inst_num_tries = models.IntegerField(null=True,blank=True)
	state = models.ForeignKey(IncomingState, null=True, blank=True)
	processed = models.NullBooleanField(default=False) #If service is none, then Null, else, false/true
	institution_incoming_service = models.ForeignKey(InstitutionIncomingService, blank=True, null=True)
	channel = models.ForeignKey(Channel)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s %s %s' % (self.remittance_product, self.amount, self.currency, self.ext_inbound_id)

class OutgoingState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Outgoing(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	remittance_product = models.ForeignKey(RemittanceProduct)
	reference = models.CharField(max_length=200, blank=True, null=True) #Transaction ID
	request = models.CharField(max_length=3840)
	amount = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	charge = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	currency = models.ForeignKey(Currency, blank=True, null=True)
	scheduled_send = models.DateTimeField(blank=True, null=True)
	response_status = models.ForeignKey(ResponseStatus)
	message = models.CharField(max_length=3840, blank=True, null=True)
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	inst_notified = models.NullBooleanField(default=False) #notify on success status
	inst_num_tries = models.IntegerField(null=True,blank=True)
	state = models.ForeignKey(OutgoingState, null=True, blank=True)
	institution_notification = models.ForeignKey(InstitutionNotification, null=True, blank=True)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s %s' % (self.remittance_product, self.amount, self.currency)

class FloatAlertType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	description = models.CharField(max_length=100)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	service = models.ForeignKey(Service)
	float_type = models.ForeignKey(FloatType)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	institution = models.ForeignKey(Institution, blank=True, null=True)
	gateway = models.ForeignKey(Gateway)
	profile = models.ManyToManyField(Profile)
	def __unicode__(self):
		return u'%s %s' % (self.float_type, self.service)
	def profile_list(self):
		return "\n".join([a.user.username for a in self.profile.all()])


class FloatAlertActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	float_manager = models.ForeignKey(FloatManager)
	float_alert_type = models.ForeignKey(FloatAlertType)
	def __unicode__(self):
		return u'%s %s' % (self.float_manager, self.float_alert_type)


