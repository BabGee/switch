from django.contrib import admin

from django.conf.urls import include, url

from django.db import models

from .views import gateway_list, gateway_detail

# IIC editor model
class IICEditor(models.Model):
 
	class Meta:
		verbose_name_plural = 'IIC Editor'
		app_label = 'iiceditor'


class IICEditorAdmin(admin.ModelAdmin):
	model = IICEditor
 
	def get_urls(self):
		view_name = f'{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'
		return [
			url(r'^$', gateway_list, name=view_name),
            url(r'^(?P<gateway_pk>\d+)/', include([
                url(r'^$', gateway_detail),
                url(r'^(?P<service_name>[\w\ ]+)/', include('secondary.channels.iiceditor.bridge.urls')),
                ]
                )),
		]

admin.site.register(IICEditor, IICEditorAdmin)