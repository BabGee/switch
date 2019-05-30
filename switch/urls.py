from django.conf.urls import *
from django.contrib import admin
admin.autodiscover()
from secondary.channels.notify import views as notify_views
from primary.core.api import views as api_views
from secondary.channels import iic

#url(r'^admin/doc/', django.contrib.admindocs.urls),
urlpatterns = [
	url(r'^admin/', admin.site.urls),
	url(r'^api/(?P<SERVICE>[\w\-\ ]{1,50})/$',  api_views.Interface().interface),
	url(r'^api/',  api_views.default),
	#url(r'^api/', include(api.urls)),
	url(r'^auth/user',     notify_views.user),
	url(r'^auth/vhost',    notify_views.vhost),
	url(r'^auth/resource', notify_views.resource),
	#url(r'^iic_editor/', include(iic.editor.urls),name='editor'),

	]
