from django.contrib.gis.db import models
from secondary.erp.crm.models import *

class AccountType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	deposit_taking = models.BooleanField(default=False) #False For loan accounts
	min_balance = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	max_balance = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) #For deposit Limits
	saving_interest_rate = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) #For Saving Interest Rate
	saving_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Saving Interest Rate
	description = models.CharField(max_length=100)
	daily_withdrawal_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	product_item = models.OneToOneField(ProductItem)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, blank=True, null=True)
	disburse_deductions = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.product_item.currency)
	def credit_type_list(self):
		return "\n".join([a.name for a in self.credit_type.all()])

#For Both Savings & Loans (credit = False - Loans, credit = True - Savings)
class SavingsCreditType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	account_type = models.ForeignKey(AccountType)
	credit = models.BooleanField(default=False) #False For loan accounts
	interest_rate = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) #For Loan Interest Rate
	interest_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	compound_interest= models.BooleanField(default=False) #True For compound, false for simple interest
	min_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	max_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	installment_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	def __unicode__(self):
		return u'%s %s %s' % (self.account_type, self.interest_rate, self.interest_time)

class AccountCharge(models.Model):#Add either withdrawal/deposit charge, add institution & gateway, null=True for specific individual rates
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)	
	name = models.CharField(max_length=50)	
	account_type = models.ForeignKey(AccountType)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=50, blank=True)	
	credit = models.BooleanField(default=False) #Dr | Cr (Credit/Debit Charge to amount)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	service = models.ManyToManyField(Service, blank=True)	
 	def __unicode__(self):
		return u'%s %s' % (self.name, self.charge_value)
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])
	def service_list(self):
		return "\n".join([a.name for a in self.service.all()])

class AccountStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class InstitutionAccount(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ForeignKey(Institution, null=True, blank=True) #Account Owner
	is_default = models.NullBooleanField(default=False)
	account_status = models.ForeignKey(AccountStatus)	
	credit_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	credit_limit_currency = models.ForeignKey(Currency, null=True, blank=True)
	account_type = models.ForeignKey(AccountType)
	def __unicode__(self):
		return u'%s %s %s' % (self.institution, self.is_default, self.account_type)
  
 
class Account(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	is_default = models.NullBooleanField(default=False)
	account_status = models.ForeignKey(AccountStatus)	
	credit_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	credit_limit_currency = models.ForeignKey(Currency, null=True, blank=True)
	account_type = models.ForeignKey(AccountType)
	profile = models.ForeignKey(Profile, null=True, blank=True) #Account Owner
	def __unicode__(self):
		return u'%s %s %s' % (self.profile, self.is_default, self.account_type)
  
 
class CreditOverdueStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class CreditOverdue(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	description = models.CharField(max_length=100)
	overdue_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	notification_details = models.CharField(max_length=1920) #JSON Payload, to be complemented by Template
	service = models.ForeignKey(Service)
	account_type = models.ForeignKey(AccountType) #Determines the institution ETC
	status = models.ForeignKey(CreditOverdueStatus)
	product_item = models.ForeignKey(ProductItem, null=True, blank=True)
	def __unicode__(self):
		return u'%s' % (self.description)


class InstitutionAccountManager(models.Model):
        date_modified = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	is_reversal = models.BooleanField(default=False)
	source_account = models.ForeignKey(Account)
	dest_account = models.ForeignKey(Account, related_name="institution_dest_account")
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.credit, self.credit_paid)

class AccountManager(models.Model):
        date_modified = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	is_reversal = models.BooleanField(default=False)
	source_account = models.ForeignKey(Account)
	dest_account = models.ForeignKey(Account, related_name="dest_account")
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	credit_paid = models.BooleanField(default=False)
	credit_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	credit_due_date = models.DateTimeField(null=True, blank=True)
	credit_overdue = models.ManyToManyField(CreditOverdue, blank=True)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	credit_overdue_update = models.BooleanField(default=False, help_text="True for record that is not the last record")
	def __unicode__(self):
		return u'%s %s %s' % (self.id, self.credit, self.credit_paid)
	def credit_overdue_list(self):
		return "\n".join([a.description for a in self.credit_overdue.all()])

class SavingsCreditManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	account_manager = models.ForeignKey(AccountManager)
	credit = models.BooleanField(default=False) #False For loan accounts
	installment_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	due_date = models.DateTimeField(null=True, blank=True)
	credit_paid = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s %s' % (self.account_manager, self.installment_time, self.due_date)


class CreditOverdueManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	savings_credit_manager = models.ForeignKey(SavingsCreditManager)
	credit_overdue = models.ForeignKey(CreditOverdue)
	response_status = models.ForeignKey(ResponseStatus)
	processed = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s %s' % (self.account_manager, self.credit_overdue, self.status)

class InvestmentAccountType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	nominal_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	investment_loan_allowed = models.DecimalField(max_digits=19, decimal_places=2, help_text='In Percentage')
	product_item = models.OneToOneField(ProductItem)
	gateway = models.ForeignKey(Gateway)
	def __unicode__(self):
		return u'%s %s %s' % (self.name, self.nominal_value, self.product_item.currency)


class InvestmentManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	investment_type = models.ForeignKey(InvestmentAccountType)
	account = models.ForeignKey(Account)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	share_value = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	processed = models.BooleanField(default=False)
	def __unicode__(self):
		return '%s %s %s %s %s %s' % (self.investment_type, self.account, self.amount, self.share_value, self.balance_bf, self.processed)

