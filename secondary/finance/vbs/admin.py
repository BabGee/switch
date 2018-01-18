from django.contrib import admin
from secondary.finance.vbs.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class CreditTypeAdmin(admin.ModelAdmin):
	list_display = ('name','description','interest_rate','interest_time','min_time','max_time',)
admin.site.register(CreditType, CreditTypeAdmin)


class AccountTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','deposit_taking', 'min_balance','max_balance','loan_interest_rate', 'loan_time',\
			 'saving_interest_rate', 'saving_time', 'description',\
			 'compound_interest','daily_withdrawal_limit','product_item','credit_type_list','gateway','institution',)
	list_filter = ('product_item__institution','institution',)
admin.site.register(AccountType, AccountTypeAdmin)

class AccountChargeAdmin(admin.ModelAdmin):
	list_display = ('name','account_type', 'min_amount','max_amount',\
			'charge_value','is_percentage','description','credit',\
			'payment_method_list','service_list',)
admin.site.register(AccountCharge, AccountChargeAdmin)

class AccountStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(AccountStatus, AccountStatusAdmin)

class InstitutionAccountAdmin(admin.ModelAdmin):
	list_display = ('id','institution', 'is_default',\
			'account_status','credit_limit','credit_limit_currency','account_type',)
	search_fields = ('institution__name',)
	list_filter = ('account_type','is_default','account_status')
admin.site.register(InstitutionAccount, InstitutionAccountAdmin)
  

class AccountAdmin(admin.ModelAdmin):
	list_display = ('id','is_default',\
			'account_status','credit_limit','credit_limit_currency','account_type',\
			'profile',)
	search_fields = ('profile__user__username','profile__user__first_name','profile__user__last_name',)
	list_filter = ('account_type','is_default','account_status')
admin.site.register(Account, AccountAdmin)
  
class CreditOverdueStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(CreditOverdueStatus, CreditOverdueStatusAdmin)

class CreditOverdueAdmin(admin.ModelAdmin):
	list_display = ('id','description','overdue_time','notification_details','service','account_type','status','product_item')
admin.site.register(CreditOverdue, CreditOverdueAdmin)
     
class InstitutionAccountManagerAdmin(admin.ModelAdmin):
	list_display = ('id','credit','transaction_reference','is_reversal','source_account','dest_account',\
			'amount','charge','balance_bf','date_created','updated',)
	list_filter = ('credit','updated',)
        search_fields = ('id','transaction_reference',)
admin.site.register(InstitutionAccountManager, InstitutionAccountManagerAdmin)  

   
class AccountManagerAdmin(admin.ModelAdmin):
	list_display = ('id','credit','transaction_reference','is_reversal','source_account','dest_account',\
			'amount','charge','balance_bf','credit_paid','credit_time',\
			'credit_due_date','credit_overdue_list','date_created','updated',)
	list_filter = ('credit','source_account__account_type__gateway','dest_account__account_type__gateway',\
			'source_account__account_type','dest_account__account_type','credit_paid','credit_overdue','updated',)
        search_fields = ('id','transaction_reference','source_account__profile__user__username',\
			'dest_account__profile__user__username',\
			'source_account__profile__user__last_name',\
			'dest_account__profile__user__last_name',\
			'source_account__profile__user__first_name',\
			'dest_account__profile__user__first_name',\
			'source_account__profile__user__username',\
			'dest_account__profile__user__username',)
admin.site.register(AccountManager, AccountManagerAdmin)  
 
class CreditOverdueActivityAdmin(admin.ModelAdmin):
	list_display = ('account_manager','credit_overdue','response_status','processed',)
admin.site.register(CreditOverdueActivity, CreditOverdueActivityAdmin)

class InvestmentAccountTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','nominal_value','investment_loan_allowed','product_item','gateway',)
admin.site.register(InvestmentAccountType, InvestmentAccountTypeAdmin)

class InvestmentManagerAdmin(admin.ModelAdmin):
	list_display = ('id','investment_type','account','amount','share_value','balance_bf','processed',)
admin.site.register(InvestmentManager, InvestmentManagerAdmin)

class LoanTypeAdmin(admin.ModelAdmin):
	list_display = ('name','description','interest_rate','interest_time','trigger_service_list','product_type_list',\
			'credit','service','details','access_level_list','institution_list','gateway_list',)
admin.site.register(LoanType, LoanTypeAdmin)

class LoanStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(LoanStatus, LoanStatusAdmin)

class LoanAdmin(admin.ModelAdmin):
	list_display = ('id','loan_type','credit','amount','security_amount','other_loans','payment_method',\
			'loan_time','transaction_reference','currency',\
			'institution','gateway','comment','account','interest_rate','interest_time',\
			'status','gateway_profile',)
admin.site.register(Loan, LoanAdmin)

class LoanActivityAdmin(admin.ModelAdmin):
	list_display = ('id','loan','request','transaction_reference',\
			'response_status','comment','processed','gateway_profile',\
			'status','follow_on_loan_list','channel','gateway','institution',)
admin.site.register(LoanActivity, LoanActivityAdmin)


