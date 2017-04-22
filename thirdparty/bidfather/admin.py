from django.contrib import admin
from thirdparty.bidfather.models import *


class BidStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description',)


admin.site.register(BidStatus, BidStatusAdmin)


class BidAdmin(admin.ModelAdmin):
    list_display = (
        'date_modified', 'date_created', 'institution', 'name', 'description', 'image', 'attachment', 'bid_min_points',
        'bid_max_points', 'bid_open', 'bid_close', 'industry_section', 'invoiced')


admin.site.register(Bid, BidAdmin)


class BidRequirementAdmin(admin.ModelAdmin):
    list_display = ('date_modified', 'date_created', 'name', 'description', 'bid', 'quantity', 'image', 'attachment',
                    'requirement_min_points', 'requirement_max_points',)


admin.site.register(BidRequirement, BidRequirementAdmin)


class BidApplicationAdmin(admin.ModelAdmin):
    list_display = ('date_modified', 'date_created', 'institution', 'bid', 'current_total_price','completed','status')


admin.site.register(BidApplication, BidApplicationAdmin)


class BidApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ('date_modified', 'date_created', 'name', 'description')


admin.site.register(BidApplicationStatus, BidApplicationStatusAdmin)


class BidRequirementApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'date_modified', 'date_created', 'bid_application', 'bid_requirement', 'description', 'attachment',
        'unit_price',)


admin.site.register(BidRequirementApplication, BidRequirementApplicationAdmin)

admin.site.register(BidApplicationChange)
admin.site.register(BidApplicationChangeType)


class BidDocumentAdmin(admin.ModelAdmin):
    list_display = ('name','bid','date_modified', 'date_created')

admin.site.register(BidDocument,BidDocumentAdmin)


class BidDocumentApplicationAdmin(admin.ModelAdmin):
    list_display = ('bid_document','attachment','bid_application','date_modified', 'date_created')

admin.site.register(BidDocumentApplication,BidDocumentApplicationAdmin)


class BidAmountActivityAdmin(admin.ModelAdmin):
    list_display = ('date_modified', 'date_created', 'application', 'price',)


admin.site.register(BidAmountActivity, BidAmountActivityAdmin)


class BidInvoiceTypeAdmin(admin.ModelAdmin):
    list_display = ('date_modified', 'date_created', 'name', 'description', 'invoicing_rate', 'product_item',)


admin.site.register(BidInvoiceType, BidInvoiceTypeAdmin)


class BidInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'date_modified', 'date_created', 'bid_invoice_type', 'bid', 'max_price', 'min_price', 'amount', 'processed',)


admin.site.register(BidInvoice, BidInvoiceAdmin)

class BidNotificationTypeStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(BidNotificationTypeStatus, BidNotificationTypeStatusAdmin)

class BidNotificationTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'status', 'notification_details', 'service', 'product_item',)
admin.site.register(BidNotificationType, BidNotificationTypeAdmin)

class BidNotificationStatusAdmin(admin.ModelAdmin):
	list_display = ('name', 'description',)
admin.site.register(BidNotificationStatus, BidNotificationStatusAdmin)

class BidNotificationAdmin(admin.ModelAdmin):
	list_display = ('date_modified', 'date_created', 'bid', 'status','notification_details',)
admin.site.register(BidNotification, BidNotificationAdmin)



