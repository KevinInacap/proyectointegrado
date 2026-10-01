from django.contrib import admin
from organization.models import Delegation
from .models import SocialCase, SocialManagement


class SocialManagementInline(admin.TabularInline):
    model = SocialManagement
    extra = 1
    fields = ('stage', 'catalog', 'management_type', 'management_date', 'result')
    show_change_link = True


from core.admin_utils import get_user_delegation

@admin.register(SocialCase)
class SocialCaseAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_rut', 'contact_phone', 'delegation', 'entry_date', 'created_at')
    list_select_related = ('delegation',)
    list_filter = ('delegation', 'entry_date')
    search_fields = ('user_name', 'user_rut', 'contact_phone')
    ordering = ('-entry_date',)
    inlines = [SocialManagementInline]

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
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "delegation":
            delegation = get_user_delegation(request)
            kwargs["queryset"] = Delegation.objects.filter(id=delegation.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SocialManagement)
class SocialManagementAdmin(admin.ModelAdmin):
    list_display = ('case', 'stage', 'catalog', 'management_type', 'management_date', 'created_at')
    list_select_related = ('case', 'catalog')
    list_filter = ('stage', 'management_date')
    search_fields = ('case__user_name', 'case__user_rut', 'management_type', 'result')
    ordering = ('case', 'stage')
