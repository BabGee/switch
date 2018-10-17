from django import template


register = template.Library()

@register.filter
def to_class_name(value):
    return value.__class__.__name__


@register.filter
def to_l_class_name(value):
    return value.__class__.__name__.lower()


@register.filter
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})
