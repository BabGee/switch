from django.db import models
from primary.core.bridge.models import *

class DataListStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class DataListGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class DataListQuery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=200)
	model_name = models.CharField(max_length=100) 
	module_name = models.CharField(max_length=100) 
	values = models.CharField(max_length=2048, blank=True, null=True) 
	date_values = models.CharField(max_length=512, blank=True, null=True)
	date_time_values = models.CharField(max_length=512, blank=True, null=True)
	month_year_values = models.CharField(max_length=512, blank=True, null=True)
	avg_values = models.CharField(max_length=512, blank=True, null=True) 
	sum_values = models.CharField(max_length=512, blank=True, null=True) 
	count_values = models.CharField(max_length=512, blank=True, null=True) 
	custom_values = models.CharField(max_length=512, blank=True, null=True) 
	or_filters = models.CharField(max_length=1024, blank=True, null=True)
	and_filters = models.CharField(max_length=1024, blank=True, null=True)
	not_filters = models.CharField(max_length=1024, blank=True, null=True)
	institution_filters = models.CharField(max_length=512, blank=True, null=True)
	institution_not_filters = models.CharField(max_length=512, blank=True, null=True)
	gateway_filters = models.CharField(max_length=512, blank=True, null=True)
	gateway_profile_filters = models.CharField(max_length=512, blank=True, null=True)
	profile_filters = models.CharField(max_length=512, blank=True, null=True)
	role_filters = models.CharField(max_length=512, blank=True, null=True)
	list_filters = models.CharField(max_length=512, blank=True, null=True) 
	duration_days_filters = models.CharField(max_length=512, blank=True, null=True)
	date_time_filters = models.CharField(max_length=512, blank=True, null=True)
	date_filters = models.CharField(max_length=512, blank=True, null=True)
	duration_seconds_filters = models.CharField(max_length=512, blank=True, null=True)
	duration_hours_filters = models.CharField(max_length=512, blank=True, null=True)
	token_filters = models.CharField(max_length=512, null=True, blank=True)
	links = models.CharField(max_length=512, blank=True, null=True) 
	link_params = models.CharField(max_length=512, blank=True, null=True) 
	last_balance = models.CharField(max_length=512, blank=True, null=True)
	order = models.CharField(max_length=512, blank=True, null=True)
	distinct = models.CharField(max_length=512, blank=True, null=True)
	limit = models.IntegerField(blank=True, null=True)
	def __str__(self):
		return u'%s %s' % (self.id, self.name)  

class DataListCaseQuery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	query = models.ForeignKey(DataListQuery, on_delete=models.CASCADE)
	case_name = models.CharField(max_length=128)
	case_values = models.CharField(max_length=2048, help_text='field%value%newvalue|')
	case_default_value = models.CharField(max_length=128)
	case_inactive = models.BooleanField(default=False)
	def __str__(self):
		return u'%s %s' % (self.id, self.query)

class DataListLinkQuery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	query = models.ForeignKey(DataListQuery, on_delete=models.CASCADE)
	link_name = models.CharField(max_length=128)
	link_service = models.ForeignKey(Service, on_delete=models.CASCADE)
	link_icon = models.ForeignKey(Icon, on_delete=models.CASCADE)
	link_case_filter = models.CharField(max_length=512, null=True, blank=True)
	link_params = models.CharField(max_length=512) 
	link_inactive = models.BooleanField(default=False)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	role = models.ManyToManyField(Role, blank=True)
	def __str__(self):
		return u'%s %s' % (self.id, self.query)
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def role_list(self):
		return "\n".join([a.name for a in self.role.all()])

