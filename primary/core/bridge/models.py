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
	icon_old= models.CharField(max_length=45, null=True, blank=True)
	icon = models.ForeignKey(Icon, null=True, blank=True)
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

class Retry(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	name = models.CharField(max_length=50, unique=True)	
	max_retry = models.IntegerField(null=True, blank=True)
	max_retry_hours = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
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
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	name = models.CharField(max_length=50, unique=True)
	product = models.ForeignKey(Product)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ServiceStatus) # Whether Poller or Other
	success_last_response = models.CharField(max_length=256, null=True, blank=True)
	failed_last_response = models.CharField(max_length=256, null=True, blank=True)
	retry = models.ForeignKey(Retry, null=True, blank=True)
	allowed_response_key = models.CharField(max_length=1024, null=True, blank=True, help_text='Comma Delimitted')
	access_level = models.ManyToManyField(AccessLevel, blank=True)
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
	def __unicode__(self):
		return u'%s %s %s' % (self.command_function, self.status.name, self.access_level_list())

class ServiceCutOff(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	service = models.OneToOneField(Service)
	cut_off_command = models.ForeignKey(ServiceCommand, null=True, blank=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s %s' % (self.id, self.service)  

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
	service = models.ForeignKey(Service, related_name='background_service')
	details = models.CharField(max_length=3840, default=json.dumps({}))
	cut_off_command = models.ForeignKey(ServiceCommand, null=True, blank=True)
	trigger = models.ManyToManyField(Trigger, blank=True)
	def __unicode__(self):
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

class BackgroundServiceActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	service = models.ForeignKey(Service)
	status = models.ForeignKey(TransactionStatus)
	gateway_profile = models.ForeignKey(GatewayProfile)
	request = models.CharField(max_length=10240)
	channel = models.ForeignKey(Channel)
	response_status = models.ForeignKey(ResponseStatus)
	transaction_reference = models.CharField(max_length=256, null=True, blank=True) #Transaction ID
	currency = models.ForeignKey(Currency, null=True, blank=True)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	charges = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	current_command = models.ForeignKey(ServiceCommand, null=True, blank=True)
	scheduled_send = models.DateTimeField(blank=True, null=True)
	message = models.CharField(max_length=3840, blank=True, null=True)
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=256, blank=True, null=True)
	def __unicode__(self):
		return u'%s %s' % (self.service, self.gateway_profile)

class ActivityStatus(models.Model):
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=200)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Activity(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
        name = models.CharField(max_length=45, unique=True)
        description = models.CharField(max_length=100)
        status = models.ForeignKey(ActivityStatus)
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
        def __unicode__(self):
                return u'%s' % (self.name)

class ActivityProduct(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
        name = models.CharField(max_length=45)
        description = models.CharField(max_length=100)
        activity = models.ForeignKey(Activity)
        ext_product_id = models.CharField(max_length=250, null=True, blank=True)
        endpoint = models.ForeignKey(ActivityEndpoint, null=True, blank=True)
        service = models.ManyToManyField(Service, blank=True)
        details = models.CharField(max_length=512, default=json.dumps({}))
        realtime = models.BooleanField(default=False)
        show_message = models.BooleanField(default=False)
        payment_method = models.ManyToManyField(PaymentMethod, blank=True)
        currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
        trigger = models.ManyToManyField(Trigger, blank=True)
        def __unicode__(self):
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
        activity_product = models.ForeignKey(ActivityProduct)
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
        message = models.CharField(max_length=3840, blank=True, null=True)
        sends = models.IntegerField()
        ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
        def __unicode__(self):
                return u'%s %s' % (self.activity_product, self.gateway_profile)


class Approval(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	trigger_service = models.ManyToManyField(Service)
	service = models.ForeignKey(Service, related_name='approvals')
	details = models.CharField(max_length=3840, default=json.dumps({}))
	cut_off_command = models.ForeignKey(ServiceCommand, null=True, blank=True)
	trigger = models.ManyToManyField(Trigger, blank=True)
	requestor = models.ForeignKey(Role)
	approver = models.ForeignKey(Role, related_name='approver')
	def __unicode__(self):
		return u'%s %s' % (self.id, self.service)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def trigger_service_list(self):
		return "\n".join([a.name for a in self.trigger_service.all()])


class ApprovalActivityStatus(models.Model):
	name = models.CharField(max_length=50) # CREATED APPROVED DENIED
	description = models.CharField(max_length=200)
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)


class ApprovalActivity(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	approval = models.ForeignKey(Approval)
	status = models.ForeignKey(ApprovalActivityStatus)
	affected_gateway_profile = models.ForeignKey(GatewayProfile, related_name='affecting_approvals')
	requestor_gateway_profile = models.ForeignKey(GatewayProfile, related_name='requested_approvals')
	approver_gateway_profile = models.ForeignKey(GatewayProfile, related_name='pending_approvals',blank=True,null=True)
	request = models.CharField(max_length=10240)
	channel = models.ForeignKey(Channel)
	response_status = models.ForeignKey(ResponseStatus)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	def __unicode__(self):
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
	def __unicode__(self):
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
	change = models.ForeignKey(GatewayProfileChange)
	gateway_profile = models.ForeignKey(GatewayProfile)
	request = models.CharField(max_length=10240)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	processed = models.BooleanField(default=False)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	def __unicode__(self):
		return u'%s %s' % (self.change, self.gateway_profile)


