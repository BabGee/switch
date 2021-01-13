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
	def __str__(self):
		return u'%s' % (self.name)

class CardType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(CardTypeStatus, on_delete=models.CASCADE)
	code = models.CharField(max_length=5, unique=True)
	def __str__(self):
		return u'%s' % (self.name)

class CardVerificationAmount(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	currency = models.OneToOneField(Currency, on_delete=models.CASCADE)
	min_amount = models.DecimalField(max_digits=19, decimal_places=2)
	max_amount = models.DecimalField(max_digits=19, decimal_places=2)
	def __str__(self):
		return u'%s %s %s' % (self.currency, self.min_amount, self.max_amount)

class CardRecordStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class CardRecord(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	status = models.ForeignKey(CardRecordStatus, on_delete=models.CASCADE)
	card_number = models.CharField(max_length=30)#=411111xxxxxx1111,
	card_type = models.ForeignKey(CardType, on_delete=models.CASCADE)#=001,
	card_expiry_date = models.DateField(max_length=30)#=12-2022,
	token = models.CharField(max_length=256, blank=True, null=True)#=4305769863115000001514,
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	pan = models.CharField(max_length=512, default='411111xxxxxx1111')
	activation_currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
	activation_amount = models.DecimalField(max_digits=19, decimal_places=2)
	activation_pin = models.CharField(max_length=200, null=True, blank=True)
	pin_retries = models.SmallIntegerField(default=0, help_text="Max PIN retries=3 then locks record")
	is_default = models.BooleanField(default=False, null=True)
	def __str__(self):
		return u'%s' % (self.card_number)

class CardRecordActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	card_record = models.ForeignKey(CardRecord, on_delete=models.CASCADE)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	order =  models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
	request = models.CharField(max_length=12800)
	currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charges = models.DecimalField(max_digits=19, decimal_places=2)
	raise_charges = models.BooleanField(default=False, null=True) #False - Not inclusive of the amount | True - Inclusive of the amount
	response = models.CharField(max_length=12800, blank=True, null=True)
	transaction_status = models.ForeignKey(TransactionStatus, on_delete=models.CASCADE)
	response_status = models.ForeignKey(ResponseStatus, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
	scheduled_send = models.DateTimeField(blank=True, null=True)
	sends = models.IntegerField()
	def __str__(self):
 		return '%s' % (self.request)
