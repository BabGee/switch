from django.db import models
from primary.core.bridge.models import *
# Create your models here.

class LoyaltyAccountType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	point_amount = models.DecimalField(max_digits=19, decimal_places=2)
	def __str__(self):
		return u'%s' % (self.name)

class LoyaltyTransactionType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class LoyaltyAccountStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class LoyaltyAccount(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True, on_delete=models.CASCADE) #Account Owner | For institution accounts, gateway profile with institution will hold balance
	account_status = models.ForeignKey(LoyaltyAccountStatus, on_delete=models.CASCADE)	
	account_type = models.ForeignKey(LoyaltyAccountType, on_delete=models.CASCADE)
	created_by = models.ForeignKey(GatewayProfile, related_name="loyalty_account_created_by", on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s' % (self.gateway_profile, self.is_default, self.account_type)

class LoyaltyAccountManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	is_reversal = models.BooleanField(default=False)
	source_account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE)
	dest_account = models.ForeignKey(LoyaltyAccount, related_name="dest_account", on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	def __str__(self):
		return u'%s %s' % (self.id, self.credit)
