from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.organizations.models import Department, Plant


class BenchmarkFramework(models.Model):
    class Status(models.TextChoices): DRAFT = "DRAFT", "Draft"; ACTIVE = "ACTIVE", "Active"; ARCHIVED = "ARCHIVED", "Archived"
    class Frequency(models.TextChoices): MONTH = "MONTH", "Monthly"; QUARTER = "QUARTER", "Quarterly"; YEAR = "YEAR", "Yearly"
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    reporting_frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTH)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_benchmark_frameworks")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="updated_benchmark_frameworks")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["-effective_from", "name"]
    def clean(self):
        if self.effective_to and self.effective_to < self.effective_from: raise ValidationError("Effective end date must not precede effective start date.")
    def __str__(self): return self.name


class BenchmarkCategory(models.Model):
    framework = models.ForeignKey(BenchmarkFramework, on_delete=models.PROTECT, related_name="categories")
    name = models.CharField(max_length=150); code = models.CharField(max_length=50); description = models.TextField(blank=True)
    weightage = models.DecimalField(max_digits=5, decimal_places=2)
    display_order = models.PositiveSmallIntegerField(default=0); is_active = models.BooleanField(default=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["framework", "code"], name="benchmark_category_code_per_framework")]; ordering = ["display_order", "name"]
    def clean(self):
        if not Decimal("0") < self.weightage <= Decimal("100"): raise ValidationError("Category weightage must be between 0 and 100.")
    def __str__(self): return self.name


class BenchmarkKPI(models.Model):
    class Direction(models.TextChoices): HIGHER = "HIGHER_IS_BETTER", "Higher is better"; LOWER = "LOWER_IS_BETTER", "Lower is better"
    class Frequency(models.TextChoices): MONTH = "MONTH", "Monthly"; QUARTER = "QUARTER", "Quarterly"; YEAR = "YEAR", "Yearly"
    category = models.ForeignKey(BenchmarkCategory, on_delete=models.PROTECT, related_name="kpis")
    name = models.CharField(max_length=200); code = models.CharField(max_length=50); description = models.TextField(blank=True); unit = models.CharField(max_length=50, blank=True)
    calculation_type = models.CharField(max_length=50, default="PERCENTAGE")
    direction = models.CharField(max_length=20, choices=Direction.choices)
    weightage = models.DecimalField(max_digits=5, decimal_places=2); frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTH)
    calculator_code = models.CharField(max_length=80); source_module = models.CharField(max_length=80, blank=True); is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_benchmark_kpis"); updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="updated_benchmark_kpis")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["category", "code"], name="benchmark_kpi_code_per_category")]; ordering = ["category", "name"]
    def clean(self):
        if not Decimal("0") < self.weightage <= Decimal("100"): raise ValidationError("KPI weightage must be between 0 and 100.")
    def __str__(self): return self.name


class BenchmarkTarget(models.Model):
    class Type(models.TextChoices): PLANT = "PLANT", "Plant"
    framework = models.ForeignKey(BenchmarkFramework, on_delete=models.PROTECT, related_name="targets"); kpi = models.ForeignKey(BenchmarkKPI, on_delete=models.PROTECT, related_name="targets")
    target_type = models.CharField(max_length=15, choices=Type.choices); plant = models.ForeignKey(Plant, null=True, blank=True, on_delete=models.PROTECT); department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    target_value = models.DecimalField(max_digits=14, decimal_places=4); effective_from = models.DateField(); effective_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_benchmark_targets"); updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="updated_benchmark_targets")
    class Meta: indexes = [models.Index(fields=["framework", "kpi", "target_type"])]
    def clean(self):
        if self.kpi_id and self.framework_id and self.kpi.category.framework_id != self.framework_id: raise ValidationError("KPI must belong to the selected framework.")
        if self.target_type != self.Type.PLANT or not self.plant_id or self.department_id:
            raise ValidationError("Benchmark targets are plant-scoped. Select a plant and leave department empty.")
        if self.effective_to and self.effective_to < self.effective_from: raise ValidationError("Target end date must not precede start date.")


class BenchmarkPerformanceLevel(models.Model):
    framework = models.ForeignKey(BenchmarkFramework, on_delete=models.PROTECT, related_name="performance_levels"); name = models.CharField(max_length=80)
    minimum_score = models.DecimalField(max_digits=5, decimal_places=2); maximum_score = models.DecimalField(max_digits=5, decimal_places=2); display_indicator = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True); display_order = models.PositiveSmallIntegerField(default=0)
    class Meta: ordering = ["display_order", "-minimum_score"]
    def clean(self):
        if not (Decimal("0") <= self.minimum_score <= self.maximum_score <= Decimal("100")): raise ValidationError("Performance ranges must be within 0–100.")
        overlaps = BenchmarkPerformanceLevel.objects.filter(framework=self.framework, is_active=True, minimum_score__lte=self.maximum_score, maximum_score__gte=self.minimum_score).exclude(pk=self.pk)
        if overlaps.exists(): raise ValidationError("Performance level ranges cannot overlap.")


