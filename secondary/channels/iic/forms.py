from django.forms import ModelForm
from django import forms
from .models import Page, PageInput


class PageOrderConfigForm(forms.Form):
    config = forms.CharField(widget = forms.HiddenInput(), required = True)


class PageInputOrderConfigForm(forms.Form):
    config = forms.CharField(widget = forms.HiddenInput(), required = True)


# Create the form class.
class PageForm(ModelForm):
    class Meta:
        model = Page
        exclude = []


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
