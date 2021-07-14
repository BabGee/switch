from django.db import models
from secondary.channels.vcs.models import *
from secondary.erp.crm.models import *
from postgres_copy import CopyManager

class Credential(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	url = models.CharField(max_length=640)
	api_key = models.CharField(max_length=128, null=True, blank=True)
	api_secret = models.CharField(max_length=1024, null=True, blank=True)
	api_token = models.CharField(max_length=1024, null=True, blank=True)
	access_token = models.CharField(max_length=1024, null=True, blank=True)
	token_validity = models.IntegerField(blank=True, null=True, help_text='In Seconds')
	token_expiration = models.DateTimeField()
	updated = models.BooleanField(default=False)
	def __str__(self):
		return u'%s' % (self.name)

class Endpoint(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	request = models.JSONField(max_length=1920, null=True, blank=True)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=128)
	username = models.CharField(max_length=128)
	password = models.CharField(max_length=256)
	api_key = models.CharField(max_length=256,blank=True, null=True)
	batch = models.SmallIntegerField(default=1)
	credential = models.ForeignKey(Credential, blank=True, null=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.name)

class NotificationStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Notification(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(NotificationStatus, on_delete=models.CASCADE)
	endpoint = models.ForeignKey(Endpoint, null=True, blank=True, on_delete=models.CASCADE)
	ext_service_id = models.CharField(max_length=250)
	ext_service_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_details = models.CharField(max_length=1920, null=True, blank=True)
	institution_url = models.CharField(max_length=640, null=True, blank=True) #Institution to be notified
	institution_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	institution_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	channel = models.ManyToManyField(Channel, blank=True)
	product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
	code = models.ForeignKey(Code, on_delete=models.CASCADE)#Code Required for Email & InApp notifications (Create Code named EMAIL|IN APP for institution)
	service = models.ForeignKey(Service, blank=True, null=True, on_delete=models.CASCADE) #Service for processing inbound tasks
	def __str__(self):
		return u'%s %s %s' % (self.id, self.name, self.ext_service_id)
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])

class NotificationProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	keyword = models.CharField(max_length=45, null=True, blank=True)
	subscribable = models.BooleanField(default=False)
	expires = models.BooleanField(default=False)
	subscription_endpoint = models.ForeignKey(Endpoint, null=True, blank=True, on_delete=models.CASCADE)
	product_type = models.ManyToManyField(ProductType, blank=True)
	unit_credit_charge = models.DecimalField(max_digits=19, decimal_places=2)
	service = models.ManyToManyField(Service, blank=True)
	unsubscription_endpoint = models.ForeignKey(Endpoint, null=True, blank=True, related_name="unsubscription_endpoint", on_delete=models.CASCADE)
	create_subscribe = models.BooleanField(default=False)
	trading_box = models.ForeignKey(TradingBox, null=True, blank=True, on_delete=models.CASCADE)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	priority = models.SmallIntegerField(default=10)
	is_bulk = models.BooleanField(default=True)
	institution_allowed = models.BooleanField(default=False)
	def __str__(self):
		return u'%s %s %s %s' % (self.id, self.name, self.unit_credit_charge, self.notification)
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])

class ResponseProduct(models.Model):#If response product exists, use response product in responses, otherwise, use self.
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	product = models.OneToOneField(NotificationProduct, on_delete=models.CASCADE)
	auto = models.BooleanField(default=False)
	response_product = models.ForeignKey(NotificationProduct, related_name="autoresponse_auto_notification", on_delete=models.CASCADE) #If None, use Default/Self Notification to respond
	def __str__(self):
		return u'%s %s' % (self.notification, self.auto)

class ContactStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Contact(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	status = models.ForeignKey(ContactStatus, on_delete=models.CASCADE) 
	product = models.ForeignKey(NotificationProduct, on_delete=models.CASCADE) 
	subscription_details = models.CharField(max_length=1920)
	subscribed = models.BooleanField(default=False)
	linkid = models.CharField(max_length=200, null=True,blank=True)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE) # A gateway profile has only one MSISDN
	def __str__(self):
		return u'%s %s' % (self.gateway_profile, self.product)

class ContactGroupStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)


class ContactGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200)
	description = models.CharField(max_length=200)
	institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, blank=True, null=True, on_delete=models.CASCADE)
	status = models.ForeignKey(ContactGroupStatus, on_delete=models.CASCADE) 
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.name)

