from primary.core.administration.models import Gateway

from secondary.channels.iic.models import PageGroup, Page, PageInputGroup, PageInput

from django.shortcuts import render


def gateway_list(request):
    # filter gateways
    gateways = Gateway.objects.all()

    return render(request, "iic/gateway_list.html", {'gateways': gateways})


def gateway_detail(request, gateway_pk):
    # filter gateway
    gateway = Gateway.objects.get(pk=gateway_pk)

    return render(request, "iic/gateway_detail.html", {'gateway': gateway})


def page_group_list(request, gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_groups = gateway.pagegroup_set.all()

    return render(request, "iic/page_group_list.html", {
        'gateway': gateway,
        'page_groups': page_groups})


def page_group_detail(request, gateway_pk, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = gateway.pagegroup_set.get(pk=page_group_pk)

    return render(request, "iic/page_group_detail.html", {
        'gateway': gateway,
        'page_group': page_group})


def page_list(request, gateway_pk, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    pages = page_group.page_set.all()

    return render(request, "iic/page_list.html", {
        'gateway': gateway,
        'pages': pages,
        'page_group': page_group})


def page_detail(request, gateway_pk, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = page_group.page_set.get(pk=page_pk)

    return render(request, "iic/page_detail.html", {
        'gateway': gateway,
        'page': page,
        'page_group': page_group})


def page_input_group_list(request, gateway_pk, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_groups = PageInputGroup.objects.filter(pageinput__page=page)

    return render(request, "iic/page_input_group_list.html", {
        'gateway': gateway,
        'page': page,
        'page_input_groups': page_input_groups,
        'page_group': page_group})


def page_input_group_detail(request, gateway_pk, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.filter(pageinput__page=page).get(pk=page_input_group_pk)

    return render(request, "iic/page_input_group_detail.html", {
        'gateway': gateway,
        'page': page,
        'page_input_group': page_input_group,
        'page_group': page_group})


def page_input_list(request, gateway_pk, page_group_pk, page_pk,page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_inputs = page_input_group.pageinput_set.all()

    return render(request, "iic/page_input_list.html", {
        'gateway': gateway,
        'page': page,
        'page_input_group': page_input_group,
        'page_inputs': page_inputs,
        'page_group': page_group})


def page_input_detail(request, gateway_pk, page_group_pk, page_pk, page_input_group_pk,page_input_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_input = page_input_group.pageinput_set.get(pk=page_input_pk)

    return render(request, "iic/page_input_detail.html", {
        'gateway': gateway,
        'page': page,
        'page_input': page_input,
        'page_input_group': page_input_group,
        'page_group': page_group})
