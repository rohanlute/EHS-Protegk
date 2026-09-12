# apps/reports/urls.py
from django.urls import path
from .views import ModuleExportView

app_name = "reports"

urlpatterns = [
    path("<slug:module_slug>/export/", ModuleExportView.as_view(), name="module_export"),
]