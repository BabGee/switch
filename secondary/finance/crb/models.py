from __future__ import unicode_literals
from django.db import models
from secondary.erp.crm.models import *
import json

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
class ReportSector(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	sector_code = models.IntegerField()
	def __unicode__(self):
		return u'%s %s' % (self.sector_code, self.name)


class ReportReason(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	reason_code = models.IntegerField()
	def __unicode__(self):
		return u'%s %s' % (self.reason_code, self.name)


class CreditGrade(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	code = models.CharField(max_length=5, unique=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	min_credit_score = models.IntegerField(null=True, blank=True)
	max_credit_score = models.IntegerField(null=True, blank=True)
	hierarchy = models.IntegerField()
	def __unicode__(self):
		return u'%s %s' % (self.code, self.name)

class IdentificationProfileStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.description)

class IdentificationProfile(models.Model):
	national_id = models.CharField(max_length=45, unique=True)
	first_name = models.CharField(max_length=30, null=True, blank=True)
	middle_name = models.CharField(max_length=30, null=True, blank=True)
	last_name = models.CharField(max_length=30, null=True, blank=True)
	status = models.ForeignKey(IdentificationProfileStatus, null=True, blank=True)
	def __unicode__(self):
		return u'%s' % (self.national_id)

class ReferenceAccountStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=250)
	defaulted = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.description)


class Reference(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	identification_profile = models.OneToOneField(IdentificationProfile)
	surname = models.CharField(max_length=30, null=True, blank=True)
	forename_1 = models.CharField(max_length=30, null=True, blank=True)
	forename_2 = models.CharField(max_length=30, null=True, blank=True)
	forename_3 = models.CharField(max_length=30, null=True, blank=True)
	salutation = models.CharField(max_length=30, null=True, blank=True)
	date_of_birth = models.DateField(null=True, blank=True)
	client_number = models.CharField(max_length=30, null=True, blank=True)
	account_number = models.CharField(max_length=30, null=True, blank=True)
	gender = models.ForeignKey(Gender, null=True, blank=True)
	nationality = models.CharField(max_length=30, null=True, blank=True)
	marital_status = models.CharField(max_length=30, null=True, blank=True)
	credit_grade = models.ForeignKey(CreditGrade, null=True, blank=True)
	credit_probability = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	credit_score = models.IntegerField(null=True, blank=True)
	credit_account_list = models.CharField(max_length=1920, null=True, blank=True)
	credit_account_summary = models.CharField(max_length=1920, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.identification_profile, self.surname)

'''
	identification_profile = models.ForeignKey(IdentificationProfile)
	##########################
	Surname	
	Forename 1	
	Forename 2	
	Forename 3	
	Salutation	
	Date of Birth	
	Client Number	
	Account Number	
	Gender	
	Nationality	
	Marital Status	
	Pri Identification Doc Type	
	Primary Identification Doc Number	
	Secondary identification Doc Type	
	Secondary Identification Doc Number	
	Other Identification Doc Type	
	Other Identification Doc Number	
	Mobile Telephone Number	
	Home Telephone Number	
	Work Telephone Number	
	Postal Address 1	
	Postal Address 2	
	Postal Location Town	
	Postal Location Country 	
	Post code	
	Physical Address 1	
	Physical Address 2	
	Plot Number	
	Location Town	
	Location Country 	
	Date of Physical Address	
	PIN Number 	
	Cosumer work E-Mail	
	Employer name 	
	Employer Industry Type	
	Employment Date	
	Employment Type	
	Salary Band	
	Lenders Registered Name	
	Lenders Trading Name	
	Lenders Branch name	
	Lenders Branch Code	
	Account joint/Single indicator	
	Account Product Type	
	Date Account Opened	
	Instalment Due Date	
	Original Amount	
	Currency of Facility	
	Amount in Kenya shillings	
	Current Balance	
	Overdue Balance	
	Overdue Date	
	No of Days in arrears	
	Nr of Installments in arrears	
	Perfoming / NPL indicator	
	Account status	
	Account status Date	
	Account Closure Reason	
	Repayment period 	
	Deferred payment date	
	Deferred payment amount	
	Payment frequency	
	Disbursement Date 	
	Instalment amount 	
	Date of Latest Payment 	
	Last payment amount 	
	Type of Security
	##############################################
	def __unicode__(self):
		return u'%s' % (self.identification_profile)
'''

class ReferenceActivityType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	service = models.ForeignKey(Service)
	product_item = models.ForeignKey(ProductItem)
	report_sector = models.ForeignKey(ReportSector)
	report_reason =models.ForeignKey(ReportReason)
	details = models.CharField(max_length=1920, default=json.dumps({}))
	def __unicode__(self):
		return u'%s %s' % (self.name, self.description)

class ReferenceActivity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True)
	identification_profile = models.ForeignKey(IdentificationProfile)
	reference_activity_type = models.ForeignKey(ReferenceActivityType)
	status = models.ForeignKey(TransactionStatus)
	response_status = models.ForeignKey(ResponseStatus)
	request = models.CharField(max_length=1920, default=json.dumps({}))
	channel = models.ForeignKey(Channel)
	transaction_reference = models.CharField(max_length=45, null=True, blank=True) #Transaction ID
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s %s' % (self.identification_profile, self.gateway_profile, self.reference_activity_type)


class ReferenceRisk(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway = models.ForeignKey(Gateway)
	institution = models.ForeignKey(Institution, null=True, blank=True)
	min_credit_grade = models.ForeignKey(CreditGrade, null=True, blank=True)
	min_credit_probability = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	min_credit_score = models.IntegerField(null=True, blank=True)
	base_initial_credit_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	lend_to_defaulters = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s %s %s' % (self.gateway, self.institution, self.min_credit_grade)


