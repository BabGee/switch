from django.contrib import admin
from iic.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms

class VariableTypeAdmin(admin.ModelAdmin):
		list_display = ('name','variable','description','date_modified','date_created')
	        search_fields = ('name','variable','description',)

admin.site.register(VariableType, VariableTypeAdmin)
		
class InputVariableAdmin(admin.ModelAdmin):
		list_display = ('id','name','variable_type','validate_min','validate_max',\
		 'default_value','variable_kind','description')
	        list_filter = ('variable_type__variable',)
	        search_fields = ('id','name','default_value')

admin.site.register(InputVariable, InputVariableAdmin)

class PageGroupAdmin(admin.ModelAdmin):
		list_display = ('name','item_level','description','icon','gateway_list')
	        search_fields = ('name','description')

admin.site.register(PageGroup, PageGroupAdmin)

class PageAdmin(admin.ModelAdmin):
		list_display = ('id', 'name','description','icon','item_level','access_level_list','page_group',\
		'gateway_list','service_list',)
	        search_fields = ('name',)
	        list_filter = ('service','page_group','access_level')

admin.site.register(Page, PageAdmin)

class PageInputStatusAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
admin.site.register(PageInputStatus, PageInputStatusAdmin)

class PageInputGroupAdmin(admin.ModelAdmin):
		list_display = ('id','name','icon','description','item_level','input_variable','section','section_size',\
				'section_height','auto_submit','gateway_list',)
	        search_fields = ('name',)
admin.site.register(PageInputGroup, PageInputGroupAdmin)

class TriggerAdmin(admin.ModelAdmin):
		list_display = ('name','description','date_modified','date_created',)
	        search_fields = ('name','description')

admin.site.register(Trigger, TriggerAdmin)

class PageInputAdmin(admin.ModelAdmin):
		list_display = ('id','page_input','icon','section_size','item_level','trigger_list',\
				'access_level_list',\
		'institution_list','input_variable','page_input_group', 'page_input_status','page',\
		'gateway_list','channel_list','payment_method_list',)
	        list_filter = ('page_input_group','page','channel','institution','gateway','payment_method')
	        search_fields = ('id','page_input','input_variable__name')

admin.site.register(PageInput, PageInputAdmin)

