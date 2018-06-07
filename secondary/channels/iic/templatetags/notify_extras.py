from django import template


register = template.Library()


@register.filter
def service_enabled(service,notification_product):
    return notification_product.service.filter(name=service.name).exists()