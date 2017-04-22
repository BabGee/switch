from django.db import models
from bridge.models import *

class DataListStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class DataListGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class DataListQuery(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=200)
	model_name = models.CharField(max_length=100) 
	values = models.CharField(max_length=1024) 
	or_filters = models.CharField(max_length=512, blank=True, null=True)
	and_filters = models.CharField(max_length=512, blank=True, null=True)
	module_name = models.CharField(max_length=100) 
	institution_filters = models.CharField(max_length=512, blank=True, null=True)
	gateway_filters = models.CharField(max_length=512, blank=True, null=True)
	order = models.CharField(max_length=512, blank=True, null=True)
	count = models.CharField(max_length=1024, blank=True, null=True) 
	filters = models.CharField(max_length=512, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)  

class DataList(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	data_name = models.CharField(max_length=100)
	url = models.URLField(max_length=640, blank=True, null=True)
	content = models.CharField(max_length=2560, blank=True, null=True)
	status = models.ForeignKey(DataListStatus)
	is_report = models.BooleanField(default=False)
	group = models.ForeignKey(DataListGroup, blank=True, null=True)
	level = models.IntegerField()
	function = models.CharField(max_length=100, blank=True, null=True)
	title = models.CharField(max_length=200, blank=True, null=True)
	query = models.ForeignKey(DataListQuery, blank=True, null=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	institution = models.ManyToManyField(Institution, blank=True)
	channel = models.ManyToManyField(Channel, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	def __unicode__(self):
		return u'%s' % (self.data_name)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def access_level_list(self):
		return "\n".join([a.name for a in self.access_level.all()])
	def channel_list(self):
		return "\n".join([a.name for a in self.channel.all()])

class FileUpload(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	gateway = models.ManyToManyField(Gateway, blank=True)
	access_level = models.ManyToManyField(AccessLevel, blank=True)
	trigger_service = models.ManyToManyField(Service)
	activity_service = models.ForeignKey(Service, related_name='dsc__fileupload__activity_service')
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

class FileUploadActivityStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)


class FileUploadActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100, blank=True, null=True)
	file_path = models.FileField(upload_to='dsc_fileuploadactivity/', max_length=200, null=True,blank=True)
	processed_file_path = models.FileField(upload_to='dsc_fileuploadactivity/', max_length=200, null=True,blank=True)
	file_upload = models.ForeignKey(FileUpload)
	status = models.ForeignKey(FileUploadActivityStatus)
	gateway_profile = models.ForeignKey(GatewayProfile)
	details = models.CharField(max_length=1920)
	channel = models.ForeignKey(Channel)
	def __unicode__(self):
		return u'%s %s' % (self.id, self.name)

