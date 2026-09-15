from django.contrib import admin
from .models import CollectiveAgenda, CommitmentHistory

@admin.register(CollectiveAgenda)
class CollectiveAgendaAdmin(admin.ModelAdmin):
    list_display = ('requester', 'territory', 'assigned_to', 'delegation', 'committed_date', 'status')
    list_filter = ('status', 'delegation', 'request_source')
    search_fields = ('requester', 'territory', 'description', 'support_area')


@admin.register(CommitmentHistory)
class CommitmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('commitment', 'previous_status', 'new_status', 'author', 'created_at')
    list_filter = ('new_status',)
    search_fields = ('commitment__requester', 'observations')
