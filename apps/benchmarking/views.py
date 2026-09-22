from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View
from django.db.models import Avg
from apps.accounts.mixins import PermissionRequiredMixin
from apps.organizations.models import Plant
from .forms import CategoryForm, FrameworkForm, KPIForm, PeriodForm, TargetForm, PerformanceLevelForm
from .models import *
from .services import accessible_results, calculate_period, refresh_live_results
from .sources import registered_calculators


class BenchmarkAccessMixin(LoginRequiredMixin, PermissionRequiredMixin): permission_required = "VIEW_BENCHMARKING"

class DashboardView(BenchmarkAccessMixin, TemplateView):
    template_name = "benchmarking/dashboard.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = accessible_results(self.request.user).filter(scope_type="PLANT").select_related("period", "plant").order_by("-period__end_date", "rank")
        latest_date = results.values_list("period__end_date", flat=True).first()
        latest = results.filter(period__end_date=latest_date) if latest_date else results.none()
        context.update({"results": latest, "latest_date": latest_date, "site_count": latest.count(), "average_score": (sum(r.overall_score for r in latest) / latest.count()) if latest.exists() else None, "best_result": latest.order_by("rank").first(), "high_gap_count": BenchmarkGap.objects.filter(benchmark_result__in=latest, priority="HIGH").count(), "can_refresh": self.request.user.is_superuser or self.request.user.has_permission("CALCULATE_BENCHMARK")})
        return context

class FrameworkListView(BenchmarkAccessMixin, ListView): 
    model = BenchmarkFramework; 
    template_name = "benchmarking/framework_list.html"
class FrameworkCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "MANAGE_BENCHMARK_FRAMEWORK"
    model = BenchmarkFramework
    form_class = FrameworkForm
    template_name = "benchmarking/form.html"
    success_url = reverse_lazy("benchmarking:framework_list")
    def form_valid(self, form):
        form.instance.created_by = form.instance.updated_by = self.request.user
        return super().form_valid(form)

class FrameworkUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "MANAGE_BENCHMARK_FRAMEWORK"
    model = BenchmarkFramework
    form_class = FrameworkForm
    template_name = "benchmarking/form.html"
    success_url = reverse_lazy("benchmarking:framework_list")
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

class FrameworkDetailView(BenchmarkAccessMixin, DetailView):
    model = BenchmarkFramework; template_name = "benchmarking/framework_detail.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("categories__kpis")

class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "MANAGE_BENCHMARK_FRAMEWORK"
    model = BenchmarkCategory
    form_class = CategoryForm
    template_name = "benchmarking/category_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.framework = get_object_or_404(BenchmarkFramework, pk=kwargs["framework_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "framework": self.framework,
            "page_title": "Add benchmark category",
            "form_title": "Category details",
            "form_subtitle": f"Configure a scoring category for {self.framework.name}.",
        })
        return context

    def form_valid(self, form):
        form.instance.framework = self.framework
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("benchmarking:framework_detail", kwargs={"pk": self.framework.pk})

class KPIListView(BenchmarkAccessMixin, ListView):
    model = BenchmarkKPI; template_name = "benchmarking/kpi_list.html"
    def get_queryset(self): return super().get_queryset().filter(category__framework_id=self.kwargs["framework_id"]).select_related("category")
class KPICreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "MANAGE_BENCHMARK_KPI"
    model = BenchmarkKPI
    form_class = KPIForm
    template_name = "benchmarking/kpi_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.framework = None
        if self.kwargs.get("framework_id"):
            self.framework = get_object_or_404(BenchmarkFramework, pk=self.kwargs["framework_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.kwargs.get("framework_id"):
            form.fields["category"].queryset = BenchmarkCategory.objects.filter(
                framework_id=self.kwargs["framework_id"], is_active=True
            )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "framework": self.framework,
            "page_title": "Add benchmark KPI",
            "form_title": "KPI details",
            "form_subtitle": f"Configure a KPI for {self.framework.name}." if self.framework else "Configure a new KPI.",
        })
        return context

    def get_success_url(self):
        return reverse_lazy("benchmarking:kpi_list", kwargs={"framework_id": self.object.category.framework_id})

    def form_valid(self, form):
        form.instance.created_by = form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
class KPIUpdateView(KPICreateView, UpdateView):
    def get_object(self): return get_object_or_404(BenchmarkKPI, pk=self.kwargs["pk"])

class TargetListView(BenchmarkAccessMixin, ListView):
    model = BenchmarkTarget; template_name = "benchmarking/target_list.html"
    def get_queryset(self):
        qs = super().get_queryset().select_related("plant", "kpi", "framework")
        if self.request.user.is_superuser or self.request.user.has_permission("VIEW_ALL_BENCHMARK_SITES"):
            return qs
        return qs.filter(plant__in=self.request.user.get_all_plants())
