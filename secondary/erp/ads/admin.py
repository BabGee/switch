from django.contrib import admin
from secondary.erp.ads.models import *

# Register your models here.

class InstitutionAdAdmin(admin.ModelAdmin):
		list_display = ('name','collector','image','description','country','date_modified','date_created',)
admin.site.register(InstitutionAd, InstitutionAdAdmin)


