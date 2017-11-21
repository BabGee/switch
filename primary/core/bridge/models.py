from django.contrib.gis.db import models
from primary.core.upc.models import *
import json

class PaymentMethodStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class PaymentMethod(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(PaymentMethodStatus)
	send = models.BooleanField(default=False)
	receive = models.BooleanField(default=True)
	default_currency = models.ForeignKey(Currency, related_name='default_currency')
	min_amount = models.DecimalField(max_digits=19, decimal_places=2)
	max_amount = models.DecimalField(max_digits=19, decimal_places=2)
	icon = models.CharField(max_length=45, null=True, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	country = models.ManyToManyField(Country, blank=True)
	currency = models.ManyToManyField(Currency, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	def __unicode__(self):
		return u'%s' % (self.name)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def country_list(self):
		return "\n".join([a.name for a in self.country.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])

class Product(models.Model):
	name = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=100)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	def __unicode__(self):
		return u'%s' % (self.name)        

class ServiceStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Service(models.Model):
	name = models.CharField(max_length=50, unique=True)
	product = models.ForeignKey(Product)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ServiceStatus) # Whether Poller or Other
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	def __unicode__(self):
		return u'%s' % (self.name)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])

class Trigger(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)


#This explains the state of a command. Whether to call API, pass or process locally
class CommandStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class ServiceCommand(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	command_function = models.CharField(max_length=50)
	level = models.IntegerField()
	service = models.ForeignKey(Service)	
	node_system = models.ForeignKey(NodeSystem)
	status = models.ForeignKey(CommandStatus)
	reverse_function = models.CharField(max_length=50, null=True, blank=True)
	description = models.CharField(max_length=100)
	details = models.CharField(max_length=512, default=json.dumps({}))
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	trigger = models.ManyToManyField(Trigger, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
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
	def __unicode__(self):
		return u'%s %s %s' % (self.command_function, self.status.name, self.access_level_list())

#This expalains the state of a transaction. Whether Processed or pending
class TransactionStatus(models.Model):
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=200)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Transaction(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile)
	service = models.ForeignKey(Service)
	channel = models.ForeignKey(Channel)
	gateway = models.ForeignKey(Gateway)
	request = models.CharField(max_length=12800)
	currency = models.ForeignKey(Currency, related_name="bridge", null=True, blank=True)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	raise_charges = models.NullBooleanField(default=False) #False - Not inclusive of the amount | True - Inclusive of the amount
	response = models.CharField(max_length=3840, blank=True, null=True)
	transaction_status = models.ForeignKey(TransactionStatus)
	#ip_address = models.CharField(max_length=20)
	ip_address = models.GenericIPAddressField(editable=False)
	response_status = models.ForeignKey(ResponseStatus)
	geometry = models.PointField(srid=4326)
	objects = models.GeoManager()
	current_command = models.ForeignKey(ServiceCommand, null=True, blank=True, related_name="transaction_current_command")
	next_command = models.ForeignKey(ServiceCommand, null=True, blank=True, related_name="transaction_next_command")
	msisdn = models.ForeignKey(MSISDN, null=True, blank=True)
	overall_status = models.ForeignKey(ResponseStatus, null=True, blank=True, related_name="bridge_transaction_overall_status")
	institution = models.ForeignKey(Institution, null=True, blank=True)
	fingerprint = models.CharField(max_length=1024, editable=False, null=True, blank=True)
	token = models.CharField(max_length=1024, editable=False, null=True, blank=True)
	def __unicode__(self):
		#return '%s %s %s' % (self.request, self.geometry.x, self.geometry.y)
 		return '%s' % (self.request)


class BackgroundService(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	trigger_service = models.ManyToManyField(Service)
	activity_service = models.ForeignKey(Service, related_name='activity_serice')
	details = models.CharField(max_length=1920, default=json.dumps({}))
	def __unicode__(self):
		return u'%s %s' % (self.id, self.activity_service)  
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def trigger_service_list(self):
		return "\n".join([a.name for a in self.trigger_service.all()])

class BackgroundServiceActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	background_service = models.ForeignKey(BackgroundService)
	status = models.ForeignKey(TransactionStatus)
	gateway_profile = models.ForeignKey(GatewayProfile)
	request = models.CharField(max_length=1920)
	channel = models.ForeignKey(Channel)
	response_status = models.ForeignKey(ResponseStatus)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	currency = models.ForeignKey(Currency, null=True, blank=True)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.background_service, self.gateway_profile)


