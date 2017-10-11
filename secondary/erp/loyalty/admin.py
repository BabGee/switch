from django.contrib import admin
from secondary.erp.loyalty.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class LoyaltyAccountTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','branch','point_amount')
admin.site.register(LoyaltyAccountType, LoyaltyAccountTypeAdmin)

class LoyaltyTransactionTypeAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(LoyaltyTransactionType, LoyaltyTransactionTypeAdmin)

class LoyaltyAccountStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(LoyaltyAccountStatus, LoyaltyAccountStatusAdmin)

class LoyaltyAccountAdmin(admin.ModelAdmin):
	list_display = ('gateway_profile','account_status',\
			'account_type','created_by',)
admin.site.register(LoyaltyAccount, LoyaltyAccountAdmin)
     
class LoyaltyAccountManagerAdmin(admin.ModelAdmin):
	list_display = ('credit','transaction_reference','is_reversal',\
			'source_account','dest_account','amount','balance_bf',)
admin.site.register(LoyaltyAccountManager, LoyaltyAccountManagerAdmin)  
    
