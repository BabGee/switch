from django.forms import ModelForm
from django import forms
from .models import Page, PageInput,PageInputGroup


class PageOrderConfigForm(forms.Form):
    config = forms.CharField(widget = forms.HiddenInput(), required = True)


class PageInputOrderConfigForm(forms.Form):
    config = forms.CharField(widget = forms.HiddenInput(), required = True)


# Create the form class.
class PageForm(ModelForm):
    description = forms.CharField(required=False,max_length=100)
    item_level = forms.IntegerField(required=False)

    class Meta:
        model = Page
        fields = ['name','item_level','description','icon']


class PageInputGroupForm(ModelForm):
    # input_variable_name = forms.IntegerField(required=False)

    name = forms.CharField(max_length=45, required=False)
    item_level = forms.CharField(max_length=4, required=False)
    section_size = forms.CharField(max_length=45, required=False)
    # icon = forms.CharField(max_length=45, required=False)
    # bind_position = forms.CharField(max_length=12800, required=False)
    input_variable_service = forms.CharField(max_length=50, required=False)

    class Meta:
        model = PageInputGroup
        fields = ['name', 'item_level','section_size','icon','bind_position']
        # exclude = []


class PageInputForm(ModelForm):
    class Meta:
        model = PageInput
        exclude = []


# todo should extend
class PageInputVariableForm(ModelForm):
    input_variable_id = forms.IntegerField(required=False)

    input_variable_name = forms.CharField(max_length=45, required=False)
    input_variable_variable_type = forms.CharField(max_length=45,required=False)
    input_variable_validate_min = forms.CharField(max_length=45,required=False)
    input_variable_validate_max = forms.CharField(max_length=45,required=False)
    input_variable_default_value = forms.CharField(max_length=12800,required=False)
    input_variable_service = forms.CharField(max_length=50,required=False)

    class Meta:
        model = PageInput
        fields = ['page_input', 'item_level']
