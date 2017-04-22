# Register your models here.
from django.contrib.gis import admin
from bridge.models import *
from django.forms.widgets import TextInput, Textarea
from django import forms

class NodeStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description','date_modified','date_created')

admin.site.register(NodeStatus, NodeStatusAdmin)

#This calls specific integrators to different destinations
class NodeSystemAdmin(admin.ModelAdmin):
		list_display = ('name','description','URL','use_ssl','cert_path',\
			'key_path','ca_path','api_key','timeout_time','username','password',\
			'node_status','date_modified','date_created',)

admin.site.register(NodeSystem, NodeSystemAdmin)


