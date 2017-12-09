from django.contrib.gis import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from primary.core.upc.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class InstitutionStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(InstitutionStatus, InstitutionStatusAdmin)

class MSISDNAdmin(admin.ModelAdmin):
		list_display = ('id','phone_number','is_active',)
		search_fields = ('phone_number',)
admin.site.register(MSISDN, MSISDNAdmin)

class InstitutionAdmin(admin.OSMGeoAdmin):
		list_display = ('id','name','business_number',\
		'background_image','description',\
		'status','tagline','logo',\
		'default_color','website','physical_address',\
		'gateway_list','currency_list','country','geometry','theme',\
		'primary_color','secondary_color','accent_color','registration_number',)
		search_fields = ('name','business_number',)
admin.site.register(Institution, InstitutionAdmin)

class ProfileStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(ProfileStatus, ProfileStatusAdmin)

class ProfileAdmin(admin.OSMGeoAdmin):
	list_display = ('id','middle_name','api_key','timezone','language','geometry', 'country', 'dob',\
			'gender','physical_address','photo','user','national_id', 'city', 'region',\
			'address','postal_code','passport_number',)
	search_fields = ('user__username','user__first_name','user__last_name','national_id','city','physical_address','address',)
admin.site.register(Profile, ProfileAdmin)

class GatewayProfileAdmin(admin.ModelAdmin):
		list_display = ('id','user','gateway','pin','msisdn','status','access_level','institution',\
				'pin_retries','activation_code','device_id','activation_device_id',\
				'email_activation_code','allowed_host_list',)
		search_fields = ('id','msisdn__phone_number','user__username','user__first_name','user__last_name','user__email',)
		list_filter = ('gateway','status','access_level','institution','allowed_host',)
admin.site.register(GatewayProfile, GatewayProfileAdmin)

class GatewayProfileDeviceAdmin(admin.ModelAdmin):
		list_display = ('id','gateway_profile','channel','activation_code','device_id','activation_device_id',\
				'email_activation_code',)
		search_fields = ('gateway_profile__msisdn__phone_number','gateway_profile__user__username',\
				'gateway_profile__user__first_name','gateway_profile__user__last_name',\
				'gateway_profile__user__email',)
		list_filter = ('gateway_profile__gateway','gateway_profile__access_level','channel',)
admin.site.register(GatewayProfileDevice, GatewayProfileDeviceAdmin)

class ChangeProfileMSISDNStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(ChangeProfileMSISDNStatus, ChangeProfileMSISDNStatusAdmin)

class ChangeProfileMSISDNAdmin(admin.ModelAdmin):
		list_display = ('id','date_modified','date_created','gateway_profile','msisdn','expiry','change_pin','status',)
admin.site.register(ChangeProfileMSISDN, ChangeProfileMSISDNAdmin)

'''
class TillTypeStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(TillTypeStatus, TillTypeStatusAdmin)

class TillTypeAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','date_modified','date_created')
admin.site.register(TillType, TillTypeAdmin)

class InstitutionTillAdmin(admin.OSMGeoAdmin):
		list_display = ('id','name','institution','image','till_type','till_number','till_currency',\
				'description','qr_code','city','physical_address','is_default','geometry','details',)
		list_filter = ('till_type',)
admin.site.register(InstitutionTill, InstitutionTillAdmin)
'''

class PasswordStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(PasswordStatus, PasswordStatusAdmin)

class PasswordPolicyAdmin(admin.ModelAdmin):
		list_display = ('id','user','reset_key','old_password','status','date_modified','date_created')
admin.site.register(PasswordPolicy, PasswordPolicyAdmin)

class SessionStatusAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','date_modified','date_created')
admin.site.register(SessionStatus, SessionStatusAdmin)

class SessionAdmin(admin.ModelAdmin):
	list_display = ('id','session_id', 'channel','gateway_profile', 'reference','num_of_tries',\
			'num_of_sends','status')
	search_fields = ('gateway_profile__msisdn__phone_number','reference',)
	list_filter = ('channel',)
admin.site.register(Session, SessionAdmin)


