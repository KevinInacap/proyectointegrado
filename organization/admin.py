from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from .models import Delegation, Position, UserProfile
from .forms import DelegationForm, UserProfileForm


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
    Incluye Acciones Personalizadas para cambiar Grupo y Delegación masivamente.
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
    actions = [
        'asignar_grupo_administradores',
        'asignar_grupo_verificadores',
        'asignar_grupo_gestores',
        'asignar_delegacion_centro',
        'asignar_delegacion_companias',
        'asignar_delegacion_pampa',
        'asignar_delegacion_rural',
        'activar_usuarios',
        'desactivar_usuarios',
    ]

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

    # --- ACCIONES PERSONALIZADAS (Admin Pro - Rúbrica) ---
    @admin.action(description="👑 Asignar Grupo: Administradores")
    def asignar_grupo_administradores(self, request, queryset):
        group = Group.objects.filter(name="Administradores").first()
        if group:
            for user in queryset:
                user.groups.clear()
                user.groups.add(group)
                user.is_staff = True
                user.save()
            self.message_user(request, f"Se asignó el rol Administradores a {queryset.count()} usuario(s).", messages.SUCCESS)

    @admin.action(description="🔍 Asignar Grupo: Verificadores")
    def asignar_grupo_verificadores(self, request, queryset):
        group = Group.objects.filter(name="Verificadores").first()
        if group:
            for user in queryset:
                user.groups.clear()
                user.groups.add(group)
                user.is_staff = True
                user.save()
            self.message_user(request, f"Se asignó el rol Verificadores a {queryset.count()} usuario(s).", messages.SUCCESS)

    @admin.action(description="📋 Asignar Grupo: Gestores Territoriales")
    def asignar_grupo_gestores(self, request, queryset):
        group = Group.objects.filter(name="Gestores Territoriales").first()
        if group:
            for user in queryset:
                user.groups.clear()
                user.groups.add(group)
                user.is_staff = True
                user.save()
            self.message_user(request, f"Se asignó el rol Gestores Territoriales a {queryset.count()} usuario(s).", messages.SUCCESS)

    @admin.action(description="🏛️ Asignar Delegación: Centro Histórico")
    def asignar_delegacion_centro(self, request, queryset):
        delegation = Delegation.objects.filter(name__icontains="Centro").first()
        if delegation:
            updated = 0
            for user in queryset:
                if hasattr(user, 'profile'):
                    user.profile.delegation = delegation
                    user.profile.save()
                    updated += 1
            self.message_user(request, f"Se asignó {delegation.name} a {updated} usuario(s).", messages.SUCCESS)

    @admin.action(description="🏛️ Asignar Delegación: Las Compañías")
    def asignar_delegacion_companias(self, request, queryset):
        delegation = Delegation.objects.filter(name__icontains="Compañías").first()
        if delegation:
            updated = 0
            for user in queryset:
                if hasattr(user, 'profile'):
                    user.profile.delegation = delegation
                    user.profile.save()
                    updated += 1
            self.message_user(request, f"Se asignó {delegation.name} a {updated} usuario(s).", messages.SUCCESS)

    @admin.action(description="🏛️ Asignar Delegación: La Pampa")
    def asignar_delegacion_pampa(self, request, queryset):
        delegation = Delegation.objects.filter(name__icontains="Pampa").first()
        if delegation:
            updated = 0
            for user in queryset:
                if hasattr(user, 'profile'):
                    user.profile.delegation = delegation
                    user.profile.save()
                    updated += 1
            self.message_user(request, f"Se asignó {delegation.name} a {updated} usuario(s).", messages.SUCCESS)

    @admin.action(description="🏛️ Asignar Delegación: Sector Rural")
    def asignar_delegacion_rural(self, request, queryset):
        delegation = Delegation.objects.filter(name__icontains="Rural").first()
        if delegation:
            updated = 0
            for user in queryset:
                if hasattr(user, 'profile'):
                    user.profile.delegation = delegation
                    user.profile.save()
                    updated += 1
            self.message_user(request, f"Se asignó {delegation.name} a {updated} usuario(s).", messages.SUCCESS)

    @admin.action(description="✅ Activar cuentas seleccionadas")
    def activar_usuarios(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} cuenta(s) activada(s).", messages.SUCCESS)

    @admin.action(description="⛔ Desactivar cuentas seleccionadas")
    def desactivar_usuarios(self, request, queryset):
        count = queryset.exclude(id=request.user.id).update(is_active=False)
        self.message_user(request, f"{count} cuenta(s) desactivada(s).", messages.WARNING)

    # Restricción de permisos: solo administradores pueden gestionar usuarios
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return True
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return True
        return False


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
    form = DelegationForm
    list_display = ('name', 'scope', 'status', 'created_at')
    list_filter = ('status', 'scope')
    search_fields = ('name', 'scope')
    ordering = ('name',)
    inlines = [UserProfileDelegationInline]

    # Solo administradores pueden crear, modificar o eliminar delegaciones
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'description')
    ordering = ('name',)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileForm
    list_display = ('full_name', 'rut', 'email', 'delegation', 'position', 'get_user_groups', 'status', 'created_at')
    list_select_related = ('user', 'delegation', 'position')
    list_filter = ('status', 'delegation', 'position', 'user__groups')
    search_fields = ('full_name', 'rut', 'email', 'user__username')
    ordering = ('full_name',)

    def get_user_groups(self, obj):
        groups = [g.name for g in obj.user.groups.all()]
        return ", ".join(groups) if groups else "-"
    get_user_groups.short_description = "Grupos"

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()
