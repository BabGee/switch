from django.http import JsonResponse, HttpResponse

from primary.core.administration.models import Gateway, Icon, AccessLevel
from primary.core.upc.models import GatewayProfile
from primary.core.bridge.models import Service, Product, ServiceStatus

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
from .forms import \
    PageForm, \
    PageInputForm, \
    PageInputVariableForm, \
    PageOrderConfigForm, \
    PageInputOrderConfigForm, \
    PageInputGroupForm
from django.db.models import Q
from primary.core.administration.models import Channel


def query_page_inputs(gateway, service='HOME'):
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

    datalists = DataList.objects.all().order_by('id')

    return render(request, "iic/datalist/list.html", {'datalists': datalists})


def module_models(request):
    from django.apps import apps
    module = request.GET.get('module').lower()
    app = module.split('.')[-1]

    app_models = apps.get_app_config(app).get_models()
    # for model in app_models:
    #     pass

    return render(request, "iic/shared/models.html", {'models': app_models})


def datalist_list_query_editor(request, data_name):
    # filter gateways
    data_list = DataList.objects.get(data_name=data_name)
    data_list_query = data_list.query

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


    return render(request, "iic/datalist/editor.html", {
        'datalists': data_list,
        'values': values_objs,
        'links': links_objs,
        'modules': modules
    })


def gateway_detail(request, gateway_pk):
    # filter gateway
    gateway = Gateway.objects.get(pk=gateway_pk)

    return render(request, "iic/gateway/detail.html", {'gateway': gateway})


def gateway_profile_list(request, gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    gateway_profiles = GatewayProfile.objects.filter(gateway=gateway)

    return render(request, "iic/gateway_profile/list.html", {
        'gateway': gateway,
        'gateway_profiles': gateway_profiles
    })


def page_group_list(request, gateway_pk, service):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    page_inputs = query_page_inputs(gateway, service)

    page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct().order_by('item_level')
    return render(request, "iic/page_group/list.html", {
        'gateway': gateway,
        'service': service,
        'page_groups': page_groups
    })


def gateway_service(request, gateway_pk, service):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    # page_inputs = query_page_inputs(gateway,service)

    page_input_groups = PageInputGroup.objects.filter(input_variable__service__name=service).order_by('item_level')

    return render(request, "iic/service/detail.html", {
        'service': Service.objects.get(name=service),
        'gateway': gateway,
        'page_input_groups': page_input_groups
    })


def page_group_detail(request, gateway_pk, service, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)

    page_inputs = query_page_inputs(gateway, service)
    page_groups = PageGroup.objects.filter(page__pageinput__in=page_inputs).distinct()
    page_group = page_groups.get(pk=page_group_pk)

    return render(request, "iic/page_group/detail.html", {
        'gateway': gateway,
        'service': service,
        'page_group': page_group})


def page_list(request, gateway_pk, service, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    # todo use page-inputs to filter, remove pages without page-inputs
    pages = page_group.page_set.all().order_by('item_level')

    page_inputs = query_page_inputs(gateway, service)
    # todo user page to optimize query
    # query pages from page inputs
    pages_with_inputs = pages.filter(pageinput__in=page_inputs).distinct()
    blank_pages = pages.exclude(pk__in=pages_with_inputs)

    return render(request, "iic/page/list.html", {
        'gateway': gateway,
        'service': service,
        'pages': pages_with_inputs,
        'blank_pages': blank_pages,
        'page_group': page_group})


def page_order(request, gateway_pk, page_group_pk):
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
                '/iic_editor/gateways/{}/page_groups/{}/pages/order/'.format(gateway_pk, page_group_pk)
            )
    else:
        form = PageOrderConfigForm()

    return render(request, "iic/page/order.html", {
        'gateway': gateway,
        'pages': pages,
        'form': form,
        'page_group': page_group
    })


def page_create(request, gateway_pk, page_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    pages = page_group.page_set.all().order_by('item_level')

    if request.method == "POST":
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            description = form.cleaned_data.get('description')
            page.description = description if description else page.name
            services = form.cleaned_data.get('services', ['HOME'])
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
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/'.format(gateway_pk, page_group_pk, page.pk)
            )
    else:
        form = PageForm()

    return render(request, "iic/page/create.html", {
        'gateway': gateway,
        'pages': pages,
        'form': form,
        'page_group': page_group
    })


def page_detail(request, gateway_pk, service, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = page_group.page_set.get(pk=page_pk)

    return render(request, "iic/page/detail.html", {
        'gateway': gateway,
        'page': page,
        'service': service,
        'page_group': page_group})


def page_copy(request, gateway_pk, service, page_group_pk, page_pk):
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
        'service': service,
        'form': form,
        'page_group': page_group
    })


