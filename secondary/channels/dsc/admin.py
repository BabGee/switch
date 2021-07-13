from django.contrib import admin
from secondary.channels.dsc.models import *

class DataListStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created')
admin.site.register(DataListStatus, DataListStatusAdmin)

class DataListGroupAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
admin.site.register(DataListGroup, DataListGroupAdmin)

class DataListQueryAdmin(admin.ModelAdmin):
	list_display = ('id','name', 'description', 'model_name', 'module_name','values','date_values','date_time_values',\
			'month_year_values','avg_values','sum_values','count_values','custom_values','or_filters','and_filters',\
			'not_filters','institution_filters','gateway_filters','gateway_profile_filters','profile_filters','role_filters',\
			'list_filters','duration_days_filters','date_time_filters','date_filters','duration_seconds_filters',\
			'duration_hours_filters','token_filters','links','link_params','last_balance','order','distinct','limit',)
	search_fields = ('name','description','model_name','module_name','values','or_filters','and_filters','not_filters',)
admin.site.register(DataListQuery, DataListQueryAdmin)

class DataListCaseQueryAdmin(admin.ModelAdmin):
        list_display = ('query','case_name','case_values','case_default_value','case_inactive',)
admin.site.register(DataListCaseQuery, DataListCaseQueryAdmin)

class DataListLinkQueryAdmin(admin.ModelAdmin):
        list_display = ('query','link_name','link_service','link_icon','link_case_filter',\
			'link_params','link_inactive','access_level_list',\
			'institution_list','channel_list','gateway_list','role_list',)
admin.site.register(DataListLinkQuery, DataListLinkQueryAdmin)

class DataListJoinQueryAdmin(admin.ModelAdmin):
	list_display = ('query','join_model_name','join_module_name',\
			'join_or_filters','join_and_filters','join_not_filters',\
			'join_institution_filters','join_gateway_filters','join_gateway_profile_filters','join_profile_filters',\
			'join_role_filters','join_duration_days_filters',\
			'join_fields','join_manytomany_fields','join_not_fields','join_manytomany_not_fields','join_case_fields','join_inactive',)
	search_fields = ('name','description','model_name','module_name',)
admin.site.register(DataListJoinQuery, DataListJoinQueryAdmin)

class PushActionAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
admin.site.register(PushAction, PushActionAdmin)

class DataResponseTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
admin.site.register(DataResponseType, DataResponseTypeAdmin)

class DataListAdmin(admin.ModelAdmin):
	list_display = ('data_name','url','content','status','is_report','group','level','node_system','command_function',\
			'title','query','pn_data','pn_id_field','pn_update_field','data_response_type',\
			'ifnull_response','indexing','push_service','pn_action_list','access_level_list',\
			'institution_list','channel_list','gateway_list',)
	search_fields = ('data_name','group__name',)
admin.site.register(DataList, DataListAdmin)

class FileUploadAdmin(admin.ModelAdmin):
	list_display = ('id','institution_list','gateway_list','access_level_list','trigger_service_list',\
			'activity_service',)
admin.site.register(FileUpload, FileUploadAdmin)

class FileUploadActivityStatusStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created')
admin.site.register(FileUploadActivityStatus, FileUploadActivityStatusStatusAdmin)

class FileUploadActivityAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','file_path','file_upload','processed_file_path',\
			'status','gateway_profile','details','channel','date_created',)
admin.site.register(FileUploadActivity, FileUploadActivityAdmin)

class ImageListTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
admin.site.register(ImageListType, ImageListTypeAdmin)

class ImageListAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'image','description', 'image_list_type',\
			 'level', 'access_level_list', 'institution_list','gateway_list',)
	list_filter = ('image_list_type', 'access_level', 'institution', 'gateway',)
admin.site.register(ImageList, ImageListAdmin)