class Recipient(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	status = models.ForeignKey(ContactStatus, on_delete=models.CASCADE) 
	details = models.JSONField(max_length=38400)
	subscribed = models.BooleanField(default=False)
	recipient = models.CharField(max_length=200)
	contact_group = models.ForeignKey(ContactGroup, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s' % (self.recipient, self.contact_group)

class Credit(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	description = models.CharField(max_length=100)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
	credit_value = models.IntegerField()
	def __str__(self):
		return u'%s' % (self.credit_value)

class TemplateStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)


class TemplateFile(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	file_path = models.FileField(upload_to='notify_templatefile_path/', max_length=200, null=True,blank=True)
	def __str__(self):
		return u'%s' % (self.name)
			
class NotificationTemplate(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	template_heading = models.CharField(max_length=200)
	template_message = models.CharField(max_length=38400)
	product = models.ManyToManyField(NotificationProduct, blank=True)#Product_type
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	description = models.CharField(max_length=50)
	status = models.ForeignKey(TemplateStatus, on_delete=models.CASCADE)
	template_file = models.ForeignKey(TemplateFile, null=True,blank=True, on_delete=models.CASCADE)
	protected = models.BooleanField(default=False)
	trigger = models.ManyToManyField(Trigger, blank=True)
	def __str__(self):
		return u'%s %s' % (self.product, self.template_message)
	def product_list(self):
		return "\n".join([a.name for a in self.product.all()])
	def trigger_list(self):
		return "\n".join([a.name for a in self.trigger.all()])

class NotificationAttachment(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	file_path = models.FileField(upload_to='notify_notificationattachment_path/', max_length=200, null=True,blank=True)
	def __str__(self):
		return u'%s' % (self.name)

class InBoundState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Inbound(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
	heading = models.CharField(max_length=200,blank=True, null=True)
	message = models.CharField(max_length=3840)
	state = models.ForeignKey(InBoundState, on_delete=models.CASCADE) #CREATED / PROCESSED / COMPLETED (Institution URL notified if not None Exists)
	inst_notified = models.BooleanField(default=False, null=True)
	inst_num_tries = models.IntegerField(null=True,blank=True)
	attachment = models.ManyToManyField(NotificationAttachment, blank=True)
	recipient = models.CharField(max_length=200, blank=True, null=True)
	def __str__(self):
		return u'%s %s %s' % (self.contact, self.heading, self.message)
	def attachment_list(self):
		return "\n".join([a.name for a in self.attachment.all()])

class OutBoundState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Outbound(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
	heading = models.CharField(max_length=512,blank=True, null=True)
	message = models.TextField()
	template = models.ForeignKey(NotificationTemplate, blank=True, null=True, on_delete=models.CASCADE)
	scheduled_send = models.DateTimeField()
	state = models.ForeignKey(OutBoundState, on_delete=models.CASCADE) #Sent/Delivered or Undelivered
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	inst_notified = models.BooleanField(default=False, null=True)
	inst_num_tries = models.IntegerField(null=True,blank=True)
	attachment = models.ManyToManyField(NotificationAttachment, blank=True)
	recipient = models.CharField(max_length=200, blank=True, null=True)
	response =  models.CharField(max_length=200, blank=True, null=True)
	contact_group = models.TextField(blank=True, null=True)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	message_len = models.IntegerField(default=1)
	batch_id = models.CharField(max_length=256, blank=True, null=True)
	objects = CopyManager()
	def __str__(self):
		return u'%s %s %s' % (self.contact, self.heading, self.message)
	def attachment_list(self):
		return "\n".join([a.name for a in self.attachment.all()])

class SessionSubscriptionStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class SessionSubscriptionType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	service = models.ManyToManyField(Service, blank=True)
	session_expiration = models.IntegerField(help_text='In Seconds')
	def __str__(self):
		return u'%s' % (self.name)
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])

class SessionSubscription(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	expiry = models.DateTimeField()
	enrollment_type = models.ForeignKey(EnrollmentType, on_delete=models.CASCADE)
	session_subscription_type = models.ForeignKey(SessionSubscriptionType, on_delete=models.CASCADE)
	last_access = models.DateTimeField()
	status = models.ForeignKey(SessionSubscriptionStatus, on_delete=models.CASCADE)
	recipient = models.CharField(max_length=200)
	sends = models.IntegerField()
	def __str__(self):
		return u'%s %s' % (self.gateway_profile, self.recipient)


