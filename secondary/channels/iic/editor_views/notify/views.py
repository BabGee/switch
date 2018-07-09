from django.http import HttpResponse
from django.shortcuts import render

from django.db.models import Q

from secondary.channels.notify.models import (
    Notification,
    NotificationProduct,
    NotificationTemplate,
    Outbound
)

from primary.core.bridge.models import (
    Service
)

from primary.core.upc.models import (
    Gateway
)


def service_notification(request, gateway_pk, service_name):
    '''
    vcs.code->
    notify.notification->
    notify.notification_product->
    notify.notification_template(add the notification_product to a message template)
    '''
    service = Service.objects.get(name=service_name)
    gateway = Gateway.objects.get(pk=gateway_pk)

    notification_products = NotificationProduct.objects.filter(
        notification__code__gateway=gateway
    )

    templates = NotificationTemplate.objects.filter(
        product__notification__code__gateway=gateway,
        service__name=service_name
    )

    services = Service.objects.all()

    # x = NotificationProduct()
    # x.notification.code.gateway

    return render(request, 'notify/notification/list.html', {
        'notification_products': notification_products,
        'notification_templates': templates,
        'all_services': services,  # todo can be a re-usable mixin
        'service': service,
    })


def notification_templates(request, service_pk):
    notification_templates = NotificationTemplate.objects.filter(service_id=service_pk)

    return render(request, 'notify/notification_template/partials/notification_templates.html', {
        'notification_templates': notification_templates
    })


def notification_product_put(request):
    data = request.POST
    page_input = NotificationProduct.objects.get(pk=data.get('pk'))
    field = data.get('name')
    value = data.get('value')

    if field == 'toggle_service':
        service = Service.objects.get(name=data.get('service_name'))
        exists = page_input.service.filter(name=service.name).exists()
        if exists:
            page_input.service.remove(service)
        else:
            page_input.service.add(service)

    return HttpResponse(status=200)


def notification_template_put(request):
    data = request.POST
    notification_template = NotificationTemplate.objects.get(pk=data.get('pk'))
    field = data.get('name')
    value = data.get('value')

    if field == 'products':
        products = NotificationProduct.objects.filter(pk__in=value.split(','))
        notification_template.product.add(*list(products))

    return HttpResponse(status=200)


def outbound_list(request):
    outbounds = Outbound.objects.filter().order_by('-id')[:10]

    return render(request, 'notify/outbound/list.html', {
        'outbounds': outbounds
    })


def outbound_list_updates(request):
    outbound = Outbound.objects.order_by('-id').filter(id__gt=int(request.GET.get('after'))).last()
    if outbound:
        return render(request, 'notify/outbound/item.html', {
            'outbound': outbound
        })
    
    return HttpResponse('')
