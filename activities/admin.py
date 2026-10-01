from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from organization.models import Delegation
from .models import ServiceCatalog, Activity, Evidence, Validation


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 1
    fields = ('evidence_code', 'file_name', 'file_path', 'uploaded_by')
    show_change_link = True


class ValidationInline(admin.StackedInline):
    model = Validation
    extra = 0
    fields = ('verifier', 'decision', 'observations')
    show_change_link = True


@admin.register(ServiceCatalog)
class ServiceCatalogAdmin(admin.ModelAdmin):
    list_display = ('area', 'service', 'attention_type', 'subattention_type', 'status', 'created_at')
    list_filter = ('area', 'status')
    search_fields = ('area', 'service', 'attention_type')
    ordering = ('area', 'service')


from core.admin_utils import get_user_delegation

@admin.action(
    description="Archivar actividades seleccionadas (Borrado lógico)",
    permissions=["change"],
)
def archive_activities(modeladmin, request, queryset):
    updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    modeladmin.message_user(
        request,
        f"{updated} actividad(es) archivada(s) correctamente.",
        level=messages.SUCCESS,
    )


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'activity_code',
        'activity_date',
        'user',
        'delegation',
        'catalog',
        'status_badge',
        'agenda_display',
        'created_at',
    )
    list_select_related = ('user', 'delegation', 'period', 'item', 'catalog')
    list_filter = (
        'validation_status', 
        'delegation', 
        'is_collective_agenda', 
        'activity_date',
    )
    search_fields = ('activity_code', 'problem_description', 'contact_name', 'executed_action')
    ordering = ('-activity_date', '-created_at')
    date_hierarchy = 'activity_date'
    inlines = [EvidenceInline, ValidationInline]
    actions = [archive_activities, 'approve_selected', 'mark_for_correction', 'restore_selected']

    # 1. Scoping en get_queryset (Lámina 7 de Clase 5): excluye archivados y acota a delegación del usuario
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        delegation = get_user_delegation(request)
        return qs.filter(delegation=delegation)

    # 2. Seguridad en modificación por objeto (Lámina 12 de Clase 5): protege accesos directos por URL
    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        delegation = get_user_delegation(request)
        return obj.delegation_id == delegation.id

    # 3. Restricción de eliminación física (Lámina 14 de Clase 5): solo superusuarios pueden borrar físicamente
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    # 4. Limitación de ForeignKey al ámbito autorizado (Láminas 9 y 10 de Clase 5)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "delegation" and not request.user.is_superuser:
            delegation = get_user_delegation(request)
            kwargs["queryset"] = Delegation.objects.filter(id=delegation.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 5. Asignación automática del ámbito (Lámina 11 de Clase 5)
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.delegation = get_user_delegation(request)
            if not obj.user_id:
                obj.user = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Estado de validación", ordering='validation_status')
    def status_badge(self, obj):
        colors = {
            'Approved': ('#dcfce7', '#15803d', 'Aprobado'),
            'Pending': ('#fef3c7', '#b45309', 'Pendiente'),
            'Rejected': ('#fee2e2', '#b91c1c', 'Rechazado'),
            'Requires correction': ('#dbeafe', '#1d4ed8', 'Requiere corrección'),
        }
        bg, fg, label = colors.get(obj.validation_status, ('#f1f5f9', '#475569', obj.validation_status))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-weight: bold; font-size: 11px; display: inline-block;">{}</span>',
            bg, fg, label
        )

    @admin.display(description="¿Agenda Colectiva?", ordering='is_collective_agenda')
    def agenda_display(self, obj):
        if obj.is_collective_agenda:
            return mark_safe('<span style="color: #15803d; font-weight: bold;">✓ Sí (En agenda)</span>')
        return mark_safe('<span style="color: #94a3b8;">— No</span>')

    @admin.action(description="✓ Aprobar actividades seleccionadas")
    def approve_selected(self, request, queryset):
        count = queryset.update(validation_status='Approved')
        self.message_user(
            request, 
            f"Se han aprobado formalmente {count} actividades seleccionadas.", 
            messages.SUCCESS
        )

    @admin.action(description="⚠ Marcar para corrección")
    def mark_for_correction(self, request, queryset):
        count = queryset.update(validation_status='Requires correction')
        self.message_user(
            request, 
            f"Se han enviado a revisión y corrección {count} actividades.", 
            messages.WARNING
        )

    @admin.action(description="♻️ Restaurar registros archivados")
    def restore_selected(self, request, queryset):
        count = queryset.update(deleted_at=None)
        self.message_user(
            request, 
            f"Se restauraron {count} actividades.", 
            messages.SUCCESS
        )



@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('evidence_code', 'activity', 'file_name', 'uploaded_by', 'created_at')
    list_select_related = ('activity', 'uploaded_by')
    search_fields = ('evidence_code', 'file_name', 'activity__activity_code')
    ordering = ('-created_at',)


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    list_display = ('activity', 'verifier', 'decision', 'created_at')
    list_select_related = ('activity', 'verifier')
    list_filter = ('decision',)
    search_fields = ('activity__activity_code', 'observations', 'verifier__username')
    ordering = ('-created_at',)