from django.contrib import admin
from crb.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms


class ReportSectorAdmin(admin.ModelAdmin):
	list_display = ('name','description','sector_code')
admin.site.register(ReportSector, ReportSectorAdmin)


class ReportReasonAdmin(admin.ModelAdmin):
	list_display = ('name','description','reason_code')
admin.site.register(ReportReason, ReportReasonAdmin)


class IdentificationAdmin(admin.ModelAdmin):
	list_display = ('name','description')
admin.site.register(Identification, IdentificationAdmin)


