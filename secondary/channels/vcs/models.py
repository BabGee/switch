from django.db import models
from secondary.erp.crm.models import *


class CodeType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Code(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	code = models.CharField(max_length=45)
	mno = models.ForeignKey(MNO, blank=True, null=True, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.CASCADE)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE) #For unique field with session id which is external
	code_type = models.ForeignKey(CodeType, blank=True, null=True, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	alias = models.CharField(max_length=45, blank=True, null=True)
	def __str__(self):
		return u'%s %s %s %s' % (self.id, self.code, self.mno, self.institution)

class SessionState(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class SessionHop(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True) #order by date created
	session_id = models.CharField(max_length=500) 
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE) #For unique field with session id which is external
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True, on_delete=models.CASCADE) #Blank For unexisting/first time profiles which is external
	reference = models.CharField(max_length=100, null=True, blank=True) #For tracking sends and recording unregistered users
	num_of_tries = models.IntegerField(null=True, blank=True)
	num_of_sends = models.IntegerField(null=True, blank=True)
	def __str__(self):
		return u'%s %s %s' % (self.session_id, self.gateway_profile, self.reference)

class MenuStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class VariableType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	variable = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)
		
class InputVariable(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200, unique=True)
	variable_type = models.ForeignKey(VariableType, on_delete=models.CASCADE)
	validate_min = models.CharField(max_length=45)
	validate_max = models.CharField(max_length=45)
	allowed_input_list = models.CharField(max_length=45, blank=True, null=True, help_text="comma delimitted inputs")
	override_group_select = models.IntegerField(blank=True, null=True)
	error_group_select = models.IntegerField(blank=True, null=True)
	override_level = models.IntegerField(blank=True, null=True)
	error_level = models.IntegerField(blank=True, null=True)
	override_service = models.ForeignKey(Service, blank=True, null=True, related_name='override_service', on_delete=models.CASCADE)
	error_service = models.ForeignKey(Service, blank=True, null=True, related_name='error_service', on_delete=models.CASCADE)
	init_nav_step = models.BooleanField(default=False)
	min_amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	max_amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	def __str__(self):
		return u'%s' % (self.name)		

class Menu(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	page_string = models.TextField()
	page_string_response = models.TextField(blank=True, null=True, help_text='response_status%page_string%state|') 
	error_prefix = models.CharField(max_length=128, null=True, blank=True)
	access_level = models.ManyToManyField(AccessLevel)
	session_state = models.ForeignKey(SessionState, on_delete=models.CASCADE)
	failed_session_state = models.ForeignKey(SessionState, blank=True, null=True, related_name='failed_session_state', on_delete=models.CASCADE)
	code = models.ManyToManyField(Code)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE)
	submit = models.BooleanField(default=False)
	level = models.IntegerField()
	group_select = models.IntegerField(null=True, blank=True)		
	input_variable = models.ForeignKey(InputVariable, on_delete=models.CASCADE)
	selection_preview = models.BooleanField(default=False)
	menu_description = models.CharField(max_length=50)
	menu_status = models.ForeignKey(MenuStatus, on_delete=models.CASCADE)
	protected = models.BooleanField(default=False)
	details = models.CharField(max_length=512, default=json.dumps({}))
	invalid = models.BooleanField(default=False)
	selection = models.CharField(max_length=64, null=True, blank=True)
	enrollment_type_included = models.ManyToManyField(EnrollmentType, blank=True)
	enrollment_type_excluded = models.ManyToManyField(EnrollmentType, blank=True, related_name='menu_enrollment_type_excluded')
	silent_service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name='silent_service')
	def __str__(self):
		return u'%s %s %s' % (self.id, self.code_list(), self.page_string)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def code_list(self):
		return "\n".join([a.code for a in self.code.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])
	def enrollment_type_included_list(self):
		return "\n".join([a.name for a in self.enrollment_type_included.all()])
	def enrollment_type_excluded_list(self):
		return "\n".join([a.name for a in self.enrollment_type_excluded.all()])

class MenuKeyword(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	code = models.ManyToManyField(Code)
	keyword = models.CharField(max_length=128)
	def __str__(self):
		return u'%s %s %s' % (self.id, self.code_list(), self.keyword)
	def code_list(self):
		return "\n".join([a.code for a in self.code.all()])

class MenuItem(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	menu_item = models.CharField(max_length=200)
	access_level = models.ManyToManyField(AccessLevel)
	profile_status = models.ManyToManyField(ProfileStatus, blank=True)
	item_level = models.IntegerField()
	item_order = models.IntegerField()
	menu = models.ForeignKey(Menu, on_delete=models.CASCADE)	
	status = models.ForeignKey(MenuStatus, on_delete=models.CASCADE)
	failed_session_include = models.BooleanField(default=False)
	response_status = models.ForeignKey(ResponseStatus, null=True, blank=True, on_delete=models.CASCADE)
	enrollment_type_included = models.ManyToManyField(EnrollmentType, blank=True)
	enrollment_type_excluded = models.ManyToManyField(EnrollmentType, blank=True, related_name='menuitem_enrollment_type_excluded')
	def __str__(self):
		return u'%s' % (self.menu_item)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def profile_status_list(self):
		return "\n".join([a.name for a in self.profile_status.all()])
	def enrollment_type_included_list(self):
		return "\n".join([a.name for a in self.enrollment_type_included.all()])
	def enrollment_type_excluded_list(self):
		return "\n".join([a.name for a in self.enrollment_type_excluded.all()])

class Navigator(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	session_hop = models.ForeignKey(SessionHop, null=True, blank=True, on_delete=models.CASCADE)
	menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.CASCADE) #What the user viewed
	item_list = models.CharField(max_length=1024, null=True, blank=True)
	nav_step = models.IntegerField(null=True, blank=True) #The user step on navigation, it increments on user return to main or starting a new service.
	input_select = models.CharField(max_length=200, null=True, blank=True)	
	code = models.ForeignKey(Code, on_delete=models.CASCADE)
	pin_auth = models.BooleanField(default=False)
	session = models.ForeignKey(Session, null=True, blank=True, on_delete=models.CASCADE)
	level = models.IntegerField()
	group_select = models.IntegerField(null=True, blank=True)
	invalid = models.BooleanField(default=False)
	def __str__(self):
		return u'%s %s %s %s' % (self.id, self.session, self.menu, self.nav_step)
