from django.conf.urls import *
from .views import *

page_patterns = [
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
    url(r'dsc/', include([
        url(r'^$', datalist_list),
        url(r'^models/$', module_models),
        # url(r'^fields$', datalist_list),
        url(r'^(?P<data_name>[\w]+)/', include([
            url(r'^$', datalist_list_query_editor),
        ])),
    ]), name='dsc'),
    url(r'gateways/', include([
        url(r'^$', gateway_list),
        url(r'^(?P<gateway_pk>\d+)/', include([
            url(r'^$', gateway_detail),
            # url(r'^page_groups/', include([
            #     url(r'^$', page_group_list),
            #     url(r'^(?P<page_group_pk>\d+)/', include([
            #         url(r'^$', page_group_detail),
            #         url(r'^pages/', include(page_paterns)),
            #     ])),
            # ])),
            url(r'^gateway_profiles/', include([
                url(r'^$', gateway_profile_list),

            ])),
            url(r'^institutions/', include([
                url(r'^$', gateway_institution_list),
                url(r'^(?P<institution_pk>\d+)/', include([
                    url(r'^$', institution_detail),
                    # url(r'^pages/', include(page_paterns)),

                    url(r'^(?P<service>[\w\ ]+)/', include([
                        # url(r'^$', gateway_service), # todo detail view
                        url(r'^page_groups/', include([
                            url(r'^$', institution_page_group_list),
                            # url(r'^(?P<page_group_pk>\d+)/', include([
                            #     url(r'^$', page_group_detail),
                            #     url(r'^pages/', include(page_patterns)),
                            # ])),
                        ])),
                    ])),
                ])),

            ])),
            url(r'^(?P<service>[\w\ ]+)/', include([
                url(r'^$', gateway_service), # todo detail view
                url(r'^interface/', include([
                    url(r'^$', interface),
                    # url(r'^create/$', page_group_create),
                    url(r'^(?P<page_group_pk>\d+)/', include([
                        url(r'^$', interface),
                        url(r'^(?P<page_pk>\d+)/', include([
                            url(r'^$', interface),
                            url(r'^(?P<page_input_group_pk>\d+)/', include([
                                url(r'^$', interface),
                                # url(r'^page_inputs/', include([
                                #     url(r'^$', page_input_list),
                                #     url(r'^order/$', page_input_order),
                                #     url(r'^create/$', page_input_create),
                                #     url(r'^(?P<page_input_pk>\d+)/', include([
                                #         url(r'^$', page_input_detail),
                                #         url(r'^copy/$', page_input_copy),
                                #     ])),
                                # ])),
                            ])),
                        ])),
                    ])),
                ])),
                url(r'^page_groups/', include([
                    url(r'^$', page_group_list),
                    url(r'^create/$', page_group_create),
                    url(r'^(?P<page_group_pk>\d+)/', include([
                        url(r'^$', page_group_detail),
                        url(r'^pages/', include(page_patterns)),
                    ])),
                ])),
            ])),
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
            url(r'^service_commands/order/$', service_command_order),
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

    ]), name='gateway_profiles'),

    url(r'pages/', include([
        url(r'^$', page_put),

    ]), name='pages'),

    url(r'page_inputs/', include([
        url(r'^$', page_input_put),

    ]), name='page_inputs'),

    url(r'page_input_groups/', include([
        url(r'^$', page_input_group_put),

    ]), name='page_input_groups')

]
