from django.db import models
from primary.core.bridge.models import *

# Create your models here.
class InstitutionAd(models.Model):
	name = models.CharField(max_length=45)
	collector = models.ForeignKey(Institution, on_delete=models.CASCADE)
	image = models.CharField(max_length=1200)
	description = models.CharField(max_length=100)	
	expiry_date = models.DateTimeField()
	country = models.ForeignKey(Country, on_delete=models.CASCADE)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)


