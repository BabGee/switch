from django.contrib import admin
from doc.models import *


class DocumentStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(DocumentStatus, DocumentStatusAdmin)

class DocumentAdmin(admin.ModelAdmin):
		list_display = ('id','name','template','status')
admin.site.register(Document, DocumentAdmin)

class DocumentActivityStatusAdmin(admin.ModelAdmin):
		list_display = ('id','name','description')
admin.site.register(DocumentActivityStatus, DocumentActivityStatusAdmin)

class DocumentActivityAdmin(admin.ModelAdmin):
		list_display = ('user','document','scan_payload','photo','status', 'created_by')
admin.site.register(DocumentActivity, DocumentActivityAdmin)

class InstitutionDocumentAdmin(admin.ModelAdmin):
		list_display = ('institution','document')
admin.site.register(InstitutionDocument, InstitutionDocumentAdmin)

