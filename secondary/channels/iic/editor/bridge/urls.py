from django.conf.urls import *

from .views import gateway_service
from secondary.channels.iic.editor.iic.views import interface
from secondary.channels.iic.editor.notify.views import service_notification

name = 'bridge'

urlpatterns = [
    url(r'^$', gateway_service),  # todo detail view
    url(r'^interface/', include([
        url(r'^$', interface),
        # url(r'^create/$', page_group_create),
        url(r'^(?P<page_group_pk>\d+)/', include([
            url(r'^$', interface),
            url(r'^(?P<page_pk>\d+)/', include([
                url(r'^$', interface),
                url(r'^(?P<page_input_group_pk>\d+)/', include([
                    url(r'^$', interface),
                ])),
            ])),
        ])),
    ])),
    url(r'^page_groups/', include('secondary.channels.iic.editor.iic.urls')),
    url(r'^notify/', include([
        url(r'^$', service_notification),
        # url(r'^create/$', page_group_create),

    ])),
]
