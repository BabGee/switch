from django.contrib import admin
from secondary.finance.crb.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class ReportSectorAdmin(admin.ModelAdmin):
	list_display = ('name','description','sector_code')
admin.site.register(ReportSector, ReportSectorAdmin)

class ReportReasonAdmin(admin.ModelAdmin):
	list_display = ('name','description','reason_code')
admin.site.register(ReportReason, ReportReasonAdmin)

class CreditGradeAdmin(admin.ModelAdmin):
	list_display = ('code','name','description','min_credit_score','max_credit_score','hierarchy',)
admin.site.register(CreditGrade, CreditGradeAdmin)

class IdentificationProfileAdmin(admin.ModelAdmin):
	list_display = ('id','national_id','first_name','middle_name','last_name')
admin.site.register(IdentificationProfile, IdentificationProfileAdmin)

class ReferenceAccountStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description','defaulted',)
admin.site.register(ReferenceAccountStatus, ReferenceAccountStatusAdmin)

class ReferenceAdmin(admin.ModelAdmin):
	list_display = ('identification_profile',\
	'surname','forename_1','forename_2','forename_3','salutation',\
	'date_of_birth','client_number','account_number','gender',\
	'nationality','marital_status','credit_grade','credit_probability',\
	'credit_score','credit_account_list','credit_account_summary',)
	search_fields = ('identification_profile__national_id',)

admin.site.register(Reference, ReferenceAdmin)

class ReferenceActivityTypeAdmin(admin.ModelAdmin):
	list_display= ('name','description','service','product_item','report_sector','report_reason','details',)
admin.site.register(ReferenceActivityType, ReferenceActivityTypeAdmin)

class ReferenceActivityAdmin(admin.ModelAdmin):
	list_display = ('gateway_profile','identification_profile','reference_activity_type',\
			'status','response_status','request','channel','transaction_reference',\
			'gateway','institution')
	list_filter = ('status','response_status','channel','gateway','institution',)
admin.site.register(ReferenceActivity, ReferenceActivityAdmin)

class ReferenceRiskAdmin(admin.ModelAdmin):
	list_display = ('gateway','institution','min_credit_grade','min_credit_probability',\
			'min_credit_score','base_initial_credit_limit','lend_to_defaulters',)
	list_filter = ('gateway','institution',)
admin.site.register(ReferenceRisk, ReferenceRiskAdmin)

