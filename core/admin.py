from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'affected_table', 'affected_record_id', 'user', 'source_ip', 'created_at')
    list_filter = ('action', 'affected_table')
    search_fields = ('affected_table', 'affected_record_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