class BenchmarkPeriod(models.Model):
    class Type(models.TextChoices): MONTH = "MONTH", "Month"; QUARTER = "QUARTER", "Quarter"; YEAR = "YEAR", "Year"
    class Status(models.TextChoices): OPEN = "OPEN", "Open"; CALCULATING = "CALCULATING", "Calculating"; CALCULATED = "CALCULATED", "Calculated"; FAILED = "FAILED", "Failed"; PUBLISHED = "PUBLISHED", "Published"
    framework = models.ForeignKey(BenchmarkFramework, on_delete=models.PROTECT, related_name="periods"); period_type = models.CharField(max_length=10, choices=Type.choices)
    start_date = models.DateField(); end_date = models.DateField(); status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    calculated_at = models.DateTimeField(null=True, blank=True); published_at = models.DateTimeField(null=True, blank=True); created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_benchmark_periods"); published_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="published_benchmark_periods")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["framework", "period_type", "start_date", "end_date"], name="unique_benchmark_period")]; ordering = ["-end_date"]
    def clean(self):
        if self.end_date < self.start_date: raise ValidationError("Period end date must not precede start date.")


class BenchmarkResult(models.Model):
    class Scope(models.TextChoices): PLANT = "PLANT", "Plant"
    class Trend(models.TextChoices): IMPROVING = "IMPROVING", "Improving"; STABLE = "STABLE", "Stable"; DECLINING = "DECLINING", "Declining"
    framework = models.ForeignKey(BenchmarkFramework, on_delete=models.PROTECT, related_name="results"); period = models.ForeignKey(BenchmarkPeriod, on_delete=models.CASCADE, related_name="results"); scope_type = models.CharField(max_length=12, choices=Scope.choices)
    plant = models.ForeignKey(Plant, null=True, blank=True, on_delete=models.PROTECT); department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2); performance_level = models.ForeignKey(BenchmarkPerformanceLevel, null=True, blank=True, on_delete=models.SET_NULL)
    target_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True); target_gap = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True); previous_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True); previous_gap = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True); best_performer_gap = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    trend = models.CharField(max_length=12, choices=Trend.choices, default=Trend.STABLE); rank = models.PositiveIntegerField(null=True, blank=True); created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["framework", "period", "scope_type", "plant", "department"], name="unique_benchmark_result_scope")]; indexes = [models.Index(fields=["period", "scope_type", "rank"])]


class BenchmarkKPIResult(models.Model):
    benchmark_result = models.ForeignKey(BenchmarkResult, on_delete=models.CASCADE, related_name="kpi_results"); kpi = models.ForeignKey(BenchmarkKPI, on_delete=models.PROTECT)
    raw_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True); target_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True); score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True); weightage = models.DecimalField(max_digits=5, decimal_places=2); weighted_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    direction = models.CharField(max_length=20, choices=BenchmarkKPI.Direction.choices); gap = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True); performance_level = models.ForeignKey(BenchmarkPerformanceLevel, null=True, blank=True, on_delete=models.SET_NULL); source_record_count = models.PositiveIntegerField(default=0); calculated_at = models.DateTimeField(auto_now_add=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["benchmark_result", "kpi"], name="unique_benchmark_kpi_result")]


class BenchmarkGap(models.Model):
    class Type(models.TextChoices): KPI = "KPI", "KPI"; CATEGORY = "CATEGORY", "Category"; TARGET = "TARGET", "Target"; BEST = "BEST_PERFORMER", "Best performer"; PREVIOUS = "PREVIOUS_PERIOD", "Previous period"
    benchmark_result = models.ForeignKey(BenchmarkResult, on_delete=models.CASCADE, related_name="gaps"); kpi = models.ForeignKey(BenchmarkKPI, null=True, blank=True, on_delete=models.SET_NULL); category = models.ForeignKey(BenchmarkCategory, null=True, blank=True, on_delete=models.SET_NULL)
    gap_type = models.CharField(max_length=20, choices=Type.choices); actual_value = models.DecimalField(max_digits=14, decimal_places=4); reference_value = models.DecimalField(max_digits=14, decimal_places=4); gap_value = models.DecimalField(max_digits=14, decimal_places=4); priority = models.CharField(max_length=10, choices=[("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")]); reason = models.TextField(blank=True); created_at = models.DateTimeField(auto_now_add=True)


class BenchmarkInsight(models.Model):
    benchmark_result = models.ForeignKey(BenchmarkResult, on_delete=models.CASCADE, related_name="insights"); title = models.CharField(max_length=255); description = models.TextField(); reason = models.TextField(blank=True); priority = models.CharField(max_length=10, choices=[("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")]); recommendation = models.TextField(blank=True); related_kpi = models.ForeignKey(BenchmarkKPI, null=True, blank=True, on_delete=models.SET_NULL); related_category = models.ForeignKey(BenchmarkCategory, null=True, blank=True, on_delete=models.SET_NULL); status = models.CharField(max_length=15, choices=[("OPEN", "Open"), ("ACKNOWLEDGED", "Acknowledged"), ("RESOLVED", "Resolved")], default="OPEN"); created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
