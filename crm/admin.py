from django.contrib import admin
from crm.models import *

class MetricAdmin(admin.ModelAdmin):
		list_display = ('id','name','si_unit','description')
admin.site.register(Metric, MetricAdmin)

class ProductStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(ProductStatus, ProductStatusAdmin)

class ProductCategoryAdmin(admin.ModelAdmin):
		list_display = ('id','name','industry','description','status','icon',)
admin.site.register(ProductCategory, ProductCategoryAdmin)

class ProductionFrequencyAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','date_modified','date_created')
admin.site.register(ProductionFrequency, ProductionFrequencyAdmin)

class ProductTypeAdmin(admin.ModelAdmin):
		list_display = ('id','name','product_category','metric','description', 'status','service','institution_till','payment_method_list')
admin.site.register(ProductType, ProductTypeAdmin)

class ProductChargeAdmin(admin.ModelAdmin):
		list_display = ('id','institution_list','product_type_list',\
				'credit','till_list','expiry','min_amount','max_amount','currency',\
				'charge_value','is_percentage','description','for_float','payment_method_list',)
admin.site.register(ProductCharge, ProductChargeAdmin)

class ProductDiscountAdmin(admin.ModelAdmin):
		list_display = ('institution_list','coupon','product_type_list',\
				'credit','till_list','expiry','min_amount','max_amount','currency',\
				'charge_value','is_percentage','description','for_float')
admin.site.register(ProductDiscount, ProductDiscountAdmin)

class ProductItemAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','product_type',\
				'institution_till_list','unit_limit_min',\
				'unit_limit_max','unit_cost','variable_unit','float_limit_min',\
				'float_limit_max','float_cost','institution','currency',\
				'vat','discount','institution_url','institution_username',\
				'institution_password','image_path')
		search_fields = ("id","name","description")
	        list_filter = ('institution_till','institution','product_type','product_type__product_category')

admin.site.register(ProductItem, ProductItemAdmin)

class ItemExtraAdmin(admin.ModelAdmin):
		list_display = ('product_item','product_source_capacity_min','product_source_capacity_max',\
				'default_image','product_path',\
				'product_url','condition','feature','manufacturer',\
				'manufactured','product_owner','details')
admin.site.register(ItemExtra, ItemExtraAdmin)

class EnrollmentTypeAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','institution','product_item')
admin.site.register(EnrollmentType, EnrollmentTypeAdmin)


class EnrollmentStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(EnrollmentStatus, EnrollmentStatusAdmin)

class EnrollmentAdmin(admin.ModelAdmin):
		list_display = ('id','record', 'alias','status','enrollment_date','gateway_profile','enrollment_type')
		search_fields = ("alias",'record','gateway_profile__user__username',\
				'gateway_profile__user__first_name','gateway_profile__user__last_name',\
				'gateway_profile__msisdn__phone_number',)
		list_filter = ('enrollment_type__institution',)
admin.site.register(Enrollment, EnrollmentAdmin)

class NominationStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(NominationStatus, NominationStatusAdmin)

class NominationAdmin(admin.ModelAdmin):
		list_display = ('id','profile', 'account_alias', 'account_record',\
				'institution','product_type','status')
admin.site.register(Nomination, NominationAdmin)

class RecurrentServiceStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(RecurrentServiceStatus, RecurrentServiceStatusAdmin)

class RecurrentServiceAdmin(admin.ModelAdmin):
		list_display = ('nomination','enrollment','currency','amount','request','service',\
				'request_auth','scheduled_send','scheduled_days','expiry',\
				'status')
admin.site.register(RecurrentService, RecurrentServiceAdmin)


