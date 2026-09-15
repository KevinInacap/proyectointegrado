from django.contrib import admin
from .models import MeasurementPeriod, MeasurementItem, Goal, DailyIndicator, PerformanceAdjustment

@admin.register(MeasurementPeriod)
class MeasurementPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'computable_days', 'minimum_threshold', 'compliance_cap', 'status')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(MeasurementItem)
class MeasurementItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type', 'status')
    list_filter = ('item_type', 'status')
    search_fields = ('name', 'description')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('period', 'position', 'item', 'target_value', 'unit_of_measure', 'weight')
    list_filter = ('period', 'position', 'item')
    search_fields = ('item__name', 'position__name')


@admin.register(DailyIndicator)
class DailyIndicatorAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'calculation_date', 'traffic_light', 'weighted_compliance', 'expected_target_to_date')
    list_filter = ('traffic_light', 'period')
    search_fields = ('user__username',)


@admin.register(PerformanceAdjustment)
class PerformanceAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'adjustment_type', 'percentage_value', 'registered_by', 'created_at')
    list_filter = ('adjustment_type', 'period')
    search_fields = ('user__username', 'reason')
