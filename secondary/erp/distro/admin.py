# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin
from .models import *


class AgentStatusAdmin(admin.ModelAdmin):
	list_display = ('id','name','description',)
admin.site.register(AgentStatus, AgentStatusAdmin)

class AgentAdmin(admin.ModelAdmin):
	list_display = ('id','profile','status','registrar',)
	list_filter = ('status',)
	search_fields = ('profile__user__username','profile__user__first_name','profile__user__last_name','profile__national_id',)
admin.site.register(Agent, AgentAdmin)

class TradingInstitutionStatusAdmin(admin.ModelAdmin):
	list_display = ('id','name','description',)
admin.site.register(TradingInstitutionStatus, TradingInstitutionStatusAdmin)

class TraderTypeAdmin(admin.ModelAdmin):
	list_display = ('id','name','description','enrollment_type',)
admin.site.register(TraderType, TraderTypeAdmin)

class TradingInstitutionAdmin(admin.ModelAdmin):
	list_display = ('id','trader_type','institution','status','agent','supplier_list',)
	list_filter = ('trader_type',)
	search_fields = ('profile__user__username','profile__user__first_name','profile__user__last_name','profile__national_id',)
admin.site.register(TradingInstitution, TradingInstitutionAdmin)

