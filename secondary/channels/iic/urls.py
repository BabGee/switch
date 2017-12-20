from django.conf.urls import *
from .views import *

page_paterns = [
    url(r'^$', page_list),
    url(r'^order/$', page_order),
    url(r'^create/$', page_create),
    url(r'^(?P<page_pk>\d+)/', include([
        url(r'^$', page_detail),
        url(r'^copy/$', page_copy),

        url(r'^page_input_groups/', include([
            url(r'^$', page_input_group_list),
            # todo url(r'^order/$', page_input_group_order),
            url(r'^create/$', page_input_group_create),

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
            ])),
            url(r'^gateway_profiles/', include([
                url(r'^$', gateway_profile_list),
                # url(r'^(?P<page_group_pk>\d+)/', include([
                #     url(r'^$', page_group_detail),
                #     url(r'^pages/', include(page_paterns)),
                # ])),
            ]))
        ]
        )),
        # url(r'create/', views.events_create, name='create')
    ]), name='gateways'),
    #
    url(r'services/', include([
        # url(r'^$', service_list),
        # url(r'^order/$', page_order),
        # url(r'^create/$', page_create),
        url(r'^(?P<service_pk>\d+)/', include([
            # url(r'^$', page_detail),
            url(r'^service_commands/$', service_command_list),
            url(r'^service_commands/from/$', service_command_copy),
        ])),
    ]), name='services'),

    url(r'input_variables/', include([
        # url(r'^$', input_variables_list),
        url(r'^$', input_variable_put),
        url(r'^(?P<input_variable_pk>\d+)/', include([
            url(r'^$', input_variable_detail),
            #url(r'^service_commands/$', service_command_list),
        ])),
    ]), name='input_variables'),

    url(r'gateway_profiles/', include([
        # url(r'^$', input_variables_list),
        url(r'^$', gateway_profile_put),

    ]), name='gateway_profiles')

]