def page_input_group_list(request, gateway_pk, service, page_group_pk, page_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)

    page_inputs = query_page_inputs(gateway, service)
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
        'service': service,
        'page_input_groups': page_input_groups,
        'blank_page_input_groups': blank_page_input_groups,
        'page_group': page_group})


def page_input_group_detail(request, gateway_pk, service, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)

    # page_inputs = query_page_inputs(gateway)
    # todo user page to optimize query
    # page_input_groups = PageInputGroup.objects.filter(pageinput__in=page_inputs, pageinput__page=page).distinct()

    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)

    return render(request, "iic/page_input_group/detail.html", {
        'gateway': gateway,
        'page': page,
        'service': service,
        'page_input_group': page_input_group,
        'page_group': page_group})


def page_input_group_create(request, gateway_pk, page_group_pk, page_pk):
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

            try:
                service = Service.objects.get(name=service_name)
            except Service.DoesNotExist:
                service = Service(name=service_name)

                service.description = service_name.title()
                service.product = Product.objects.get(name='SYSTEM')
                service.status = ServiceStatus.objects.get(name='POLLER')

                service.save()
                # service.access_level = None

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

            return redirect(
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/page_input_groups/{}/'.format(
                    gateway_pk, page_group_pk, page_pk, page_input_group.pk
                )
            )
    else:
        form = PageInputGroupForm()
    return render(request, "iic/page_input_group/create.html", {
        'gateway': gateway,
        'page_group': page_group,
        'page': page,
        'form': form})


def page_input_create(request, gateway_pk, service, page_group_pk, page_pk, page_input_group_pk):
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
                        service = Service.objects.get(name=service_name)
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

                    input_variable.service = service

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
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/page_input_groups/{}/page_inputs/'.format(
                    gateway_pk, page_group_pk, page_pk, page_input_group_pk
                )
            )
    else:
        form = PageInputVariableForm()
    return render(request, "iic/page_input/create.html", {
        'gateway': gateway,
        'page': page,
        'variable_types': VariableType.objects.all(),
        'service': service,
        'form': form,
        'page_input_group': page_input_group,
        'page_group': page_group})


def page_input_order(request, gateway_pk, page_group_pk, page_pk, page_input_group_pk):
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
                '/iic_editor/gateways/{}/page_groups/{}/pages/{}/page_input_groups/{}/page_inputs/order/'.format(
                    gateway_pk,
                    page_group_pk,
                    page_pk,
                    page_input_group_pk
                )
            )
    else:
        form = PageInputOrderConfigForm()

    return render(request, "iic/page_input/order.html", {
        'gateway': gateway,
        'page': page,
        'form': form,
        'page_input_group': page_input_group,
        'page_inputs': page_inputs,
        'page_group': page_group})


def page_input_list(request, gateway_pk, service, page_group_pk, page_pk, page_input_group_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page_group = PageGroup.objects.get(pk=page_group_pk)
    page = Page.objects.get(pk=page_pk)
    page_input_group = PageInputGroup.objects.get(pk=page_input_group_pk)
    page_inputs = page_input_group.pageinput_set.all().order_by('item_level')

    return render(request, "iic/page_input/list.html", {
        'gateway': gateway,
        'page': page,
        'service': service,
        'page_input_group': page_input_group,
        'page_inputs': page_inputs,
        'page_group': page_group})


def page_input_detail(request, gateway_pk, page_group_pk, page_pk, page_input_group_pk, page_input_pk):
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


def page_input_copy(request, gateway_pk, page_group_pk, page_pk, page_input_group_pk, page_input_pk):
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

    return render(request, "iic/service_command/list.html", {
        'service_commands': service_commands
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


def input_variable_put(request):
    data = request.POST
    InputVariable.objects.filter(pk=data.get('pk')).update(name=data.get('value'))
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


def page_input_put(request):
    data = request.POST
    new_levels = [int(x) for x in data.getlist('value[]')]
    page_input = PageInput.objects.get(pk=data.get('pk'))
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
