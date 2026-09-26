from django.contrib import admin
from .models import MeasurementPeriod, MeasurementItem, Goal, DailyIndicator, PerformanceAdjustment


class GoalInline(admin.TabularInline):
    model = Goal
    extra = 1
    fields = ('position', 'item', 'target_value', 'unit_of_measure', 'weight')
    show_change_link = True


@admin.register(MeasurementPeriod)
class MeasurementPeriodAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'start_date', 
        'end_date', 
        'computable_days', 
        'minimum_threshold', 
        'compliance_cap', 
        'status',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('name',)
    ordering = ('-start_date',)
    inlines = [GoalInline]


@admin.register(MeasurementItem)
class MeasurementItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type', 'status', 'created_at')
    list_filter = ('item_type', 'status')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('period', 'position', 'item', 'target_value', 'unit_of_measure', 'weight', 'created_at')
    list_select_related = ('period', 'position', 'item')
    list_filter = ('period', 'position', 'item')
    search_fields = ('item__name', 'position__name')
    ordering = ('period', 'position')


@admin.register(DailyIndicator)
class DailyIndicatorAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'period', 
        'calculation_date', 
        'traffic_light', 
        'weighted_compliance', 
        'expected_target_to_date',
    )
    list_select_related = ('user', 'period')
    list_filter = ('traffic_light', 'period')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    ordering = ('-calculation_date', 'user')


@admin.register(PerformanceAdjustment)
class PerformanceAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'adjustment_type', 'percentage_value', 'registered_by', 'created_at')
    list_select_related = ('user', 'period', 'registered_by')
    list_filter = ('adjustment_type', 'period')
    search_fields = ('user__username', 'reason')
    ordering = ('-created_at',)
