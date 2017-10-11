from __future__ import unicode_literals

from django.contrib.gis.db import models
from secondary.finance.vbs.models import *

class InvestmentType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	value = models.DecimalField(max_digits=19, decimal_places=2) #AMKA Pies Value per pie
	limit_review_rate = models.DecimalField(max_digits=19, decimal_places=2)
	product_item = models.OneToOneField(ProductItem)
	def __unicode__(self):
		return u'%s %s %s' % (self.name, self.value, self.product_item.currency)


class Investment(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	investment_type = models.ForeignKey(InvestmentType)
	account = models.ForeignKey(Account)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	pie = models.DecimalField(max_digits=19, decimal_places=2) #AMKA Pies
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	processed = models.BooleanField(default=False)
	def __unicode__(self):
		return '%s %s %s %s %s %s' % (self.investment_type, self.account, self.amount, self.pie, self.balance_bf, self.processed)
