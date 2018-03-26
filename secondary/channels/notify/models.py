from django.contrib.gis.db import models
from secondary.channels.vcs.models import *
from secondary.erp.crm.models import *

class Endpoint(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	url = models.CharField(max_length=640)
	account_id = models.CharField(max_length=128)
	username = models.CharField(max_length=128)
	password = models.CharField(max_length=256)
	api_key = models.CharField(max_length=256,blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class NotificationStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Notification(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(NotificationStatus)
	endpoint = models.ForeignKey(Endpoint, null=True, blank=True)
	ext_service_id = models.CharField(max_length=250)
	ext_service_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	ext_service_details = models.CharField(max_length=1920, null=True, blank=True)
	institution_url = models.CharField(max_length=640, null=True, blank=True) #Institution to be notified
	institution_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	institution_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	channel = models.ManyToManyField(Channel, blank=True)
	product_type = models.ForeignKey(ProductType)
	code = models.ForeignKey(Code)#Code Required for Email & InApp notifications (Create Code named EMAIL|IN APP for institution)
	service = models.ForeignKey(Service, blank=True, null=True) #Service for processing inbound tasks
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.name, self.ext_service_id)
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])

class NotificationProduct(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	notification = models.ForeignKey(Notification)
	ext_product_id = models.CharField(max_length=250, null=True, blank=True)
	keyword = models.CharField(max_length=45, null=True, blank=True)
	subscribable = models.NullBooleanField(default=False)
	expires = models.NullBooleanField(default=False)
	subscription_endpoint = models.ForeignKey(Endpoint, null=True, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	unit_credit_charge = models.DecimalField(max_digits=19, decimal_places=2)
	service = models.ManyToManyField(Service, blank=True)
	unsubscription_endpoint = models.ForeignKey(Endpoint, null=True, blank=True, related_name="unsubscription_endpoint")
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	def __unicode__(self):
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
	product = models.OneToOneField(NotificationProduct)
	auto = models.BooleanField(default=False)
	response_product = models.ForeignKey(NotificationProduct, related_name="autoresponse_auto_notification") #If None, use Default/Self Notification to respond
	def __unicode__(self):
		return u'%s %s' % (self.notification, self.auto)

class ContactStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class ContactGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200)
	description = models.CharField(max_length=200)
	institution = models.ForeignKey(Institution, blank=True, null=True)
	gateway = models.ForeignKey(Gateway, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Contact(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	status = models.ForeignKey(ContactStatus) 
	product = models.ForeignKey(NotificationProduct) 
	subscription_details = models.CharField(max_length=1920)
	subscribed = models.BooleanField(default=False)
	linkid = models.CharField(max_length=200, null=True,blank=True)
	gateway_profile = models.ForeignKey(GatewayProfile) # A gateway profile has only one MSISDN
	contact_group = models.ManyToManyField(ContactGroup, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.gateway_profile, self.product)
	def contact_group_list(self):
		return "\n".join([a.name for a in self.contact_group.all()])

class Credit(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	description = models.CharField(max_length=100)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	product_type = models.ForeignKey(ProductType)
	credit_value = models.IntegerField()
	def __unicode__(self):
		return u'%s' % (self.credit_value)

class TemplateStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)


class TemplateFile(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	file_path = models.FileField(upload_to='notify_templatefile_path/', max_length=200, null=True,blank=True)
	def __unicode__(self):
		return u'%s' % (self.name)
			
class NotificationTemplate(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	template_heading = models.CharField(max_length=45)
	template_message = models.CharField(max_length=3840)
	product = models.ManyToManyField(NotificationProduct, blank=True)#Product_type
	service = models.ForeignKey(Service)
	description = models.CharField(max_length=50)
	status = models.ForeignKey(TemplateStatus)
	template_file = models.ForeignKey(TemplateFile, null=True,blank=True)
	trigger = models.ManyToManyField(Trigger, blank=True)
	def __unicode__(self):
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
	def __unicode__(self):
		return u'%s' % (self.name)

class InBoundState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Inbound(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
        contact = models.ForeignKey(Contact)
	heading = models.CharField(max_length=50,blank=True, null=True)
	message = models.CharField(max_length=3840)
	state = models.ForeignKey(InBoundState) #CREATED / PROCESSED / COMPLETED (Institution URL notified if not None Exists)
	inst_notified = models.NullBooleanField(default=False)
	inst_num_tries = models.IntegerField(null=True,blank=True)
	attachment = models.ManyToManyField(NotificationAttachment, blank=True)
	def __unicode__(self):
		return u'%s %s %s' % (self.contact, self.heading, self.message)
	def attachment_list(self):
		return "\n".join([a.name for a in self.attachment.all()])

class OutBoundState(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Outbound(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
        contact = models.ForeignKey(Contact)
	heading = models.CharField(max_length=50,blank=True, null=True)
	message = models.CharField(max_length=3840)
	template = models.ForeignKey(NotificationTemplate, blank=True, null=True)
	scheduled_send = models.DateTimeField()
	state = models.ForeignKey(OutBoundState) #Sent/Delivered or Undelivered
	sends = models.IntegerField()
	ext_outbound_id = models.CharField(max_length=200, blank=True, null=True)
	inst_notified = models.NullBooleanField(default=False)
	inst_num_tries = models.IntegerField(null=True,blank=True)
	attachment = models.ManyToManyField(NotificationAttachment, blank=True)
	recipient = models.CharField(max_length=200, blank=True, null=True)

	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False,
								 help_text="Push Notification Acknowledged")

	def __unicode__(self):
		return u'%s %s %s' % (self.contact, self.heading, self.message)
	def attachment_list(self):
		return "\n".join([a.name for a in self.attachment.all()])

