from django.contrib.gis.db import models
from secondary.erp.pos.models import *

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
	product_item = models.OneToOneField(ProductItem, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.CASCADE)
	disburse_deductions = models.BooleanField(default=False)
	restrict_multiple_credit = models.BooleanField(default=False)
	def __str__(self):
		return u'%s %s' % (self.name, self.product_item.currency)
	def credit_type_list(self):
		return "\n".join([a.name for a in self.credit_type.all()])

#For Both Savings & Loans (credit = False - Loans, credit = True - Savings)
class SavingsCreditType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
	credit = models.BooleanField(default=False) #False For loan accounts
	interest_rate = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) #For Loan Interest Rate
	interest_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	compound_interest= models.BooleanField(default=False) #True For compound, false for simple interest
	min_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	max_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	installment_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	def __str__(self):
		return u'%s %s %s' % (self.account_type, self.interest_rate, self.interest_time)

class AccountCharge(models.Model):#Add either withdrawal/deposit charge, add institution & gateway, null=True for specific individual rates
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	name = models.CharField(max_length=50)	
	account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=50, blank=True)	
	credit = models.BooleanField(default=False) #Dr | Cr (Credit/Debit Charge to amount)
	for_charge = models.BooleanField(default=False) #Dr | Cr (Credit/Debit Charge to amount)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	service = models.ManyToManyField(Service, blank=True)	
	def __str__(self):
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
	def __str__(self):
		return u'%s' % (self.name)

class Account(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	is_default = models.BooleanField(default=False, null=True)
	account_status = models.ForeignKey(AccountStatus, on_delete=models.CASCADE)	
	credit_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
	profile = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.CASCADE) #Account Owner
	institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE) #Account Owner
	gateway_profile = models.ManyToManyField(GatewayProfile, blank=True)
	def __str__(self):
		return u'%s %s %s' % (self.profile, self.is_default, self.account_type)
	def gateway_profile_list(self):
		return "\n".join([a.msisdn.phone_number for a in self.gateway_profile.all() if a.msisdn])
 
 
class CreditOverdueStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class CreditOverdue(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	description = models.CharField(max_length=100)
	overdue_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	notification_details = models.CharField(max_length=1920) #JSON Payload, to be complemented by Template
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE) #Determines the institution ETC
	status = models.ForeignKey(CreditOverdueStatus, on_delete=models.CASCADE)
	product_item = models.ForeignKey(ProductItem, null=True, blank=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.description)

 
class ManagerStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class AccountManager(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	credit = models.BooleanField(default=False) #Dr | Cr
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	is_reversal = models.BooleanField(default=False)
	source_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.CASCADE)
	dest_account = models.ForeignKey(Account, related_name="dest_account", on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	credit_paid = models.BooleanField(default=False)
	credit_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	credit_due_date = models.DateTimeField(null=True, blank=True)
	credit_overdue = models.ManyToManyField(CreditOverdue, blank=True)
	updated = models.BooleanField(default=False, help_text="True for record that is not the last record")
	credit_overdue_update = models.BooleanField(default=False, help_text="True for record that is not the last record")
	incoming_payment = models.ForeignKey(Incoming, null=True, blank=True, on_delete=models.CASCADE)
	outgoing_payment = models.ForeignKey(Outgoing, null=True, blank=True, on_delete=models.CASCADE)
	status = models.ForeignKey(ManagerStatus, null=True, blank=True, on_delete=models.CASCADE)
	purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s' % (self.id, self.credit, self.credit_paid)
	def credit_overdue_list(self):
		return "\n".join([a.description for a in self.credit_overdue.all()])

class SavingsCreditManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	account_manager = models.ForeignKey(AccountManager, on_delete=models.CASCADE)
	credit = models.BooleanField(default=False) #False For loan accounts
	installment_time = models.IntegerField(null=True, blank=True, help_text="In Days") #For Loan Interest Rate
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	charge = models.DecimalField(max_digits=19, decimal_places=2)
	due_date = models.DateTimeField(null=True, blank=True)
	credit_paid = models.BooleanField(default=False)
	paid = models.DecimalField(max_digits=19, decimal_places=2)
	outstanding = models.DecimalField(max_digits=19, decimal_places=2)
	processed_overdue_credit = models.BooleanField(default=False)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	incoming_payment = models.ForeignKey(Incoming, null=True, blank=True, on_delete=models.CASCADE)
	outgoing_payment = models.ForeignKey(Outgoing, null=True, blank=True, on_delete=models.CASCADE)
	follow_on = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
	def __str__(self):
		return u'%s %s %s' % (self.account_manager, self.installment_time, self.due_date)


class CreditOverdueManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	savings_credit_manager = models.ForeignKey(SavingsCreditManager, on_delete=models.CASCADE)
	credit_overdue = models.ForeignKey(CreditOverdue, on_delete=models.CASCADE)
	processed = models.BooleanField(default=False)
	def __str__(self):
		return u'%s %s %s' % (self.savings_credit_manager, self.credit_overdue, self.processed)

class InvestmentAccountType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	nominal_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	investment_loan_allowed = models.DecimalField(max_digits=19, decimal_places=2, help_text='In Percentage')
	product_item = models.OneToOneField(ProductItem, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s' % (self.name, self.nominal_value, self.product_item.currency)


class InvestmentManager(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	investment_type = models.ForeignKey(InvestmentAccountType, on_delete=models.CASCADE)
	account = models.ForeignKey(Account, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=19, decimal_places=2)
	share_value = models.DecimalField(max_digits=19, decimal_places=2)
	balance_bf = models.DecimalField(max_digits=19, decimal_places=2)
	processed = models.BooleanField(default=False)
	def __str__(self):
		return '%s %s %s %s %s %s' % (self.investment_type, self.account, self.amount, self.share_value, self.balance_bf, self.processed)