class PerformanceLevelListView(BenchmarkAccessMixin, ListView): model = BenchmarkPerformanceLevel; template_name = "benchmarking/performance_level_list.html"
class PeriodListView(BenchmarkAccessMixin, ListView):
    model = BenchmarkPeriod
    template_name = "benchmarking/period_list.html"

    def get_queryset(self):
        return super().get_queryset().select_related("framework")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create_period"] = (
            self.request.user.is_superuser
            or self.request.user.has_permission("CALCULATE_BENCHMARK")
        )
        return context


class PeriodCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create an open reporting window before its plant results are calculated."""
    permission_required = "CALCULATE_BENCHMARK"
    model = BenchmarkPeriod
    form_class = PeriodForm
    template_name = "benchmarking/period_form.html"
    success_url = reverse_lazy("benchmarking:period_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Benchmark period created. You can calculate it when the source data is ready.")
        return super().form_valid(form)


class PeriodDetailView(BenchmarkAccessMixin, DetailView):
    """Display a read-only, plant-scoped report for one benchmark period."""
    model = BenchmarkPeriod
    template_name = "benchmarking/period_detail.html"

    def dispatch(self, request, *args, **kwargs):
        # This report deliberately returns 403 for an authenticated user who
        # lacks read access, rather than exposing any period context.
        if request.user.is_authenticated and not (
            request.user.is_superuser or request.user.has_permission("VIEW_BENCHMARKING")
        ):
            return HttpResponseForbidden("You do not have permission to view benchmarking.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.object
        user = self.request.user
        results = accessible_results(user).filter(
            period=period, scope_type=BenchmarkResult.Scope.PLANT
        ).select_related("plant", "performance_level").order_by("rank", "-overall_score", "plant__name")
        result_list = list(results)
        result_count = len(result_list)
        levels = list(period.framework.performance_levels.filter(is_active=True).order_by("display_order", "-minimum_score"))
        kpi_results = list(BenchmarkKPIResult.objects.filter(
            benchmark_result__in=results
        ).select_related("benchmark_result__plant", "kpi__category", "performance_level"))

        def level_for(score):
            if score is None:
                return None
            return next((level for level in levels if level.minimum_score <= score <= level.maximum_score), None)

        category_values = {}
        for item in kpi_results:
            category_values.setdefault(item.kpi.category_id, {
                "name": item.kpi.category.name,
                "code": item.kpi.category.code,
                "weight": item.kpi.category.weightage,
                "plants": {},
            })["plants"].setdefault(item.benchmark_result_id, []).append(item.score)

        previous_period = BenchmarkPeriod.objects.filter(
            framework=period.framework, end_date__lt=period.start_date
        ).order_by("-end_date").first()
        previous_averages = {}
        if previous_period:
            previous_items = BenchmarkKPIResult.objects.filter(
                benchmark_result__in=accessible_results(user).filter(
                    period=previous_period, scope_type=BenchmarkResult.Scope.PLANT
                ), score__isnull=False
            ).values("kpi__category_id").annotate(average=Avg("score"))
            previous_averages = {item["kpi__category_id"]: item["average"] for item in previous_items}

        category_rows = []
        heatmap = {}
        for result in result_list:
            heatmap[result.plant.name] = {}
        for category_id, details in category_values.items():
            plant_scores = []
            for result in result_list:
                scores = [score for score in details["plants"].get(result.pk, []) if score is not None]
                score = sum(scores) / len(scores) if scores else None
                if score is not None:
                    plant_scores.append((result.plant.name, score))
                level = level_for(score)
                heatmap[result.plant.name][details["code"]] = {
                    "score": score,
                    "level_name": level.name if level else "Not rated",
                    "level_indicator": level.display_indicator if level else "",
                }
            average = sum(score for _, score in plant_scores) / len(plant_scores) if plant_scores else None
            previous_average = previous_averages.get(category_id)
            category_rows.append({
                "name": details["name"], "code": details["code"], "weight": details["weight"],
                "average": average,
                "best": max(plant_scores, key=lambda item: item[1]) if plant_scores else None,
                "worst": min(plant_scores, key=lambda item: item[1]) if plant_scores else None,
                "delta": average - previous_average if average is not None and previous_average is not None else None,
            })

        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        top_gaps = sorted(
            BenchmarkGap.objects.filter(benchmark_result__in=results).select_related("kpi", "benchmark_result__plant"),
            key=lambda gap: (priority_order.get(gap.priority, 3), -abs(gap.gap_value)),
        )[:10]
        insights = sorted(
            BenchmarkInsight.objects.filter(benchmark_result__in=results, status="OPEN").select_related("related_kpi", "benchmark_result__plant"),
            key=lambda insight: priority_order.get(insight.priority, 3),
        )[:10]
        can = lambda code: user.is_superuser or user.has_permission(code)
        average_score = sum(result.overall_score for result in result_list) / result_count if result_count else None
        best_result = result_list[0] if result_list else None
        worst_result = result_list[-1] if result_count > 1 else None

        context.update({
            "results": result_list, "result_count": result_count, "average_score": average_score,
            "best_result": best_result, "worst_result": worst_result,
            "above_target_count": sum(1 for result in result_list if result.target_score is not None and result.overall_score >= result.target_score),
            "distribution": [{"level_name": level.name, "level_color": level.display_indicator, "count": sum(1 for result in result_list if result.performance_level_id == level.id)} for level in levels],
            "category_rows": category_rows, "heatmap": heatmap,
            "heatmap_categories": [row["code"] for row in category_rows],
            "top_gaps": top_gaps, "insights": insights,
            "sibling_periods": BenchmarkPeriod.objects.filter(framework=period.framework, period_type=period.period_type).order_by("start_date"),
            "is_locked": period.status == BenchmarkPeriod.Status.PUBLISHED,
            "can_calculate": period.status in {BenchmarkPeriod.Status.OPEN, BenchmarkPeriod.Status.CALCULATED, BenchmarkPeriod.Status.FAILED} and can("CALCULATE_BENCHMARK"),
            "can_publish": period.status == BenchmarkPeriod.Status.CALCULATED and can("PUBLISH_BENCHMARK"),
            "can_edit": period.status not in {BenchmarkPeriod.Status.PUBLISHED, BenchmarkPeriod.Status.CALCULATING} and can("MANAGE_BENCHMARK_PERIOD"),
            "can_export": result_count > 0 and can("EXPORT_BENCHMARK_REPORT"),
            "can_generate": can("MANAGE_BENCHMARK_PERIOD"),
            "registered_calculator_count": len(registered_calculators),
            "total_kpi_count": len(kpi_results),
            "populated_kpi_count": sum(1 for item in kpi_results if item.score is not None),
            "skipped_kpi_count": sum(1 for item in kpi_results if item.score is None),
        })
        return context

class PeriodCalculateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "CALCULATE_BENCHMARK"
    def post(self, request, pk):
        period = get_object_or_404(BenchmarkPeriod, pk=pk)
        allowed_plants = Plant.objects.filter(is_active=True) if request.user.is_superuser or request.user.has_permission("VIEW_ALL_BENCHMARK_SITES") else request.user.get_all_plants()
        try: calculate_period(period, plants=allowed_plants); messages.success(request, "Benchmark period calculated for your authorized plants.")
        except Exception: messages.error(request, "Calculation failed; the period was marked failed.")
        return redirect("benchmarking:period_detail", pk=pk)


class PeriodRefreshView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Explicit user-triggered refresh; GET requests never recalculate results."""
    permission_required = "CALCULATE_BENCHMARK"

    def post(self, request):
        refresh_live_results(request.user)
        messages.success(request, "Current unpublished benchmark periods were refreshed for your authorized plants.")
        return redirect("benchmarking:dashboard")

