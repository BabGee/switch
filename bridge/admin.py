from django.contrib.gis import admin
from bridge.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class PaymentMethodStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')  
admin.site.register(PaymentMethodStatus, PaymentMethodStatusAdmin)

class PaymentMethodAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','send','receive','gateway_list','country_list','currency_list','channel_list',)
admin.site.register(PaymentMethod, PaymentMethodAdmin)

class ProductAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')        

admin.site.register(Product, ProductAdmin)

class ServiceStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')        

admin.site.register(ServiceStatus, ServiceStatusAdmin)

class ServiceAdmin(admin.ModelAdmin):
		list_display = ('id','name','product','description',\
		 'status','access_level_list','date_modified', 'date_created')        
	        search_fields = ('name',)
		list_filter = ('product','access_level',)
admin.site.register(Service, ServiceAdmin)

class TriggerAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
	        search_fields = ('name','description')

admin.site.register(Trigger, TriggerAdmin)


class CommandStatusAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created')
admin.site.register(CommandStatus, CommandStatusAdmin)

class ServiceCommandAdmin(admin.ModelAdmin):
		list_display = ('id','command_function','level','service','node_system', 'status',\
		 'reverse_function','description', 'service_account', 'access_level_list', 'channel_list',\
		 'payment_method_list','trigger_list','gateway_list',)
	        list_filter = ('service','node_system','gateway','access_level','channel','payment_method',)
		search_fields = ('command_function','service__name','reverse_function',)
admin.site.register(ServiceCommand, ServiceCommandAdmin)

class TransactionStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(TransactionStatus, TransactionStatusAdmin)

class TransactionAdmin(admin.OSMGeoAdmin):
		list_display = ('id','gateway_profile','service','channel','gateway',\
		 'request','currency','amount',\
		  'charges','raise_charges','response','ip_address','transaction_status','response_status',\
		    'geometry','current_command','next_command','msisdn','overall_status','institution',\
			'fingerprint','date_modified','date_created')
	        search_fields = ('id','gateway_profile__user__first_name','gateway_profile__user__last_name',\
				'gateway_profile__user__username','gateway_profile__msisdn__phone_number',
				'request','response',)
		list_filter = ('service','channel','gateway','transaction_status','response_status','overall_status',)
admin.site.register(Transaction, TransactionAdmin)

