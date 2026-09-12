from django.urls import path
from . import views
app_name = "benchmarking"
urlpatterns = [
 path("", views.DashboardView.as_view(), name="dashboard"), path("frameworks/", views.FrameworkListView.as_view(), name="framework_list"), path("frameworks/create/", views.FrameworkCreateView.as_view(), name="framework_create"), path("frameworks/<int:pk>/", views.FrameworkDetailView.as_view(), name="framework_detail"), path("frameworks/<int:pk>/edit/", views.FrameworkUpdateView.as_view(), name="framework_update"), path("frameworks/<int:framework_id>/categories/create/", views.CategoryCreateView.as_view(), name="category_create"),
 path("frameworks/<int:framework_id>/kpis/", views.KPIListView.as_view(), name="kpi_list"), path("frameworks/<int:framework_id>/kpis/create/", views.KPICreateView.as_view(), name="kpi_create"), path("kpis/<int:pk>/edit/", views.KPIUpdateView.as_view(), name="kpi_update"),
 path("targets/", views.TargetListView.as_view(), name="target_list"), path("performance-levels/", views.PerformanceLevelListView.as_view(), name="performance_level_list"), path("sites/", views.ResultListView.as_view(), name="site_comparison"), path("ranking/", views.PerformanceRankingView.as_view(), name="ranking"), path("heatmap/", views.ResultListView.as_view(), name="heatmap"), path("gaps/", views.GapListView.as_view(), name="gap_analysis"),
 path("periods/", views.PeriodListView.as_view(), name="period_list"), path("periods/<int:pk>/", views.PeriodDetailView.as_view(), name="period_detail"), path("periods/<int:pk>/calculate/", views.PeriodCalculateView.as_view(), name="period_calculate"), path("periods/<int:pk>/publish/", views.PeriodPublishView.as_view(), name="period_publish"), path("reports/export/excel/", views.ExcelExportView.as_view(), name="export_excel"),
]
