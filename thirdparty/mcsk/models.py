from django.contrib.gis.db import models
from crm.models import *


class Member(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	enrollment = models.ForeignKey(Enrollment)
	full_names = models.CharField(max_length=200)
	address = models.CharField(max_length=100, blank=True, null=True)
	town = models.CharField(max_length=100, blank=True, null=True)
	email = models.CharField(max_length=100, blank=True, null=True)
	member_number = models.CharField(max_length=100)
	phone_number = models.CharField(max_length=100, blank=True, null=True)
	alt_phone_number = models.CharField(max_length=100, blank=True, null=True)
	bank_name = models.CharField(max_length=100, blank=True, null=True)
	bank_branch = models.CharField(max_length=100, blank=True, null=True)
	bank_account_no = models.CharField(max_length=100, blank=True, null=True)
	ipi_number = models.CharField(max_length=100, blank=True, null=True)
	details = models.CharField(max_length=1280, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.full_names)

class Beneficiary(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	member = models.ForeignKey(Member)
	full_names = models.CharField(max_length=200)
	passport_id_no = models.CharField(max_length=45, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.full_names)

class CodeRequestType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Region(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class CodeRequest(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	request_type = models.ForeignKey(CodeRequestType)
	gateway_profile = models.ForeignKey(GatewayProfile, blank=True, null=True)
	full_names = models.CharField(max_length=200, blank=True, null=True)
	phone_number = models.CharField(max_length=20, blank=True, null=True)
	passport_id_no = models.CharField(max_length=45, blank=True, null=True)
	code_allocation = models.IntegerField(unique=True)
	code_preview = models.CharField(max_length=320, blank=True, null=True)
	details_match = models.CharField(max_length=5, help_text='Name:MemberNumber', blank=True, null=True)
	approved = models.BooleanField(default=False)
	region = models.ForeignKey(Region, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.full_names)

