from django.contrib import admin
from vbs.models import *
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

class AccountAdmin(admin.ModelAdmin):
	list_display = ('id','gateway_profile', 'is_default',\
			'account_branch','account_status','credit_limit','credit_limit_currency','account_type',)
	search_fields = ('gateway_profile__msisdn__phone_number','gateway_profile__user__username',\
			'gateway_profile__user__first_name','gateway_profile__user__last_name',)
admin.site.register(Account, AccountAdmin)
  
class CreditOverdueStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(CreditOverdueStatus, CreditOverdueStatusAdmin)

class CreditOverdueAdmin(admin.ModelAdmin):
	list_display = ('id','description','overdue_time','notification_details','service','account_type','status','product_item')
admin.site.register(CreditOverdue, CreditOverdueAdmin)
    
class AccountManagerAdmin(admin.ModelAdmin):
	list_display = ('id','credit','transaction_reference','is_reversal','source_account','dest_account',\
			'amount','charge','balance_bf','credit_paid','credit_time',\
			'credit_due_date','credit_overdue_list',)
	list_filter = ('credit','source_account__gateway_profile__gateway','dest_account__gateway_profile__gateway',\
			'source_account__account_type','dest_account__account_type','credit_paid',)
        search_fields = ('id','transaction_reference','source_account__gateway_profile__msisdn__phone_number',\
			'dest_account__gateway_profile__msisdn__phone_number',\
			'source_account__gateway_profile__user__last_name',\
			'dest_account__gateway_profile__user__last_name',\
			'source_account__gateway_profile__user__first_name',\
			'dest_account__gateway_profile__user__first_name',\
			'source_account__gateway_profile__user__username',\
			'dest_account__gateway_profile__user__username',)
admin.site.register(AccountManager, AccountManagerAdmin)  

class InvestmentAccountTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','nominal_value','investment_loan_allowed','product_item','gateway',)
admin.site.register(InvestmentAccountType, InvestmentAccountTypeAdmin)

class InvestmentManagerAdmin(admin.ModelAdmin):
	list_display = ('id','investment_type','account','amount','share_value','balance_bf','processed',)
admin.site.register(InvestmentManager, InvestmentManagerAdmin)


