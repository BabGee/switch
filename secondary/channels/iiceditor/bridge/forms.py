from django import forms
from primary.core.bridge.models import Service

class ServiceForm(forms.Form):
    name = forms.CharField(widget = forms.TextInput(), required = True)
    gateway = forms.CharField(widget=forms.HiddenInput())

