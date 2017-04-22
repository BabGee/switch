from django.contrib.gis import admin
from muziqbit.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms

class GenreAdmin(admin.ModelAdmin):
	list_display = ('id','name','description')
admin.site.register(Genre, GenreAdmin)

class MusicAdmin(admin.ModelAdmin):
	list_display = ('product_item','artiste','album','genre','release_date',\
			'file_path','stream_start','stream_duration','enrollment_list')
	list_filter = ('product_item__institution','product_item__product_type','genre',)
	search_fields = ('product_item__name','artiste')
admin.site.register(Music, MusicAdmin)

class DownloadTypeAdmin(admin.ModelAdmin):
	list_display = ('name','service','description')
admin.site.register(DownloadType, DownloadTypeAdmin)

class DownloadAdmin(admin.ModelAdmin):
	list_display = ('music','download_type','gateway_profile','transaction_reference')
admin.site.register(Download, DownloadAdmin)

