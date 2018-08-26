from django.contrib import admin
from secondary.finance.vbs.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class AccountTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','deposit_taking', 'min_balance','max_balance', 'description',\
			 'daily_withdrawal_limit','product_item','gateway','institution',\
			 'disburse_deductions','restrict_multiple_credit',)
	list_filter = ('product_item__institution','institution',)
admin.site.register(AccountType, AccountTypeAdmin)

class SavingsCreditTypeAdmin(admin.ModelAdmin):
	list_display = ('account_type','credit','interest_rate','interest_time','compound_interest',\
			'min_time','max_time','installment_time',)
admin.site.register(SavingsCreditType, SavingsCreditTypeAdmin)


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
			'account_status','credit_limit','account_type',)
	search_fields = ('institution__name',)
	list_filter = ('account_type','is_default','account_status')
admin.site.register(InstitutionAccount, InstitutionAccountAdmin)
  

class AccountAdmin(admin.ModelAdmin):
	list_display = ('id','is_default',\
			'account_status','credit_limit','account_type',\
			'profile','gateway_profile_list',)
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
			'amount','charge','balance_bf','date_modified','date_created','updated',)
	list_filter = ('credit','updated',)
        search_fields = ('id','transaction_reference',)
admin.site.register(InstitutionAccountManager, InstitutionAccountManagerAdmin)  

   
class AccountManagerAdmin(admin.ModelAdmin):
	list_display = ('id','credit','transaction_reference','is_reversal','source_account','dest_account',\
			'amount','charge','balance_bf','credit_paid','credit_time',\
			'credit_due_date','credit_overdue_list','date_modified','date_created','updated',\
			'incoming_payment',)
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
  
class SavingsCreditManagerAdmin(admin.ModelAdmin):
	list_display = ('account_manager','credit','installment_time','amount','charge','due_date','credit_paid','paid','outstanding',)
admin.site.register(SavingsCreditManager, SavingsCreditManagerAdmin)

class CreditOverdueManagerAdmin(admin.ModelAdmin):
	list_display = ('savings_credit_manager','credit_overdue','response_status','processed',)
admin.site.register(CreditOverdueManager, CreditOverdueManagerAdmin)

class InvestmentAccountTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','nominal_value','investment_loan_allowed','product_item','gateway',)
admin.site.register(InvestmentAccountType, InvestmentAccountTypeAdmin)

class InvestmentManagerAdmin(admin.ModelAdmin):
	list_display = ('id','investment_type','account','amount','share_value','balance_bf','processed',)
admin.site.register(InvestmentManager, InvestmentManagerAdmin)

