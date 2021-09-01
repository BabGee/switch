from django.db import models
from django.contrib.gis.db.models import MultiPolygonField, PointField, Manager as GeoManager
from primary.core.upc.models import *
import json

class PaymentMethodStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class PaymentMethod(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(PaymentMethodStatus, on_delete=models.CASCADE)
	send = models.BooleanField(default=False)
	receive = models.BooleanField(default=True)
	default_currency = models.ForeignKey(Currency, related_name='default_currency', on_delete=models.CASCADE)
	min_amount = models.DecimalField(max_digits=19, decimal_places=2)
	max_amount = models.DecimalField(max_digits=19, decimal_places=2)
	icon_old= models.CharField(max_length=45, null=True, blank=True)
	icon = models.ForeignKey(Icon, null=True, blank=True, on_delete=models.CASCADE)
	gateway = models.ManyToManyField(Gateway, blank=True)
	country = models.ManyToManyField(Country, blank=True)
	currency = models.ManyToManyField(Currency, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	def __str__(self):
		return u'%s' % (self.name)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def country_list(self):
		return "\n".join([a.name for a in self.country.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])

class PaymentMethodProductStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class PaymentMethodProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	payment_method= models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	details = models.JSONField(max_length=1920, null=True, blank=True)
	status = models.ForeignKey(PaymentMethodStatus, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s' % (self.name, self.payment_method)


class Product(models.Model):
	name = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=100)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	def __str__(self):
		return u'%s' % (self.name)	

class Retry(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	name = models.CharField(max_length=50, unique=True)	
	max_retry = models.IntegerField(null=True, blank=True)
	max_retry_hours = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	def __str__(self):
		return u'%s' % (self.name)	

class ServiceStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Service(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	name = models.CharField(max_length=50, unique=True)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ServiceStatus, on_delete=models.CASCADE) # Whether Poller or Other
	last_response = models.CharField(max_length=2048, null=True, blank=True, help_text='response_status%response|...')
	success_last_response = models.CharField(max_length=256, null=True, blank=True)
	failed_last_response = models.CharField(max_length=256, null=True, blank=True)
	retry = models.ForeignKey(Retry, null=True, blank=True, on_delete=models.CASCADE)
	allowed_response_key = models.CharField(max_length=1024, null=True, blank=True, help_text='Comma Delimitted')
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	def __str__(self):
		return u'%s' % (self.name)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])

class Trigger(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)


#This explains the state of a command. Whether to call API, pass or process locally
class CommandStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class ServiceCommand(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	command_function = models.CharField(max_length=50)
	level = models.IntegerField()
	service = models.ForeignKey(Service, on_delete=models.CASCADE)	
	node_system = models.ForeignKey(NodeSystem, on_delete=models.CASCADE)
	status = models.ForeignKey(CommandStatus, on_delete=models.CASCADE)
	reverse_function = models.CharField(max_length=50, null=True, blank=True)
	description = models.CharField(max_length=100)
	details = models.CharField(max_length=512, default=json.dumps({}))
	response = models.CharField(max_length=256, null=True, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	trigger = models.ManyToManyField(Trigger, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	success_response_status = models.ManyToManyField(ResponseStatus, blank=True)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def trigger_list(self):
		return "\n".join([a.name for a in self.trigger.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def success_response_status_list(self):
		return "\n".join([a.response for a in self.success_response_status.all()])
	def __str__(self):
		return u'%s %s %s' % (self.command_function, self.status.name, self.access_level_list())

class ServiceCutOff(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	service = models.OneToOneField(Service, on_delete=models.CASCADE)
	cut_off_command = models.ForeignKey(ServiceCommand, null=True, blank=True, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s %s' % (self.id, self.service)  

#This expalains the state of a transaction. Whether Processed or pending
class TransactionStatus(models.Model):
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=200)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Transaction(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	request = models.CharField(max_length=12800)
	currency = models.ForeignKey(Currency, related_name="bridge", null=True, blank=True, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	raise_charges = models.BooleanField(default=False, null=True) #False - Not inclusive of the amount | True - Inclusive of the amount
	response = models.CharField(max_length=3840, blank=True, null=True)
	transaction_status = models.ForeignKey(TransactionStatus, on_delete=models.CASCADE)
	#ip_address = models.CharField(max_length=20)
	ip_address = models.GenericIPAddressField(editable=False)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	geometry = PointField(srid=4326)
	objects = GeoManager()
	current_command = models.ForeignKey(ServiceCommand, null=True, blank=True, related_name="transaction_current_command", on_delete=models.CASCADE)
	next_command = models.ForeignKey(ServiceCommand, null=True, blank=True, related_name="transaction_next_command", on_delete=models.CASCADE)
	msisdn = models.ForeignKey(MSISDN, null=True, blank=True, on_delete=models.CASCADE)
	overall_status = models.ForeignKey(ResponseStatus, null=True, blank=True, related_name="bridge_transaction_overall_status", on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	fingerprint = models.CharField(max_length=1024, editable=False, null=True, blank=True)
	token = models.CharField(max_length=1024, editable=False, null=True, blank=True)
	user_agent = models.TextField(editable=False, null=True, blank=True)
	def __str__(self):
		#return '%s %s %s' % (self.request, self.geometry.x, self.geometry.y)
 		return '%s' % (self.request)


class BackgroundService(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	trigger_service = models.ManyToManyField(Service)
	service = models.ForeignKey(Service, related_name='background_service', on_delete=models.CASCADE)
	details = models.CharField(max_length=3840, default=json.dumps({}))
	cut_off_command = models.ForeignKey(ServiceCommand, null=True, blank=True, on_delete=models.CASCADE)
	trigger = models.ManyToManyField(Trigger, blank=True)
	def __str__(self):
		return u'%s %s' % (self.id, self.service)  
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def trigger_service_list(self):
		return "\n".join([a.name for a in self.trigger_service.all()])
	def trigger_list(self):
		return "\n".join([a.name for a in self.trigger.all()])

class PollFrequency(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	run_every = models.IntegerField(help_text='In Seconds')
	def __str__(self):
		return u'%s' % (self.name)

class PollStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Poll(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = models.JSONField()
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	frequency = models.ForeignKey(PollFrequency, on_delete=models.CASCADE)
	last_run = models.DateTimeField(auto_now=True)
	status = models.ForeignKey(PollStatus, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.name)

class BackgroundServiceActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	status = models.ForeignKey(TransactionStatus, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	request_old = models.CharField(max_length=10240, null=True, blank=True)
	request = models.JSONField()
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	transaction_reference = models.CharField(max_length=256, null=True, blank=True) #Transaction ID
	currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	current_command = models.ForeignKey(ServiceCommand, null=True, blank=True, on_delete=models.CASCADE)
	scheduled_send = models.DateTimeField(blank=True, null=True)
	message = models.CharField(max_length=3840, blank=True, null=True)
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=256, blank=True, null=True)
	def __str__(self):
		return u'%s %s' % (self.service, self.gateway_profile)

class ActivityStatus(models.Model):
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=200)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Activity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ActivityStatus, on_delete=models.CASCADE)
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

class ActivityEndpoint(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = models.CharField(max_length=1920, null=True, blank=True)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=512, null=True, blank=True)
	username = models.CharField(max_length=128, null=True, blank=True)
	password = models.CharField(max_length=1024, null=True, blank=True)
	def __str__(self):
		return u'%s' % (self.name)

class ActivityProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	endpoint = models.ForeignKey(ActivityEndpoint, null=True, blank=True, on_delete=models.CASCADE)
	service = models.ManyToManyField(Service, blank=True)
	details = models.CharField(max_length=512, default=json.dumps({}))
	realtime = models.BooleanField(default=False)
	show_message = models.BooleanField(default=False)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
	trigger = models.ManyToManyField(Trigger, blank=True)
	def __str__(self):
		return u'%s %s' % (self.name, self.investment)
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])
	def trigger_list(self):
		return "\n".join([a.name for a in self.trigger.all()])


class ActivityTransaction(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	activity_product = models.ForeignKey(ActivityProduct, on_delete=models.CASCADE)
	status = models.ForeignKey(TransactionStatus, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	request = models.CharField(max_length=1920)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	message = models.CharField(max_length=3840, blank=True, null=True)
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	def __str__(self):
		return u'%s %s' % (self.activity_product, self.gateway_profile)


class Approval(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	trigger_service = models.ManyToManyField(Service)
	service = models.ForeignKey(Service, related_name='approvals', on_delete=models.CASCADE)
	details = models.CharField(max_length=3840, default=json.dumps({}))
	cut_off_command = models.ForeignKey(ServiceCommand, null=True, blank=True, on_delete=models.CASCADE)
	trigger = models.ManyToManyField(Trigger, blank=True)
	requestor = models.ForeignKey(Role, on_delete=models.CASCADE)
	approver = models.ForeignKey(Role, related_name='approver', on_delete=models.CASCADE)
	pending_count = models.IntegerField(null=True,blank=True,default=0) # null is unlimited
	approval_identifier = models.CharField(max_length=200, blank=True, null=True)
	pending_related_service = models.ManyToManyField(Service, related_name='pending_related_service', blank=True)
	def __str__(self):
		return u'%s %s' % (self.id, self.service)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def trigger_service_list(self):
		return "\n".join([a.name for a in self.trigger_service.all()])
	def pending_related_service_list(self):
		return "\n".join([a.name for a in self.pending_related_service.all()])


class ApprovalActivityStatus(models.Model):
	name = models.CharField(max_length=50) # CREATED APPROVED REJECTED
	description = models.CharField(max_length=200)
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)


class ApprovalActivity(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	approval = models.ForeignKey(Approval, on_delete=models.CASCADE)
	status = models.ForeignKey(ApprovalActivityStatus, on_delete=models.CASCADE)
	affected_gateway_profile = models.ForeignKey(GatewayProfile, related_name='affecting_approvals', on_delete=models.CASCADE)
	requestor_gateway_profile = models.ForeignKey(GatewayProfile, related_name='requested_approvals', on_delete=models.CASCADE)
	approver_gateway_profile = models.ForeignKey(GatewayProfile, related_name='pending_approvals',blank=True,null=True, on_delete=models.CASCADE)
	request = models.JSONField()
	#request = models.CharField(max_length=10240)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	identifier = models.CharField(null=True,blank=True,max_length=20)
	def __str__(self):
		return u'%s %s' % (self.id, self.approval)


class GatewayProfileChange(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	details = models.CharField(max_length=3840, default=json.dumps({}))
	def __str__(self):
		return u'%s %s' % (self.id, self.name)  
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])


class GatewayProfileChangeActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	change = models.ForeignKey(GatewayProfileChange, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	request = models.CharField(max_length=10240)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	processed = models.BooleanField(default=False)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	def __str__(self):
		return u'%s %s' % (self.change, self.gateway_profile)


class QuicksetupServices(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)
    
class NetworkProvider(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)    
    
class AccountType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)
    
    