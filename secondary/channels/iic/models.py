from django.contrib.auth.models import User
from secondary.erp.crm.models import *
from django.contrib.gis.db import models
from primary.core.bridge.models import Trigger
#interactive interface controller

class VariableType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	variable = models.CharField(max_length=100)
	description = models.CharField(max_length=200)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

		
class InputVariable(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	variable_type = models.ForeignKey(VariableType)
	validate_min = models.CharField(max_length=45)
	validate_max = models.CharField(max_length=45)
	default_value = models.CharField(max_length=12800, null=True, blank=True)
	variable_kind = models.CharField(max_length=45, null=True, blank=True)
	description = models.CharField(max_length=200, null=True, blank=True)
	service = models.ForeignKey(Service, null=True, blank=True)	
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.name, self.variable_type)		

'''		
class InputVariable(models.Model):
	name = models.CharField(max_length=45)
	variable_type = models.ForeignKey(VariableType)
	validate_min = models.CharField(max_length=45)
	validate_max = models.CharField(max_length=45)
	default_value = models.CharField(max_length=600, null=True, blank=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.variable_type)		
'''

class PageGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	item_level = models.IntegerField()
	description = models.CharField(max_length=200)
	icon_old= models.CharField(max_length=45, null=True, blank=True)
	icon = models.ForeignKey(Icon, null=True, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)	
	def __unicode__(self):
		return u'%s' % (self.name)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])

class Page(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	icon_old= models.CharField(max_length=45, null=True, blank=True)
	item_level = models.IntegerField()
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	page_group = models.ForeignKey(PageGroup)
	icon = models.ForeignKey(Icon, null=True, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)	
	service = models.ManyToManyField(Service, blank=True)	
	def __unicode__(self):
		return u'%s %s %s %s' % (self.id, self.name, self.service_list(), self.access_level_list())
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])

# p = Page()
# p.access_level.all()

class PageInputStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class BindPosition(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class PageInputGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	icon_old= models.CharField(max_length=45, null=True, blank=True)
	description = models.CharField(max_length=200)
	item_level = models.CharField(max_length=4)
	input_variable = models.ForeignKey(InputVariable)
	style = models.TextField(blank=True)
	section_size = models.CharField(max_length=45)
	section_height = models.IntegerField()
	auto_submit = models.BooleanField(default=False)
	icon = models.ForeignKey(Icon, null=True, blank=True)
	bind_position = models.ForeignKey(BindPosition, null=True, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)	
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.name, self.input_variable)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
'''
class Trigger(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)
'''
class PageInput(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	page_input = models.CharField(max_length=200)
	icon_old= models.CharField(max_length=45, null=True, blank=True)
	section_size = models.CharField(max_length=45, null=True, blank=True)
	item_level = models.CharField(max_length=4)
	trigger = models.ManyToManyField(Trigger, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	input_variable = models.ForeignKey(InputVariable)
	page_input_group = models.ForeignKey(PageInputGroup)
	page_input_status = models.ForeignKey(PageInputStatus)
	page = models.ForeignKey(Page)
	gateway = models.ManyToManyField(Gateway, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	channel = models.ManyToManyField(Channel)
	style = models.TextField(blank=True)
	section_height = models.IntegerField(null=True, blank=True)
	icon = models.ForeignKey(Icon, null=True, blank=True)
        payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	enrollment_type_included = models.ManyToManyField(EnrollmentType, blank=True)
	enrollment_type_excluded = models.ManyToManyField(EnrollmentType, blank=True, related_name='pageinput_enrollment_type_excluded')
	def __unicode__(self):
		return u'%s' % (self.page_input)
	def trigger_list(self):
		return "\n".join([a.name for a in self.trigger.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def enrollment_type_included_list(self):
		return "\n".join([a.name for a in self.enrollment_type_included.all()])
	def enrollment_type_excluded_list(self):
		return "\n".join([a.name for a in self.enrollment_type_excluded.all()])

