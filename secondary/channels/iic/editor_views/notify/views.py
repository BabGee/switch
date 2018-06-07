from django.shortcuts import render

from django.db.models import Q

from secondary.channels.notify.models import (
    Notification,
    NotificationProduct,
    NotificationTemplate
)

from primary.core.upc.models import (
    Gateway
)


def service_notification(request,gateway_pk, service_name):
    '''
    vcs.code->
    notify.notification->
    notify.notification_product->
    notify.notification_template(add the notification_product to a message template)
    '''

    gateway = Gateway.objects.get(pk=gateway_pk)

    notification_products = NotificationProduct.objects.filter(
        notification__code__gateway=gateway,
        service__name=service_name
    )

    notification_templates = NotificationTemplate.objects.filter(
        product__notification__code__gateway=gateway,
        service__name=service_name
    )



    # x = NotificationProduct()
    # x.notification.code.gateway

    return render(request,'iic/notify/notification/list.html',{
        'notification_products': notification_products,
        'notification_templates': notification_templates,
    })