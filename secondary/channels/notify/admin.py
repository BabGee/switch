from django.contrib import admin
from .models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class CredentialAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','url','api_key','api_secret','api_token','access_token',\
			'token_validity','token_expiration','updated',)
admin.site.register(Credential, CredentialAdmin)

class EndpointAdmin(admin.ModelAdmin):
	list_display = ('name','description','request','url','account_id','username','password','api_key', 'batch',\
			'credential',)
admin.site.register(Endpoint, EndpointAdmin)

class NotificationStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(NotificationStatus, NotificationStatusAdmin)

class NotificationAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','status','endpoint',\
			'ext_service_id','ext_service_username','ext_service_password',\
			'ext_service_details','institution_url',\
			'institution_username','institution_password','channel_list',\
			'product_type','code','service',)
	list_filter = ('code__institution','code','code__gateway','code__mno',)
admin.site.register(Notification, NotificationAdmin)

class ResponseProductAdmin(admin.ModelAdmin):
	list_display = ('product','auto','response_product')
admin.site.register(ResponseProduct, ResponseProductAdmin)

class NotificationProductAdmin(admin.ModelAdmin):
	list_display = ('id','name', 'description', 'notification','ext_product_id',\
			'keyword','subscribable','expires','subscription_endpoint',\
			'product_type_list','unit_credit_charge','service_list',\
			'unsubscription_endpoint','create_subscribe','payment_method_list',\
			'trading_box','priority','is_bulk','institution_allowed')
	list_filter = ('notification','notification__code','notification__code__institution','service','notification__code__gateway','notification__code__mno',)
admin.site.register(NotificationProduct, NotificationProductAdmin)

class ContactStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description',)
admin.site.register(ContactStatus, ContactStatusAdmin)

class ContactAdmin(admin.ModelAdmin):
	list_display = ('id','status','product','subscription_details','subscribed',\
			'linkid','gateway_profile')
	list_filter = ('product','subscribed','status',)
	search_fields = ('gateway_profile__msisdn__phone_number','gateway_profile__user__email',)
admin.site.register(Contact, ContactAdmin)

class ContactGroupStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description',)
admin.site.register(ContactGroupStatus, ContactGroupStatusAdmin)

class ContactGroupAdmin(admin.ModelAdmin):
	list_display = ('id','name', 'description','institution','gateway','status','channel',)
admin.site.register(ContactGroup, ContactGroupAdmin)

class RecipientAdmin(admin.ModelAdmin):
	list_display = ('id','status','details','subscribed', 'recipient','contact_group')
	list_filter = ('contact_group__gateway','contact_group__institution','subscribed','status','contact_group__name',)
	search_fields = ('recipient',)
admin.site.register(Recipient, RecipientAdmin)

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
		'service','description','status','template_file','protected','trigger_list',)
		search_fields = ('template_heading','template_message','description',)
		list_filter = ('service','product','status',)
admin.site.register(NotificationTemplate, NotificationTemplateAdmin)

class InBoundStateAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(InBoundState, InBoundStateAdmin)

class InboundAdmin(admin.ModelAdmin):
		list_display = ('contact','heading','message',\
			'state','inst_notified','inst_num_tries','attachment_list','recipient',)
admin.site.register(Inbound, InboundAdmin)

class OutBoundStateAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created',)
admin.site.register(OutBoundState, OutBoundStateAdmin)

class OutboundAdmin(admin.ModelAdmin):
		paginator = TimeLimitedPaginator
		list_display = ('id','contact','heading','message',\
			'template','scheduled_send','state','sends',\
			'ext_outbound_id','inst_notified','inst_num_tries','attachment_list',\
			'recipient','response','contact_group','pn','pn_ack','message_len', 'batch_id',)
		list_filter = ('contact__product','state','contact__subscribed','contact__status','contact__product__notification__code__mno','contact__product__notification__code__institution','contact__product__notification__code__gateway',)
		search_fields = ('id','recipient','contact__gateway_profile__msisdn__phone_number','contact__gateway_profile__user__email','contact__gateway_profile__user__username','message',)

		def suit_row_attributes(self, obj, request):
			css_class = {
				'DELIVERED': 'success',
				'PROCESSING': 'warning',
				'FAILED': 'error',
				'CREATED': '',
				'SENT': 'info',
			}.get(obj.state.name)
			if css_class:
				return {'class': css_class}

admin.site.register(Outbound, OutboundAdmin)

class SessionSubscriptionStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(SessionSubscriptionStatus, SessionSubscriptionStatusAdmin)

class SessionSubscriptionTypeAdmin(admin.ModelAdmin):
	list_display = ('name','description','channel','service_list','session_expiration',)
admin.site.register(SessionSubscriptionType, SessionSubscriptionTypeAdmin)

class SessionSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id','gateway_profile','expiry','enrollment_type', 'session_subscription_type','last_access','status','recipient','sends',)
admin.site.register(SessionSubscription, SessionSubscriptionAdmin)



