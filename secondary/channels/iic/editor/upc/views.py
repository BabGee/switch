from django.http import HttpResponse
from django.shortcuts import render

from django.db.models import Q

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from primary.core.administration.models import Role, AccessLevel

from primary.core.upc.models import (
    Gateway, GatewayProfile, Institution,ProfileStatus
)


def gateway_profile_list(request, gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    # page_groups = gateway.pagegroup_set.all()

    gateway_profiles = GatewayProfile.objects.filter(gateway=gateway).order_by('-id')
    page = request.GET.get('page', 1)

    q = request.GET.get('q', None)
    if q:
        q = q.strip()
        if '@' in q:  # filter using email
            gateway_profiles = gateway_profiles.filter(user__email__icontains=q)
        else:  # filter username or phone number
            qn = q[-9:]  # clean phone number, remove +254
            if qn.isdigit():  # phone number
                gateway_profiles = gateway_profiles.filter(
                    Q(msisdn__phone_number__icontains=qn) |
                    Q(user__username__icontains=qn)
                )
            else:  # username
                gateway_profiles = gateway_profiles.filter(
                    Q(msisdn__phone_number__icontains=q) |
                    Q(user__username__icontains=q)
                )

    paginator = Paginator(gateway_profiles, 50)
    try:
        gateway_profiles = paginator.page(page)
    except PageNotAnInteger:
        gateway_profiles = paginator.page(1)
    except EmptyPage:
        gateway_profiles = paginator.page(paginator.num_pages)

    return render(request, "iic/gateway_profile/list.html", {
        'gateway': gateway,
        'access_levels': AccessLevel.objects.all(),
        'roles': Role.objects.filter(status__name='ACTIVE'),
        'gateway_profiles': gateway_profiles
    })


def gateway_profile_list_export(request, gateway_pk):
    import csv
    gateway = Gateway.objects.get(pk=gateway_pk)

    import datetime
    now = datetime.datetime.now()

    gateway_profiles = GatewayProfile.objects.filter(gateway=gateway).order_by('-id')

    filename = now.strftime("gateway_profile_{}_%B_%d_%Y__%H_%M".format(gateway.name))

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(filename)

    writer = csv.writer(response)
    writer.writerow([
        'pk',
        'name',
        'email',
        'institution',
        'access_level',
    ])

    for li in gateway_profiles:
        writer.writerow([
            li.id,
            li.user.first_name + ' ' + li.user.last_name,
            li.user.email,
            li.institution.name if li.institution else 'XXXX',
            li.access_level.name
        ])

    return response


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


def institution_profile_list(request, gateway_pk, institution_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    institution = gateway.institution_set.get(pk=institution_pk)

    # page_groups = gateway.pagegroup_set.all()

    gateway_profiles = GatewayProfile.objects.filter(gateway=gateway, institution=institution).order_by('-id')
    page = request.GET.get('page', 1)

    q = request.GET.get('q', None)
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


def gateway_profile_put(request):
    data = request.POST
    gateway_profile = GatewayProfile.objects.get(pk=data.get('pk'))
    field = data.get('name')
    value = data.get('value')
    if field == 'access_level':
        access_level = AccessLevel.objects.get(pk=value)
        gateway_profile.access_level = access_level

    if field == 'role':
        if int(value) == 0:
            gateway_profile.role = None
        else:
            role = Role.objects.get(pk=value)
            gateway_profile.role = role
            gateway_profile.access_level = role.access_level

    elif field == 'status':
        status = ProfileStatus.objects.get(pk=value)
        gateway_profile.status = status

    elif field == 'pin_retries':
        gateway_profile.pin_retries = value

    elif field == 'institution':
        gateway_profile.institution_id = value

    gateway_profile.save()
    return HttpResponse(status=200)
