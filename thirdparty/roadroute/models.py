from django.contrib.gis.db import models
from secondary.erp.crm.models import *


class TownCity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	country = models.ForeignKey(Country)
	def __unicode__(self):
		return u'%s' % (self.name)

class RoadStreetStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class RoadStreet(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(RoadStreetStatus)
	town_city = models.ForeignKey(TownCity)
	def __unicode__(self):
		return u'%s' % (self.name)

class UpdateStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class UpdateSource(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class RoadStreetUpdate(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	ext_update_id = models.CharField(max_length=50, blank=True, null=True)
	status = models.ForeignKey(UpdateStatus)
	road_street = models.ForeignKey(RoadStreet)
	update = models.CharField(max_length=1024)
	update_source = models.ForeignKey(UpdateSource)
	reporter = models.CharField(max_length=200, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)

