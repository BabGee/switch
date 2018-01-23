# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.gis.db import models
from secondary.erp.pos.models import *


class AgentStatus(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.description)
class Agent(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	profile = models.OneToOneField(Profile)
	status = models.ForeignKey(AgentStatus)
	registrar = models.ForeignKey(Profile, related_name='registrar')
	def __unicode__(self):
		return '%s %s %s' % (self.profile, self.status, self.registrar)

class TradingInstitutionStatus(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.description)

class TraderType(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	product_item = models.ForeignKey(ProductItem)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.description)

class TradingInstitution(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	trader_type = models.ForeignKey(TraderType)
	institution = models.OneToOneField(Institution)
	status = models.ForeignKey(TradingInstitutionStatus)
	agent = models.ForeignKey(Agent)
	supplier = models.ManyToManyField('self', blank=True)
	def __unicode__(self):
		return '%s %s %s' % (self.trader_type, self.institution, self.status)
	def supplier_list(self):
		return "\n".join([a.__unicode__() for a in self.supplier.all()])

