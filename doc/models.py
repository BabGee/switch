from django.db import models
from upc.models import *
# Create your models here.

class DocumentStatus(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Document(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	template = models.CharField(max_length=200, null=True, blank=True)
	status = models.ForeignKey(DocumentStatus)
	def __unicode__(self):
		return u'%s' % (self.name)

class DocumentActivityStatus(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class DocumentActivity(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User)
	document = models.ForeignKey(Document)
	scan_payload = models.CharField(max_length=1200, blank=True, null=True)
	photo = models.ImageField(upload_to='document_image/', max_length=200)
	status = models.ForeignKey(DocumentActivityStatus)
	created_by = models.ForeignKey(User, related_name="docs_documentactivity_created_by")
	def __unicode__(self):
		return u'%s %s' % (self.user, self.document)

class InstitutionDocument(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ForeignKey(Institution)
	document = models.ForeignKey(Document)
	def __unicode__(self):
		return u'%s %s' % (self.institution, self.document)