class PeriodPublishView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "PUBLISH_BENCHMARK"
    def post(self, request, pk):
        from django.utils import timezone
        period = get_object_or_404(BenchmarkPeriod, pk=pk)
        if period.status != period.Status.CALCULATED: return HttpResponseForbidden("Only calculated periods may be published.")
        period.status = period.Status.PUBLISHED; period.published_at = timezone.now(); period.published_by = request.user; period.save(); return redirect("benchmarking:period_detail", pk=pk)

class ResultListView(BenchmarkAccessMixin, ListView):
    template_name = "benchmarking/result_list.html"; context_object_name = "results"
    def get_queryset(self):
        return accessible_results(self.request.user).filter(scope_type="PLANT").order_by("-period__end_date", "rank")

class PerformanceRankingView(BenchmarkAccessMixin, ListView):
    template_name = "benchmarking/performance_ranking.html"
    context_object_name = "results"

    def get_queryset(self):
        results = accessible_results(self.request.user).filter(scope_type="PLANT")
        latest_period_id = results.order_by("-period__end_date", "-period_id").values_list("period_id", flat=True).first()
        if not latest_period_id:
            self.latest_date = None
            return results.none()
        latest_period = results.filter(period_id=latest_period_id).values_list("period__end_date", flat=True).first()
        self.latest_date = latest_period
        return results.filter(period_id=latest_period_id).select_related(
            "period", "plant", "performance_level"
        ).order_by("rank", "-overall_score", "plant__name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = context["results"]
        context.update({
            "latest_date": self.latest_date,
            "site_count": results.count(),
            "average_score": (sum(result.overall_score for result in results) / results.count()) if results.exists() else None,
            "top_result": results.first(),
        })
        return context

class GapListView(BenchmarkAccessMixin, ListView):
    template_name = "benchmarking/gap_list.html"; context_object_name = "gaps"
    def get_queryset(self):
        return BenchmarkGap.objects.filter(benchmark_result__in=accessible_results(self.request.user)).select_related("benchmark_result", "kpi")

class ExcelExportView(BenchmarkAccessMixin, View):
    permission_required = "EXPORT_BENCHMARK_REPORT"
    def get(self, request):
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Benchmark results"; ws.append(["Period", "Plant", "Score", "Rank", "Trend"])
        for r in accessible_results(request.user).filter(scope_type="PLANT").select_related("period", "plant"): ws.append([str(r.period.end_date), r.plant.name, float(r.overall_score), r.rank, r.trend])
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"); response["Content-Disposition"] = 'attachment; filename="benchmark-results.xlsx"'; wb.save(response); return response
