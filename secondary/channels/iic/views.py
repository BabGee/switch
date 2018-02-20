from django.http import JsonResponse, HttpResponse

from primary.core.administration.models import Gateway, Icon, AccessLevel
from primary.core.upc.models import GatewayProfile, Institution
from primary.core.bridge.models import Service, Product, ServiceStatus,ServiceCommand,CommandStatus

# data list editor
from secondary.channels.dsc.models import DataList
from primary.core.api.models import NodeSystem

# iic editor
import json
from secondary.channels.iic.models import \
    PageGroup, \
    Page, \
    PageInputGroup, \
    PageInput, \
    InputVariable, \
    VariableType, \
    PageInputStatus
from django.db.models import Count, IntegerField
from django.db.models.functions import Cast
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import \
    PageForm, \
    PageInputForm, \
    PageInputVariableForm, \
    PageOrderConfigForm, \
    PageInputOrderConfigForm, \
    PageInputGroupForm, \
    PageGroupPageForm,\
    DataListForm,\
    DataListQueryForm

from django.db.models import Q
from primary.core.administration.models import Channel


def query_page_inputs(gateway, service='HOME', institution=None):
    return PageInput.objects \
        .filter(Q(page__service__name=service),
                Q(page_input_status__name='ACTIVE'),
                # Q(Q(access_level=gateway_profile.access_level) | Q(access_level=None)),
                # Q(Q(page__access_level=gateway_profile.access_level) | Q(page__access_level=None)),
                # Q(Q(profile_status=gateway_profile.status) | Q(profile_status=None)),
                # Q(Q(page__profile_status=gateway_profile.status) | Q(page__profile_status=None)), Q(channel__id=payload['chid']),
                # ~Q(page__item_level=0),
                Q(page__page_group__gateway=gateway) | Q(page__page_group__gateway=None),
                Q(page_input_group__gateway=gateway) | Q(page_input_group__gateway=None),
                Q(page__gateway=gateway) | Q(page__gateway=None),
                Q(gateway=gateway) | Q(gateway=None)
                ).prefetch_related('trigger', 'page', 'access_level', 'institution', 'input_variable',
                                   'page_input_group', 'gateway', 'channel', 'payment_method')


def gateway_list(request):
    # filter gateways
    gateways = Gateway.objects.all()

    return render(request, "iic/gateway/list.html", {'gateways': gateways})


def datalist_list(request):
    # filter gateways

    datalists = DataList.objects.all().order_by('-id')

    return render(request, "iic/datalist/list.html", {'datalists': datalists})


def module_models(request):
    from django.apps import apps
    module = request.GET.get('module').lower()
    selected_model = request.GET.get('model').lower()
    app = module.split('.')[-1]

    app_models = apps.get_app_config(app).get_models()
    # for model in app_models:
    #     pass

    return render(request, "iic/shared/models.html", {'models': app_models,'selected_model':selected_model})


import ast, os
from django.conf import settings
# this two are used in the next two views

def node_system_service_commands(request): # todo update url and pass id in  view args
    node_system = NodeSystem.objects.get(pk=request.GET.get('node_system_id'))
    ast_filename = os.path.join(settings.BASE_DIR,node_system.URL.lower().replace('.','/'),'tasks.py')


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


def node_system_service_commands_code(request,node_system_pk,service_command_pk):
    node_system = NodeSystem.objects.get(pk=node_system_pk)
    service_command = ServiceCommand.objects.get(pk=service_command_pk)

    ast_filename = os.path.join(settings.BASE_DIR,node_system.URL.lower().replace('.','/'),'tasks.py')

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
    #### parse the code fragment
    with open(ast_filename) as fd:
        file_contents = fd.readlines()
        in_block = False
        for line in file_contents:
            if (not in_block) and 'def' in line and service_command.command_function in line:
                code.append(line)
                in_block = True
            elif (in_block) and ('class' in line or ('def' in line and end_line_contains in line)): # (class_node and (class_def is not class_node))
                in_block = False
                break

            if in_block:
                code.append(line)
    # class_node = class_def
    #### end parse code fragment

    return render(request, "iic/shared/service_command_code.html", {
        'fragment':''.join(code),
    })


