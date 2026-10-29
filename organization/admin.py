from django import forms
from django.contrib import admin
from .models import Delegation, Position, Role, UserProfile


class UserProfileInline(admin.TabularInline):
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
    inlines = [UserProfileInline]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'description')
    ordering = ('name',)


class RoleAdminForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = '__all__'

    def clean_position(self):
        position = self.cleaned_data.get('position')
        original = Role.objects.filter(pk=self.instance.pk).first() if self.instance.pk else None
        if not position and (original is None or original.position_id):
            raise forms.ValidationError('Selecciona un cargo para el rol.')
        if position and (not original or position.pk != original.position_id):
            if position.status != 'Activo' or position.deleted_at is not None:
                raise forms.ValidationError('Selecciona un cargo activo.')
            if original and original.base_positions.exclude(pk=position.pk).exists():
                raise forms.ValidationError('El rol base debe permanecer vinculado a su cargo.')
            if original and original.users.exclude(position_id=position.pk).exists():
                raise forms.ValidationError('Revisa primero los funcionarios asociados a otro cargo.')
        return position


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    form = RoleAdminForm
    list_display = ('name', 'position', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'

    def clean(self):
        data = super().clean()
        position, roles = data.get('position'), data.get('roles')
        if roles is None:
            return data
        original = UserProfile.objects.filter(pk=self.instance.pk).first() if self.instance.pk else None
        same_position = original and original.position_id == (position.pk if position else None)
        existing = set(original.roles.values_list('pk', flat=True)) if same_position else set()
        def belongs(role):
            return bool(position and (role.position_id == position.pk or (
                role.position_id is None and position.base_role_id == role.pk
                and not role.base_positions.exclude(pk=position.pk).exists())))
        if any(not belongs(role) for role in roles if role.pk not in existing):
            self.add_error('roles', 'Los roles nuevos deben pertenecer al cargo del funcionario.')
        return data


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('full_name', 'rut', 'email', 'delegation', 'position', 'status', 'created_at')
    list_select_related = ('user', 'delegation', 'position')
    list_filter = ('status', 'delegation', 'position')
    search_fields = ('full_name', 'rut', 'email', 'user__username')
    filter_horizontal = ('roles',)
    ordering = ('full_name',)
