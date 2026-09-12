from django.shortcuts import render

# Create your views here.
# apps/reports/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.views import View

from .registry import REGISTRY
from .services.excel_engine import workbook_http_response


class ModuleExportView(LoginRequiredMixin, View):
    """
    One view for every module.
    URL: /reports/<module_slug>/export/
    """
    def get(self, request, module_slug):
        entry = REGISTRY.get(module_slug)
        if not entry:
            raise Http404(f"Unknown module: {module_slug}")
        spec = entry["spec_builder"](request)
        if isinstance(spec, HttpResponse):
            return spec
        return workbook_http_response(spec)
