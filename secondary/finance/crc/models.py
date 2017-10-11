from django.db import models
from secondary.erp.pos.models import *
from secondary.finance.vbs.models import *
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
	code = models.CharField(max_length=5, unique=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class CardVerificationAmount(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	currency = models.OneToOneField(Currency)
	min_amount = models.DecimalField(max_digits=19, decimal_places=2)
	max_amount = models.DecimalField(max_digits=19, decimal_places=2)
	def __unicode__(self):
		return u'%s %s %s' % (self.currency, self.min_amount, self.max_amount)

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
	activation_currency = models.ForeignKey(Currency)
	activation_amount = models.DecimalField(max_digits=19, decimal_places=2)
	activation_pin = models.CharField(max_length=200, null=True, blank=True)
	pin_retries = models.SmallIntegerField(default=0, help_text="Max PIN retries=3 then locks record")
	is_default = models.NullBooleanField(default=False)
	def __unicode__(self):
		return u'%s' % (self.card_number)

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
	scheduled_send = models.DateTimeField(blank=True, null=True)
	sends = models.IntegerField()
	def __unicode__(self):
 		return '%s' % (self.request)
