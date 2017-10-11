from django.contrib import admin
from thirdparty.amkagroup_co_ke.models import *


class InvestmentTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','value','limit_review_rate','product_item',)
admin.site.register(InvestmentType, InvestmentTypeAdmin)

class InvestmentAdmin(admin.ModelAdmin):
	list_display = ('id','investment_type','account','amount','pie','balance_bf','processed',)
	list_filter = ('investment_type',)
	search_fields = ('account__gateway_profile__msisdn__phone_number',)
admin.site.register(Investment, InvestmentAdmin)


