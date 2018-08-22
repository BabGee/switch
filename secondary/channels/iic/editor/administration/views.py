from django.http import HttpResponse
from django.shortcuts import render

from django.db.models import Q


from primary.core.upc.models import (
    Gateway
)

def gateway_list(request):
    # filter gateways
    gateways = Gateway.objects.all()

    return render(request, "editor/administration/gateway/list.html", {'gateways': gateways})


def gateway_detail(request, gateway_pk):
    # filter gateway
    gateway = Gateway.objects.get(pk=gateway_pk)

    return render(request, "editor/administration/gateway/detail.html", {'gateway': gateway})
