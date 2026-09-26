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
        'deleted_at',
    )
    list_select_related = ('user', 'delegation', 'period', 'item', 'catalog')
    list_filter = (
        'validation_status', 
        'delegation', 
        'is_collective_agenda', 
        'activity_date',
        ('deleted_at', admin.EmptyFieldListFilter),
    )
    search_fields = ('activity_code', 'problem_description', 'contact_name', 'executed_action')
    ordering = ('-activity_date', '-created_at')
    inlines = [EvidenceInline, ValidationInline]
    actions = ['approve_selected', 'mark_for_correction', 'soft_delete_selected', 'restore_selected']

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

    @admin.action(description="🗑️ Aplicar borrado lógico (Soft delete)")
    def soft_delete_selected(self, request, queryset):
        count = queryset.update(deleted_at=timezone.now())
        self.message_user(
            request, 
            f"Se aplicó borrado lógico a {count} actividades (registrado en deleted_at).", 
            messages.INFO
        )

    @admin.action(description="♻️ Restaurar registros eliminados")
    def restore_selected(self, request, queryset):
        count = queryset.update(deleted_at=None)
        self.message_user(
            request, 
            f"Se restauraron {count} actividades.", 
            messages.SUCCESS
        )

    # Scoping de seguridad por Delegación
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return qs.filter(delegation=request.user.profile.delegation)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.delegation:
            obj.delegation = request.user.profile.delegation
            if not obj.user_id:
                obj.user = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "delegation":
            if hasattr(request.user, 'profile') and request.user.profile.delegation:
                kwargs["queryset"] = Delegation.objects.filter(id=request.user.profile.delegation_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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