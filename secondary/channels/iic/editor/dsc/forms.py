from django.forms import ModelForm

from secondary.channels.dsc.models import DataList,DataListQuery


class DataListForm(ModelForm):
    class Meta:
        model = DataList
        exclude = []

class DataListQueryForm(ModelForm):
    class Meta:
        model = DataListQuery
        exclude = []