from django.db import models
from secondary.erp.crm.models import *
from django.contrib.postgres.fields import JSONField


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
	float_product_type = models.ForeignKey(ProductType, blank=True, null=True, related_name='float_product_type', on_delete=models.CASCADE)
	def __str__(self):
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
	float_type = models.ForeignKey(FloatType, on_delete=models.CASCADE)
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
	def __str__(self):
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
	float_type = models.ForeignKey(FloatType, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.CASCADE)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	def __str__(self):
		return u'%s %s %s' % (self.id, self.float_type, self.balance_bf)


class AgentFloatManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	float_amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	expiry = models.DateTimeField(null=True, blank=True)
	float_type = models.ForeignKey(FloatType, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	def __str__(self):
		return u'%s %s %s' % (self.id, self.float_type, self.balance_bf)


class Endpoint(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = JSONField(max_length=1920, null=True, blank=True)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=512, null=True, blank=True)
	username = models.CharField(max_length=128, null=True, blank=True)
	password = models.CharField(max_length=1024, null=True, blank=True)
	def __str__(self):
		return u'%s' % (self.name)

class RemittanceStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Remittance(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(RemittanceStatus, on_delete=models.CASCADE)
	ext_service_id = models.CharField(max_length=250)
	ext_service_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_details = models.CharField(max_length=1920, null=True, blank=True)
	service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE) #Service for processing outgoing tasks
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __str__(self):
		return u'%s %s' % (self.name, self.ext_service_id)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])


class RemittanceProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	remittance = models.ForeignKey(Remittance, on_delete=models.CASCADE)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	endpoint = models.ForeignKey(Endpoint, null=True, blank=True, on_delete=models.CASCADE)
	product_type = models.ManyToManyField(ProductType, blank=True) #Add all products that process service on account number
	service = models.ManyToManyField(Service, blank=True)
	realtime = models.BooleanField(default=False)
	show_message = models.BooleanField(default=False)
	fail_continues = models.BooleanField(default=False)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
	def __str__(self):
		return u'%s %s' % (self.name, self.remittance)
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])

class InstitutionNotification(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
	remittance_product = models.ForeignKey(RemittanceProduct, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	request = models.CharField(max_length=1920, null=True, blank=True)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=512, null=True, blank=True)
	username = models.CharField(max_length=128, null=True, blank=True)
	password = models.CharField(max_length=1024, null=True, blank=True)
	def __str__(self):
		return u'%s %s' % (self.institution, self.remittance_product)


class InstitutionIncomingService(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	keyword = models.CharField(max_length=50, unique=True, blank=True, null=True)
	product_item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	details = models.CharField(max_length=512, default=json.dumps({}))
	process_order = models.NullBooleanField(help_text='Null=Both Order & None-Order, True=Only Order, False=Only Non-Orders')
	def __str__(self):
		return u'%s %s' % (self.product_item.institution, self.service)

class IncomingState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Incoming(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	remittance_product = models.ForeignKey(RemittanceProduct, on_delete=models.CASCADE)
	reference = models.CharField(max_length=200, blank=True, null=True) #Transaction ID
	request = models.CharField(max_length=3840)
	amount = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	charge = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	currency = models.ForeignKey(Currency, blank=True, null=True, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	message = models.CharField(max_length=3840, blank=True, null=True)
	ext_inbound_id = models.CharField(max_length=200, blank=True, null=True) #External Transaction ID for use in duplicate transactions check
	ext_first_name = models.CharField(max_length=200, blank=True, null=True)
	ext_middle_name = models.CharField(max_length=200, blank=True, null=True)
	ext_last_name = models.CharField(max_length=200, blank=True, null=True)
	inst_notified = models.NullBooleanField(default=False)
	inst_num_tries = models.IntegerField(null=True,blank=True)
	state = models.ForeignKey(IncomingState, null=True, blank=True, on_delete=models.CASCADE)
	processed = models.NullBooleanField(default=False) #If service is none, then Null, else, false/true
	institution_incoming_service = models.ForeignKey(InstitutionIncomingService, blank=True, null=True, on_delete=models.CASCADE)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s %s' % (self.remittance_product, self.amount, self.currency, self.ext_inbound_id)

class PollerFrequency(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	run_every = models.IntegerField(help_text='In Seconds')
	def __str__(self):
		return u'%s' % (self.name)

class IncomingPollerStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class IncomingPoller(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = models.CharField(max_length=1920)
	remittance_product = models.ForeignKey(RemittanceProduct, on_delete=models.CASCADE)
	inbound_remittance_product = models.ForeignKey(RemittanceProduct, related_name='inbound_remittance_product', on_delete=models.CASCADE)
	frequency = models.ForeignKey(PollerFrequency, on_delete=models.CASCADE)
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	next_run = models.DateTimeField()
	status = models.ForeignKey(IncomingPollerStatus, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.name)

class OutgoingState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Outgoing(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	remittance_product = models.ForeignKey(RemittanceProduct, on_delete=models.CASCADE)
	reference = models.CharField(max_length=200, blank=True, null=True) #Transaction ID
	request = models.CharField(max_length=3840)
	amount = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	charge = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
	currency = models.ForeignKey(Currency, blank=True, null=True, on_delete=models.CASCADE)
	scheduled_send = models.DateTimeField(blank=True, null=True)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	message = models.CharField(max_length=3840, blank=True, null=True)
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	inst_notified = models.NullBooleanField(default=False) #notify on success status
	inst_num_tries = models.IntegerField(null=True,blank=True)
	state = models.ForeignKey(OutgoingState, null=True, blank=True, on_delete=models.CASCADE)
	institution_notification = models.ForeignKey(InstitutionNotification, null=True, blank=True, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s' % (self.remittance_product, self.amount, self.currency)

class RemittanceManagerStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class RemittanceManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	remittance_product = models.ForeignKey(RemittanceProduct, on_delete=models.CASCADE)
	status = models.ForeignKey(RemittanceManagerStatus, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	incoming_payment = models.ForeignKey(Incoming, null=True, blank=True, on_delete=models.CASCADE)
	outgoing_payment = models.ForeignKey(Outgoing, null=True, blank=True, on_delete=models.CASCADE)
	credit = models.BooleanField(default=False) #Dr | Cr
	currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	payment_method = models.ForeignKey(PaymentMethod, null=True, blank=True, on_delete=models.CASCADE)
	follow_on = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
	sends = models.IntegerField()
	def __unicode__(self):
		return u'%s %s' % (self.remittance_product, self.gateway_profile)


class FloatAlertType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	description = models.CharField(max_length=100)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	float_type = models.ForeignKey(FloatType, on_delete=models.CASCADE)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	profile = models.ManyToManyField(Profile)
	def __str__(self):
		return u'%s %s' % (self.float_type, self.service)
	def profile_list(self):
		return "\n".join([a.user.username for a in self.profile.all()])


class FloatAlertActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	float_manager = models.ForeignKey(FloatManager, on_delete=models.CASCADE)
	float_alert_type = models.ForeignKey(FloatAlertType, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s' % (self.float_manager, self.float_alert_type)


