from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Delegation, Position, UserProfile


class UserProfileStackedInline(admin.StackedInline):
    """
    Permite asignar la Delegación, Cargo y RUT directamente
    desde la pantalla de edición del Usuario en Django Admin.
    """
    model = UserProfile
    can_delete = False
    verbose_name = "Perfil Institucional y Delegación"
    verbose_name_plural = "Perfil Institucional y Delegación"
    fields = ('rut', 'full_name', 'email', 'delegation', 'position', 'status')


class CustomUserAdmin(BaseUserAdmin):
    """
    Extensión del UserAdmin estándar para gestionar Usuarios,
    sus Grupos (Roles nativos) y su Delegación en una sola pantalla.
    """
    inlines = [UserProfileStackedInline]
    list_display = (
        'username', 
        'get_full_name_custom', 
        'get_rut', 
        'get_delegation', 
        'get_groups', 
        'is_staff', 
        'is_active'
    )
    list_filter = ('groups', 'is_staff', 'is_active', 'profile__delegation', 'profile__position')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__rut', 'profile__full_name')

    def get_full_name_custom(self, obj):
        if hasattr(obj, 'profile') and obj.profile.full_name:
            return obj.profile.full_name
        return obj.get_full_name() or obj.username
    get_full_name_custom.short_description = "Nombre Completo"

    def get_rut(self, obj):
        return obj.profile.rut if hasattr(obj, 'profile') else "-"
    get_rut.short_description = "RUT"

    def get_delegation(self, obj):
        return obj.profile.delegation.name if hasattr(obj, 'profile') and obj.profile.delegation else "-"
    get_delegation.short_description = "Delegación Asignada"

    def get_groups(self, obj):
        groups = [g.name for g in obj.groups.all()]
        return ", ".join(groups) if groups else "(Sin Grupo)"
    get_groups.short_description = "Grupos / Roles"


# Re-registrar User para incluir Delegación y Grupos unificados
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class UserProfileDelegationInline(admin.TabularInline):
    model = UserProfile
    extra = 0
    fields = ('rut', 'full_name', 'email', 'position', 'status')
    show_change_link = True


@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'status', 'created_at')
    list_filter = ('status', 'scope')
    search_fields = ('name', 'scope')
    ordering = ('name',)
    inlines = [UserProfileDelegationInline]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'rut', 'email', 'delegation', 'position', 'get_user_groups', 'status', 'created_at')
    list_select_related = ('user', 'delegation', 'position')
    list_filter = ('status', 'delegation', 'position', 'user__groups')
    search_fields = ('full_name', 'rut', 'email', 'user__username')
    ordering = ('full_name',)

    def get_user_groups(self, obj):
        groups = [g.name for g in obj.user.groups.all()]
        return ", ".join(groups) if groups else "-"
    get_user_groups.short_description = "Grupos"
