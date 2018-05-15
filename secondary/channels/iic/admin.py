from django.contrib import admin
from secondary.channels.iic.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms

class VariableTypeAdmin(admin.ModelAdmin):
		list_display = ('name','variable','description','date_modified','date_created')
	        search_fields = ('name','variable','description',)

admin.site.register(VariableType, VariableTypeAdmin)
		
class InputVariableAdmin(admin.ModelAdmin):
		list_display = ('id','name','variable_type','validate_min','validate_max','required',\
		 'default_value','variable_kind','description','service','details')
	        list_filter = ('variable_type__variable','service')
	        search_fields = ('id','name','default_value')

admin.site.register(InputVariable, InputVariableAdmin)

class PageGroupAdmin(admin.ModelAdmin):
		list_display = ('name','item_level','description','icon','gateway_list')
	        search_fields = ('name','description')

admin.site.register(PageGroup, PageGroupAdmin)

class PageAdmin(admin.ModelAdmin):
		list_display = ('id', 'name','description','icon','item_level','access_level_list','profile_status_list','page_group',\
		'gateway_list','service_list',)
	        search_fields = ('name',)
	        list_filter = ('service','page_group','access_level','gateway',)

admin.site.register(Page, PageAdmin)

class RoleActionAdmin(admin.ModelAdmin):
		list_display = ('id','name','description',)
admin.site.register(RoleAction, RoleActionAdmin)

class RoleRightAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','page_list',)
admin.site.register(RoleRight, RoleRightAdmin)

class RolePermissionAdmin(admin.ModelAdmin):
		list_display = ('id','role','role_right','role_action_list',)
admin.site.register(RolePermission, RolePermissionAdmin)

class PageInputStatusAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(PageInputStatus, PageInputStatusAdmin)

class BindPositionAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(BindPosition, BindPositionAdmin)

class PageInputGroupAdmin(admin.ModelAdmin):
		list_display = ('id','name','icon_old','description','item_level','input_variable','style','section_size',\
				'section_height','auto_submit','icon','bind_position','gateway_list',)
	        search_fields = ('name','input_variable__name',)
		list_filter = ('input_variable__service',)
admin.site.register(PageInputGroup, PageInputGroupAdmin)
'''
class TriggerAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
	        search_fields = ('name','description')

admin.site.register(Trigger, TriggerAdmin)
'''
class PageInputAdmin(admin.ModelAdmin):
		list_display = ('id','page_input','icon','section_size','item_level',\
				'trigger_list','access_level_list','profile_status_list',\
				'institution_list','input_variable','page_input_group', 'page_input_status','page',\
				'gateway_list','product_type_list','channel_list','style','section_height','bind_position',\
				'payment_method_list','enrollment_type_included_list','enrollment_type_excluded_list','role_action_list',)
	        list_filter = ('page_input_group','page','channel','institution','gateway','payment_method','page__service','role_action',)
	        search_fields = ('id','page_input','input_variable__name','trigger__name')

admin.site.register(PageInput, PageInputAdmin)

