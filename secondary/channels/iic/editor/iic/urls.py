from django.conf.urls import url,include
from .views import \
    page_list,\
    page_order,\
    page_create, \
    page_role_right_create,\
    page_detail,\
    page_copy,\
    page_input_group_list,\
    page_input_group_create,\
    page_input_group_detail,\
    page_input_list,\
    page_input_order,\
    page_input_create,\
    page_input_copy,\
    page_input_detail,\
    page_group_detail,\
    page_group_list,\
    page_group_create


name = 'iic'

page_patterns = [
    url(r'^$', page_list),
    url(r'^order/$', page_order),
    url(r'^create_role/$', page_role_right_create),
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
    url(r'^$', page_group_list),
    url(r'^create/$', page_group_create),
    url(r'^(?P<page_group_pk>\d+)/', include([
        url(r'^$', page_group_detail),
        url(r'^pages/', include(page_patterns)),
    ])),
]
