from django.contrib.gis import admin
from crc.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms

class CardTypeStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(CardTypeStatus, CardTypeStatusAdmin)

class CardTypeAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','code',)
admin.site.register(CardType, CardTypeAdmin)

class CardVerificationAmountAdmin(admin.ModelAdmin):
		list_display = ('id','currency','min_amount','max_amount')
admin.site.register(CardVerificationAmount, CardVerificationAmountAdmin)

class CardRecordStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(CardRecordStatus, CardRecordStatusAdmin)

class CardRecordAdmin(admin.ModelAdmin):
		list_display = ('id','status',\
		'card_number','card_type','card_expiry_date','token',\
		'gateway_profile','pan','activation_currency','activation_amount',\
		'activation_pin','pin_retries','is_default',)
admin.site.register(CardRecord, CardRecordAdmin)

class CardRecordActivityAdmin(admin.ModelAdmin):
		list_display = ('id','card_record','transaction_reference','order','request','currency','amount',\
				'charges','raise_charges','response','transaction_status','response_status','institution',\
				'scheduled_send','sends',)
admin.site.register(CardRecordActivity, CardRecordActivityAdmin)

