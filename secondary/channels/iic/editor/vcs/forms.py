from django import forms
from secondary.channels.vcs.models import Menu,MenuItem

class MenuForm(forms.ModelForm):
    page_string = forms.CharField(widget = forms.TextInput(), required = False)
    copy_from = forms.CharField(widget=forms.TextInput(),required=False)
    input_variable_id = forms.IntegerField(required=False)

    service_name = forms.CharField(max_length=50, required=False)
    service_create = forms.BooleanField(widget=forms.CheckboxInput(),initial=True)

    class Meta:
        model = Menu
        fields = ['page_string', 'level','group_select','session_state']


class MenuItemForm(forms.ModelForm):
    menu_item = forms.CharField(widget = forms.TextInput())
    # copy_from = forms.CharField(widget=forms.TextInput(),required=False)
    #menu_id = forms.IntegerField(required=True)
    # service_name = forms.CharField(max_length=50, required=False)
    # service_create = forms.BooleanField(widget=forms.CheckboxInput(),initial=True)

    class Meta:
        model = MenuItem
        fields = ['menu_item', 'item_level','item_order',]

