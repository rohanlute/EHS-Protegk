from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View
from apps.accounts.mixins import PermissionRequiredMixin
from apps.organizations.models import Plant
from .forms import CategoryForm, FrameworkForm, KPIForm, PeriodForm, TargetForm, PerformanceLevelForm
from .models import *
from .services import accessible_results, calculate_period, refresh_live_results


class BenchmarkAccessMixin(LoginRequiredMixin, PermissionRequiredMixin): permission_required = "VIEW_BENCHMARKING"

class DashboardView(BenchmarkAccessMixin, TemplateView):
    template_name = "benchmarking/dashboard.html"
    def get_context_data(self, **kwargs):
        refresh_live_results(self.request.user)
        context = super().get_context_data(**kwargs)
        results = accessible_results(self.request.user).filter(scope_type="PLANT").select_related("period", "plant").order_by("-period__end_date", "rank")
        latest_date = results.values_list("period__end_date", flat=True).first()
        latest = results.filter(period__end_date=latest_date) if latest_date else results.none()
        context.update({"results": latest, "latest_date": latest_date, "site_count": latest.count(), "average_score": (sum(r.overall_score for r in latest) / latest.count()) if latest.exists() else None, "best_result": latest.order_by("rank").first(), "high_gap_count": BenchmarkGap.objects.filter(benchmark_result__in=latest, priority="HIGH").count()})
        return context

class FrameworkListView(BenchmarkAccessMixin, ListView): model = BenchmarkFramework; template_name = "benchmarking/framework_list.html"
class FrameworkCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "MANAGE_BENCHMARK_FRAMEWORK"; model = BenchmarkFramework; form_class = FrameworkForm; template_name = "benchmarking/form.html"; success_url = reverse_lazy("benchmarking:framework_list")
    def form_valid(self, form): form.instance.created_by = form.instance.updated_by = self.request.user; return super().form_valid(form)
class FrameworkUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "MANAGE_BENCHMARK_FRAMEWORK"; model = BenchmarkFramework; form_class = FrameworkForm; template_name = "benchmarking/form.html"; success_url = reverse_lazy("benchmarking:framework_list")
    def form_valid(self, form): form.instance.updated_by = self.request.user; return super().form_valid(form)
class FrameworkDetailView(BenchmarkAccessMixin, DetailView):
    model = BenchmarkFramework; template_name = "benchmarking/framework_detail.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("categories__kpis")

class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "MANAGE_BENCHMARK_FRAMEWORK"
    model = BenchmarkCategory; form_class = CategoryForm; template_name = "benchmarking/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.framework = get_object_or_404(BenchmarkFramework, pk=kwargs["framework_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Add benchmark category", "form_title": "Category details", "form_subtitle": f"Configure a scoring category for {self.framework.name}."})
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
    permission_required = "MANAGE_BENCHMARK_KPI"; model = BenchmarkKPI; form_class = KPIForm; template_name = "benchmarking/form.html"
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.kwargs.get("framework_id"):
            form.fields["category"].queryset = BenchmarkCategory.objects.filter(framework_id=self.kwargs["framework_id"], is_active=True)
        return form
    def get_success_url(self): return reverse_lazy("benchmarking:kpi_list", kwargs={"framework_id": self.object.category.framework_id})
    def form_valid(self, form): form.instance.created_by = form.instance.updated_by = self.request.user; return super().form_valid(form)
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
class PeriodListView(BenchmarkAccessMixin, ListView): model = BenchmarkPeriod; template_name = "benchmarking/period_list.html"
class PeriodDetailView(BenchmarkAccessMixin, DetailView): model = BenchmarkPeriod; template_name = "benchmarking/period_detail.html"

class PeriodCalculateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "CALCULATE_BENCHMARK"
    def post(self, request, pk):
        period = get_object_or_404(BenchmarkPeriod, pk=pk)
        allowed_plants = Plant.objects.filter(is_active=True) if request.user.is_superuser or request.user.has_permission("VIEW_ALL_BENCHMARK_SITES") else request.user.get_all_plants()
        try: calculate_period(period, plants=allowed_plants); messages.success(request, "Benchmark period calculated for your authorized plants.")
        except Exception: messages.error(request, "Calculation failed; the period was marked failed.")
        return redirect("benchmarking:period_detail", pk=pk)

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
        refresh_live_results(self.request.user)
        return accessible_results(self.request.user).filter(scope_type="PLANT").order_by("-period__end_date", "rank")

class PerformanceRankingView(BenchmarkAccessMixin, ListView):
    template_name = "benchmarking/performance_ranking.html"
    context_object_name = "results"

    def get_queryset(self):
        refresh_live_results(self.request.user)
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
        refresh_live_results(self.request.user)
        return BenchmarkGap.objects.filter(benchmark_result__in=accessible_results(self.request.user)).select_related("benchmark_result", "kpi")

class ExcelExportView(BenchmarkAccessMixin, View):
    permission_required = "EXPORT_BENCHMARK_REPORT"
    def get(self, request):
        from openpyxl import Workbook
        refresh_live_results(request.user)
        wb = Workbook(); ws = wb.active; ws.title = "Benchmark results"; ws.append(["Period", "Plant", "Score", "Rank", "Trend"])
        for r in accessible_results(request.user).filter(scope_type="PLANT").select_related("period", "plant"): ws.append([str(r.period.end_date), r.plant.name, float(r.overall_score), r.rank, r.trend])
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"); response["Content-Disposition"] = 'attachment; filename="benchmark-results.xlsx"'; wb.save(response); return response
