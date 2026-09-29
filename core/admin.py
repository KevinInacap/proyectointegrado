from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'affected_table', 'affected_record_id', 'user', 'source_ip', 'created_at')
    list_select_related = ('user',)
    list_filter = ('action', 'affected_table', 'created_at')
    search_fields = ('affected_table', 'affected_record_id', 'user__username')
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'deleted_at', 
        'action', 
        'affected_table', 
        'affected_record_id', 
        'user', 
        'source_ip', 
        'previous_value', 
        'new_value'
    )
    ordering = ('-created_at',)

    # Los registros de auditoría institucional son estrictamente inmutables
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