def datalist_list_query_editor(request, data_name):
    # filter gateways
    data_list = DataList.objects.get(data_name=data_name)
    data_list_query = data_list.query

    if request.method == 'POST':
        data = request.POST
        prop = data.get('name')

        if prop == 'links':
            data_list_query.links = data.get('value')
            data_list_query.save()

        elif prop == 'values':
            data_list_query.values = data.get('value')
            data_list_query.save()

        return HttpResponse('')  # todo update only new input

    modules = NodeSystem.objects.filter(node_status__name='LOCAL')

    values = data_list_query.values.split('|')
    values_objs = []
    for value in values:
        v = value.split('%')
        tmp = {
            'label': v[0],
            'path': v[1]
        }
        values_objs.append(tmp)

    values = []
    if data_list_query.links:
        values = data_list_query.links.split('|')
    links_objs = []
    for value in values:
        v = value.split('%')
        tmp = {
            'label': v[0],
            'service': v[1],
            'icon': v[2]
        }
        links_objs.append(tmp)

    usages = PageInput.objects.filter(
        input_variable__service__name='DATA SOURCE',
        input_variable__default_value__icontains=data_name
    )

    return render(request, "iic/datalist/editor.html", {
        'data_list': data_list,
        'values': values_objs,
        'links': links_objs,
        'modules': modules,
        'usages':usages
    })


def datalist_duplicate(request, data_name):
    # filter gateways
    data_list = DataList.objects.get(data_name=data_name)
    data_list_query = data_list.query

    if request.method == 'POST':
        data_list_form = DataListForm(instance=data_list)
        new_data_list = data_list_form.save(commit=False)
        new_data_list.pk = None
        new_data_list.data_name = request.POST.get('new_data_name')

        data_list_query_form = DataListQueryForm(instance=data_list_query)
        new_data_list_query = data_list_query_form.save(commit=False)
        new_data_list_query.name = new_data_list.data_name
        new_data_list_query.pk = None
        new_data_list_query.save()
        new_data_list.query = new_data_list_query

        new_data_list.save()

        return redirect('/iic_editor/dsc/{}/'.format(new_data_list.data_name))


def gateway_detail(request, gateway_pk):
    # filter gateway
    gateway = Gateway.objects.get(pk=gateway_pk)

    return render(request, "iic/gateway/detail.html", {'gateway': gateway})


