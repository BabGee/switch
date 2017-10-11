from __future__ import unicode_literals

import logging
import pytz
from django.utils import timezone
import json
from secondary.erp.crm.models import *

lgr = logging.getLogger('nikobizz')


class SubdomainStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100, unique=True)
	def __unicode__(self):
		return u'%s' % (self.name)



class Subdomain(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	subdomain = models.CharField(max_length=200, unique=True)
	institution = models.ForeignKey(Institution)
	status = models.ForeignKey(SubdomainStatus)
	ssl_certificate = models.TextField(null=True, blank=True)
	ssl_certificate_key = models.TextField(null=True, blank=True)
	ssl_certificate_ca = models.TextField(null=True, blank=True)
	def __unicode__(self):
		return u'%s' % (self.subdomain)



