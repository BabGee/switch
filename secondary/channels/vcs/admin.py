from django.contrib import admin
from .models import *
from django.forms.widgets import TextInput, Textarea
from django import forms
'''
class MNOAdmin(admin.ModelAdmin):
	list_display = ('id','name','country','description',)
admin.site.register(MNO, MNOAdmin)

class MNOPrefixAdmin(admin.ModelAdmin):
	list_display = ('mno','prefix','description','date_modified','date_created',)
admin.site.register(MNOPrefix, MNOPrefixAdmin)
'''
class CodeTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created',)
admin.site.register(CodeType, CodeTypeAdmin)

class CodeAdmin(admin.ModelAdmin):
	list_display = ('id','code','mno','institution','channel','code_type','description','gateway','alias',)
	list_filter = ('institution','gateway','mno','channel','code_type',)
	search_fields = ('code','description',)
admin.site.register(Code, CodeAdmin)

class SessionStateAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','date_modified','date_created')
admin.site.register(SessionState, SessionStateAdmin)

class SessionHopAdmin(admin.ModelAdmin):
	list_display = ('id','session_id', 'channel','gateway_profile', 'reference','num_of_tries',\
			'num_of_sends','date_modified','date_created')
	search_fields = ('gateway_profile__msisdn__phone_number','reference',)
	list_filter = ('channel',)
admin.site.register(SessionHop, SessionHopAdmin)

class MenuStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created',)
admin.site.register(MenuStatus, MenuStatusAdmin)

class VariableTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'variable', 'date_modified', 'date_created',)
admin.site.register(VariableType, VariableTypeAdmin)
	
class InputVariableAdmin(admin.ModelAdmin):
	list_display = ('name', 'variable_type', 'validate_min', 'validate_max', 'allowed_input_list', 'override_group_select','error_group_select','override_level','error_level')
admin.site.register(InputVariable, InputVariableAdmin)

class MenuAdmin(admin.ModelAdmin):
	list_display = ('id','page_string', 'access_level_list', 'session_state', 'code_list','profile_status_list','service',\
			'submit', 'level', 'group_select', 'input_variable', 'selection_preview','menu_description',\
			'menu_status','protected','details','enrollment_type_included_list','enrollment_type_excluded_list',)
	list_filter = ('code', 'access_level', 'service', 'menu_status', 'code__institution','profile_status__name','code__gateway','protected',)
	search_fields = ('page_string','menu_description',)
admin.site.register(Menu, MenuAdmin)

class MenuItemAdmin(admin.ModelAdmin):
	list_display = ('menu_item', 'access_level_list', 'profile_status_list', 'item_level', 'menu', 'status','enrollment_type_included_list','enrollment_type_excluded_list',)
	list_filter = ('menu__code','menu', 'menu__service', 'status',)
admin.site.register(MenuItem, MenuItemAdmin)

class NavigatorAdmin(admin.ModelAdmin):
	list_display = ('date_created','date_modified','session_hop', 'menu', 'item_list', 'nav_step', 'input_select','code','pin_auth','session','level','group_select',)
	list_filter = ('menu__code','menu__code__institution','menu__code__mno','menu__code__channel','menu__code__code_type',)
	search_fields = ('menu__code__code','menu__page_string','item_list','nav_step','input_select','session__gateway_profile__msisdn__phone_number','session__reference',)
admin.site.register(Navigator, NavigatorAdmin)

