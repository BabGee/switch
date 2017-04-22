from django.conf.urls import *
from django.contrib import admin
admin.autodiscover()
from notify import views as notify_views


urlpatterns = [
	url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
	url(r'^admin/', include(admin.site.urls)),
	url(r'^administration/', include('administration.urls')),
	url(r'^api/', include('api.urls')),
	url(r'^auth/user',     notify_views.user),
	url(r'^auth/vhost',    notify_views.vhost),
	url(r'^auth/resource', notify_views.resource),
	#url(r'^bidfather/', include('thirdparty.bidfather.urls'), name='bidfather'),

	]

