from django.conf.urls import url, include
from secondary.channels.iic.editor.upc.views import (
    gateway_profile_list,
    gateway_profile_list_export
)

urlpatterns = [
    url(r'^$', gateway_profile_list),
    url(r'^export$', gateway_profile_list_export),

]
