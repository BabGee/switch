from django.contrib import admin
from thirdparty.roadroute.models import *
# Register your models here.

class TownCityAdmin(admin.ModelAdmin):
	list_display = ('name','description','country',)
admin.site.register(TownCity, TownCityAdmin)

class RoadStreetStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(RoadStreetStatus, RoadStreetStatusAdmin)

class RoadStreetAdmin(admin.ModelAdmin):
	list_display = ('name','description','status','town_city',)
admin.site.register(RoadStreet, RoadStreetAdmin)

class UpdateStatusAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(UpdateStatus, UpdateStatusAdmin)

class UpdateSourceAdmin(admin.ModelAdmin):
	list_display = ('name','description',)
admin.site.register(UpdateSource, UpdateSourceAdmin)

class RoadStreetUpdateAdmin(admin.ModelAdmin):
	list_display = ('ext_update_id','status','road_street','update','update_source','reporter',)
admin.site.register(RoadStreetUpdate, RoadStreetUpdateAdmin)

