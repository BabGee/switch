from django.db import models
from pos.models import *
# Create your models here.
# Card records controller
# Address Verification Service
# CSC Card Security Code

class CardTypeStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class CardType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(CardTypeStatus)
	code = models.CharField(max_length=5, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class CardRecordStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class CardRecord(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	status = models.ForeignKey(CardRecordStatus)
	card_number = models.CharField(max_length=30)#=411111xxxxxx1111,
	card_type = models.ForeignKey(CardType)#=001,
	card_expiry_date = models.DateField(max_length=30)#=12-2022,
	token = models.CharField(max_length=256, blank=True, null=True)#=4305769863115000001514,
	gateway_profile = models.ForeignKey(GatewayProfile)
	pan = models.CharField(max_length=512, default='411111xxxxxx1111')
	def __unicode__(self):
		return u'%s' % (self.card_number)

class CardRecordActivityStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class CardRecordActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	card_record = models.ForeignKey(CardRecord)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	order =  models.ForeignKey(PurchaseOrder)
	request = models.CharField(max_length=12800)
	currency = models.ForeignKey(Currency)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charges = models.DecimalField(max_digits=19, decimal_places=2)
	raise_charges = models.NullBooleanField(default=False) #False - Not inclusive of the amount | True - Inclusive of the amount
	response = models.CharField(max_length=12800, blank=True, null=True)
	transaction_status = models.ForeignKey(TransactionStatus)
	response_status = models.ForeignKey(ResponseStatus)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	def __unicode__(self):
 		return '%s' % (self.request)

