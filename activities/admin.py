from django.contrib import admin
from .models import Activity, Evidence, Validation

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'activity_code', 
        'activity_date', 
        'validation_status', 
        'is_collective_agenda', 
        'created_at'
    )
    list_filter = ('validation_status', 'is_collective_agenda', 'activity_date')
    search_fields = ('activity_code', 'problem_description', 'contact_name')


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('evidence_code', 'activity', 'file_name', 'created_at')
    search_fields = ('evidence_code', 'file_name')


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    list_display = ('activity', 'decision', 'created_at')
    list_filter = ('decision',)
    search_fields = ('activity__activity_code', 'observations')