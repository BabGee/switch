from django.contrib import admin
from pos.models import *

class SaleContactTypeAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','institution')
admin.site.register(SaleContactType, SaleContactTypeAdmin)

class SaleContactAdmin(admin.ModelAdmin):
	list_display = ('name','description','sale_contact_type','location',\
		'geometry','sale_contact_number','institution',\
		'primary_contact_profile','comment','details')
admin.site.register(SaleContact, SaleContactAdmin)

class SaleChargeTypeAdmin(admin.ModelAdmin):
	list_display = ('name','description','product_item')
admin.site.register(SaleChargeType, SaleChargeTypeAdmin)

class SaleChargeAdmin(admin.ModelAdmin):
	list_display = ('sale_charge_type','credit','expiry','min_amount','max_amount','charge_value','is_percentage','description',\
				'payment_method_list','product_type_list','institution_list','gateway_list')

admin.site.register(SaleCharge, SaleChargeAdmin)

class CartStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(CartStatus, CartStatusAdmin)

class CartItemAdmin(admin.ModelAdmin):
		list_display = ('id','product_item','gateway_profile',\
				'currency','status','quantity','expiry','price',\
				'sub_total','vat','other_tax','discount','other_relief',\
				'total','details','till','token','channel',)
		list_filter = ('product_item__institution','gateway_profile__gateway','product_item__product_type',)
		search_fields = ('gateway_profile__msisdn__phone_number','product_item__name','details','quantity','price','sub_total','total','token')
admin.site.register(CartItem, CartItemAdmin)

class OrderStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')
admin.site.register(OrderStatus, OrderStatusAdmin)

class PurchaseOrderAdmin(admin.ModelAdmin):
		list_display = ('id','cart_item_list','reference','amount', 'currency',\
				 'description','status','expiry','cart_processed',\
				 'gateway_profile','date_created')
		list_filter = ('status__name','currency','cart_item__product_item__institution','cart_processed','gateway_profile__gateway','cart_item__product_item__product_type',)
		search_fields = ('gateway_profile__msisdn__phone_number','cart_item__product_item__name','reference',)
admin.site.register(PurchaseOrder, PurchaseOrderAdmin)

class BillManagerAdmin(admin.ModelAdmin):
		list_display = ('id','credit','transaction_reference','action_reference',\
				'order','amount','balance_bf','payment_method','date_modified','date_created',)
		search_fields = ('order__gateway_profile__msisdn__phone_number','order__cart_item__product_item__name','order__reference',)
		list_filter = ('order__cart_item__product_item__institution','order__cart_item__product_item__product_type',)
admin.site.register(BillManager, BillManagerAdmin)

