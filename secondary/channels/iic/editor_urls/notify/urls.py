from django.conf.urls import *

# notify
from secondary.channels.iic.editor_views.notify.views import (
    notification_product_put,
    notification_template_put,
)

urlpatterns = [
    url(r'notification_products/', include([
        url(r'^$', notification_product_put),

    ]), name='notification_products'),
    url(r'notification_templates/', include([
        url(r'^$', notification_template_put),

    ]), name='notification_templates')

]
