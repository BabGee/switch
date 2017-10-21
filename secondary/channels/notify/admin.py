from django.contrib import admin
from .models import *
from django.forms.widgets import TextInput, Textarea
from django import forms



class EndpointAdmin(admin.ModelAdmin):
	list_display = ('name','description','url','account_id','username','password')
admin.site.register(Endpoint, EndpointAdmin)

class NotificationStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(NotificationStatus, NotificationStatusAdmin)

class NotificationAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','status','endpoint',\
			'ext_service_id','ext_service_username','ext_service_password',\
			'ext_service_details','institution_url',\
			'institution_username','institution_password','channel_list',\
			'product_type','institution_till','code','service',)
	list_filter = ('code__institution','code',)
admin.site.register(Notification, NotificationAdmin)

class ResponseProductAdmin(admin.ModelAdmin):
	list_display = ('product','auto','response_product')
admin.site.register(ResponseProduct, ResponseProductAdmin)

class NotificationProductAdmin(admin.ModelAdmin):
	list_display = ('id','name', 'description', 'notification','ext_product_id',\
			'keyword','subscribable','expires','subscription_endpoint',\
			'product_type_list','unit_credit_charge','service_list',\
			'unsubscription_endpoint','payment_method_list',)
	list_filter = ('notification','notification__code','notification__code__institution','service',)
admin.site.register(NotificationProduct, NotificationProductAdmin)

class ContactStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description',)
admin.site.register(ContactStatus, ContactStatusAdmin)

class ContactGroupAdmin(admin.ModelAdmin):
	list_display = ('id','name', 'description','institution','gateway',)
admin.site.register(ContactGroup, ContactGroupAdmin)

class ContactAdmin(admin.ModelAdmin):
	list_display = ('id','status','product','subscription_details','subscribed',\
			'linkid','gateway_profile', 'contact_group_list')
	list_filter = ('product','subscribed','status',)
	search_fields = ('gateway_profile__msisdn__phone_number',)
admin.site.register(Contact, ContactAdmin)

class CreditAdmin(admin.ModelAdmin):
	list_display = ('description','institution', 'product_type','credit_value',)
admin.site.register(Credit, CreditAdmin)

class TemplateStatusAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(TemplateStatus, TemplateStatusAdmin)
			
class TemplateFileAdmin(admin.ModelAdmin):
		list_display = ('name','description','file_path',)
admin.site.register(TemplateFile, TemplateFileAdmin)
					
class NotificationTemplateAdmin(admin.ModelAdmin):
		list_display = ('id','template_heading','template_message','product_list',\
		'service','description','status','template_file','trigger_list',)
		search_fields = ('template_heading','template_message','description',)
		list_filter = ('service','product','status',)
admin.site.register(NotificationTemplate, NotificationTemplateAdmin)

class InBoundStateAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(InBoundState, InBoundStateAdmin)

class InboundAdmin(admin.ModelAdmin):
		list_display = ('contact','heading','message',\
			'state','inst_notified','inst_num_tries','attachment_list',)
admin.site.register(Inbound, InboundAdmin)

class OutBoundStateAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(OutBoundState, OutBoundStateAdmin)

class OutboundAdmin(admin.ModelAdmin):
		list_display = ('id','contact','heading','message',\
			'template','scheduled_send','state','sends',\
			'ext_outbound_id','inst_notified','inst_num_tries','attachment_list',\
			'recipient',)
		list_filter = ('contact__product','state','contact__subscribed','contact__status',)
		search_fields = ('id','contact__gateway_profile__msisdn__phone_number','message',)
admin.site.register(Outbound, OutboundAdmin)

