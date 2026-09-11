from django import forms
from .models import BenchmarkFramework, BenchmarkKPI, BenchmarkPerformanceLevel, BenchmarkPeriod, BenchmarkTarget


class FrameworkForm(forms.ModelForm):
    class Meta: model = BenchmarkFramework; fields = ["name", "code", "description", "effective_from", "effective_to", "reporting_frequency"]

class KPIForm(forms.ModelForm):
    class Meta: model = BenchmarkKPI; fields = ["category", "name", "code", "description", "unit", "calculation_type", "direction", "weightage", "frequency", "calculator_code", "source_module", "is_active"]

class TargetForm(forms.ModelForm):
    class Meta: model = BenchmarkTarget; fields = ["framework", "kpi", "target_type", "plant", "target_value", "effective_from", "effective_to"]

class PerformanceLevelForm(forms.ModelForm):
    class Meta: model = BenchmarkPerformanceLevel; fields = ["framework", "name", "minimum_score", "maximum_score", "display_indicator", "is_active", "display_order"]

class PeriodForm(forms.ModelForm):
    class Meta: model = BenchmarkPeriod; fields = ["framework", "period_type", "start_date", "end_date"]
