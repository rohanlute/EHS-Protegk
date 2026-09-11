from django.contrib import admin
from .models import *

@admin.register(BenchmarkFramework)
class FrameworkAdmin(admin.ModelAdmin): list_display = ("code", "name", "status", "reporting_frequency", "effective_from")
@admin.register(BenchmarkCategory)
class CategoryAdmin(admin.ModelAdmin): list_display = ("name", "framework", "weightage", "is_active")
@admin.register(BenchmarkKPI)
class KPIAdmin(admin.ModelAdmin): list_display = ("code", "name", "category", "calculator_code", "is_active")
@admin.register(BenchmarkTarget)
class TargetAdmin(admin.ModelAdmin): list_display = ("kpi", "target_type", "plant", "department", "target_value")
admin.site.register(BenchmarkPerformanceLevel)
admin.site.register(BenchmarkPeriod)
admin.site.register(BenchmarkResult)
admin.site.register(BenchmarkKPIResult)
admin.site.register(BenchmarkGap)
admin.site.register(BenchmarkInsight)
