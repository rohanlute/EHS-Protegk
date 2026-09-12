from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from .constants import TREND_THRESHOLD
from .engine.scoring import calculate_kpi_score, calculate_overall_score
from .models import BenchmarkGap, BenchmarkInsight, BenchmarkKPIResult, BenchmarkPeriod, BenchmarkResult
from .sources import calculate_kpi_value
from apps.organizations.models import Plant


def accessible_results(user):
    qs = BenchmarkResult.objects.select_related("plant", "department", "period", "performance_level")
    if user.is_superuser or user.has_permission("VIEW_ALL_BENCHMARK_SITES"):
        return qs.filter(scope_type=BenchmarkResult.Scope.PLANT, plant__isnull=False)
    plant_ids = [p.pk for p in user.get_all_plants()]
    return qs.filter(scope_type=BenchmarkResult.Scope.PLANT, plant_id__in=plant_ids)


def refresh_live_results(user):
    """Refresh the current, unpublished benchmark periods for the user's plants."""
    today = timezone.localdate()
    periods = BenchmarkPeriod.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
    ).exclude(status=BenchmarkPeriod.Status.PUBLISHED).select_related("framework")
    plants = Plant.objects.filter(is_active=True)
    if not user.is_superuser and not user.has_permission("VIEW_ALL_BENCHMARK_SITES"):
        plants = plants.filter(pk__in=[plant.pk for plant in user.get_all_plants()])
    for period in periods:
        calculate_period(period, plants=plants)


def target_for(kpi, framework, plant, date):
    """Return the target configured for this exact plant; there is no company fallback."""
    targets = framework.targets.filter(kpi=kpi, effective_from__lte=date).filter(models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=date))
    found = targets.filter(target_type="PLANT", plant=plant, department__isnull=True).order_by("-effective_from").first()
    return found.target_value if found else None


def performance_level(framework, score):
    return framework.performance_levels.filter(is_active=True, minimum_score__lte=score, maximum_score__gte=score).first()


@transaction.atomic
def calculate_period(period, plants=None):
    """Persist snapshots for specified active plants; no company-level data is created."""
    period.status = period.Status.CALCULATING; period.save(update_fields=["status", "updated_at"])
    framework = period.framework
    categories = framework.categories.filter(is_active=True).prefetch_related("kpis")
    try:
        plant_queryset = Plant.objects.filter(is_active=True)
        if plants is not None:
            plant_queryset = plant_queryset.filter(pk__in=[plant.pk for plant in plants])
        for plant in plant_queryset:
            result, _ = BenchmarkResult.objects.update_or_create(framework=framework, period=period, scope_type="PLANT", plant=plant, department=None, defaults={"overall_score": 0})
            category_scores = []
            for category in categories:
                kpi_scores = []
                for kpi in category.kpis.filter(is_active=True):
                    raw, count = calculate_kpi_value(kpi.calculator_code, plant, None, period.start_date, period.end_date)
                    target = target_for(kpi, framework, plant, period.end_date)
                    score = calculate_kpi_score(raw, target, kpi.direction)
                    weighted = (score * kpi.weightage / 100) if score is not None else None
                    BenchmarkKPIResult.objects.update_or_create(benchmark_result=result, kpi=kpi, defaults={"raw_value": raw, "target_value": target, "score": score, "weightage": kpi.weightage, "weighted_score": weighted, "direction": kpi.direction, "gap": (raw-target if raw is not None and target is not None else None), "source_record_count": count})
                    if score is not None: kpi_scores.append((score, kpi.weightage))
                category_scores.append((calculate_overall_score(kpi_scores), category.weightage))
            overall = calculate_overall_score(category_scores)
            previous = BenchmarkResult.objects.filter(framework=framework, scope_type="PLANT", plant=plant, period__end_date__lt=period.start_date).order_by("-period__end_date").first()
            result.overall_score = overall; result.target_score = Decimal("100"); result.target_gap = overall - 100; result.previous_score = previous.overall_score if previous else None; result.previous_gap = overall - previous.overall_score if previous else None
            result.trend = "STABLE" if not previous or abs(result.previous_gap) < Decimal(str(TREND_THRESHOLD)) else ("IMPROVING" if result.previous_gap > 0 else "DECLINING")
            result.performance_level = performance_level(framework, overall); result.save()
            _gaps_and_insights(result)
        _rank(period, framework)
        period.status = period.Status.CALCULATED; period.calculated_at = timezone.now(); period.save(update_fields=["status", "calculated_at", "updated_at"])
    except Exception:
        period.status = period.Status.FAILED; period.save(update_fields=["status", "updated_at"]); raise


def _rank(period, framework):
    results = list(BenchmarkResult.objects.filter(period=period, framework=framework, scope_type="PLANT").order_by("-overall_score", "plant__name"))
    for position, result in enumerate(results, 1):
        result.rank = position
    BenchmarkResult.objects.bulk_update(results, ["rank"])
    best = results[0].overall_score if results else None
    if best is not None:
        for result in results: result.best_performer_gap = result.overall_score - best
        BenchmarkResult.objects.bulk_update(results, ["best_performer_gap"])


def _gaps_and_insights(result):
    result.gaps.all().delete(); result.insights.all().delete()
    for item in result.kpi_results.select_related("kpi", "kpi__category").filter(score__lt=100):
        priority = "HIGH" if item.score < 60 else "MEDIUM" if item.score < 80 else "LOW"
        BenchmarkGap.objects.create(benchmark_result=result, kpi=item.kpi, category=item.kpi.category, gap_type="KPI", actual_value=item.raw_value or 0, reference_value=item.target_value or 0, gap_value=item.gap or 0, priority=priority, reason="KPI is below its configured target.")
        if priority == "HIGH": BenchmarkInsight.objects.create(benchmark_result=result, title=f"Improve {item.kpi.name}", description="This KPI is materially below target.", reason="Calculated score below 60.", priority=priority, recommendation="Review source records, assign actions, and track closure.", related_kpi=item.kpi, related_category=item.kpi.category)