def gateway_profile_list(request, gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    gateway_profiles = GatewayProfile.objects.filter(gateway=gateway).order_by('-id')
    page = request.GET.get('page', 1)

    q = request.GET.get('q',None)
    if q:
        gateway_profiles = gateway_profiles.filter(msisdn__phone_number__icontains=q)

    paginator = Paginator(gateway_profiles, 50)
    try:
        gateway_profiles = paginator.page(page)
    except PageNotAnInteger:
        gateway_profiles = paginator.page(1)
    except EmptyPage:
        gateway_profiles = paginator.page(paginator.num_pages)

    return render(request, "iic/gateway_profile/list.html", {
        'gateway': gateway,
        'gateway_profiles': gateway_profiles
    })


def institution_profile_list(request, gateway_pk,institution_pk):

    gateway = Gateway.objects.get(pk=gateway_pk)
    institution = gateway.institution_set.get(pk=institution_pk)

    # page_groups = gateway.pagegroup_set.all()

    gateway_profiles = GatewayProfile.objects.filter(gateway=gateway,institution=institution).order_by('-id')
    page = request.GET.get('page', 1)

    q = request.GET.get('q',None)
    if q:
        gateway_profiles = gateway_profiles.filter(msisdn__phone_number__icontains=q)

    paginator = Paginator(gateway_profiles, 50)
    try:
        gateway_profiles = paginator.page(page)
    except PageNotAnInteger:
        gateway_profiles = paginator.page(1)
    except EmptyPage:
        gateway_profiles = paginator.page(paginator.num_pages)

    return render(request, "iic/gateway_profile/list.html", {
        'gateway': gateway,
        'gateway_profiles': gateway_profiles
    })


def gateway_institution_list(request, gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    gateway_institutions = Institution.objects.filter(gateway=gateway)

    return render(request, "iic/gateway_institution/list.html", {
        'gateway': gateway,
        'gateway_institutions': gateway_institutions
    })


def institution_detail(request, gateway_pk, institution_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    institution = gateway.institution_set.get(pk=institution_pk)

    # page_inputs = query_page_inputs(gateway, service)
    # page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct()
    # page_group = page_groups.get(pk=page_group_pk)

    return render(request, "iic/gateway_institution/detail.html", {
        'gateway': gateway,
        'institution': institution
    })


def page_group_list(request, gateway_pk, service_name):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    page_inputs = query_page_inputs(gateway, service_name)

    page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct().order_by('item_level')
    return render(request, "iic/page_group/list.html", {
        'gateway': gateway,
        'service': service_name,
        'page_groups': page_groups
    })


def interface(request, gateway_pk, service_name, page_group_pk=None, page_pk=None, page_input_group_pk=None):
    gateway = Gateway.objects.get(pk=gateway_pk)

    page_inputs = query_page_inputs(gateway, service_name)

    page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct().order_by('item_level')

    # query pages for first page group
    if page_group_pk:
        page_group = page_groups.get(pk=page_group_pk)
    else:
        page_group = page_groups.first()


    # todo use page-inputs to filter, remove pages without page-inputs
    pages = page_group.page_set.all().order_by('item_level')

    # todo user page to optimize query
    # query pages from page inputs
    pages_with_inputs = pages.filter(pageinput__in=page_inputs).distinct()
    # blank_pages = pages.exclude(pk__in=pages_with_inputs)

    # query page input groups for first page
    if page_pk:
        page = pages_with_inputs.get(pk=page_pk)
    else:
        page = pages_with_inputs.first()
    page_input_groups = PageInputGroup.objects.filter(pageinput__in=page_inputs, pageinput__page=page).distinct()

    # query page inputs for first page input group
    if page_input_group_pk:
        page_input_group = page_input_groups.get(pk=page_input_group_pk)
    else:
        page_input_group = page_input_groups.first()

    # TODO optimization already queried page inputs above
    page_inputs = page_input_group.pageinput_set.filter(Q(gateway=gateway) | Q(gateway=None)).extra(
        select={
            'item_level_int': 'CAST(item_level AS INTEGER)'
        }
    ).order_by('item_level_int')

    # all().order_by('item_level')

    return render(request, "iic/page_group/interface.html", {
        'gateway': gateway,
        'service': service_name,
        'page_groups': page_groups,
        'page_group': page_group,
        'pages': pages_with_inputs,
        'page': page,
        'page_input_groups': page_input_groups,
        'page_input_group': page_input_group,
        'page_inputs': page_inputs,

    })


def page_group_create(request, gateway_pk, service_name):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    # page_inputs = query_page_inputs(gateway, service)
    # page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct().order_by('item_level')

    if request.method == "POST":
        form = PageGroupPageForm(request.POST)
        if form.is_valid():

            page = form.save(commit=False)
            try:
                service_obj = Service.objects.get(name=service_name)
            except Service.DoesNotExist:
                return None

            # add get_section service command if not exists
            try:
                service_obj.servicecommand_set.get(command_function='get_section')
            except ServiceCommand.DoesNotExist as e:
                service_command = ServiceCommand()

                service_command.service = service_obj

                service_command.command_function = 'get_section'

                last_sc = service_obj.servicecommand_set.order_by('level').last()
                service_command.level = (last_sc.level) + 1 if last_sc else 0
                service_command.node_system_id = 6 # todo IIC

                service_command.status = CommandStatus.objects.get(name='ENABLED')
                service_command.description = 'Get Section'
                service_command.save()

            page.save()

            page.service.add(service_obj)

            # create page input group
            page_input_group = PageInputGroup()
            page_input_group.name = page.name
            page_input_group.description = page.name
            page_input_group.item_level = 0

            input_variable = InputVariable()
            input_variable.name = page.name
            input_variable.variable_type = VariableType.objects.get(name='FORM')  # iic.models.VariableType
            # todo assigning variable_type using id is better
            # todo FORM & HIDDEN FORM

            input_variable.validate_min = 0
            input_variable.validate_max = 0
            # input_variable.variable_kind = None
            # todo create submit service and service commands
            # input_variable.default_value = page_input_group_config.get('service')

            # # todo create configured service and commands
            # service_name = form.cleaned_data.get('input_variable_service')
            # if service_name:
            #     pass
            # else:
            #     service_name = service

            # try:
            #     service = Service.objects.get(name=service_name)
            # except Service.DoesNotExist:
            #     service = Service(name=service_name)
            #
            #     service.description = service_name.title()
            #     service.product = Product.objects.get(name='SYSTEM')
            #     service.status = ServiceStatus.objects.get(name='POLLER')
            #
            #     service.save()
            #     # service.access_level = None
            #
            # input_variable.service = service
            input_variable.save()

            page_input_group.input_variable = input_variable  # iic.models.InputVariable
            page_input_group.section_size = '24|24|24'
            page_input_group.section_height = 900

            page_input_group.save()
            # create page input

            page_input = PageInput()
            page_input.page_input = page.name
            page_input.item_level = 0
            page_input.section_size = '24|24|24'

            page_input_input_variable = InputVariable()
            page_input_input_variable.name = 'placeholder'
            # iic.models.VariableType
            try:
                page_input_input_variable.variable_type = VariableType.objects.get(name='SUBMIT')
            except VariableType.DoesNotExist:
                # self.log(self.command.style.ERROR('NO ELEMENT'))
                # THIS SHOULD NEVER HAPPEN
                raise

            page_input_input_variable.validate_min = 0
            page_input_input_variable.validate_max = 0
            # input_variable.default_value = form.cleaned_data['input_variable_default_value']

            page_input_input_variable.save()

            page_input.input_variable = page_input_input_variable
            page_input.page = page
            page_input.page_input_group = page_input_group
            page_input.page_input_status = PageInputStatus.objects.get(name='ACTIVE')

            # channel
            default_channels = {
                'iOS', 'BlackBerry', 'Amazon Kindle', 'Windows Phone'
            }
            passed_channels = [] # todo finish me
            if len(passed_channels):
                for c in passed_channels:
                    default_channels.add(c)
            else:
                default_channels.add('WEB')
                default_channels.add('Android')

            # todo optimize with ids
            page_input.save()
            page_input.channel.add(*Channel.objects.filter(name__in=default_channels))

            # create input variable

            # http://localhost:8000/iic_editor/gateways/4/page_groups/30/pages/order/
            return redirect(
                '/iic_editor/gateways/{}/{}/page_groups/'.format(gateway_pk, service_name)
            )
    else:
        form = PageGroupPageForm()
        form.fields['name'].initial = service_name.title()
        # form.fields['page_group'].initial = request.GET['page_group']


    return render(request, "iic/page_group/create.html", {
        'gateway': gateway,
        'service': service_name,
        # 'page_groups': page_groups,
        'form': form,
    })


def institution_page_group_list(request, gateway_pk, institution_pk, service):
    gateway = Gateway.objects.get(pk=gateway_pk)
    institution = gateway.institution_set.get(pk=institution_pk)

    page_inputs = query_page_inputs(gateway, service, institution)

    page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct().order_by('item_level')
    return render(request, "iic/page_group/list.html", {
        'gateway': gateway,
        'institution': institution,
        'service': service,
        'page_groups': page_groups
    })


def gateway_service(request, gateway_pk, service_name):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    service = Service.objects.get(name=service_name)

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


def page_group_detail(request, gateway_pk, service_name, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)

    page_inputs = query_page_inputs(gateway, service_name)
    page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct()
    page_group = page_groups.get(pk=page_group_pk)

    return render(request, "iic/page_group/detail.html", {
        'gateway': gateway,
        'service': service_name,
        'page_group': page_group})


def page_list(request, gateway_pk, service_name, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    # todo use page-inputs to filter, remove pages without page-inputs
    pages = page_group.page_set.all().order_by('item_level')

    page_inputs = query_page_inputs(gateway, service_name)
    # todo user page to optimize query
    # query pages from page inputs
    pages_with_inputs = pages.filter(pageinput__in=page_inputs).distinct()
    blank_pages = pages.exclude(pk__in=pages_with_inputs)

    return render(request, "iic/page/list.html", {
        'gateway': gateway,
        'service': service_name,
        'pages': pages_with_inputs,
        'blank_pages': blank_pages,
        'page_group': page_group})


def page_order(request, gateway_pk,service_name, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    pages = page_group.page_set.all().order_by('item_level')

    if request.method == "POST":
        form = PageOrderConfigForm(request.POST)
        if form.is_valid():

            order_configs = json.loads(form.cleaned_data['config'])
            for order_config in order_configs:
                Page.objects.filter(pk=order_config['page']).update(item_level=order_config['level'])

            # http://localhost:8000/iic_editor/gateways/4/page_groups/30/pages/order/
            return redirect(
                '/iic_editor/gateways/{}/{}/page_groups/{}/pages/order/'.format(gateway_pk,service_name, page_group_pk)
            )
    else:
        form = PageOrderConfigForm()

    return render(request, "iic/page/order.html", {
        'gateway': gateway,
        'service': service_name,
        'pages': pages,
        'form': form,
        'page_group': page_group
    })


def page_create(request, gateway_pk, service_name, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    pages = page_group.page_set.all().order_by('item_level')

    if request.method == "POST":
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            description = form.cleaned_data.get('description')
            page.description = description if description else page.name
            services = form.cleaned_data.get('services', [service_name])
            # print(services)
            level = form.cleaned_data.get('item_level')
            if not level:
                level_pages = pages
                highest_page = level_pages.last()
                if highest_page:
                    if str(highest_page.item_level).isdigit():
                        page.item_level = int(highest_page.item_level) + 1
                    else:
                        page.item_level = level_pages.count() + 1
                else:
                    page.item_level = 0
            else:
                page.item_level = level

            page.page_group = page_group  # iic.models.PageGroup
            page.save()

            # todo page.access_level.add(*[al for al in AccessLevel.objects.filter(name__in=form.cleaned_data.get('access_levels', []))])
            # administration.models.Gateway
            # todo page.gateway.add(*Gateway.objects.filter(name__in=form.cleaned_data.get('gateways')))
            # bridge.models.Service
            page.service.add(*Service.objects.filter(name__in=services))

            return redirect(
                '/iic_editor/gateways/{}/{}/page_groups/{}/pages/{}/'.format(gateway_pk, service_name, page_group_pk,
                                                                             page.pk)
            )
    else:
        form = PageForm()

    return render(request, "iic/page/create.html", {
        'gateway': gateway,
        'service': service_name,

        'pages': pages,
        'form': form,
        'page_group': page_group
    })


def page_detail(request, gateway_pk, service_name, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = page_group.page_set.get(pk=page_pk)

    return render(request, "iic/page/detail.html", {
        'gateway': gateway,
        'page': page,
        'service': service_name,
        'page_group': page_group})


def page_copy(request, gateway_pk, service_name, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = page_group.page_set.get(pk=page_pk)

    if request.method == "POST":
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)

            page.save()
            return redirect(
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/'.format(gateway_pk, page_group_pk, page_pk)
            )
    else:
        form = PageForm(instance=page)

    return render(request, "iic/page/create.html", {
        'gateway': gateway,
        'page': page,
        'service': service_name,
        'form': form,
        'page_group': page_group
    })


def page_input_group_list(request, gateway_pk, service_name, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)

    page_inputs = query_page_inputs(gateway, service_name)
    # todo user page to optimize query
    page_input_groups = PageInputGroup.objects.filter(pageinput__in=page_inputs, pageinput__page=page).distinct()
    blank_page_input_groups = PageInputGroup.objects \
        .annotate(pageinputs_count=Count('pageinput')) \
        .filter(pageinputs_count__lt=1) \
        .order_by('-id')

    # query pages
    # pages = Page.objects.filter(pageinput__in=page_inputs)
    # page input groups of pages
    # page_input_groups = PageInputGroup.objects.filter(pageinput__page=pages).distinct()

    return render(request, "iic/page_input_group/list.html", {
        'gateway': gateway,
        'page': page,
        'service': service_name,
        'page_input_groups': page_input_groups,
        'blank_page_input_groups': blank_page_input_groups,
        'page_group': page_group})


def page_input_group_detail(request, gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)

    node_systems = NodeSystem.objects.filter(node_status__name='LOCAL')

    # page_inputs = query_page_inputs(gateway)
    # todo user page to optimize query
    # page_input_groups = PageInputGroup.objects.filter(pageinput__in=page_inputs, pageinput__page=page).distinct()

    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)

    return render(request, "iic/page_input_group/detail.html", {
        'gateway': gateway,
        'page': page,
        'service': service_name,
        'page_input_group': page_input_group,
        'page_group': page_group,
        # Extra
        'node_systems': node_systems
    })


def page_input_group_create(request, gateway_pk, service_name, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_inputs = query_page_inputs(gateway)
    # todo user page to optimize query
    # page_input_groups = PageInputGroup.objects.filter(pageinput__in=page_inputs, pageinput__page=page).distinct()

    # page_input = page_input_group.pageinput_set.get(pk=page_input_pk)
    if request.method == "POST":
        form = PageInputGroupForm(request.POST)
        if form.is_valid():
            page_input_group = form.save(commit=False)

            # input_variable_id =

            name = form.cleaned_data['name']
            if not name:
                name = page.name

            page_input_group.name = name
            description = form.cleaned_data.get('description')
            page_input_group.description = description if description else name

            level = form.cleaned_data.get('item_level')
            if not level:
                page_inputs = query_page_inputs(gateway)
                # todo user page to optimize query
                level_page_input_group = PageInputGroup.objects.filter(pageinput__in=page_inputs,
                                                                       pageinput__page=page).distinct().order_by(
                    'item_level')
                highest_page_input_group = level_page_input_group.last()
                if highest_page_input_group:
                    if highest_page_input_group.item_level.isdigit():
                        page_input_group.item_level = int(highest_page_input_group.item_level) + 1
                    else:
                        page_input_group.item_level = level_page_input_group.count() + 1

                else:
                    page_input_group.item_level = 0
            else:
                page_input_group.item_level = level

            input_variable = InputVariable()
            input_variable.name = name

            input_variable.variable_type = VariableType.objects.get(name='FORM')  # iic.models.VariableType
            # todo assigning variable_type using id is better
            # todo FORM & HIDDEN FORM

            input_variable.validate_min = 0
            input_variable.validate_max = 0
            # input_variable.variable_kind = None
            # todo create submit service and service commands
            # input_variable.default_value = page_input_group_config.get('service')

            # todo create configured service and commands
            service_name = form.cleaned_data.get('input_variable_service')
            if service_name:
                pass
            else:
                service_name = name.upper()

            # todo input_variable.service = service_name

            # todo this is duplicated
            try:
                service = Service.objects.get(name=service_name)
            except Service.DoesNotExist:
                service = Service(name=service_name)

                service.description = service_name.title()
                service.product = Product.objects.get(name='SYSTEM')
                service.status = ServiceStatus.objects.get(name='POLLER')

                # service.save() todo usefull in submitable sections
                # service.access_level = None

            if False:
                input_variable.service = service
            input_variable.save()

            page_input_group.input_variable = input_variable  # iic.models.InputVariable
            page_input_group.section_size = '24|24|24'
            page_input_group.section_height = 900

            page_input_group.save()
            # administration.models.Gateway
            print(page_input_group)

            page_input_group.gateway.add(
                *Gateway.objects.filter(name__in=form.cleaned_data.get('gateways', []))
            )

            # todo update redirect page bread crumbs

            return redirect(
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/page_input_groups/{}/'.format(
                    gateway_pk, page_group_pk, page_pk, page_input_group.pk
                )
            )
    else:
        form = PageInputGroupForm()
    return render(request, "iic/page_input_group/create.html", {
        'gateway': gateway,
        'service': service_name,
        'page_group': page_group,
        'page': page,
        'form': form})


def page_input_create(request, gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    # page_input = page_input_group.pageinput_set.get(pk=page_input_pk)
    if request.method == "POST":
        form = PageInputVariableForm(request.POST)
        if form.is_valid():
            page_input = form.save(commit=False)

            # section size
            page_input.section_size = '24|24|24'

            # page_input
            # item_level
            if not page_input.item_level:
                last_page_input = page_input_group.pageinput_set.order_by('item_level').last()
                page_input.item_level = (int(last_page_input.item_level)+1) if last_page_input else 0

            # input_variable
            #   name,variable_type,validate_min,validate_max
            input_variable_id = form.cleaned_data['input_variable_id']
            if input_variable_id:
                input_variable = InputVariable.objects.get(pk=input_variable_id)
            else:
                input_variable = InputVariable()
                input_variable.name = form.cleaned_data['input_variable_name']
                # iic.models.VariableType
                try:
                    input_variable.variable_type = VariableType.objects.get(
                        name=form.cleaned_data['input_variable_variable_type'])
                except VariableType.DoesNotExist:
                    # self.log(self.command.style.ERROR('NO ELEMENT'))
                    raise

                input_variable.validate_min = form.cleaned_data['input_variable_validate_min']
                input_variable.validate_max = form.cleaned_data['input_variable_validate_max']
                input_variable.default_value = form.cleaned_data['input_variable_default_value']
                # input_variable.variable_kind = None

                service_name = form.cleaned_data.get('input_variable_service')
                if service_name:
                    try:
                        service_name = Service.objects.get(name=service_name)
                    except Service.DoesNotExist:
                        raise
                        # service = Service(name=service_name)
                        #
                        # service.description = service_name.title()
                        # service.product = Product.objects.get(name='SYSTEM')
                        # service.status = ServiceStatus.objects.get(name='POLLER')
                        #
                        # service.save()
                        # service.access_level = None

                    input_variable.service = service_name

                input_variable.save()

            page_input.input_variable = input_variable

            # page_input_group*
            #   name,description,item_level,input_variable FORM, section_size,section_height
            page_input.page_input_group = page_input_group

            # page_input_status
            # page*
            #   name,description,item_level,page_group*
            page_input.page = page

            # status ACTIVE INACTIVE
            # iic.models.PageInputStatus
            page_input.page_input_status = PageInputStatus.objects.get(name='ACTIVE')

            # channel
            default_channels = {
                'iOS', 'BlackBerry', 'Amazon Kindle', 'Windows Phone'
            }
            passed_channels = []
            if len(passed_channels):
                for c in passed_channels:
                    default_channels.add(c)
            else:
                default_channels.add('WEB')
                default_channels.add('Android')

            # todo optimize with ids
            page_input.save()
            page_input.channel.add(*Channel.objects.filter(name__in=default_channels))
            return redirect(
                '/iic_editor/gateways/{}/{}/page_groups/{}/pages/{}/page_input_groups/{}/page_inputs/'.format(
                    gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk
                )
            )
    else:
        form = PageInputVariableForm(initial={'input_variable_validate_min': '1','input_variable_validate_max':'100'})
    return render(request, "iic/page_input/create.html", {
        'gateway': gateway,
        'page': page,
        'variable_types': VariableType.objects.all(),
        'service': service_name,
        'form': form,
        'page_input_group': page_input_group,
        'page_group': page_group})


def page_input_order(request, gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_inputs = page_input_group.pageinput_set.all().annotate(pos=Cast('item_level', IntegerField())).order_by('pos')

    if request.method == "POST":
        form = PageInputOrderConfigForm(request.POST)
        if form.is_valid():

            order_configs = json.loads(form.cleaned_data['config'])
            for order_config in order_configs:
                PageInput.objects.filter(pk=order_config['page_input']).update(item_level=order_config['level'])

            # http://localhost:8000/iic_editor/gateways/4/page_groups/30/pages/order/
            return redirect(
                '/iic_editor/gateways/{}/{}/page_groups/{}/pages/{}/page_input_groups/{}/page_inputs/'.format(
                    gateway_pk,
                    service_name,
                    page_group_pk,
                    page_pk,
                    page_input_group_pk
                )
            )
    else:
        form = PageInputOrderConfigForm()

    return render(request, "iic/page_input/order.html", {
        'gateway': gateway,
        'service': service_name,
        'page': page,
        'form': form,
        'page_input_group': page_input_group,
        'page_inputs': page_inputs,
        'page_group': page_group})


def page_input_list(request, gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_inputs = page_input_group.pageinput_set.extra(
        select={
            'item_level_int': 'CAST(item_level AS INTEGER)'
        }
    ).order_by('item_level_int')

    return render(request, "iic/page_input/list.html", {
        'gateway': gateway,
        'page': page,
        'service': service_name,
        'page_input_group': page_input_group,
        'page_inputs': page_inputs,
        'page_group': page_group
    })


def page_input_detail(request, gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk, page_input_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_input = page_input_group.pageinput_set.get(pk=page_input_pk)

    if request.method == "POST":
        action = request.POST.get('action').strip()
        new_status = PageInputStatus.objects.get(
            name='ACTIVE' if (page_input.page_input_status.name == 'INACTIVE') else 'INACTIVE'
        )
        page_input.page_input_status = new_status
        page_input.save()
        return JsonResponse({'status': "Hide" if page_input.page_input_status.name == 'ACTIVE' else "Show"})
    else:
        return render(request, "iic/page_input/detail.html", {
            'gateway': gateway,
            'page': page,
            'page_input': page_input,
            'page_input_group': page_input_group,
            'page_group': page_group})


def page_input_copy(request, gateway_pk, service_name, page_group_pk, page_pk, page_input_group_pk, page_input_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_input = page_input_group.pageinput_set.get(pk=page_input_pk)
    if request.method == "POST":
        form = PageInputForm(request.POST)
        if form.is_valid():
            page_input = form.save(commit=False)

            page_input.save()
            return redirect(
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/page_input_groups/{}/page_inputs/{}/'.format(
                    gateway_pk, page_group_pk, page_pk, page_input_group_pk, page_input_pk
                )
            )
    else:
        form = PageInputForm(instance=page_input)
    return render(request, "iic/page_input/create.html", {
        'gateway': gateway,
        'page': page,
        'form': form,
        'page_input': page_input,
        'page_input_group': page_input_group,
        'page_group': page_group})


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
        service_command.node_system_id  = request.POST.get('node_system')
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


def input_variable_put(request):
    data = request.POST

    field = data.get('name')
    value = data.get('value')

    input_variable = InputVariable.objects.get(pk=data.get('pk'))

    if field == 'name':
        input_variable.name = value

    if field == 'default_value':
        input_variable.default_value = value

    elif field == 'service':
        try:
            service = Service.objects.get(name=value)
        except Service.DoesNotExist:
            service = Service()
            service.name = value.upper()
            service.description = value.title()
            service.product = Product.objects.get(name='SYSTEM')
            service.status = ServiceStatus.objects.get(name='POLLER')
            service.save()

        input_variable.service = service

    input_variable.save()

    return HttpResponse(status=200)


def gateway_profile_put(request):
    data = request.POST
    access_level = AccessLevel.objects.get(pk=data.get('value'))

    GatewayProfile.objects.filter(pk=data.get('pk')).update(access_level=access_level)
    return HttpResponse(status=200)


def page_put(request):
    data = request.POST
    new_levels = [int(x) for x in data.getlist('value[]')]
    page = Page.objects.get(pk=data.get('pk'))
    current_levels = page.access_level.values_list('pk', flat=True)

    remove_levels = list(set(current_levels).difference(new_levels))
    add_levels = list(set(new_levels).difference(current_levels))

    page.access_level.add(*AccessLevel.objects.filter(pk__in=add_levels))
    page.access_level.remove(*AccessLevel.objects.filter(pk__in=remove_levels))

    return HttpResponse(status=200)


def page_input_group_put(request):
    data = request.POST
    page_input_group = PageInputGroup.objects.get(pk=data.get('pk'))
    field = data.get('name')
    value = data.get('value')

    if field == 'name':
        page_input_group.name = value

    page_input_group.save()

    return HttpResponse(status=200)


def page_input_put(request):
    data = request.POST
    page_input = PageInput.objects.get(pk=data.get('pk'))
    field = data.get('name')
    value = data.get('value')

    if field == 'page_input_group':
        page_input.page_input_group_id = value
        page_input.save()
    elif field == 'page':
        page_input.page_id = value
        page_input.save()

    elif field == 'page_input':
        page_input.page_input = value
        page_input.save()

    elif field == 'section_size':
        page_input.section_size = value
        page_input.save()

    else:
        # TODO this should use name too and not be default
        new_levels = [int(x) for x in data.getlist('value[]')]

        current_levels = page_input.access_level.values_list('pk', flat=True)

        remove_levels = list(set(current_levels).difference(new_levels))
        add_levels = list(set(new_levels).difference(current_levels))

        page_input.access_level.add(*AccessLevel.objects.filter(pk__in=add_levels))
        page_input.access_level.remove(*AccessLevel.objects.filter(pk__in=remove_levels))

    return HttpResponse(status=200)


def input_variable_detail(request, input_variable_pk):
    input_variable = InputVariable.objects.get(pk=input_variable_pk)

    return render(request, "iic/service_command/list.html", {

    })
