from django.db import models
from crm.models import *

# Create your models here.

class URLType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	location = models.CharField(max_length=200)
	updated = models.BooleanField(default=False)
	max_visits = models.IntegerField()
	def __unicode__(self):
		return u'%s' % (self.name)

class ShortenerStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Shortener(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	base = models.CharField(max_length=20)
	url = models.CharField(max_length=1024)
	url_type = models.ForeignKey(URLType)
	expiry = models.DateTimeField()
	visits = models.IntegerField()
	updated = models.BooleanField(default=False)
	name = models.CharField(max_length=200)
	status = models.ForeignKey(ShortenerStatus)
	gateway_profile = models.ForeignKey(GatewayProfile, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)