class DataListJoinQuery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	query = models.ForeignKey(DataListQuery, on_delete=models.CASCADE)
	join_model_name = models.CharField(max_length=100)
	join_module_name = models.CharField(max_length=100) 
	join_or_filters = models.CharField(max_length=512, blank=True, null=True)
	join_and_filters = models.CharField(max_length=512, blank=True, null=True)
	join_not_filters = models.CharField(max_length=512, blank=True, null=True)
	join_institution_filters = models.CharField(max_length=512, blank=True, null=True)
	join_institution_not_filters = models.CharField(max_length=512, blank=True, null=True)
	join_gateway_filters = models.CharField(max_length=512, blank=True, null=True)
	join_gateway_profile_filters = models.CharField(max_length=512, blank=True, null=True)
	join_profile_filters = models.CharField(max_length=512, blank=True, null=True)
	join_role_filters = models.CharField(max_length=512, blank=True, null=True)
	join_duration_days_filters = models.CharField(max_length=512, blank=True, null=True)
	join_fields = models.CharField(max_length=512, null=True, blank=True)
	join_manytomany_fields = models.CharField(max_length=512, null=True, blank=True)
	join_not_fields = models.CharField(max_length=512, null=True, blank=True)
	join_manytomany_not_fields = models.CharField(max_length=512, null=True, blank=True)
	join_case_fields = models.CharField(max_length=512, null=True, blank=True)
	join_inactive = models.BooleanField(default=False)
	def __str__(self):
		return u'%s %s' % (self.id, self.query)  


class PushAction(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class DataResponseType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)


class DataList(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	data_name = models.CharField(max_length=100)
	url = models.URLField(max_length=640, blank=True, null=True)
	content = models.CharField(max_length=2560, blank=True, null=True)
	status = models.ForeignKey(DataListStatus, on_delete=models.CASCADE)
	is_report = models.BooleanField(default=False)
	group = models.ForeignKey(DataListGroup, blank=True, null=True, on_delete=models.CASCADE)
	level = models.IntegerField()
	node_system = models.ForeignKey(NodeSystem, blank=True, null=True, on_delete=models.CASCADE)
	command_function = models.CharField(max_length=100, blank=True, null=True)
	title = models.CharField(max_length=200, blank=True, null=True)
	query = models.ForeignKey(DataListQuery, blank=True, null=True, on_delete=models.CASCADE)
	pn_data = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_id_field = models.CharField('Push Notification ID Field', max_length=50, blank=True, null=True)
	pn_update_field = models.CharField('Push Update Field', max_length=50, blank=True, null=True)
	data_response_type = models.ForeignKey(DataResponseType, on_delete=models.CASCADE)
	ifnull_response = models.CharField(max_length=256, null=True, blank=True)
	push_service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE)
	indexing = models.CharField(max_length=2048, blank=True, null=True) 
	pn_action = models.ManyToManyField(PushAction, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __str__(self):
		return u'%s' % (self.data_name)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])
	def pn_action_list(self):
		return "\n".join([a.name for a in self.pn_action.all()])

class FileUpload(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	trigger_service = models.ManyToManyField(Service)
	activity_service = models.ForeignKey(Service, related_name='dsc_fileupload_activity_service', on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s' % (self.id, self.activity_service)  
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def trigger_service_list(self):
		return "\n".join([a.name for a in self.trigger_service.all()])

class FileUploadActivityStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)


class FileUploadActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100, blank=True, null=True)
	file_path = models.FileField(upload_to='dsc_fileuploadactivity/', max_length=200, null=True,blank=True)
	processed_file_path = models.FileField(upload_to='dsc_fileuploadactivity/', max_length=200, null=True,blank=True)
	file_upload = models.ForeignKey(FileUpload, on_delete=models.CASCADE)
	status = models.ForeignKey(FileUploadActivityStatus, on_delete=models.CASCADE)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	details = models.CharField(max_length=1920)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s' % (self.id, self.name)

class ImageListType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class ImageList(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=100, blank=True, null=True)
	image = models.ImageField(upload_to='dsc_imagelist_image/', max_length=200)
	description = models.CharField(max_length=512, blank=True, null=True)
	image_list_type = models.ForeignKey(ImageListType, on_delete=models.CASCADE)
	level = models.IntegerField(default=0)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __str__(self):
		return u'%s' % (self.name)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])
