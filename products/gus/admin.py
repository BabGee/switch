from django.contrib import admin
from products.gus.models import *

class URLTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','location','updated','max_visits')
admin.site.register(URLType, URLTypeAdmin)

class ShortenerStatusAdmin(admin.ModelAdmin):
	list_display = ('id','name','description')
admin.site.register(ShortenerStatus, ShortenerStatusAdmin)

class ShortenerAdmin(admin.ModelAdmin):
	list_display = ('base','url','url_type','expiry','visits','updated','name',\
			'status','gateway_profile')
admin.site.register(Shortener, ShortenerAdmin)




