from django.contrib.gis import admin
from primary.core.bridge.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class PaymentMethodStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')  
admin.site.register(PaymentMethodStatus, PaymentMethodStatusAdmin)

class PaymentMethodAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','send','receive','default_currency','min_amount',\
				'max_amount','icon','gateway_list','country_list','currency_list','channel_list',)
admin.site.register(PaymentMethod, PaymentMethodAdmin)

class ProductAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')        
admin.site.register(Product, ProductAdmin)

class RetryAdmin(admin.ModelAdmin):
		list_display = ('id','name','max_retry','max_retry_hours')
admin.site.register(Retry, RetryAdmin)

class ServiceStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')        

admin.site.register(ServiceStatus, ServiceStatusAdmin)

class ServiceAdmin(admin.ModelAdmin):
		list_display = ('id','name','product','description','status','success_last_response',\
		 'failed_last_response','retry','allowed_response_key','access_level_list') 
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
		 'reverse_function','description','response','details', 'access_level_list',\
		 'profile_status_list', 'channel_list',\
		 'payment_method_list','trigger_list','gateway_list','success_response_status_list',)
	        list_filter = ('service','node_system','gateway','access_level','channel','payment_method',)
		search_fields = ('command_function','service__name','reverse_function','trigger__name','details',)
admin.site.register(ServiceCommand, ServiceCommandAdmin)

class ServiceCutOffAdmin(admin.ModelAdmin):
		list_display = ('service','cut_off_command','description')
admin.site.register(ServiceCutOff, ServiceCutOffAdmin)


class TransactionStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(TransactionStatus, TransactionStatusAdmin)

class TransactionAdmin(admin.OSMGeoAdmin):
		list_display = ('id','gateway_profile','service','channel','gateway',\
		 'request','currency','amount',\
		  'charges','raise_charges','response','ip_address','transaction_status','response_status',\
		    'geometry','current_command','next_command','msisdn','overall_status','institution',\
			'fingerprint','token','date_modified','date_created')
	        search_fields = ('id','gateway_profile__user__first_name','gateway_profile__user__last_name',\
				'gateway_profile__user__username','gateway_profile__msisdn__phone_number',
				'request','response','ip_address',)
		list_filter = ('service','channel','gateway','transaction_status','response_status','overall_status',)
admin.site.register(Transaction, TransactionAdmin)

class BackgroundServiceAdmin(admin.ModelAdmin):
	list_display = ('id','institution_list','gateway_list','access_level_list','trigger_service_list',\
			'service','details','cut_off_command','trigger_list',)
admin.site.register(BackgroundService, BackgroundServiceAdmin)

class BackgroundServiceActivityAdmin(admin.ModelAdmin):
	list_display = ('id','service','status','gateway_profile','request','channel',\
			'response_status','transaction_reference','currency','amount','charges',\
			'gateway','institution','current_command',\
			'scheduled_send','message','sends','ext_outbound_id',)
	list_filter = ('service', 'status', 'gateway_profile__gateway', 'response_status',)
admin.site.register(BackgroundServiceActivity, BackgroundServiceActivityAdmin)


class ActivityStatusAdmin(admin.ModelAdmin):
        list_display = ('name','description',)
admin.site.register(ActivityStatus, ActivityStatusAdmin)


class ActivityAdmin(admin.ModelAdmin):
        list_display = ('id','name','description','status','ext_service_id','ext_service_username',\
                        'ext_service_password','ext_service_details',\
                        'service','gateway_list',)
admin.site.register(Activity, ActivityAdmin)

class ActivityEndpointAdmin(admin.ModelAdmin):
        list_display = ('id','name','description','request','url','account_id','username','password',)
admin.site.register(ActivityEndpoint, ActivityEndpointAdmin)


class ActivityProductAdmin(admin.ModelAdmin):
        list_display = ('id','name','description','activity','ext_product_id','endpoint',\
                        'service_list','details','realtime','show_message',\
                        'payment_method_list','currency_list','trigger_list',)
        list_filter = ('activity','service','payment_method',)
admin.site.register(ActivityProduct, ActivityProductAdmin)

class ActivityTransactionAdmin(admin.ModelAdmin):
        list_display = ('id','activity_product','status','gateway_profile','request','channel','response_status',\
                        'transaction_reference','currency','amount','charges','gateway','institution',\
                        'message','sends','ext_outbound_id',)
admin.site.register(ActivityTransaction, ActivityTransactionAdmin)

class ApprovalAdmin(admin.ModelAdmin):
        list_display = ('id','institution_list','gateway_list','access_level_list',\
			'service','details','cut_off_command','trigger_service_list','requestor','approver',)
admin.site.register(Approval, ApprovalAdmin)

class ApprovalActivityStatusAdmin(admin.ModelAdmin):
        list_display = ('name','description',)
admin.site.register(ApprovalActivityStatus, ApprovalActivityStatusAdmin)

class ApprovalActivityAdmin(admin.ModelAdmin):
        list_display = ('id','approval','status','requestor_gateway_profile','affected_gateway_profile','approver_gateway_profile',\
			'request','channel','response_status','gateway','institution',)
admin.site.register(ApprovalActivity, ApprovalActivityAdmin)

class GatewayProfileChangeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','institution_list',\
			'gateway_list','access_level_list','details',)
admin.site.register(GatewayProfileChange, GatewayProfileChangeAdmin)

class GatewayProfileChangeActivityAdmin(admin.ModelAdmin):
	list_display = ('id','change','gateway_profile','request','gateway',\
			'institution','processed',)
admin.site.register(GatewayProfileChangeActivity, GatewayProfileChangeActivityAdmin)

