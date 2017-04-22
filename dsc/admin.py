from django.contrib import admin
from dsc.models import *


class DataListStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'date_modified', 'date_created')
admin.site.register(DataListStatus, DataListStatusAdmin)

class DataListGroupAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
admin.site.register(DataListGroup, DataListGroupAdmin)

class DataListQueryAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'model_name', 'values', 'or_filters','and_filters','module_name',\
			'institution_filters','gateway_filters','order','count','filters',)
admin.site.register(DataListQuery, DataListQueryAdmin)

class DataListAdmin(admin.ModelAdmin):
	list_display = ('data_name','url','content','status','is_report','group','level','function',\
			'title','query','access_level_list','institution_list','channel_list','gateway_list')
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
			'status','gateway_profile','details','channel',)
admin.site.register(FileUploadActivity, FileUploadActivityAdmin)

