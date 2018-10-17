# data list editor

# iic editor

from django.shortcuts import render

# data list editor
from primary.core.bridge.models import ServiceCommand
from primary.core.bridge.models import Trigger
# iic editor
from secondary.channels.iic.models import \
    PageInput


def query_page_inputs(gateway, service='HOME', institution=None):
    return PageInput.objects \
        .filter(Q(page__service__name=service),
                Q(page_input_status__name='ACTIVE'),
                # Q(Q(access_level=gateway_profile.access_level) | Q(access_level=None)),
                # Q(Q(page__access_level=gateway_profile.access_level) | Q(page__access_level=None)),
                # Q(Q(profile_status=gateway_profile.status) | Q(profile_status=None)),
                # Q(Q(page__profile_status=gateway_profile.status) | Q(page__profile_status=None)), Q(channel__id=payload['chid']),
                # ~Q(page__item_level=0),
                # Q(page__page_group__gateway=gateway) | Q(page__page_group__gateway=None),
                Q(page_input_group__gateway=gateway) | Q(page_input_group__gateway=None),
                Q(page__gateway=gateway) | Q(page__gateway=None),
                Q(gateway=gateway) | Q(gateway=None)
                ).prefetch_related('trigger', 'page', 'access_level', 'institution', 'input_variable',
                                   'page_input_group', 'gateway', 'channel', 'payment_method')


def trigger_list(request):
    triggers = Trigger.objects.all().order_by('-id')

    return render(request, "iic/trigger/list.html", {'triggers': triggers})


import ast, os
from django.conf import settings
from django.db.models import Q
from primary.core.api.models import NodeSystem


# this two are used in the next two views


def node_system_service_commands(request):  # todo update url and pass id in  view args
    node_system = NodeSystem.objects.get(pk=request.GET.get('node_system_id'))
    ast_filename = os.path.join(settings.BASE_DIR, node_system.URL.lower().replace('.', '/'), 'tasks.py')

    with open(ast_filename) as fd:
        file_contents = fd.read()

    module = ast.parse(file_contents)
    class_definitions = [node for node in module.body if isinstance(node, ast.ClassDef)]
    service_commands = []

    for class_def in class_definitions:

        method_definitions = class_def.body
        for f in method_definitions:
            if isinstance(f, ast.FunctionDef):
                service_commands.append(dict(
                    command_function=f.name,
                    docstring=ast.get_docstring(f)
                ))

    return render(request, "iic/shared/service_commands.html", {
        'service_commands': service_commands
    })


def node_system_service_commands_code(request, node_system_pk, service_command_pk):
    node_system = NodeSystem.objects.get(pk=node_system_pk)
    service_command = ServiceCommand.objects.get(pk=service_command_pk)

    ast_filename = os.path.join(settings.BASE_DIR, node_system.URL.lower().replace('.', '/'), 'tasks.py')

    with open(ast_filename) as fd:
        file_contents = fd.read()

    module = ast.parse(file_contents)
    class_definitions = [node for node in module.body if isinstance(node, ast.ClassDef)]

    service_commands = []

    start_line_contains = False
    end_line_contains = None

    class_node = None
    for class_def in class_definitions:
        method_definitions = class_def.body
        for f in method_definitions:
            if isinstance(f, ast.FunctionDef):
                if not start_line_contains and f.name == service_command.command_function:
                    start_line_contains = True
                    continue

                if start_line_contains and not end_line_contains:
                    end_line_contains = f.name
                    break

    code = []

    # code.append(end_line_contains)

    # parse the code fragment #
    with open(ast_filename) as fd:
        file_contents = fd.readlines()
        in_block = False
        for line in file_contents:
            if (not in_block) and 'def ' in line and service_command.command_function == line.split('(')[0].split(' ')[1].strip():
                code.append('\n')
                in_block = True
            elif (in_block) and ('class ' in line or (
                    'def' in line and end_line_contains in line)):  # (class_node and (class_def is not class_node))
                break

            if in_block:
                code.append(line)
    # class_node = class_def
    # end parse code fragment #

    return render(request, "iic/shared/service_command_code.html", {
        'fragment': ''.join(code),
    })
