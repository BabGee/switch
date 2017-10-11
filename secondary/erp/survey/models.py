from django.contrib.gis.db import models
from secondary.erp.pos.models import *


class SurveyStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class SurveyGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	data_name = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Survey(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	group = models.ForeignKey(SurveyGroup)
	description = models.CharField(max_length=100)
	institution = models.ManyToManyField(Institution, blank=True)
	product_type = models.ForeignKey(ProductType)
	status = models.ForeignKey(SurveyStatus)
	product_item = models.ForeignKey(ProductItem, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])

class SurveyItemStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class SurveyItem(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	survey = models.ForeignKey(Survey)
	status = models.ForeignKey(SurveyItemStatus)
	expiry = models.DateTimeField(null=True, blank=True)
	code = models.CharField(max_length=45, null=True, blank=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class SurveyResponseStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class SurveyResponse(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	item = models.ForeignKey(SurveyItem)
	status = models.ForeignKey(SurveyResponseStatus)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.item.name, self.gateway_profile)

