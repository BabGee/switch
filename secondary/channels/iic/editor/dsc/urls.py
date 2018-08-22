from django.conf.urls import *

# notify
from secondary.channels.iic.editor.dsc.views import (
    datalist_list,
    module_models,
    module_model_fields,
    datalist_list_query_editor,
    datalist_duplicate,
)

name = 'dsc'

urlpatterns = [
    url(r'^$', datalist_list),
    url(r'^models/$', module_models),
    url(r'^fields/$', module_model_fields),
    url(r'^(?P<data_name>[\w]+)/', include([
        url(r'^$', datalist_list_query_editor),
        url(r'^duplicate$', datalist_duplicate),
    ])),

]
