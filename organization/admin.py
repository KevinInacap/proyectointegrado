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


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'rut', 'email', 'delegation', 'position', 'status', 'created_at')
    list_select_related = ('user', 'delegation', 'position')
    list_filter = ('status', 'delegation', 'position')
    search_fields = ('full_name', 'rut', 'email', 'user__username')
    filter_horizontal = ('roles',)
    ordering = ('full_name',)
