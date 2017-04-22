from django.contrib.gis.db import models
from crm.models import *


class CodeType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Code(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	code = models.CharField(max_length=45)
	mno = models.ForeignKey(MNO, blank=True, null=True)
	institution = models.ForeignKey(Institution, blank=True, null=True)
	channel = models.ForeignKey(Channel) #For unique field with session id which is external
	code_type = models.ForeignKey(CodeType, blank=True, null=True)
	description = models.CharField(max_length=100)
	gateway = models.ForeignKey(Gateway)
	alias = models.CharField(max_length=45, blank=True, null=True)
	def __unicode__(self):
		return u'%s %s %s %s' % (self.id, self.code, self.mno, self.institution)

class SessionState(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class SessionHop(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True) #order by date created
	session_id = models.CharField(max_length=500) 
	channel = models.ForeignKey(Channel) #For unique field with session id which is external
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True) #Blank For unexisting/first time profiles which is external
	reference = models.CharField(max_length=100, null=True, blank=True) #For tracking sends and recording unregistered users
	num_of_tries = models.IntegerField(null=True, blank=True)
	num_of_sends = models.IntegerField(null=True, blank=True)
	def __unicode__(self):
		return u'%s %s %s' % (self.session_id, self.gateway_profile, self.reference)

class MenuStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class VariableType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	variable = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)
		
class InputVariable(models.Model):
	name = models.CharField(max_length=45, unique=True)
	variable_type = models.ForeignKey(VariableType)
	validate_min = models.CharField(max_length=45)
	validate_max = models.CharField(max_length=45)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)		

class Menu(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	page_string = models.CharField(max_length=320)
	access_level = models.ManyToManyField(AccessLevel)
	session_state = models.ForeignKey(SessionState)
	code = models.ManyToManyField(Code)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	service = models.ForeignKey(Service, null=True, blank=True)
	submit = models.BooleanField(default=False)
	level = models.IntegerField()
	group_select = models.IntegerField(null=True, blank=True)		
	input_variable = models.ForeignKey(InputVariable)
	selection_preview = models.BooleanField(default=False)
	menu_description = models.CharField(max_length=50)
	menu_status = models.ForeignKey(MenuStatus)
	protected = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.code_list(), self.page_string)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def code_list(self):
		return "\n".join([a.code for a in self.code.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])

class MenuItem(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	menu_item = models.CharField(max_length=200)
	access_level = models.ManyToManyField(AccessLevel)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	item_level = models.IntegerField()
	menu = models.ForeignKey(Menu)	
	status = models.ForeignKey(MenuStatus)
	def __unicode__(self):
		return u'%s' % (self.menu_item)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])

class Navigator(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	session = models.ForeignKey(SessionHop)
	menu = models.ForeignKey(Menu, null=True, blank=True) #What the user viewed
	item_list = models.CharField(max_length=1024, null=True, blank=True)
	nav_step = models.IntegerField(null=True, blank=True) #The user step on navigation, it increments on user return to main or starting a new service.
	input_select = models.CharField(max_length=200, null=True, blank=True)	
	code = models.ForeignKey(Code)
	pin_auth = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s %s' % (self.session.gateway_profile, self.menu, self.nav_step)
