from django.contrib import admin
from organization.models import Delegation
from .models import CollectiveAgenda, CommitmentHistory


class CommitmentHistoryInline(admin.TabularInline):
    model = CommitmentHistory
    extra = 1
    fields = ('previous_status', 'new_status', 'author', 'observations')
    readonly_fields = ('created_at',)
    show_change_link = True


from core.admin_utils import get_user_delegation

@admin.register(CollectiveAgenda)
class CollectiveAgendaAdmin(admin.ModelAdmin):
    list_display = (
        'requester', 
        'territory', 
        'assigned_to', 
        'delegation', 
        'committed_date', 
        'status',
        'created_at',
    )
    list_select_related = ('delegation', 'assigned_to', 'source_activity')
    list_filter = ('status', 'delegation', 'request_source')
    search_fields = ('requester', 'territory', 'description', 'support_area')
    ordering = ('committed_date',)
    inlines = [CommitmentHistoryInline]

    # Scoping de seguridad por delegación (Clase 5)
    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        delegation = get_user_delegation(request)
        return qs.filter(delegation=delegation)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        delegation = get_user_delegation(request)
        return obj.delegation_id == delegation.id

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.delegation = get_user_delegation(request)
            if not obj.assigned_to_id:
                obj.assigned_to = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "delegation":
            delegation = get_user_delegation(request)
            kwargs["queryset"] = Delegation.objects.filter(id=delegation.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(CommitmentHistory)
class CommitmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('commitment', 'previous_status', 'new_status', 'author', 'created_at')
    list_select_related = ('commitment', 'author')
    list_filter = ('new_status',)
    search_fields = ('commitment__requester', 'observations')
    ordering = ('-created_at',)
