from django.http import HttpResponse
from django.shortcuts import render,redirect

from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from primary.core.bridge.models import Service, Product, ServiceStatus, ServiceCommand, CommandStatus

from secondary.channels.vcs.models import (
    Code,Menu,MenuItem,MenuStatus,SessionState,InputVariable
)
from primary.core.upc.models import (
    Gateway, GatewayProfile, Institution,AccessLevel,ProfileStatus
)
from .forms import MenuForm,MenuItemForm

def code_list(request,gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    page = request.GET.get('page', 1)

    gateway_profiles = Code.objects.filter(gateway_id=gateway_pk)

    paginator = Paginator(gateway_profiles, 50)
    try:
        gateway_profiles = paginator.page(page)
    except PageNotAnInteger:
        gateway_profiles = paginator.page(1)
    except EmptyPage:
        gateway_profiles = paginator.page(paginator.num_pages)

    return render(request, "editor/vcs/code/list.html", {
        'gateway': gateway,
        'codes': gateway_profiles
    })


def ussd(request,gateway_pk,code_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    code = Code.objects.get(pk=code_pk)

    level = request.GET.get('level',0)
    select = request.GET.get('select',0)
    protected = request.GET.get('protected',False)

    access_level_names = request.GET.get('access_level','SYSTEM').split(',')
    profile_status = request.GET.get('profile_status',None)

    access_level_queryset = AccessLevel.objects.get(name__in=access_level_names)
    profile_status_queryset = None
    profile_status_names = []
    if profile_status:
        profile_status_names = profile_status.split(',')
        profile_status_queryset = ProfileStatus.objects.filter(name__in=profile_status_names)

    if request.method == "POST":
        form = MenuForm(request.POST)
        if form.is_valid():
            copy_from = form.cleaned_data.get('copy_from',None)
            if copy_from:
                copy_from_menu = Menu.objects.get(id=copy_from)

                menu = Menu.objects.get(id=copy_from)
                menu.pk = None
                if form.cleaned_data.get('page_string',None):
                    menu.page_string = form.cleaned_data['page_string']

                menu.level = form.cleaned_data['level']
                menu.group_select = form.cleaned_data['group_select']

                menu.save()

                #menu.access_level.add(*copy_from_menu.access_level.all())
                #menu.code.add(*Code.objects.filter(gateway=gateway,channel__name='USSD'))
                #menu.profile_status.add(*copy_from_menu.profile_status.all())

                # todo menu.enrollment_type_included.add(*copy_from_menu.enrollment_type_included.all())
                # todo menu.enrollment_type_excluded.add(*copy_from_menu.enrollment_type_excluded.all())

                for copy_from_menu_item in copy_from_menu.menuitem_set.all():
                    menu_item = MenuItem.objects.get(pk=copy_from_menu_item.pk)
                    menu_item.pk = None
                    menu_item.menu = menu

                    menu_item.save()

                    #menu_item.access_level.add(*copy_from_menu_item.access_level.all())
                    menu_item.access_level.add(*access_level_queryset)
                    #menu_item.profile_status.add(*copy_from_menu_item.profile_status.all())
                    if profile_status:
                        menu.profile_status.add(*profile_status_queryset)

                    #todo menu_item.enrollment_type_excluded.add(*copy_from_menu_item.enrollment_type_excluded.all())
                    #todo menu_item.enrollment_type_included.add(*copy_from_menu_item.enrollment_type_included.all())
            else:
                menu = form.save(commit=False)
                menu.menu_status = MenuStatus.objects.get(name='ENABLED')
                menu.details = '{}'

                service_name = form.cleaned_data.get('service_name',None)
                if service_name:
                    try:
                        service = Service.objects.get(name=service_name)
                        menu.service = service
                    except Service.DoesNotExist:
                        if form.cleaned_data.get('service_create'):
                            service = Service()
                            service.name = service_name.upper()
                            service.description = service_name.title()
                            service.product = Product.objects.get(name='SYSTEM')
                            service.status = ServiceStatus.objects.get(name='POLLER')
                            service.save()
                            menu.service = service

                menu.input_variable = InputVariable.objects.get(pk=form.cleaned_data.get('input_variable_id'))

                menu.save()

            if len(access_level_names): menu.access_level.add(*access_level_queryset)
            if profile_status_queryset:
                menu.profile_status.add(*profile_status_queryset)
            menu.code.add(*Code.objects.filter(gateway=gateway, channel__name='USSD'))

            return redirect('/iic_editor/gateways/{}/vcs/codes/{}/ussd?level={}&select={}&access_level={}&profile_status={}'.format(
                gateway_pk,code_pk,level,select,','.join(access_level_names),','.join(profile_status_names)
            ))
    else:
        form = MenuForm(initial={
            'level': int(level),
            'group_select': int(select),
            'session_state':SessionState.objects.get(name='CON'),
            #'profile_status':profile_status
        })

    # get menu
    menus = Menu.objects.filter(
        code__gateway=gateway,
        level=level,
        group_select=select,
        protected=True if protected else False
    )
    if len(profile_status_names):menus.filter(profile_status__name__in=profile_status_names)
    if len(access_level_names):menus.filter(access_level__name__in=access_level_names)

    menus = menus.distinct()
    # get menu items
    #

    #     last_menu_item = menu.pageinput_set.extra(
    #         select={
    #             'item_level_int': 'CAST(item_level AS INTEGER)'
    #         }
    #     ).order_by('item_level_int')
    #
    item_form = MenuItemForm()

    return render(request, "editor/vcs/code/ussd.html", {
        'gateway': gateway,
        'code': code,
        'level':level,
        'select':select,
        'access_level':access_level_names,
        'profile_status':profile_status_names,
        'menus': menus,
        'form':form,
        'item_form':item_form,

        'all_menu_status':MenuStatus.objects.all()
    })


def menu_item_create(request,gateway_pk,code_pk,menu_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    code = Code.objects.get(pk=code_pk)
    menu = Menu.objects.get(pk=menu_pk)

    # level = request.GET.get('level',0)
    # select = request.GET.get('select',0)
    # access_level = request.GET.get('access_level','SYSTEM')
    # profile_status = request.GET.get('profile_status',None)

    # a_l = AccessLevel.objects.get(name=access_level)
    # if profile_status:
    #     p_s = ProfileStatus.objects.get(name=profile_status)

    if request.method == "POST":
        form = MenuItemForm(request.POST)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.status = MenuStatus.objects.get(name='ENABLED')
            menu_item.menu  = menu

            menu_item.save()
            menu_item.access_level.add(*menu.access_level.all())
            menu_item.profile_status.add(*menu.profile_status.all())

            return redirect('/iic_editor/gateways/{}/vcs/codes/{}/ussd?level={}&select={}&access_level={}&profile_status={}'.format(
                gateway_pk,code_pk,
                menu.level,
                menu.group_select,
                request.POST['access_level_name'],
                request.POST['profile_status_name']
            ))


def menu_item_put(request,gateway_pk,code_pk,menu_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # code = Code.objects.get(pk=code_pk)

    data = request.POST
    menu_item = MenuItem.objects.get(pk=data.get('pk'))

    field = data.get('name')
    value = data.get('value')
    if field == 'status':
        status = MenuStatus.objects.get(pk=value)
        menu_item.status = status

    elif field == 'item_level':
        menu_item.item_level = value

    elif field == 'item_order':
        menu_item.item_order = value

    elif field == 'menu_item':
        menu_item.menu_item = value

    menu_item.save()

    return HttpResponse(status=200)


def menu_put(request,gateway_pk,code_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # code = Code.objects.get(pk=code_pk)

    data = request.POST
    menu = Menu.objects.get(pk=data.get('pk'))

    field = data.get('name')
    value = data.get('value')
    if field == 'access_level':
        access_level = AccessLevel.objects.get(pk=value)
        menu.access_level = access_level

    elif field == 'profile_status':
        status = ProfileStatus.objects.get(pk=value)
        menu.status = status

    elif field == 'level':
        menu.level = value
    elif field == 'details':
        menu.details = value

    elif field == 'select':
        menu.group_select = value

    elif field == 'page_string':
        menu.page_string = value
    elif field == 'menu_description':
        menu.menu_description = value

    if field == 'status':
        status = MenuStatus.objects.get(pk=value)
        menu.menu_status = status

    if field == 'input_variable_id':
        menu.input_variable_id = value

    elif field == 'service':
        try:
            service = Service.objects.get(name=value)
            menu.service = service
        except Service.DoesNotExist:
            service = Service()
            service.name = value.upper()
            service.description = value.title()
            # service.product = Product.objects.get(name='SYSTEM')
            # service.status = ServiceStatus.objects.get(name='POLLER')
            # service.save()
            pass



    menu.save()

    return HttpResponse(status=200)