from django.contrib import admin
from organization.models import Delegation
from .models import SocialCase, SocialManagement


class SocialManagementInline(admin.TabularInline):
    model = SocialManagement
    extra = 1
    fields = ('stage', 'catalog', 'management_type', 'management_date', 'result')
    show_change_link = True


@admin.register(SocialCase)
class SocialCaseAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_rut', 'contact_phone', 'delegation', 'entry_date', 'created_at', 'deleted_at')
    list_select_related = ('delegation',)
    list_filter = ('delegation', 'entry_date', ('deleted_at', admin.EmptyFieldListFilter))
    search_fields = ('user_name', 'user_rut', 'contact_phone')
    ordering = ('-entry_date',)
    inlines = [SocialManagementInline]

    # Scoping de seguridad por delegación
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return qs.filter(delegation=request.user.profile.delegation)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.delegation:
            obj.delegation = request.user.profile.delegation
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "delegation":
            if hasattr(request.user, 'profile') and request.user.profile.delegation:
                kwargs["queryset"] = Delegation.objects.filter(id=request.user.profile.delegation_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SocialManagement)
class SocialManagementAdmin(admin.ModelAdmin):
    list_display = ('case', 'stage', 'catalog', 'management_type', 'management_date', 'created_at')
    list_select_related = ('case', 'catalog')
    list_filter = ('stage', 'management_date')
    search_fields = ('case__user_name', 'case__user_rut', 'management_type', 'result')
    ordering = ('case', 'stage')
