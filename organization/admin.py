from django.contrib import admin
from .models import Delegation, Position, Role, UserProfile

@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'status', 'created_at')
    list_filter = ('status', 'scope')
    search_fields = ('name', 'scope')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'description')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'rut', 'email', 'delegation', 'position', 'status')
    list_filter = ('status', 'delegation', 'position')
    search_fields = ('full_name', 'rut', 'email')
    filter_horizontal = ('roles',)
