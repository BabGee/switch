from django.conf.urls import *


name = 'bridge'

urlpatterns = [
    url(r'^page_groups/', include('secondary.channels.iiceditor.iic.urls')),
]
