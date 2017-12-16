from django.conf.urls import *
from .views import *

page_paterns = [
    url(r'^$', page_list),
    url(r'^order/$', page_order),
    url(r'^(?P<page_pk>\d+)/', include([
        url(r'^$', page_detail),
        url(r'^copy/$', page_copy),

        url(r'^page_input_groups/', include([
            url(r'^$', page_input_group_list),
            url(r'^(?P<page_input_group_pk>\d+)/', include([
                url(r'^$', page_input_group_detail),
                url(r'^page_inputs/', include([
                    url(r'^$', page_input_list),
                    url(r'^order/$', page_input_order),
                    url(r'^create/$', page_input_create),
                    url(r'^(?P<page_input_pk>\d+)/', include([
                        url(r'^$', page_input_detail),
                        url(r'^copy/$', page_input_copy),
                    ])),
                ])),
            ])),
        ])),
    ])),
]

urlpatterns = [
    url(r'gateways/', include([

        url(r'^$', gateway_list),
        url(r'^(?P<gateway_pk>\d+)/', include([
            url(r'^$', gateway_detail),
            url(r'^page_groups/', include([
                url(r'^$', page_group_list),
                url(r'^(?P<page_group_pk>\d+)/', include([
                    url(r'^$', page_group_detail),
                    url(r'^pages/', include(page_paterns)),
                ])),
            ]))
        ]
        )),
        # url(r'create/', views.events_create, name='create')

    ]), name='gateways')
]
