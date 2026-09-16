from django import forms
from django.apps import apps as django_apps
from .models import BenchmarkCategory, BenchmarkFramework, BenchmarkKPI, BenchmarkPerformanceLevel, BenchmarkPeriod, BenchmarkTarget
from .sources import registered_calculators


CALCULATOR_LABELS = {
    "ACCIDENT_CLOSURE_RATE": "Injury Closure Rate",
    "AUDIT_PASS_RATE": "Audit Pass Rate",
    "CAPA_CLOSURE_RATE": "CAPA Closure Rate",
    "CHEMICAL_INVENTORY_COMPLIANCE": "Chemical Inventory Compliance",
    "EMERGENCY_DRILL_COMPLETION": "Emergency Drill Completion",
    "HAZARD_CLOSURE_RATE": "Hazard Closure Rate",
    "INSPECTION_SCORE": "Inspection Compliance Score",
    "PERMIT_CLOSURE_RATE": "Permit Closure Rate",
    "PPE_INSPECTION_COMPLETION": "PPE Inspection Completion",
    "TOOLBOX_TALK_COMPLETION": "Toolbox Talk Completion",
    "TRAINING_COMPLETION_RATE": "Training Completion Rate",
}


def calculator_choices():
    """Choices are sourced from the registered calculator keys, never duplicated as logic."""
    return [(code, CALCULATOR_LABELS.get(code, code.replace("_", " ").title())) for code in registered_calculators]


def project_module_choices():
    excluded_modules = {
        "accounts",
        "alert_engine",
        "benchmarking",
        "contractor",
        "dashboards",
        "envdata",
        "environmental_mis",
        "legal_compliance",
        "notifications",
        "organizations",
    }
    choices = [("", "Select a source module")]
    local_apps = sorted(
        (
            config for config in django_apps.get_app_configs()
            if config.name.startswith("apps.")
            and config.label.casefold() not in excluded_modules
        ),
        key=lambda config: config.verbose_name.lower(),
    )
    choices.extend((config.label, config.verbose_name.title()) for config in local_apps)
    return choices


class FrameworkForm(forms.ModelForm):
    class Meta: model = BenchmarkFramework; fields = ["name", "code", "description", "effective_from", "effective_to", "reporting_frequency"]

class CategoryForm(forms.ModelForm):
    class Meta: model = BenchmarkCategory; fields = ["name", "code", "description", "weightage", "display_order", "is_active"]

class KPIForm(forms.ModelForm):
    calculator_code = forms.ChoiceField(
        choices=calculator_choices,
        label="Calculation method",
        help_text="Select the registered plant-scoped calculation used to fetch live source records.",
    )
    source_module = forms.ChoiceField(
        choices=project_module_choices,
        required=False,
        label="Source module",
        help_text="Select the project module whose live plant records this KPI reads.",
    )
    class Meta: model = BenchmarkKPI; fields = ["category", "name", "code", "description", "unit", "calculation_type", "direction", "weightage", "frequency", "calculator_code", "source_module", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep legacy KPI records editable even if their code is not registered.
        current_code = self.instance.calculator_code if self.instance and self.instance.pk else ""
        available_codes = {code for code, _ in self.fields["calculator_code"].choices}
        if current_code and current_code not in available_codes:
            self.fields["calculator_code"].choices = [
                (current_code, f"Legacy / unregistered: {current_code}"),
                *self.fields["calculator_code"].choices,
            ]

class TargetForm(forms.ModelForm):
    class Meta: model = BenchmarkTarget; fields = ["framework", "kpi", "target_type", "plant", "target_value", "effective_from", "effective_to"]

class PerformanceLevelForm(forms.ModelForm):
    class Meta: model = BenchmarkPerformanceLevel; fields = ["framework", "name", "minimum_score", "maximum_score", "display_indicator", "is_active", "display_order"]

class PeriodForm(forms.ModelForm):
    class Meta: model = BenchmarkPeriod; fields = ["framework", "period_type", "start_date", "end_date"]
