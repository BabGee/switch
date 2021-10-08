from django.contrib import admin
from secondary.erp.crm.models import *

class MetricAdmin(admin.ModelAdmin):
		list_display = ('id','name','si_unit','description')
admin.site.register(Metric, MetricAdmin)

class ProductStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(ProductStatus, ProductStatusAdmin)

class ProductCategoryAdmin(admin.ModelAdmin):
		list_display = ('id','name','industry','description','status','icon',)
admin.site.register(ProductCategory, ProductCategoryAdmin)

class ShopProductCategoryAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','icon',)
admin.site.register(ShopProductCategory, ShopProductCategoryAdmin)

class ProductionFrequencyAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','date_modified','date_created')
admin.site.register(ProductionFrequency, ProductionFrequencyAdmin)

class ProductTypeAdmin(admin.ModelAdmin):
		list_display = ('id','name','product_category','metric','description',\
				'status','service','settlement_service','payment_method_list')
		search_fields = ('name','description',)
		list_filter = ('product_category','metric','payment_method',)
admin.site.register(ProductType, ProductTypeAdmin)

class ShopProductTypeAdmin(admin.ModelAdmin):
		list_display = ('id','name','shop_product_category','description',\
				'status','icon','institution',)
		search_fields = ('name','description',)
		list_filter = ('shop_product_category',)
admin.site.register(ShopProductType, ShopProductTypeAdmin)

class ProductChargeAdmin(admin.ModelAdmin):
		list_display = ('id','institution_list','product_type_list',\
				'credit','expiry','min_amount','max_amount','currency',\
				'charge_value','is_percentage','description','for_float','payment_method_list',)
admin.site.register(ProductCharge, ProductChargeAdmin)

class ProductDiscountAdmin(admin.ModelAdmin):
		list_display = ('institution_list','coupon','product_type_list',\
				'credit','expiry','min_amount','max_amount','currency',\
				'charge_value','is_percentage','description','for_float')
admin.site.register(ProductDiscount, ProductDiscountAdmin)

class ProductDisplayAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(ProductDisplay, ProductDisplayAdmin)


class ProductItemAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','status','product_type',\
				'unit_limit_min',\
				'unit_limit_max','unit_cost','variable_unit','float_limit_min',\
				'float_limit_max','float_cost','institution','currency',\
				'vat','discount','institution_url','institution_username',\
				'institution_password','default_image','product_display','uneditable',\
				'kind','default_product','buying_cost','shop_product_type',\
				'barcode',)
		search_fields = ("id","name","description")
		list_filter = ('institution','product_type','product_type__product_category')

admin.site.register(ProductItem, ProductItemAdmin)

class ProductImageAdmin(admin.ModelAdmin):
		list_display = ('id','product_item','image','name','description','default')
admin.site.register(ProductImage, ProductImageAdmin)


class ItemExtraAdmin(admin.ModelAdmin):
		list_display = ('product_item','product_source_capacity_min','product_source_capacity_max',\
				'default_image','product_path',\
				'product_url','condition','feature','manufacturer',\
				'manufactured','product_owner','details')
admin.site.register(ItemExtra, ItemExtraAdmin)

class EnrollmentTypeAdmin(admin.ModelAdmin):
		list_display = ('id', 'name', 'description','product_item')
admin.site.register(EnrollmentType, EnrollmentTypeAdmin)


class EnrollmentStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(EnrollmentStatus, EnrollmentStatusAdmin)

class EnrollmentAdmin(admin.ModelAdmin):
		list_display = ('id','record', 'alias','status','enrollment_date','enrollment_type','profile','expiry','updated',)
		search_fields = ("alias",'record','profile__user__username','profile__middle_name',\
				'profile__user__first_name','profile__user__last_name',)
		list_filter = ('enrollment_type',)
admin.site.register(Enrollment, EnrollmentAdmin)

class PaymentOptionStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(PaymentOptionStatus, PaymentOptionStatusAdmin)

class PaymentOptionAdmin(admin.ModelAdmin):
		list_display = ('id','account_alias', 'account_record',\
				'status','payment_method','profile',)
admin.site.register(PaymentOption, PaymentOptionAdmin)


class NominationStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(NominationStatus, NominationStatusAdmin)

class NominationAdmin(admin.ModelAdmin):
		list_display = ('id','gateway_profile', 'account_alias', 'account_record',\
				'currency', 'amount','request',\
				'product_item','status')
admin.site.register(Nomination, NominationAdmin)

class RecurrentServiceStatusAdmin(admin.ModelAdmin):
		list_display = ('name', 'description','date_modified','date_created')
admin.site.register(RecurrentServiceStatus, RecurrentServiceStatusAdmin)

class RecurrentServiceAdmin(admin.ModelAdmin):
		list_display = ('nomination','service',\
				'request_auth','scheduled_send','scheduled_days','expiry',\
				'status')
admin.site.register(RecurrentService, RecurrentServiceAdmin)

class AgentStatusAdmin(admin.ModelAdmin):
	list_display = ('id','name','description',)
admin.site.register(AgentStatus, AgentStatusAdmin)

class AgentAdmin(admin.ModelAdmin):
	list_display = ('id','profile','status','registrar','enrollment')
	list_filter = ('status',)
	search_fields = ('profile__user__username','profile__user__first_name','profile__user__last_name','profile__national_id',)
admin.site.register(Agent, AgentAdmin)

class AgentInstitutionTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','name',)
admin.site.register(AgentInstitutionType, AgentInstitutionTypeAdmin)


class AgentInstitutionAdmin(admin.ModelAdmin):
	list_display = ('id','institution','agent','institution_type')
admin.site.register(AgentInstitution, AgentInstitutionAdmin)

