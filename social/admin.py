from django.contrib import admin
from .models import SocialCase, SocialManagement

@admin.register(SocialCase)
class SocialCaseAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_rut', 'contact_phone', 'delegation', 'entry_date')
    list_filter = ('delegation', 'entry_date')
    search_fields = ('user_name', 'user_rut', 'contact_phone')


@admin.register(SocialManagement)
class SocialManagementAdmin(admin.ModelAdmin):
    list_display = ('case', 'stage', 'catalog', 'management_type', 'management_date')
    list_filter = ('stage', 'management_date')
    search_fields = ('case__user_name', 'management_type', 'result')
