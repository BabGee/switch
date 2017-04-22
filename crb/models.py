from __future__ import unicode_literals
from django.db import models

# Create your models here.
'''
class ConsumerCrb(models.Model):
    service_api_name = models.CharField(max_length=50)  # api name.product103,product104 etc
    surname = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    county = models.CharField(max_length=100)
    score = models.IntegerField(max_length=100, default=0)
    reasonsCode = models.TextField()
    probability = models.CharField(max_length=100)
    grade = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s' % (self.service_api_name)
'''
