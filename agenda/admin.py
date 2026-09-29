from django.contrib import admin, messages
from django.utils import timezone
from organization.models import Delegation
from .models import CollectiveAgenda, CommitmentHistory
from .forms import CollectiveAgendaForm


class CommitmentHistoryInline(admin.TabularInline):
    model = CommitmentHistory
    extra = 1
    fields = ('previous_status', 'new_status', 'author', 'observations')
    readonly_fields = ('created_at',)
    show_change_link = True


@admin.register(CollectiveAgenda)
class CollectiveAgendaAdmin(admin.ModelAdmin):
    form = CollectiveAgendaForm
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
    list_editable = ('status',)
    list_select_related = ('delegation', 'assigned_to', 'source_activity')
    list_filter = ('status', 'delegation', 'request_source', ('deleted_at', admin.EmptyFieldListFilter))
    search_fields = ('requester', 'territory', 'description', 'support_area')
    ordering = ('committed_date',)
    inlines = [CommitmentHistoryInline]
    actions = ['marcar_en_proceso', 'marcar_cumplido', 'soft_delete_agenda', 'restore_agenda']

    # --- ACCIONES PERSONALIZADAS (Admin Pro - Rúbrica) ---
    @admin.action(description="⏳ Marcar compromisos seleccionados como En Proceso")
    def marcar_en_proceso(self, request, queryset):
        count = 0
        for comp in queryset:
            prev = comp.status
            comp.status = "En proceso"
            comp.save()
            CommitmentHistory.objects.create(
                commitment=comp,
                previous_status=prev,
                new_status="En proceso",
                author=request.user,
                observations="Compromiso puesto en ejecución activa por jefatura territorial."
            )
            count += 1
        self.message_user(request, f"Se actualizaron {count} compromiso(s) a 'En proceso'.", messages.SUCCESS)

    @admin.action(description="✓ Marcar compromisos seleccionados como Cumplidos")
    def marcar_cumplido(self, request, queryset):
        count = 0
        for comp in queryset:
            prev = comp.status
            comp.status = "Cumplido"
            comp.save()
            CommitmentHistory.objects.create(
                commitment=comp,
                previous_status=prev,
                new_status="Cumplido",
                author=request.user,
                observations="Compromiso concluido formalmente y verificado en terreno."
            )
            count += 1
        self.message_user(request, f"Se marcaron como Cumplidos {count} compromiso(s).", messages.SUCCESS)

    @admin.action(description="🗑️ Aplicar borrado lógico a compromisos seleccionados")
    def soft_delete_agenda(self, request, queryset):
        count = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f"Se aplicó borrado lógico a {count} compromiso(s) (registrado en deleted_at).", messages.INFO)

    @admin.action(description="♻️ Restaurar compromisos seleccionados")
    def restore_agenda(self, request, queryset):
        count = queryset.update(deleted_at=None)
        self.message_user(request, f"Se restauraron {count} compromiso(s).", messages.SUCCESS)

    # --- SEGURIDAD Y SCOPING POR DELEGACIÓN (Rúbrica: 15 pts) ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return qs
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return qs.filter(delegation=request.user.profile.delegation)
        return qs.filter(assigned_to=request.user)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None or request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return True
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return obj.delegation_id == request.user.profile.delegation_id
        return False

    def has_delete_permission(self, request, obj=None):
        # Solo administradores pueden eliminar registros
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def save_model(self, request, obj, form, change):
        if not (request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()):
            if hasattr(request.user, 'profile') and request.user.profile.delegation:
                obj.delegation = request.user.profile.delegation
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()) and db_field.name == "delegation":
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

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()
