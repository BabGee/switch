from django.contrib.gis import admin
from primary.core.administration.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms

class UserPasswordHistoryAdmin(admin.OSMGeoAdmin):
	list_display = ('id','date_modified','date_created','user','password',)
admin.site.register(UserPasswordHistory, UserPasswordHistoryAdmin)

'''
class CountryStatusAdmin(admin.OSMGeoAdmin):
	list_display = ('id','name','description')
admin.site.register(CountryStatus, CountryStatusAdmin)
'''
class CountryAdmin(admin.OSMGeoAdmin):
	list_display = ('name','area','pop2005','fips','iso2','iso3','un','region','subregion','lon','lat','ccode',)
        search_fields = ('name',)

admin.site.register(Country, CountryAdmin)

class CurrencyAdmin(admin.ModelAdmin):
	list_display = ('id','code', 'num','exponent', 'currency', 'date_modified', 'date_created')
	search_fields = ('currency','code',)
admin.site.register(Currency, CurrencyAdmin)

class LanguageAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','date_modified','date_created')
admin.site.register(Language, LanguageAdmin)

class IndustrySectionAdmin(admin.ModelAdmin):
	list_display = ('isic_code','description',)
	search_fields = ('isic_code','description',)
admin.site.register(IndustrySection, IndustrySectionAdmin)

class IndustryDivisionAdmin(admin.ModelAdmin):
	list_display = ('isic_code','description','section')
	search_fields = ('isic_code','description',)
admin.site.register(IndustryDivision, IndustryDivisionAdmin)

class IndustryGroupAdmin(admin.ModelAdmin):
	list_display = ('isic_code','description','division',)
	search_fields = ('isic_code','description',)
admin.site.register(IndustryGroup, IndustryGroupAdmin)

class IndustryClassAdmin(admin.ModelAdmin):
	list_display = ('isic_code','description','group',)
	search_fields = ('isic_code','description',)
admin.site.register(IndustryClass, IndustryClassAdmin)

class IndustryAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(Industry, IndustryAdmin)

class HostStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created')
admin.site.register(HostStatus, HostStatusAdmin)

class HostAdmin(admin.ModelAdmin):
	list_display = ('id', 'host', 'status', 'description', 'date_modified', 'date_created')
	search_fields = ('host',)
admin.site.register(Host, HostAdmin)

class StructureAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
admin.site.register(Structure, StructureAdmin)

class DesignSystemAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created')
admin.site.register(DesignSystem, DesignSystemAdmin)

class GatewayAdmin(admin.ModelAdmin):
	list_display = ('id','name', 'logo', 'description','background_image','default_color',\
			'default_host_list','theme','primary_color','secondary_color',\
			'accent_color','max_pin_retries','session_expiry','structure',)
admin.site.register(Gateway, GatewayAdmin)

class PasswordComplexityAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','regex','validation_response',)
admin.site.register(PasswordComplexity, PasswordComplexityAdmin)

class PasswordPolicyAdmin(admin.ModelAdmin):
	list_display = ('id','date_modified','date_created','gateway','password_complexity_list','old_password_count',\
			'min_characters','max_characters','expiration_days',)
admin.site.register(PasswordPolicy, PasswordPolicyAdmin)

class TemplateAdmin(admin.ModelAdmin):
	list_display = ('name', 'description','gateway',)
admin.site.register(Template, TemplateAdmin)

class AccessLevelStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created')
admin.site.register(AccessLevelStatus, AccessLevelStatusAdmin)

class AccessLevelAdmin(admin.ModelAdmin):
	list_display = ('id','name','status','description', 'hierarchy',)
admin.site.register(AccessLevel, AccessLevelAdmin)

class RoleAdmin(admin.ModelAdmin):
	list_display = ('id','name','status','description','access_level','gateway','session_expiry',)
admin.site.register(Role, RoleAdmin)

class ChannelAdmin(admin.ModelAdmin):
	list_display = ('id','name','description', 'date_modified', 'date_created')
admin.site.register(Channel, ChannelAdmin)

class GenderAdmin(admin.ModelAdmin):
	list_display = ('id','code','description', 'date_modified', 'date_created')
admin.site.register(Gender, GenderAdmin)

class UploadingAdmin(admin.ModelAdmin):
	list_display = ('name', 'processing_path', 'file_format', 'access_level','description','date_modified','date_created',)  
admin.site.register(Uploading, UploadingAdmin)


class AuditTrailsAdmin(admin.ModelAdmin):
	list_display = ('user','action','date_modified','date_created') 
admin.site.register(AuditTrails, AuditTrailsAdmin)

class ResponseStatusAdmin(admin.ModelAdmin):
		list_display = ('id','response','description','action',\
		 'action_description','date_modified','date_created')
		search_fields = ('response','description','action_description',)
admin.site.register(ResponseStatus, ResponseStatusAdmin)

class MNOAdmin(admin.ModelAdmin):
	list_display = ('id','name','country','description',)
admin.site.register(MNO, MNOAdmin)

class MNOPrefixAdmin(admin.ModelAdmin):
	list_display = ('mno','prefix','description','date_modified','date_created',)
admin.site.register(MNOPrefix, MNOPrefixAdmin)

class ForexAdmin(admin.ModelAdmin):
	list_display = ('base_currency','quote_currency','exchange_rate','trading_date','description',)
admin.site.register(Forex, ForexAdmin)

class IconGroupAdmin(admin.ModelAdmin):
	list_display = ('name', 'description',)
admin.site.register(IconGroup, IconGroupAdmin)


class IconAdmin(admin.ModelAdmin):
	list_display = ('icon', 'description','group',)
admin.site.register(Icon, IconAdmin)


