from django.contrib import admin
from thirdparty.mcsk.models import *

class MemberAdmin(admin.ModelAdmin):
		list_display = ('id','enrollment','full_names','address','town','email',\
				'member_number','phone_number','alt_phone_number',\
				'bank_name','bank_branch','bank_account_no','ipi_number',\
				'details')
		search_fields = ('member_number',)
admin.site.register(Member, MemberAdmin)

class BeneficiaryAdmin(admin.ModelAdmin):
		list_display = ('id','member','full_names','passport_id_no')
admin.site.register(Beneficiary, BeneficiaryAdmin)

class CodeRequestTypeAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(CodeRequestType, CodeRequestTypeAdmin)

class RegionAdmin(admin.ModelAdmin):
	list_display = ('id','name','description')
admin.site.register(Region, RegionAdmin)

class CodeRequestAdmin(admin.ModelAdmin):
		list_display = ('id','request_type','gateway_profile','full_names','phone_number',\
				'passport_id_no',\
				'code_allocation','code_preview','details_match','approved', 'region')
		search_fields = ('code_allocation','code_preview','phone_number','gateway_profile__msisdn__phone_number','full_names',)
		list_filter = ('region',)
admin.site.register(CodeRequest, CodeRequestAdmin)


