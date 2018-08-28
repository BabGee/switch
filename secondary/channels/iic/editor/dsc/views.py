from django.http import HttpResponse,JsonResponse
from django.shortcuts import render, redirect

from primary.core.api.models import NodeSystem
from secondary.channels.dsc.models import DataList
from secondary.channels.iic.models import \
    PageInput
from .forms import \
    DataListForm, \
    DataListQueryForm


def datalist_list(request):
    # filter gateways

    datalists = DataList.objects.all().order_by('-id')

    return render(request, "editor/dsc/list.html", {'datalists': datalists})


def module_models(request):
    from django.apps import apps
    module = request.GET.get('module').lower()
    selected_model = request.GET.get('model').lower()
    app = module.split('.')[-1]

    app_models = apps.get_app_config(app).get_models()
    # for model in app_models:
    #     pass

    return render(request, "iic/shared/models.html", {'models': app_models, 'selected_model': selected_model})


def module_model_fields(request):
    from django.apps import apps
    module = request.GET.get('module').lower()
    selected_model = request.GET.get('model').lower()
    app = module.split('.')[-1]

    model = apps.get_app_config(app).get_model(selected_model)
    # for model in app_models:
    #     pass

    def model_module(field):
        import re
        field_str = str(field.related_model)
        # <class 'secondary.channels.iic.models.PageGroup'>
        # <class 'thirdparty.i_invest.models.PostalAddress'>
        model_module_path = re.findall(r"'(.*?)'", field_str)[0]
        model_module_path_parts = model_module_path.split('.')

        return dict(
            module='.'.join(model_module_path_parts[0:len(model_module_path_parts)-2]),
            model=model_module_path_parts[-1]
        )


    def serialize_field(field):
        return dict(
            name=field.name,
            many_to_many=field.many_to_many,
            many_to_one=field.many_to_one,
            one_to_many=field.one_to_many,
            one_to_one=field.one_to_one,
            is_relation=field.is_relation,
            related_model=model_module(field) if field.related_model else None,
        )

    fields = [serialize_field(field) for field in model._meta.get_fields()]

    data = {}

    data['model'] = request.GET.get('model')
    data['fields'] = fields

    return JsonResponse(data,safe=False)


def datalist_list_query_editor(request, data_name):
    # filter gateways
    data_list = DataList.objects.get(data_name=data_name)

    context = {
        'data_list': data_list,
        'data_name':data_name
    }

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
    usages = PageInput.objects.filter(
        input_variable__service__name='DATA SOURCE',
        input_variable__default_value__icontains=data_name
    )

    context.update({
        'usages': usages,
        'modules': modules,
    })

    if data_list.query:
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

        context.update({
            'values': values_objs,
            'links': links_objs,

        })

    return render(request, "editor/dsc/editor/details.html", context)


def datalist_list_query_editor_values(request, data_name):
    # filter gateways
    data_list = DataList.objects.get(data_name=data_name)

    context = {
        'data_list': data_list,
        'data_name': data_name
    }

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
    usages = PageInput.objects.filter(
        input_variable__service__name='DATA SOURCE',
        input_variable__default_value__icontains=data_name
    )

    context.update({
        'usages': usages,
        'modules': modules,
    })

    if data_list.query:
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

        context.update({
            'values': values_objs,
            'links': links_objs,

        })

    return render(request, "editor/dsc/editor/values.html", context)


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
