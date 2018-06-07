from django.shortcuts import render

from django.db.models import Q

from secondary.channels.notify.models import (
    Notification,
    NotificationProduct,
    NotificationTemplate
)

from primary.core.bridge.models import (
Service
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
    service = Service.objects.get(name=service_name)
    gateway = Gateway.objects.get(pk=gateway_pk)

    notification_products = NotificationProduct.objects.filter(
        notification__code__gateway=gateway,
        service__name=service_name
    )

    notification_templates = NotificationTemplate.objects.filter(
        product__notification__code__gateway=gateway,
        service__name=service_name
    )

    services = Service.objects.all()

    # x = NotificationProduct()
    # x.notification.code.gateway

    return render(request,'notify/notification/list.html',{
        'notification_products': notification_products,
        'notification_templates': notification_templates,
        'all_services':services, # todo can be a re-usable mixin
        'service':service,
    })

def notification_templates(request,service_pk):

    notification_templates = NotificationTemplate.objects.filter(service_id=service_pk)


    return render(request,'notify/notification_template/partials/notification_templates.html',{
        'notification_templates':notification_templates
    })