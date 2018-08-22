from django.conf.urls import include,url

from secondary.channels.iic.editor.notify.views import (
    notification_templates,
    outbound_list,
    outbound_list_updates
)

from .views import trigger_list,\
    node_system_service_commands,\
    node_system_service_commands_code

from secondary.channels.iic.editor.upc.views import gateway_profile_put

from secondary.channels.iic.editor.bridge.views import service_create,\
    service_command_list,\
    service_command_copy,\
    service_command_order

from secondary.channels.iic.editor.iic.views import (
    input_variable_detail,
    page_put,
    page_input_put,
    page_input_group_put,
    input_variable_put
)


urlpatterns = [
    url(r'dsc/', include('secondary.channels.iic.editor.dsc.urls')),
    url(r'triggers/', include([
        url(r'^$', trigger_list),

    ]), name='dsc'),
    url(r'outbound/', include([
        url(r'^$', outbound_list),
        url(r'^updates$', outbound_list_updates),

    ]), name='dsc'),
    url(r'node_systems/', include([

        url(r'^service_commands/$', node_system_service_commands), # TODO move this below

        url(r'^(?P<node_system_pk>\d+)/', include([
            # url(r'^$', page_group_detail),
            url(r'^service_commands/(?P<service_command_pk>\d+)/code$', node_system_service_commands_code),
        ])),

    ]), name='dsc'),
    url(r'gateways/', include('secondary.channels.iic.editor.administration.urls'), name='gateways'),

    url(r'services/', include([
        # url(r'^$', service_list),
        # url(r'^order/$', page_order),
        url(r'^create/$', service_create),
        url(r'^(?P<service_pk>\d+)/', include([
            # url(r'^$', page_detail),
            url(r'^service_commands/$', service_command_list),
            url(r'^service_commands/from/$', service_command_copy),
            url(r'^service_commands/order/$', service_command_order),

            url(r'^notification_templates/$', notification_templates),


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

    ]), name='page_input_groups'),

    url(r'notify/',include('secondary.channels.iic.editor.notify.urls'))

]
