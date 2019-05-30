from django.contrib.gis.db import models
from primary.core.administration.models import *

class NodeStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)		
	
#This calls specific integrators to different destinations
class NodeSystem(models.Model):
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=50, blank=True, null=True)
	URL = models.CharField(max_length=250)
	use_ssl = models.BooleanField(default=False)
	cert_path = models.CharField(max_length=200, blank=True, null=True)
	key_path = models.CharField(max_length=200, blank=True, null=True)
	ca_path = models.CharField(max_length=200, blank=True, null=True)
	api_key = models.CharField(max_length=200, blank=True, null=True)
	timeout_time = models.IntegerField(blank=True, null=True, help_text='In Seconds') #In seconds
	username = models.CharField(max_length=50, blank=True, null=True)
	password = models.CharField(max_length=50, blank=True, null=True)
	node_status = models.ForeignKey(NodeStatus, on_delete=models.CASCADE)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)


