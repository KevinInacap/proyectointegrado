from django.contrib import admin
from .models import ServiceCatalog, Activity, Evidence, Validation

@admin.register(ServiceCatalog)
class ServiceCatalogAdmin(admin.ModelAdmin):
    list_display = ('area', 'service', 'attention_type', 'subattention_type', 'status')
    list_filter = ('area', 'status')
    search_fields = ('area', 'service', 'attention_type')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'activity_code',
        'activity_date',
        'user',
        'delegation',
        'item',
        'validation_status',
        'is_collective_agenda',
    )
    list_filter = ('validation_status', 'delegation', 'is_collective_agenda', 'activity_date')
    search_fields = ('activity_code', 'problem_description', 'contact_name', 'executed_action')


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('evidence_code', 'activity', 'file_name', 'uploaded_by', 'created_at')
    search_fields = ('evidence_code', 'file_name', 'activity__activity_code')


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    list_display = ('activity', 'verifier', 'decision', 'created_at')
    list_filter = ('decision',)
    search_fields = ('activity__activity_code', 'observations', 'verifier__username')