from django.contrib import admin
from survey.models import *

class SurveyStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(SurveyStatus, SurveyStatusAdmin)

class SurveyGroupAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','data_name')
admin.site.register(SurveyGroup, SurveyGroupAdmin)

class SurveyAdmin(admin.ModelAdmin):
		list_display = ('id','name','group','description','institution_list','product_type','status','product_item')
admin.site.register(Survey, SurveyAdmin)

class SurveyItemStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(SurveyItemStatus, SurveyItemStatusAdmin)

class SurveyItemAdmin(admin.ModelAdmin):
	list_display = ('name','description','survey','status','expiry','code')
	search_fields = ('name','description','survey__name','code',)
admin.site.register(SurveyItem, SurveyItemAdmin)

class SurveyResponseStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(SurveyResponseStatus, SurveyResponseStatusAdmin)

class SurveyResponseAdmin(admin.ModelAdmin):
		list_display = ('item','status','transaction_reference', 'gateway_profile',)
		list_filter = ('status',)
		search_fields = ('item__name','item__code',)
admin.site.register(SurveyResponse, SurveyResponseAdmin)


