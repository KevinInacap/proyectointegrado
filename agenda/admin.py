from django.contrib import admin
from organization.models import Delegation
from .models import CollectiveAgenda, CommitmentHistory


class CommitmentHistoryInline(admin.TabularInline):
    model = CommitmentHistory
    extra = 1
    fields = ('previous_status', 'new_status', 'author', 'observations')
    readonly_fields = ('created_at',)
    show_change_link = True


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
        'deleted_at',
    )
    list_select_related = ('delegation', 'assigned_to', 'source_activity')
    list_filter = ('status', 'delegation', 'request_source', ('deleted_at', admin.EmptyFieldListFilter))
    search_fields = ('requester', 'territory', 'description', 'support_area')
    ordering = ('committed_date',)
    inlines = [CommitmentHistoryInline]

    # Scoping de seguridad por delegación
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return qs.filter(delegation=request.user.profile.delegation)
        return qs.filter(assigned_to=request.user)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.delegation:
            obj.delegation = request.user.profile.delegation
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "delegation":
            if hasattr(request.user, 'profile') and request.user.profile.delegation:
                kwargs["queryset"] = Delegation.objects.filter(id=request.user.profile.delegation_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(CommitmentHistory)
class CommitmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('commitment', 'previous_status', 'new_status', 'author', 'created_at')
    list_select_related = ('commitment', 'author')
    list_filter = ('new_status',)
    search_fields = ('commitment__requester', 'observations')
    ordering = ('-created_at',)
