from django.conf.urls import *
from primary.core.api.views import *

urlpatterns = [
	url(r'^(?P<SERVICE>[\w\ ]{1,45})/$',  Interface().interface),
	url(r'',  default),
		]



