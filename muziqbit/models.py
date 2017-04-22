from django.contrib.gis.db import models
from crm.models import *

class Genre(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Music(models.Model):
	product_item = models.OneToOneField(ProductItem)
	artiste = models.CharField(max_length=200)
	album = models.CharField(max_length=200, null=True, blank=True)
	genre = models.ForeignKey(Genre)
	release_date = models.DateField(null=True, blank=True)
	file_path = models.FileField(upload_to='muziqbit_music_path/', max_length=200)
	stream_start = models.IntegerField(help_text="In Seconds")
	stream_duration = models.IntegerField(help_text="In Seconds")
	enrollment = models.ManyToManyField(Enrollment, blank=True)
	def __unicode__(self):
		return u'%s' % (self.product_item)
	def enrollment_list(self):
		return "\n".join([a.member_alias for a in self.enrollment.all()])

class DownloadType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	service = models.ForeignKey(Service)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Download(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	music = models.ForeignKey(Music)
	download_type = models.ForeignKey(DownloadType)
	gateway_profile = models.ForeignKey(GatewayProfile)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	def __unicode__(self):
		return u'%s %s' % (self.music,self.download_type)

