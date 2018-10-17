from django.conf.urls import include,url

# notify
from secondary.channels.iic.editor.vcs.views import (
    code_list,ussd,menu_item_create,menu_put,menu_item_put
)

urlpatterns = [
    url(r'^$', code_list),
    url(r'^codes/', include([
        url(r'^$', code_list),
        # todo url(r'^create/$', create),
        url(r'^(?P<code_pk>\d+)/', include([
            url(r'^ussd$', ussd),
            url(r'^ussd/menus/', include([
                url(r'^$', menu_put),
                url(r'^(?P<menu_pk>\d+)/', include([
                    url(r'^menu_items/create/', menu_item_create),
                    url(r'^menu_items/', menu_item_put),
                ])),
            ])),
        ])),
    ])),


]
