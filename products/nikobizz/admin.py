from django.contrib import admin
from products.nikobizz.models import *


class SubdomainStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description',)
admin.site.register(SubdomainStatus, SubdomainStatusAdmin)

class SubdomainAdmin(admin.ModelAdmin):
    list_display = ('subdomain', 'institution','status','ssl_certificate','ssl_certificate_key','ssl_certificate_ca')
admin.site.register(Subdomain, SubdomainAdmin)

