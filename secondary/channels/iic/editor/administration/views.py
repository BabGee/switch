from django.http import HttpResponse
from django.shortcuts import render,redirect

from django.db.models import Q

from primary.core.administration.models import Role
from secondary.channels.iic.editor.administration.forms import RoleForm

from primary.core.upc.models import (
    Gateway,
    AccessLevelStatus
)


def role_list(request,gateway_pk):
    gateway = Gateway.objects.get(pk=gateway_pk)
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)

            role.gateway_id = gateway_pk
            role.description = role.name
            role.status = AccessLevelStatus.objects.get(name='ACTIVE')

            role.save()
            return redirect('/iic_editor/gateways/{}/roles/'.format(gateway_pk))
    else:
        gateways = Role.objects.filter(gateway=gateway)
        form = RoleForm()

        return render(request, "editor/administration/role/list.html", {
            'roles': gateways,
            'form': form,
            'gateway': gateway
        })


def gateway_list(request):
    # filter gateways
    gateways = Gateway.objects.all()

    return render(request, "editor/administration/gateway/list.html", {'gateways': gateways})


def gateway_detail(request, gateway_pk):
    # filter gateway
    gateway = Gateway.objects.get(pk=gateway_pk)

    return render(request, "editor/administration/gateway/detail.html", {'gateway': gateway})
