from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, DetailView, UpdateView
from .forms import ChemicalForm, ChemicalRequestApprovalForm, ChemicalRequestForm
from .models import Chemical, ChemicalRequest
from .utils import *


class ChemicalCreateView(LoginRequiredMixin, CreateView):
    model = Chemical
    form_class = ChemicalForm
    template_name = 'chemicals/chemical_form.html'
    success_url = reverse_lazy('chemicals:chemical_list')


    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Chemical created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

# =========================================================
# CHEMICAL DETAIL
# =========================================================
class ChemicalDetailView(LoginRequiredMixin, DetailView):
    model = Chemical
    template_name = 'chemicals/chemical_detail.html'
    context_object_name = 'chemical'

    def get_queryset(self):
        return (
            Chemical.objects.select_related(
                'plant',
                'zone',
                'location',
                'sublocation',
                'department',
                'created_by'
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        chemical = self.object

        # =========================================================
        # EHS COMPLIANCE
        # =========================================================
        ehs = chemical.ehs_compliance or {}

        context['ghs_list'] = ehs.get(
            'ghs',
            []
        )

        context['ppe_list'] = ehs.get(
            'ppe',
            []
        )

        # =========================================================
        # ACTIVE SDS
        # =========================================================
        active_sds = chemical.active_sds
        active_sds_version = chemical.active_sds_version

        context['active_sds'] = active_sds
        context['active_sds_version'] = active_sds_version
        context['has_active_sds'] = chemical.has_active_sds

        # =========================================================
        # ACTIVE SDS - HAZARD INFORMATION
        # =========================================================
        active_sds_hazard = None

        if active_sds_version:
            active_sds_hazard = getattr(
                active_sds_version,
                'section_2',
                None
            )

        context['active_sds_hazard'] = active_sds_hazard
        context['has_active_sds_hazard'] = (
            active_sds_hazard is not None
        )

        # =========================================================
        # SDS HISTORY
        # =========================================================
        context['sds_records'] = (
            chemical.sds_records.order_by(
                '-created_at'
            )
        )

        return context
    
class ChemicalUpdateView(LoginRequiredMixin, UpdateView):
    model = Chemical
    form_class = ChemicalForm
    template_name = 'chemicals/chemical_edit.html'
    success_url = reverse_lazy('chemicals:chemical_list')

    def get_form_kwagrs(self):
        kwargs = super().get_form_kwargs()
        kwargs['files'] = self.request.FILES or None

    def form_valid(self, form):
        messages.success(self.request, "Chemical updated successfully.")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['chemical'] = self.object

        return context

class ChemicalListView(LoginRequiredMixin, ListView):
    model = Chemical
    template_name = 'chemicals/chemical_list.html'
    context_object_name = 'chemicals'
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            Chemical.objects.select_related(
                'plant',
                'zone',
                'location',
                'sublocation',
                'department',
                'created_by',
            )
            .all()
            .order_by('-created_at')
        )

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(chemical_name__icontains=search)
                | Q(trade_name__icontains=search)
                | Q(cas_number__icontains=search)
                | Q(supplier__icontains=search)
            )

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Chemical.STATUS_CHOICES
        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
        }
        context['total_chemicals'] = Chemical.objects.count()
        context['pending_requests'] = ChemicalRequest.objects.filter(status='pending').count()
        context['approved_requests'] = ChemicalRequest.objects.filter(status='approved').count()
        return context


class ChemicalRequestCreateView(LoginRequiredMixin, CreateView):
    model = ChemicalRequest
    form_class = ChemicalRequestForm
    template_name = 'chemicals/chemical_request_form.html'
    success_url = reverse_lazy('chemicals:chemical_approvals')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Chemical request submitted successfully and is pending for approval.",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class ChemicalApprovalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'chemicals/chemical_approval_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = ChemicalRequest.objects.select_related(
            'plant',
            'zone',
            'location',
            'sublocation',
            'department',
            'requester_user',
            'approved_by',
            'chemical',
        ).order_by('-created_at')

        pending_requests = list(base_qs.filter(status='pending'))
        approved_requests = list(base_qs.filter(status='approved'))
        rejected_requests = list(base_qs.filter(status='rejected'))

        context.update(
            {
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'rejected_requests': rejected_requests,
                'pending_count': len(pending_requests),
                'approved_count': len(approved_requests),
                'rejected_count': len(rejected_requests),
                'approval_chemical_choices': Chemical.objects.order_by('chemical_name'),
            }
        )
        return context


class ChemicalRequestApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chemical_request = get_object_or_404(ChemicalRequest, pk=pk)

        if chemical_request.status != 'pending':
            messages.error(request, "Only pending requests can be approved.")
            return redirect('chemicals:chemical_approvals')

        form = ChemicalRequestApprovalForm(
            {
                'status': 'approved',
                'chemical': request.POST.get('chemical'),
                'rejection_reason': '',
            },
            instance=chemical_request,
            approver=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Chemical request approved successfully.")
        else:
            messages.error(
                request,
                form.errors.get('__all__', ['Unable to approve the chemical request.'])[0],
            )

        return redirect('chemicals:chemical_approvals')


class ChemicalRequestRejectView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chemical_request = get_object_or_404(ChemicalRequest, pk=pk)

        if chemical_request.status != 'pending':
            messages.error(request, "Only pending requests can be rejected.")
            return redirect('chemicals:chemical_approvals')

        form = ChemicalRequestApprovalForm(
            {
                'status': 'rejected',
                'chemical': '',
                'rejection_reason': request.POST.get('rejection_reason', '').strip(),
            },
            instance=chemical_request,
            approver=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Chemical request rejected successfully.")
        else:
            error_message = form.errors.get(
                'rejection_reason',
                form.errors.get('__all__', ['Unable to reject the chemical request.']),
            )[0]
            messages.error(request, error_message)

        return redirect('chemicals:chemical_approvals')

class ChemicalPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        chemical = get_object_or_404(
            Chemical.objects.select_related(
                'plant',
                'zone',
                'location',
                'sublocation',
                'department',
                'created_by',
            ),
            pk=pk
        )

        return generate_chemical_pdf(chemical)

# views.py

from django.views.generic import TemplateView
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import json

from .models import Chemical


class ChemicalDashboardView(TemplateView):
    template_name = 'chemicals/chemical_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        last_6_months = today - timedelta(days=180)

        qs = Chemical.objects.all()

        # ================= KPI =================
        context['total_chemicals'] = qs.count()
        context['low_stock'] = qs.filter(status='low_stock').count()
        context['out_of_stock'] = qs.filter(status='out_of_stock').count()
        context['expired'] = qs.filter(expiration_date__lt=today).count()

        context['expiring_soon'] = qs.filter(
            expiration_date__range=[today, today + timedelta(days=30)]
        ).count()

        # ================= STATUS CHART =================
        status_data = qs.values('status').annotate(count=Count('id'))
        context['status_labels_json'] = json.dumps([i['status'] for i in status_data])
        context['status_data_json'] = json.dumps([i['count'] for i in status_data])

        # ================= MONTHLY TREND =================
        monthly = (
            qs.filter(created_at__gte=last_6_months)
            .extra(select={'month': "strftime('%%m', created_at)"})
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        context['trend_labels_json'] = json.dumps([f"Month {i['month']}" for i in monthly])
        context['trend_data_json'] = json.dumps([i['count'] for i in monthly])

        # ================= DEPARTMENT =================
        dept_data = qs.values('department__name').annotate(count=Count('id'))
        context['dept_labels_json'] = json.dumps([
            i['department__name'] or "N/A" for i in dept_data
        ])
        context['dept_data_json'] = json.dumps([i['count'] for i in dept_data])

        # ================= EXPIRY =================
        expired = qs.filter(expiration_date__lt=today).count()
        less_30 = qs.filter(expiration_date__range=[today, today + timedelta(days=30)]).count()
        less_90 = qs.filter(expiration_date__range=[today, today + timedelta(days=90)]).count()
        greater_90 = qs.filter(expiration_date__gt=today + timedelta(days=90)).count()

        context['expiry_labels_json'] = json.dumps([
            "Expired", "<30 Days", "30-90 Days", ">90 Days"
        ])
        context['expiry_data_json'] = json.dumps([
            expired, less_30, less_90, greater_90
        ])

        return context