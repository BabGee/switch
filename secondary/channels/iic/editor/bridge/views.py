from django.http import HttpResponse
from django.shortcuts import render, redirect

import json

from django.db.models import Q
from secondary.channels.dsc.models import DataList
from primary.core.api.models import NodeSystem
from primary.core.bridge.models import (
    Service,
    ServiceCommand,
    ServiceStatus,
    Product,
    CommandStatus
)
from secondary.channels.iic.models import \
    PageInputGroup

from primary.core.upc.models import (
    Gateway
)

from .forms import \
    ServiceForm


def gateway_service(request, gateway_pk, service_name):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()
    try:
        service = Service.objects.get(name=service_name)
    except Service.DoesNotExist as e:

        service_form = ServiceForm(initial={
            'name': service_name,
            'gateway': gateway.pk
        })

        return render(request, 'iic/service/create.html', {
            'form': service_form,
            'gateway': gateway
        })

    service_commands = service.servicecommand_set.all().order_by('level')

    # page_inputs = query_page_inputs(gateway,service)
    node_systems = NodeSystem.objects.filter(node_status__name='LOCAL')

    page_input_groups = PageInputGroup.objects.filter(input_variable__service__name=service).order_by('item_level')

    return render(request, "iic/service/detail.html", {
        'service': Service.objects.get(name=service),
        'service_commands': service_commands,
        'gateway': gateway,
        'page_input_groups': page_input_groups,
        # Extra
        'node_systems': node_systems
    })


def service_create(request):
    if request.method == 'POST':
        service_name = request.POST.get('name')
        gateway_pk = request.POST.get('gateway')

        service = Service(name=service_name)
        service.description = service_name.title()
        service.product = Product.objects.get(name='SYSTEM')
        service.status = ServiceStatus.objects.get(name='POLLER')

        service.success_last_response = ' '
        service.failed_last_response = ' '

        service.save()

        return redirect('/iic_editor/gateways/{}/{}/'.format(gateway_pk, service_name))


def service_command_list(request, service_pk):
    service = Service.objects.get(pk=service_pk)
    service_commands = service.servicecommand_set.all().order_by('level')

    if request.method == 'POST':
        # todo duplicated above
        service_command = ServiceCommand()

        service_command.service_id = service_pk
        service_command.command_function = request.POST.get('command_function')
        last_sc = service.servicecommand_set.order_by('level').last()
        service_command.level = (last_sc.level + 1) if last_sc else 0
        service_command.node_system_id = request.POST.get('node_system')
        service_command.status = CommandStatus.objects.get(name='ENABLED')
        service_command.description = service_command.command_function
        service_command.save()

        return HttpResponse(status=200)

    return render(request, "iic/service_command/list.html", {
        'service_commands': service_commands,
        'service': service
    })


def service_command_copy(request, service_pk):
    if request.method == 'POST':
        service = Service.objects.get(name=request.POST.get('from'))
        service_commands = service.servicecommand_set.all()

        for service_command in service_commands:
            service_command.pk = None
            service_command.service_id = service_pk
            service_command.save()

    return HttpResponse(status=200)


def service_command_order(request, service_pk):
    if request.method == 'POST':
        order_configs = json.loads(request.POST.get('config'))
        for order_config in order_configs:
            ServiceCommand.objects.filter(pk=order_config['service_command']).update(level=order_config['level'])

    return HttpResponse(status=200)
