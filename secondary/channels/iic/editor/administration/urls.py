from django.conf.urls import url,include
from .views import gateway_detail,gateway_list,role_list


urlpatterns = [
    url(r'^$', gateway_list),
    url(r'^(?P<gateway_pk>\d+)/', include([
        url(r'^$', gateway_detail),
        url(r'^gateway_profiles/', include('secondary.channels.iic.editor.upc.urls.gateway_profile')),
        url(r'^institutions/', include('secondary.channels.iic.editor.upc.urls.institution')),
        url(r'^roles/', role_list),
        url(r'^vcs/', include('secondary.channels.iic.editor.vcs.urls')),
        url(r'^(?P<service_name>[\w\ ]+)/', include('secondary.channels.iic.editor.bridge.urls')),
    ]
    )),

]