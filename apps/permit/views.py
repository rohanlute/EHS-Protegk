from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.views import View
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from django.db.models import Q, Prefetch, Count
from .forms import *
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .utils import generate_permit_pdf
import json

# PERMIT TYPE LIST VIEW
class PermitTypeListView(LoginRequiredMixin, ListView):
    model = PermitType
    template_name = 'permit/permit_type_list.html'
    context_object_name = 'permit_types'
    paginate_by = 10

    def get_queryset(self):
        queryset = PermitType.objects.all().order_by('-created_at')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Permit Types'
        context['search_query'] = self.request.GET.get('search', '')
        context['active_count'] = PermitType.objects.filter(is_active=True).count()
        return context

# PERMIT TYPE CREATE VIEW
class PermitTypeCreateView(LoginRequiredMixin, CreateView):
    model = PermitType
    fields = ['name', 'code', 'description', 'is_active']
    template_name = 'permit/permit_type_form.html'
    success_url = reverse_lazy('permit:permit_type_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Permit Type created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context


# PERMIT TYPE UPDATE VIEW
class PermitTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = PermitType
    fields = ['name', 'code', 'description', 'is_active']
    template_name = 'permit/permit_type_form.html'
    success_url = reverse_lazy('permit:permit_type_list')

    def form_valid(self, form):
        messages.success(self.request, "Permit Type updated successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

# PERMIT TYPE DELETE VIEW
class PermitTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = PermitType
    template_name = 'permit/permit_type_confirm_delete.html'
    success_url = reverse_lazy('permit:permit_type_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Permit Type deleted successfully.")
        return super().delete(request, *args, **kwargs)

class PermitCreateView(LoginRequiredMixin, CreateView):
    model = Permit
    form_class = PermitForm
    template_name = 'permit/permit_create.html'
    success_url = reverse_lazy('permit:permit_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.method == "POST":
            context['contractor_formset'] = PermitContractorFormSet(
                self.request.POST
            )
            context['attachment_formset'] = PermitAttachmentFormSet(
                self.request.POST,
                self.request.FILES
            )
        else:
            context['contractor_formset'] = PermitContractorFormSet()
            context['attachment_formset'] = PermitAttachmentFormSet()

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        contractor_formset = context['contractor_formset']
        attachment_formset = context['attachment_formset']

        if contractor_formset.is_valid() and attachment_formset.is_valid():

            # NEW: set requester + draft status
            form.instance.requester_user = self.request.user
            form.instance.status = 'draft'

            self.object = form.save()

            # LOG: created
            PermitApprovalLog.objects.create(
                permit=self.object,
                action='created',
                performed_by=self.request.user,
                to_status='draft'
            )

            contractor_formset.instance = self.object
            contractor_formset.save()

            attachments = attachment_formset.save(commit=False)
            for att in attachments:
                if att.file or att.description:
                    att.permit = self.object
                    att.save()

            return super().form_valid(form)

        return self.form_invalid(form)

class PermitListView(LoginRequiredMixin, ListView):
    model = Permit
    template_name = 'permit/permit_list.html'
    context_object_name = 'permits'
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            Permit.objects
            .select_related(
                'permit_type',
                'plant',
                'zone',
                'location',
                'department',
                'requester_user'
            )
            .all()
            .order_by('-created_at')
        )
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(permit_number__icontains=search) |
                Q(requester_name__icontains=search) |
                Q(job_description__icontains=search) |
                Q(contractor_company__icontains=search)
            )

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        permit_type = self.request.GET.get('permit_type')
        if permit_type:
            queryset = queryset.filter(permit_type_id=permit_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['status_choices'] = Permit.STATUS_CHOICES
        context['permit_types'] = (
            Permit.objects.values_list('permit_type__id', 'permit_type__name')
            .distinct()
        )

        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'permit_type': self.request.GET.get('permit_type', ''),
        }

        return context


class PermitAnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'permit/permit_analytics_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period_days = int(self.request.GET.get('period', 30))
        if period_days not in [7, 30, 90, 365]:
            period_days = 30

        now = timezone.now()
        period_start = now - timedelta(days=period_days)
        previous_period_start = period_start - timedelta(days=period_days)

        permits = (
            Permit.objects.select_related('permit_type', 'department', 'location', 'plant')
            .prefetch_related('approval_logs')
            .all()
        )

        period_permits = permits.filter(created_at__gte=period_start)
        previous_period_permits = permits.filter(created_at__gte=previous_period_start, created_at__lt=period_start)

        active_statuses = ['approved', 'active']
        active_permits_count = permits.filter(status__in=active_statuses).count()
        total_permits_count = permits.count()
        pending_permits_count = permits.filter(status__in=['pending', 'reapproval']).count()
        expired_permits_count = permits.filter(status__in=active_statuses, end_date__lt=now).count()

        pending_previous = previous_period_permits.filter(status__in=['pending', 'reapproval']).count()
        pending_change = pending_permits_count - pending_previous

        new_permits_this_week = permits.filter(created_at__gte=now - timedelta(days=7)).count()
        permits_this_month = permits.filter(created_at__year=now.year, created_at__month=now.month).count()

        weekly_ranges = []
        weekly_labels = []
        for i in range(4, -1, -1):
            start = (now - timedelta(days=(i + 1) * 7 - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (now - timedelta(days=i * 7)).replace(hour=23, minute=59, second=59, microsecond=999999)
            weekly_ranges.append((start, end))
            weekly_labels.append(f"Week {5 - i}")

        submitted_trend = []
        approved_trend = []
        rejected_trend = []
        weekly_activity = []
        for start, end in weekly_ranges:
            week_qs = permits.filter(created_at__gte=start, created_at__lte=end)
            week_count = week_qs.count()
            submitted_trend.append(week_count)
            approved_trend.append(week_qs.filter(status__in=['approved', 'active', 'closed']).count())
            rejected_trend.append(week_qs.filter(status='rejected').count())

            if week_count <= 5:
                risk_class = 'risk-low'
            elif week_count <= 10:
                risk_class = 'risk-medium'
            elif week_count <= 15:
                risk_class = 'risk-high'
            else:
                risk_class = 'risk-critical'
            weekly_activity.append({'count': week_count, 'risk_class': risk_class})

        type_counts = list(
            period_permits.values('permit_type__name').annotate(total=Count('id')).order_by('-total')
        )
        type_labels = [item['permit_type__name'] or 'Unknown' for item in type_counts]
        type_data = [item['total'] for item in type_counts]

        status_order = ['active', 'approved', 'pending', 'reapproval', 'closed', 'rejected', 'draft']
        status_label_map = dict(Permit.STATUS_CHOICES)
        status_counts_map = {key: 0 for key, _ in Permit.STATUS_CHOICES}
        for row in period_permits.values('status').annotate(total=Count('id')):
            status_counts_map[row['status']] = row['total']
        status_labels = [status_label_map[key] for key in status_order if status_counts_map.get(key)]
        status_data = [status_counts_map[key] for key in status_order if status_counts_map.get(key)]

        dept_rows = []
        department_qs = period_permits.values('department__name').annotate(total_permits=Count('id')).order_by('-total_permits')[:5]
        for row in department_qs:
            dept_name = row['department__name'] or 'Unassigned'
            dept_permits = period_permits.filter(department__name=row['department__name'])
            approved_count = dept_permits.filter(status__in=['approved', 'active', 'closed']).count()
            approval_rate = round((approved_count / row['total_permits']) * 100, 1) if row['total_permits'] else 0

            processing_hours = []
            for permit in dept_permits:
                approved_log = next((log for log in permit.approval_logs.all() if log.to_status == 'approved'), None)
                if approved_log:
                    processing_hours.append(round((approved_log.timestamp - permit.created_at).total_seconds() / 3600, 2))
            avg_processing = round(sum(processing_hours) / len(processing_hours), 1) if processing_hours else 0

            dept_rows.append({
                'name': dept_name,
                'total_permits': row['total_permits'],
                'approval_rate': approval_rate,
                'avg_processing_time': avg_processing,
            })

        processing_labels = [item['name'] for item in dept_rows]
        processing_data = [item['avg_processing_time'] for item in dept_rows]

        risk_counts = {
            'minor': period_permits.filter(hazard_risk_level='minor').count(),
            'moderate': period_permits.filter(hazard_risk_level='moderate').count(),
            'major': period_permits.filter(hazard_risk_level='major').count(),
            'critical': period_permits.filter(hazard_risk_level='critical').count(),
        }
        total_risk_permits = sum(risk_counts.values()) or 1

        low_risk_permits = risk_counts['minor']
        medium_risk_permits = risk_counts['moderate']
        high_risk_permits = risk_counts['major']
        critical_risk_permits = risk_counts['critical']

        processing_improvement = 0
        current_approved_logs = [
            round((log.timestamp - log.permit.created_at).total_seconds() / 3600, 2)
            for log in PermitApprovalLog.objects.select_related('permit').filter(
                permit__created_at__gte=period_start,
                to_status='approved',
            )
        ]
        prev_approved_logs = [
            round((log.timestamp - log.permit.created_at).total_seconds() / 3600, 2)
            for log in PermitApprovalLog.objects.select_related('permit').filter(
                permit__created_at__gte=previous_period_start,
                permit__created_at__lt=period_start,
                to_status='approved',
            )
        ]
        if current_approved_logs and prev_approved_logs:
            current_avg = sum(current_approved_logs) / len(current_approved_logs)
            prev_avg = sum(prev_approved_logs) / len(prev_approved_logs)
            if prev_avg:
                processing_improvement = round(((prev_avg - current_avg) / prev_avg) * 100)

        context.update({
            'selected_period': str(period_days),
            'active_permits_count': active_permits_count,
            'total_permits_count': total_permits_count,
            'pending_permits_count': pending_permits_count,
            'expired_permits_count': expired_permits_count,
            'pending_change': pending_change,
            'new_permits_this_week': new_permits_this_week,
            'permits_this_month': permits_this_month,
            'department_performance': dept_rows,
            'low_risk_permits': low_risk_permits,
            'medium_risk_permits': medium_risk_permits,
            'high_risk_permits': high_risk_permits,
            'critical_risk_permits': critical_risk_permits,
            'low_risk_percentage': round((low_risk_permits / total_risk_permits) * 100, 1),
            'medium_risk_percentage': round((medium_risk_permits / total_risk_permits) * 100, 1),
            'high_risk_percentage': round((high_risk_permits / total_risk_permits) * 100, 1),
            'critical_risk_percentage': round((critical_risk_permits / total_risk_permits) * 100, 1),
            'weekly_activity': weekly_activity,
            'processing_improvement': processing_improvement,
            'trend_labels_json': json.dumps(weekly_labels),
            'submitted_trend_json': json.dumps(submitted_trend),
            'approved_trend_json': json.dumps(approved_trend),
            'rejected_trend_json': json.dumps(rejected_trend),
            'permit_type_labels_json': json.dumps(type_labels),
            'permit_type_data_json': json.dumps(type_data),
            'status_labels_json': json.dumps(status_labels),
            'status_data_json': json.dumps(status_data),
            'processing_labels_json': json.dumps(processing_labels),
            'processing_data_json': json.dumps(processing_data),
        })
        return context

from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

class PermitDetailView(LoginRequiredMixin, DetailView):
    model = Permit
    template_name = 'permit/permit_detail.html'
    context_object_name = 'permit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contractors'] = self.object.contractors.all()
        context['attachments'] = self.object.attachments.all()
        context['cancel_url'] = reverse_lazy('permit:permit_list')
        context['closure'] = getattr(self.object, 'closure', None)
        context['extension_form'] = PermitExtensionRequestForm(
            initial={'new_end_date': self.object.end_date}
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # SUBMIT FOR APPROVAL
        if "submit_for_approval" in request.POST:
            if self.object.status in ['draft', 'rejected']:

                self.object.status = 'pending'
                self.object.save()

                # LOG ENTRY
                PermitApprovalLog.objects.create(
                    permit=self.object,
                    action='submitted',
                    performed_by=request.user,
                    from_status='draft',
                    to_status='pending',
                    comments="Submitted for approval"
                )

                messages.success(request, "Permit submitted for approval.")

        return redirect('permit:permit_detail', pk=self.object.pk)
class PermitUpdateView(LoginRequiredMixin, UpdateView):
    model = Permit
    form_class = PermitForm
    template_name = 'permit/permit_edit.html'
    success_url = reverse_lazy('permit:permit_list')

    # Pass user to form
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    # Context (Formsets + hazards)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context['contractor_formset'] = PermitContractorFormSet(
                self.request.POST,
                instance=self.object
            )
            context['attachment_formset'] = PermitAttachmentFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object
            )

            # hazards from POST
            context['selected_hazards'] = self.request.POST.getlist('hazards')

        else:
            context['contractor_formset'] = PermitContractorFormSet(
                instance=self.object
            )
            context['attachment_formset'] = PermitAttachmentFormSet(
                instance=self.object
            )

            # hazards from DB
            context['selected_hazards'] = self.object.hazards or []

        return context

    # MAIN SAVE LOGIC
    def form_valid(self, form):
        context = self.get_context_data()
        contractor_formset = context['contractor_formset']
        attachment_formset = context['attachment_formset']

        if not contractor_formset.is_valid() or not attachment_formset.is_valid():
            return self.form_invalid(form)

        form.instance.hazards = self.request.POST.getlist('hazards')

        old_status = self.object.status

        self.object = form.save()

        # SUBMIT FOR APPROVAL
        if 'submit_for_approval' in self.request.POST:
            self.object.status = 'pending'
            self.object.save()

            PermitApprovalLog.objects.create(
                permit=self.object,
                action='submitted',
                performed_by=self.request.user,
                from_status=old_status,
                to_status='pending'
            )

            messages.success(self.request, "Permit submitted for approval.")

        # CONTRACTORS
        contractor_formset.instance = self.object
        contractors = contractor_formset.save(commit=False)

        for c in contractors:
            if any([c.name, c.trade, c.id_number, c.esi_number, c.contact_number]):
                c.permit = self.object
                c.save()

        for obj in contractor_formset.deleted_objects:
            obj.delete()

        # ATTACHMENTS
        attachment_formset.instance = self.object
        attachments = attachment_formset.save(commit=False)

        for att in attachments:
            if att.file or att.description:
                att.permit = self.object
                att.save()

        for obj in attachment_formset.deleted_objects:
            obj.delete()

        return super().form_valid(form)

class PermitApprovalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'permit/permit_approval_dashboard.html'

    @staticmethod
    def _attach_dashboard_log_data(permits):
        for permit in permits:
            latest_log = next(iter(permit.approval_logs.all()), None)
            permit.dashboard_latest_log = latest_log
            permit.dashboard_action_label = (
                latest_log.get_action_display() if latest_log else permit.get_status_display()
            )
            permit.dashboard_status_label = (
                dict(Permit.STATUS_CHOICES).get(latest_log.to_status, permit.get_status_display())
                if latest_log and latest_log.to_status
                else permit.get_status_display()
            )
        return permits

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_qs = (
            Permit.objects
            .select_related(
                'permit_type',
                'plant',
                'zone',
                'location',
                'department',
                'requester_user',
                'approver'
            )
            .prefetch_related(
                Prefetch(
                    'approval_logs',
                    queryset=PermitApprovalLog.objects.select_related('performed_by').order_by('-timestamp')
                )
            )
        )

        # FILTER BY STATUS
        pending_permits = list(base_qs.filter(status__in=['pending', 'reapproval']))
        approved_permits = list(base_qs.filter(status='approved'))
        rejected_permits = list(base_qs.filter(status='rejected'))

        self._attach_dashboard_log_data(pending_permits)
        self._attach_dashboard_log_data(approved_permits)
        self._attach_dashboard_log_data(rejected_permits)

        # URGENCY LOGIC
        now = timezone.now()

        urgent_permits = [
            permit for permit in pending_permits
            if permit.start_date and permit.start_date <= now + timedelta(hours=24)
        ]

        overdue_permits = [
            permit for permit in pending_permits
            if permit.start_date and permit.start_date < now
        ]

        # STATS
        context.update({
            # MAIN LISTS
            'pending_permits': pending_permits,
            'approved_permits': approved_permits,
            'rejected_permits': rejected_permits,

            # COUNTS
            'pending_count': len(pending_permits),
            'approved_count': len(approved_permits),
            'rejected_count': len(rejected_permits),

            # EXTRA STATS (for future UI)
            'urgent_count': len(urgent_permits),
            'overdue_count': len(overdue_permits),
            'extension_form': PermitExtensionRequestForm(),
        })

        return context


class PermitApprovalView(LoginRequiredMixin, View):

    def post(self, request, pk):
        permit = get_object_or_404(Permit, pk=pk)

        if permit.status not in ['pending', 'reapproval']:
            messages.error(request, "Only pending approval permits can be approved.")
            return redirect('permit:permit_approvals')

        old_status = permit.status
        approval_comments = "Approved"

        if permit.status == 'reapproval':
            pending_extension = permit.extensions.filter(status='pending').order_by('-created_at').first()
            if not pending_extension:
                messages.error(request, "No pending extension request found for this permit.")
                return redirect('permit:permit_approvals')

            pending_extension.status = 'approved'
            pending_extension.reviewed_by = request.user
            pending_extension.reviewed_at = timezone.now()
            pending_extension.review_comments = "Extension approved"
            pending_extension.save()

            permit.end_date = pending_extension.new_end_date
            approval_comments = "Extension approved"

        permit.status = 'approved'
        permit.approver = request.user
        permit.save()

        PermitApprovalLog.objects.create(
            permit=permit,
            action='approved',
            performed_by=request.user,
            from_status=old_status,
            to_status='approved',
            comments=approval_comments
        )

        messages.success(request, "Permit approved successfully.")
        return redirect('permit:permit_approvals')

class PermitRejectView(LoginRequiredMixin, View):

    def post(self, request, pk):
        permit = get_object_or_404(Permit, pk=pk)

        if permit.status not in ['pending', 'reapproval']:
            messages.error(request, "Only pending approval permits can be rejected.")
            return redirect('permit:permit_approvals')

        reason = request.POST.get('reason')

        if not reason:
            messages.error(request, "Rejection reason is required.")
            return redirect('permit:permit_approvals')

        old_status = permit.status
        new_status = 'rejected'
        rejection_comments = reason

        if permit.status == 'reapproval':
            pending_extension = permit.extensions.filter(status='pending').order_by('-created_at').first()
            if not pending_extension:
                messages.error(request, "No pending extension request found for this permit.")
                return redirect('permit:permit_approvals')

            pending_extension.status = 'rejected'
            pending_extension.reviewed_by = request.user
            pending_extension.reviewed_at = timezone.now()
            pending_extension.review_comments = reason
            pending_extension.save()

            permit.status = 'approved'
            new_status = 'approved'
            rejection_comments = f"Extension rejected: {reason}"
        else:
            permit.status = 'rejected'
            permit.rejection_reason = reason

        permit.save()

        PermitApprovalLog.objects.create(
            permit=permit,
            action='rejected',
            performed_by=request.user,
            from_status=old_status,
            to_status=new_status,
            comments=rejection_comments
        )

        if old_status == 'reapproval':
            messages.success(request, "Extension request rejected successfully.")
        else:
            messages.success(request, "Permit rejected successfully.")
        return redirect('permit:permit_approvals')

class PermitExtensionRequestView(LoginRequiredMixin, CreateView):
    model = PermitExtension
    form_class = PermitExtensionRequestForm
    template_name = 'permit/extension_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.permit = get_object_or_404(Permit, pk=self.kwargs['pk'])
        if self.permit.status != 'approved':
            messages.error(request, "Only approved permits can be extended.")
            return redirect('permit:permit_detail', pk=self.permit.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['permit'] = self.permit
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['new_end_date'] = self.permit.end_date
        return initial

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            return referer
        return reverse_lazy('permit:permit_detail', kwargs={'pk': self.permit.pk})

    def form_valid(self, form):
        form.instance.permit = self.permit
        form.instance.requested_by = self.request.user
        form.instance.original_end_date = self.permit.end_date

        self.permit.status = 'reapproval'
        self.permit.save()

        PermitApprovalLog.objects.create(
            permit=self.permit,
            action='extended',
            performed_by=self.request.user,
            comments="Extension requested",
            from_status='approved',
            to_status='reapproval'
        )

        messages.success(self.request, "Extension requested.")

        return super().form_valid(form)

    def form_invalid(self, form):
        error_message = form.errors.get('new_end_date', form.non_field_errors())
        if error_message:
            messages.error(self.request, error_message[0])
        else:
            messages.error(self.request, "Unable to submit extension request.")
        return redirect(self.get_success_url())


class PermitCloseView(LoginRequiredMixin, View):
    template_name = 'permit/permit_closure.html'

    def get_permit(self, pk):
        return get_object_or_404(
            Permit.objects.select_related('permit_type', 'location'),
            pk=pk
        )

    def build_context(self, permit, form):
        return {
            'permit': permit,
            'form': form,
            'cancel_url': reverse_lazy('permit:permit_detail', kwargs={'pk': permit.pk}),
            'primary_contractor': permit.contractors.first(),
            'closure': getattr(permit, 'closure', None),
        }

    def get(self, request, pk):
        from django.shortcuts import render

        permit = self.get_permit(pk)

        if permit.status not in ['approved', 'active']:
            messages.error(request, "Only approved or active permits can be closed.")
            return redirect('permit:permit_detail', pk=pk)

        if hasattr(permit, 'closure'):
            messages.info(request, "This permit has already been closed.")
            return redirect('permit:permit_detail', pk=pk)

        form = PermitClosureForm(
            permit=permit,
            initial={'actual_end_date': timezone.localtime(timezone.now()).strftime('%Y-%m-%dT%H:%M')}
        )
        return render(request, self.template_name, self.build_context(permit, form))

    def post(self, request, pk):
        from django.shortcuts import render

        permit = self.get_permit(pk)

        if permit.status not in ['approved', 'active']:
            messages.error(request, "Cannot close this permit.")
            return redirect('permit:permit_detail', pk=pk)

        if hasattr(permit, 'closure'):
            messages.info(request, "This permit has already been closed.")
            return redirect('permit:permit_detail', pk=pk)

        form = PermitClosureForm(request.POST, permit=permit)
        closure_photos = request.FILES.getlist('closure_photos')

        if len(closure_photos) < 2:
            form.add_error(None, "Please upload at least 2 photos of the completed work area.")

        if not form.is_valid():
            return render(request, self.template_name, self.build_context(permit, form))

        old_status = permit.status
        with transaction.atomic():
            closure = form.save(commit=False)
            closure.permit = permit
            closure.closed_by = request.user
            closure.save()

            for photo in closure_photos:
                PermitClosurePhoto.objects.create(
                    closure=closure,
                    photo=photo,
                    uploaded_by=request.user
                )

            permit.status = 'closed'
            permit.close_out_notes = closure.closure_comments or closure.work_summary
            permit.save()

            PermitApprovalLog.objects.create(
                permit=permit,
                action='closed',
                performed_by=request.user,
                from_status=old_status,
                to_status='closed',
                comments=closure.work_summary
            )

        messages.success(request, "Permit closed successfully.")

        return redirect('permit:permit_detail', pk=pk)


class PermitPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        permit = get_object_or_404(
            Permit.objects.select_related(
                'permit_type',
                'plant',
                'zone',
                'location',
                'sublocation',
                'department',
                'approver',
            ).prefetch_related(
                'contractors',
                'attachments',
                'closure__photos',
            ),
            pk=pk,
        )
        return generate_permit_pdf(permit)
