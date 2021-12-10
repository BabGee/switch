from django.shortcuts import render

from primary.core.upc.models import Gateway

from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def gateway_list(request):
   #filter gateways
	gateways = Gateway.objects.all()
	return render(request, 'iiceditor/gateway/list.html', {'gateways':gateways})


@staff_member_required
def gateway_detail(request, gateway_pk):
    # filter gateway
    gateway = Gateway.objects.get(pk=gateway_pk)

    return render(request, "iiceditor/gateway/detail.html", {'gateway': gateway})

