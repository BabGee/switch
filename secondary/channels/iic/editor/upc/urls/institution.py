from django.conf.urls import url, include
from secondary.channels.iic.editor.upc.views import (
    gateway_institution_list,
    institution_detail,
    institution_page_group_list,
    institution_profile_list

)

urlpatterns = [
    url(r'^$', gateway_institution_list),
    url(r'^(?P<institution_pk>\d+)/', include([
        url(r'^$', institution_detail),

        url(r'^institution_profiles/', include([
            url(r'^$', institution_profile_list),
        ])),
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

]
