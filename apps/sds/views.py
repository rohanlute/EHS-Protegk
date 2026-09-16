from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.db import models
from django.http import HttpResponse, request
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
    TemplateView,
)

from ..chemicals.models import Chemical
from .models import (SDS, SDSVersion, SDSReview, SDSAuditLog, SDSSection1, SDSSection2, 
                     SDSSection3, SDSSection4, SDSSection5, SDSSection6, SDSSection7,
                     SDSSection8, SDSSection9, SDSSection10, SDSSection11, SDSSection12, 
                    SDSSection13, SDSSection14, SDSSection15, SDSSection16)
from .forms import (SDSForm, SDSVersionForm, SDSReviewForm, SDSSection1Form, SDSSection2Form, 
                    SDSSection3Form, SDSSection3IngredientFormSet, SDSSection4Form, SDSSection5Form, 
                    SDSSection6Form, SDSSection7Form, SDSSection8Form, SDSSection9Form, SDSSection10Form, 
                    SDSSection11Form, SDSSection12Form, SDSSection13Form, SDSSection14Form, 
                    SDSSection15Form, SDSSection16Form)


# ============================================================
# COMMON ACCESS HELPER
# ============================================================

class SDSAccessMixin:
    """
    Provides common plant/location access checking for SDS records.
    """

    def user_can_access_sds(self, sds):
        user = self.request.user

        if user.is_superuser:
            return True

        if getattr(user, 'is_admin_user', False):
            return True

        if sds.plant:
            return user.has_access_to_plant(sds.plant)

        # If SDS has no plant restriction, allow authenticated users.
        return True

    def check_sds_access(self, sds):
        if not self.user_can_access_sds(sds):
            raise PermissionDenied(
                "You do not have permission to access this SDS."
            )

    # =========================================================
    # CHECK SDS VERSION EDIT ACCESS
    # =========================================================
    def check_version_edit_access(self, version):
        if version.status != 'DRAFT':
            raise PermissionDenied(
                'This SDS version is locked and cannot be modified.'
            )   


# =========================================================
# SDS AUDIT LOG HELPER
# =========================================================
def create_sds_audit_log(
    sds,
    action,
    user,
    version=None,
    description='',
    old_status='',
    new_status=''
):
    return SDSAuditLog.objects.create(
        sds=sds,
        version=version,
        action=action,
        description=description,
        old_status=old_status,
        new_status=new_status,
        performed_by=user
    )

# ============================================================
# SDS DASHBOARD
# ============================================================

class SDSDashboardView(LoginRequiredMixin, SDSAccessMixin, TemplateView):
    template_name = 'sds/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_accessible_queryset()

        today = timezone.now().date()

        context['total_sds'] = queryset.count()

        context['active_sds'] = queryset.filter(
            status='ACTIVE',
            is_active=True
        ).count()

        context['draft_sds'] = queryset.filter(
            status='DRAFT'
        ).count()

        context['under_review_sds'] = queryset.filter(
            status='UNDER_REVIEW'
        ).count()

        context['approved_sds'] = queryset.filter(
            status='APPROVED'
        ).count()

        context['expired_sds'] = queryset.filter(
            next_review_date__lt=today
        ).count()

        context['review_due_30_days'] = queryset.filter(
            next_review_date__gte=today,
            next_review_date__lte=today + timedelta(days=30)
        ).count()

        context['review_due_60_days'] = queryset.filter(
            next_review_date__gte=today,
            next_review_date__lte=today + timedelta(days=60)
        ).count()

        context['review_due_90_days'] = queryset.filter(
            next_review_date__gte=today,
            next_review_date__lte=today + timedelta(days=90)
        ).count()

        context['superseded_sds'] = queryset.filter(
            status='SUPERSEDED'
        ).count()

        context['recent_sds'] = queryset.order_by(
            '-created_at'
        )[:10]

        return context

    def get_accessible_queryset(self):
        user = self.request.user

        queryset = SDS.objects.select_related(
            'plant',
            'zone',
            'location',
            'sublocation',
            'created_by',
            'updated_by',
        )

        if user.is_superuser or getattr(user, 'is_admin_user', False):
            return queryset

        assigned_plants = user.get_all_plants()

        if assigned_plants:
            return queryset.filter(
                Q(plant__in=assigned_plants) |
                Q(plant__isnull=True)
            )

        return queryset.filter(
            plant__isnull=True
        )



# =========================================================
# SDS ANALYTICAL DASHBOARD
# =========================================================
class SDSAnalyticalDashboardView(
    LoginRequiredMixin,
    SDSAccessMixin,
    TemplateView
):
    """
    Analytical dashboard for SDS compliance,
    coverage, review, expiry and lifecycle monitoring.
    """

    template_name = 'sds/analytical_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # =========================================================
        # CURRENT DATE
        # =========================================================
        today = timezone.localdate()

        # =========================================================
        # CURRENT USER
        # =========================================================
        user = self.request.user

        is_admin = (
            user.is_superuser
            or getattr(
                user,
                'is_admin_user',
                False
            )
        )

        # =========================================================
        # BASE QUERYSETS
        # =========================================================
        sds_queryset = SDS.objects.all()

        version_queryset = SDSVersion.objects.all()

        review_queryset = SDSReview.objects.all()

        chemical_queryset = Chemical.objects.all()

        # =========================================================
        # USER / PLANT ACCESS
        # =========================================================
        assigned_plants = []

        if not is_admin:

            assigned_plants = user.get_all_plants()

            if assigned_plants:

                sds_queryset = sds_queryset.filter(
                    plant__in=assigned_plants
                )

                chemical_queryset = chemical_queryset.filter(
                    plant__in=assigned_plants
                )

            else:

                sds_queryset = sds_queryset.filter(
                    plant__isnull=True
                )

                chemical_queryset = chemical_queryset.filter(
                    plant__isnull=True
                )

        # =========================================================
        # VERSION AND REVIEW ACCESS
        # =========================================================
        version_queryset = version_queryset.filter(
            sds__in=sds_queryset
        )

        review_queryset = review_queryset.filter(
            sds__in=sds_queryset
        )

        # =========================================================
        # BASIC SDS COUNTS
        # =========================================================
        total_sds = sds_queryset.count()

        active_sds = sds_queryset.filter(
            status='ACTIVE',
            is_active=True
        ).count()

        draft_sds = sds_queryset.filter(
            status='DRAFT'
        ).count()

        submitted_sds = sds_queryset.filter(
            status='SUBMITTED'
        ).count()

        under_review_sds = sds_queryset.filter(
            status='UNDER_REVIEW'
        ).count()

        approved_sds = sds_queryset.filter(
            status='APPROVED'
        ).count()

        rejected_sds = sds_queryset.filter(
            status='REJECTED'
        ).count()

        superseded_sds = sds_queryset.filter(
            status='SUPERSEDED'
        ).count()

        expired_sds = sds_queryset.filter(
            status='EXPIRED'
        ).count()

        # =========================================================
        # MASTER SDS REVIEW / EXPIRY COUNTS
        # =========================================================
        overdue_sds = sds_queryset.filter(
            next_review_date__lt=today
        ).count()

        due_30_sds = sds_queryset.filter(
            next_review_date__gte=today,
            next_review_date__lte=(
                today + timedelta(days=30)
            )
        ).count()

        due_60_sds = sds_queryset.filter(
            next_review_date__gt=(
                today + timedelta(days=30)
            ),
            next_review_date__lte=(
                today + timedelta(days=60)
            )
        ).count()

        due_90_sds = sds_queryset.filter(
            next_review_date__gt=(
                today + timedelta(days=60)
            ),
            next_review_date__lte=(
                today + timedelta(days=90)
            )
        ).count()

        # =========================================================
        # ACTIVE SDS VERSIONS
        # =========================================================
        active_versions = version_queryset.filter(
            status='ACTIVE'
        )

        active_version_count = active_versions.count()

        # =========================================================
        # VERSION REVIEW ANALYTICS
        # =========================================================
        overdue_versions = 0

        due_30_versions = 0

        due_60_versions = 0

        due_90_versions = 0

        not_due_versions = 0

        no_review_date_versions = 0

        for version in active_versions:

            review_status = version.review_due_status

            if review_status == 'OVERDUE':

                overdue_versions += 1

            elif review_status == 'DUE_SOON':

                due_30_versions += 1

            elif review_status == 'DUE_WITHIN_60_DAYS':

                due_60_versions += 1

            elif review_status == 'DUE_WITHIN_90_DAYS':

                due_90_versions += 1

            elif review_status == 'NOT_DUE':

                not_due_versions += 1

            else:

                no_review_date_versions += 1

        # =========================================================
        # REVIEW TOTAL
        # =========================================================
        review_total_versions = (
            overdue_versions
            + due_30_versions
            + due_60_versions
            + due_90_versions
            + not_due_versions
        )

        # =========================================================
        # REVIEW COMPLIANCE
        # =========================================================
        if review_total_versions:

            review_compliance_percentage = round(
                (
                    (
                        review_total_versions
                        - overdue_versions
                    )
                    / review_total_versions
                ) * 100,
                1
            )

        else:

            review_compliance_percentage = 100

        # =========================================================
        # REVIEW DISTRIBUTION
        # =========================================================
        review_distribution = [
            {
                'label': 'Overdue',
                'value': overdue_versions,
            },
            {
                'label': 'Due ≤30 Days',
                'value': due_30_versions,
            },
            {
                'label': 'Due 31–60 Days',
                'value': due_60_versions,
            },
            {
                'label': 'Due 61–90 Days',
                'value': due_90_versions,
            },
            {
                'label': 'Not Due',
                'value': not_due_versions,
            },
        ]

        # =========================================================
        # SDS COVERAGE
        # =========================================================
        active_sds_for_coverage = sds_queryset.filter(
            chemical__isnull=False,
            status='ACTIVE',
            is_active=True
        )

        chemicals_with_active_sds = (
            active_sds_for_coverage
            .values('chemical_id')
            .distinct()
            .count()
        )

        # =========================================================
        # TOTAL CHEMICALS
        # =========================================================
        total_chemicals = chemical_queryset.count()

        # =========================================================
        # CHEMICALS WITHOUT ACTIVE SDS
        # =========================================================
        active_chemical_ids = (
            active_sds_for_coverage
            .values_list(
                'chemical_id',
                flat=True
            )
            .distinct()
        )

        chemicals_without_active_sds = (
            chemical_queryset
            .exclude(
                id__in=active_chemical_ids
            )
            .count()
        )

        # =========================================================
        # SDS COVERAGE PERCENTAGE
        # =========================================================
        if total_chemicals:

            sds_coverage_percentage = round(
                (
                    chemicals_with_active_sds
                    / total_chemicals
                ) * 100,
                1
            )

        else:

            sds_coverage_percentage = 0

        # =========================================================
        # SECTION COMPLETION
        # =========================================================
        if active_version_count:

            total_completion = sum(
                version.section_completion_percentage
                for version in active_versions
            )

            section_completion_percentage = round(
                total_completion
                / active_version_count,
                1
            )

        else:

            section_completion_percentage = 0

        # =========================================================
        # INCOMPLETE ACTIVE VERSIONS
        # =========================================================
        incomplete_active_versions = sum(
            1
            for version in active_versions
            if not version.is_section_complete
        )

        # =========================================================
        # REVIEW WORKFLOW COUNTS
        # =========================================================
        pending_reviews = review_queryset.filter(
            status='PENDING'
        ).count()

        in_review_reviews = review_queryset.filter(
            status='IN_REVIEW'
        ).count()

        approved_reviews = review_queryset.filter(
            status='APPROVED'
        ).count()

        rejected_reviews = review_queryset.filter(
            status='REJECTED'
        ).count()

        # =========================================================
        # SDS STATUS DISTRIBUTION
        # =========================================================
        status_distribution = [
            {
                'label': 'Draft',
                'value': draft_sds,
            },
            {
                'label': 'Submitted',
                'value': submitted_sds,
            },
            {
                'label': 'Under Review',
                'value': under_review_sds,
            },
            {
                'label': 'Approved',
                'value': approved_sds,
            },
            {
                'label': 'Active',
                'value': active_sds,
            },
            {
                'label': 'Rejected',
                'value': rejected_sds,
            },
            {
                'label': 'Superseded',
                'value': superseded_sds,
            },
            {
                'label': 'Expired',
                'value': expired_sds,
            },
        ]



        # =========================================================
        # PLANT ANALYTICS
        # =========================================================
        plant_analytics = []

        plant_queryset = sds_queryset.values(
            'plant_id',
            'plant__name'
        ).annotate(
            total_sds=Count('id'),
            active_sds=Count(
                'id',
                filter=models.Q(
                    status='ACTIVE',
                    is_active=True
                )
            ),
            expired_sds=Count(
                'id',
                filter=models.Q(
                    status='EXPIRED'
                )
            )
        ).order_by(
            '-total_sds'
        )

        for plant in plant_queryset:

            plant_id = plant['plant_id']

            plant_name = (
                plant['plant__name']
                or 'Unassigned'
            )

            plant_chemical_queryset = chemical_queryset.filter(
                plant_id=plant_id
            )

            plant_total_chemicals = (
                plant_chemical_queryset.count()
            )

            plant_active_chemical_ids = (
                sds_queryset.filter(
                    plant_id=plant_id,
                    chemical__isnull=False,
                    status='ACTIVE',
                    is_active=True
                )
                .values_list(
                    'chemical_id',
                    flat=True
                )
                .distinct()
            )

            plant_chemicals_with_active_sds = (
                len(plant_active_chemical_ids)
            )

            if plant_total_chemicals:

                plant_coverage_percentage = round(
                    (
                        plant_chemicals_with_active_sds
                        / plant_total_chemicals
                    ) * 100,
                    1
                )

            else:

                plant_coverage_percentage = 0

            plant_versions = active_versions.filter(
                sds__plant_id=plant_id
            )

            plant_overdue_reviews = 0

            for version in plant_versions:

                if version.review_due_status == 'OVERDUE':

                    plant_overdue_reviews += 1

            plant_analytics.append(
                {
                    'plant_id': plant_id,
                    'plant_name': plant_name,
                    'total_sds': plant['total_sds'],
                    'active_sds': plant['active_sds'],
                    'expired_sds': plant['expired_sds'],
                    'overdue_reviews': plant_overdue_reviews,
                    'total_chemicals': plant_total_chemicals,
                    'chemicals_with_active_sds': (
                        plant_chemicals_with_active_sds
                    ),
                    'coverage_percentage': (
                        plant_coverage_percentage
                    ),
                }
            )

        # =========================================================
        # PLANT CHART DATA
        # =========================================================
        plant_chart_data = []

        for plant in plant_analytics:

            plant_chart_data.append(
                {
                    'label': plant['plant_name'],
                    'total': plant['total_sds'],
                    'active': plant['active_sds'],
                    'expired': plant['expired_sds'],
                }
            )


        # =========================================================
        # SDS SECTION COMPLETION ANALYTICS
        # =========================================================
        section_completion = []

        section_definitions = [
            (1,'Identification'),
            (2,'Hazard Identification'),
            (3,'Composition / Ingredients'),
            (4,'First-Aid Measures'),
            (5,'Fire-Fighting Measures'),
            (6,'Accidental Release Measures'),
            (7,'Handling and Storage'),
            (8,'Exposure Controls / PPE'),
            (9,'Physical and Chemical Properties'),
            (10,'Stability and Reactivity'),
            (11,'Toxicological Information'),
            (12,'Ecological Information'),
            (13,'Disposal Considerations'),
            (14,'Transport Information'),
            (15,'Regulatory Information'),
            (16,'Other Information'),
        ]

        for section_number,section_name in section_definitions:

            completion_values = []

            for version in active_versions:

                completion = getattr(
                    version,
                    f'section_{section_number}_completion_percentage',
                    None
                )

                if completion is not None:

                    completion_values.append(
                        completion
                    )

            if completion_values:

                average_completion = round(
                    sum(completion_values)
                    / len(completion_values),
                    1
                )

            else:

                average_completion = 0

            section_completion.append(
                {
                    'number': section_number,
                    'name': section_name,
                    'completion': average_completion,
                }
            )

        # =========================================================
        # SECTION COMPLETION SUMMARY
        # =========================================================
        fully_completed_versions = 0
        incomplete_versions = 0

        for version in active_versions:

            if version.is_section_complete:

                fully_completed_versions += 1

            else:

                incomplete_versions += 1

        if active_version_count:

            section_completion_percentage = round(
                (
                    fully_completed_versions
                    / active_version_count
                ) * 100,
                1
            )

        else:

            section_completion_percentage = 0



        # =========================================================
        # SDS ATTENTION ANALYTICS
        # =========================================================
        attention_items = []

        if overdue_sds > 0:
            attention_items.append(
                {
                    'type': 'OVERDUE',
                    'title': 'Overdue SDS Reviews',
                    'description': (
                        'SDS documents have passed their review date.'
                    ),
                    'count': overdue_sds,
                    'priority': 'HIGH',
                }
            )

        if due_30_sds > 0:
            attention_items.append(
                {
                    'type': 'DUE_SOON',
                    'title': 'Reviews Due Within 30 Days',
                    'description': (
                        'SDS documents require review within 30 days.'
                    ),
                    'count': due_30_sds,
                    'priority': 'MEDIUM',
                }
            )

        if expired_sds > 0:
            attention_items.append(
                {
                    'type': 'EXPIRED',
                    'title': 'Expired SDS',
                    'description': (
                        'SDS documents are currently marked as expired.'
                    ),
                    'count': expired_sds,
                    'priority': 'HIGH',
                }
            )

        if incomplete_versions > 0:
            attention_items.append(
                {
                    'type': 'INCOMPLETE',
                    'title': 'Incomplete Active SDS',
                    'description': (
                        'Active SDS versions have incomplete sections.'
                    ),
                    'count': incomplete_versions,
                    'priority': 'MEDIUM',
                }
            )

        if chemicals_without_active_sds > 0:
            attention_items.append(
                {
                    'type': 'NO_SDS',
                    'title': 'Chemicals Without Active SDS',
                    'description': (
                        'Chemicals do not currently have an active SDS.'
                    ),
                    'count': chemicals_without_active_sds,
                    'priority': 'HIGH',
                }
            )

        # =========================================================
        # LOW COVERAGE PLANTS
        # =========================================================
        low_coverage_plants = []

        for plant in plant_analytics:

            if (
                plant['total_chemicals'] > 0
                and plant['coverage_percentage'] < 90
            ):
                low_coverage_plants.append(
                    plant
                )

        if low_coverage_plants:

            attention_items.append(
                {
                    'type': 'PLANT_COVERAGE',
                    'title': 'Plants Below 90% SDS Coverage',
                    'description': (
                        'Plants have chemical SDS coverage below 90%.'
                    ),
                    'count': len(low_coverage_plants),
                    'priority': 'MEDIUM',
                }
            )

        # =========================================================
        # ATTENTION SUMMARY
        # =========================================================
        high_priority_attention = sum(
            1
            for item in attention_items
            if item['priority'] == 'HIGH'
        )

        medium_priority_attention = sum(
            1
            for item in attention_items
            if item['priority'] == 'MEDIUM'
        )


        # =========================================================
        # SDS TREND ANALYTICS
        # =========================================================
        trend_today = today
        trend_start = (
            trend_today.replace(
                day=1
            )
            - relativedelta(
                months=11
            )
        )

        trend_months = []

        for month_offset in range(12):

            month_date = (
                trend_start
                + relativedelta(
                    months=month_offset
                )
            )

            next_month = (
                month_date
                + relativedelta(
                    months=1
                )
            )

            sds_created_count = sds_queryset.filter(
                created_at__date__gte=month_date,
                created_at__date__lt=next_month
            ).count()

            sds_updated_count = sds_queryset.filter(
                updated_at__date__gte=month_date,
                updated_at__date__lt=next_month
            ).count()

            reviews_created_count = review_queryset.filter(
                created_at__date__gte=month_date,
                created_at__date__lt=next_month
            ).count()

            reviews_completed_count = review_queryset.filter(
                status='APPROVED',
                updated_at__date__gte=month_date,
                updated_at__date__lt=next_month
            ).count()

            trend_months.append(
                {
                    'label': month_date.strftime('%b %Y'),
                    'short_label': month_date.strftime('%b'),
                    'sds_created': sds_created_count,
                    'sds_updated': sds_updated_count,
                    'reviews_created': reviews_created_count,
                    'reviews_completed': reviews_completed_count,
                }
            )

        # =========================================================
        # TREND SUMMARY
        # =========================================================
        sds_created_last_12_months = sum(
            month['sds_created']
            for month in trend_months
        )

        sds_updated_last_12_months = sum(
            month['sds_updated']
            for month in trend_months
        )

        reviews_created_last_12_months = sum(
            month['reviews_created']
            for month in trend_months
        )

        reviews_completed_last_12_months = sum(
            month['reviews_completed']
            for month in trend_months
        )


        # =========================================================
        # TREND CHART DATA
        # =========================================================
        trend_chart_data = {
            'labels': [
                month['short_label']
                for month in trend_months
            ],
            'sds_created': [
                month['sds_created']
                for month in trend_months
            ],
            'sds_updated': [
                month['sds_updated']
                for month in trend_months
            ],
            'reviews_created': [
                month['reviews_created']
                for month in trend_months
            ],
            'reviews_completed': [
                month['reviews_completed']
                for month in trend_months
            ],
        }

        # =========================================================
        # DASHBOARD CONTEXT
        # =========================================================
        context.update(
            {
                # -------------------------------------------------
                # Dashboard Header
                # -------------------------------------------------
                'dashboard_title': (
                    'SDS Analytical Dashboard'
                ),

                'dashboard_subtitle': (
                    'Monitor SDS compliance, coverage and '
                    'document status.'
                ),

                # -------------------------------------------------
                # Plant Analytics
                # -------------------------------------------------
                'plant_analytics': plant_analytics,

                'plant_chart_data': plant_chart_data,

                # -------------------------------------------------
                # Section Completion Analytics
                # -------------------------------------------------
                'section_completion': section_completion,

                'fully_completed_versions': (
                    fully_completed_versions
                ),

                'incomplete_versions': (
                    incomplete_versions
                ),

                'section_completion_percentage': (
                    section_completion_percentage
                ),

                # -------------------------------------------------
                # Trend Analytics
                # -------------------------------------------------
                'trend_months': trend_months,

                'trend_chart_data': trend_chart_data,

                'sds_created_last_12_months': (
                    sds_created_last_12_months
                ),

                'sds_updated_last_12_months': (
                    sds_updated_last_12_months
                ),

                'reviews_created_last_12_months': (
                    reviews_created_last_12_months
                ),

                'reviews_completed_last_12_months': (
                    reviews_completed_last_12_months
                ),
                
                # -------------------------------------------------
                # Attention Analytics
                # -------------------------------------------------
                'attention_items': attention_items,

                'high_priority_attention': (
                    high_priority_attention
                ),

                'medium_priority_attention': (
                    medium_priority_attention
                ),

                'low_coverage_plants': (
                    low_coverage_plants
                ),

                # -------------------------------------------------
                # Executive KPIs
                # -------------------------------------------------
                'total_sds': total_sds,

                'active_sds': active_sds,

                'sds_coverage_percentage': (
                    sds_coverage_percentage
                ),

                'overdue_sds': overdue_sds,

                'due_30_sds': due_30_sds,

                'chemicals_without_active_sds': (
                    chemicals_without_active_sds
                ),

                'section_completion_percentage': (
                    section_completion_percentage
                ),

                'superseded_sds': superseded_sds,

                # -------------------------------------------------
                # SDS Status
                # -------------------------------------------------
                'draft_sds': draft_sds,

                'submitted_sds': submitted_sds,

                'under_review_sds': (
                    under_review_sds
                ),

                'approved_sds': approved_sds,

                'rejected_sds': rejected_sds,

                'expired_sds': expired_sds,

                # -------------------------------------------------
                # Master Review / Expiry
                # -------------------------------------------------
                'due_60_sds': due_60_sds,

                'due_90_sds': due_90_sds,

                # -------------------------------------------------
                # Version Review Analytics
                # -------------------------------------------------
                'overdue_versions': (
                    overdue_versions
                ),

                'due_30_versions': (
                    due_30_versions
                ),

                'due_60_versions': (
                    due_60_versions
                ),

                'due_90_versions': (
                    due_90_versions
                ),

                'not_due_versions': (
                    not_due_versions
                ),

                'no_review_date_versions': (
                    no_review_date_versions
                ),

                'review_total_versions': (
                    review_total_versions
                ),

                'review_compliance_percentage': (
                    review_compliance_percentage
                ),

                # -------------------------------------------------
                # Review Workflow
                # -------------------------------------------------
                'pending_reviews': (
                    pending_reviews
                ),

                'in_review_reviews': (
                    in_review_reviews
                ),

                'approved_reviews': (
                    approved_reviews
                ),

                'rejected_reviews': (
                    rejected_reviews
                ),

                # -------------------------------------------------
                # Section Completion
                # -------------------------------------------------
                'active_version_count': (
                    active_version_count
                ),

                'incomplete_active_versions': (
                    incomplete_active_versions
                ),

                # -------------------------------------------------
                # Chemical Coverage
                # -------------------------------------------------
                'total_chemicals': (
                    total_chemicals
                ),

                'chemicals_with_active_sds': (
                    chemicals_with_active_sds
                ),

                # -------------------------------------------------
                # Chart Data
                # -------------------------------------------------
                'status_distribution': (
                    status_distribution
                ),

                'review_distribution': (
                    review_distribution
                ),
            }
        )

        return context

    
# ============================================================
# SDS LIST
# ============================================================

class SDSListView(LoginRequiredMixin, SDSAccessMixin, ListView):
    model = SDS
    template_name = 'sds/sds_list.html'
    context_object_name = 'sds_list'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        queryset = SDS.objects.select_related(
            'plant',
            'zone',
            'location',
            'sublocation',
            'created_by',
            'updated_by',
        )

        # ----------------------------------------------------
        # User access filtering
        # ----------------------------------------------------

        if not user.is_superuser and not getattr(
            user,
            'is_admin_user',
            False
        ):
            assigned_plants = user.get_all_plants()

            if assigned_plants:
                queryset = queryset.filter(
                    Q(plant__in=assigned_plants) |
                    Q(plant__isnull=True)
                )
            else:
                queryset = queryset.filter(
                    plant__isnull=True
                )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        search = self.request.GET.get(
            'search',
            ''
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(sds_number__icontains=search) |
                Q(product_name__icontains=search) |
                Q(product_identifier__icontains=search) |
                Q(manufacturer_name__icontains=search) |
                Q(supplier_name__icontains=search)
            )

        # ----------------------------------------------------
        # Status filter
        # ----------------------------------------------------

        status = self.request.GET.get('status')

        if status:
            queryset = queryset.filter(
                status=status
            )

        # ----------------------------------------------------
        # SDS type filter
        # ----------------------------------------------------

        sds_type = self.request.GET.get('sds_type')

        if sds_type:
            queryset = queryset.filter(
                sds_type=sds_type
            )

        # ----------------------------------------------------
        # Plant filter
        # ----------------------------------------------------

        plant = self.request.GET.get('plant')

        if plant:
            try:
                queryset = queryset.filter(
                    plant_id=int(plant)
                )
            except (ValueError, TypeError):
                pass

        # ----------------------------------------------------
        # Review status
        # ----------------------------------------------------

        review_status = self.request.GET.get(
            'review'
        )

        today = timezone.now().date()

        if review_status == 'expired':
            queryset = queryset.filter(
                next_review_date__lt=today
            )

        elif review_status == '30':
            queryset = queryset.filter(
                next_review_date__gte=today,
                next_review_date__lte=today + timedelta(days=30)
            )

        elif review_status == '60':
            queryset = queryset.filter(
                next_review_date__gte=today,
                next_review_date__lte=today + timedelta(days=60)
            )

        elif review_status == '90':
            queryset = queryset.filter(
                next_review_date__gte=today,
                next_review_date__lte=today + timedelta(days=90)
            )

        return queryset.order_by(
            'product_name'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        context['statuses'] = SDS.STATUS_CHOICES
        context['sds_types'] = SDS.SDS_TYPE_CHOICES

        if user.is_superuser or getattr(
            user,
            'is_admin_user',
            False
        ):
            from apps.organizations.models import Plant

            context['plants'] = Plant.objects.filter(
                is_active=True
            ).order_by('name')

        else:
            context['plants'] = user.get_all_plants()

        context['search'] = self.request.GET.get(
            'search',
            ''
        )

        context['selected_status'] = self.request.GET.get(
            'status',
            ''
        )

        context['selected_sds_type'] = self.request.GET.get(
            'sds_type',
            ''
        )

        context['selected_plant'] = self.request.GET.get(
            'plant',
            ''
        )

        context['selected_review'] = self.request.GET.get(
            'review',
            ''
        )

        return context


# ============================================================
# CREATE SDS
# ============================================================

class SDSCreateView(LoginRequiredMixin, SDSAccessMixin, CreateView):
    model = SDS
    form_class = SDSForm
    template_name = 'sds/sds_form.html'
    success_url = reverse_lazy('sds:sds_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            f'SDS "{self.object.sds_number}" created successfully.'
        )

        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Please correct the errors below.'
        )

        return super().form_invalid(form)


# ============================================================
# SDS DETAIL
# ============================================================

# =========================================================
# SDS DETAIL VIEW
# =========================================================
class SDSDetailView(LoginRequiredMixin, SDSAccessMixin, DetailView):
    model = SDS
    template_name = 'sds/sds_detail.html'
    context_object_name = 'sds'

    def get_queryset(self):
        return SDS.objects.select_related(
            'chemical',
            'plant',
            'zone',
            'location',
            'sublocation',
            'created_by',
            'updated_by'
        ).prefetch_related(
            'versions',
            'reviews'
        )

    def get_object(self, queryset=None):
        sds = super().get_object(queryset)
        self.check_sds_access(sds)
        return sds

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        versions = self.object.versions.select_related(
            'uploaded_by'
        ).order_by(
            '-version_number'
        )

        reviews = self.object.reviews.select_related(
            'reviewer',
            'submitted_by',
            'version'
        ).order_by(
            '-created_at'
        )

        context['versions'] = versions
        context['reviews'] = reviews
        context['current_version'] = self.object.current_version

        return context


# ============================================================
# UPDATE SDS
# ============================================================

class SDSUpdateView(LoginRequiredMixin, SDSAccessMixin, UpdateView):
    model = SDS
    form_class = SDSForm
    template_name = 'sds/sds_form.html'

    def get_queryset(self):
        return SDS.objects.select_related(
            'plant',
            'zone',
            'location',
            'sublocation',
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.check_sds_access(obj)
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            f'SDS "{self.object.sds_number}" updated successfully.'
        )

        return response

    def get_success_url(self):
        return reverse_lazy(
            'sds:sds_detail',
            kwargs={'pk': self.object.pk}
        )


# ============================================================
# DELETE / ARCHIVE SDS
# ============================================================

class SDSDeleteView(LoginRequiredMixin, SDSAccessMixin, DeleteView):
    model = SDS
    template_name = 'sds/sds_confirm_delete.html'
    success_url = reverse_lazy('sds:sds_list')

    def get_queryset(self):
        return SDS.objects.all()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.check_sds_access(obj)
        return obj

    def form_valid(self, form):
        sds_number = self.object.sds_number

        response = super().form_valid(form)

        messages.success(
            self.request,
            f'SDS "{sds_number}" deleted successfully.'
        )

        return response


# ============================================================
# ADD SDS VERSION
# ============================================================
class SDSVersionCreateView(
    LoginRequiredMixin,
    SDSAccessMixin,
    CreateView
):
    model = SDSVersion
    form_class = SDSVersionForm
    template_name = 'sds/version_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.sds = get_object_or_404(
            SDS,
            pk=kwargs['sds_id']
        )

        self.check_sds_access(self.sds)

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['sds'] = self.sds
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sds'] = self.sds
        return context

    # =========================================================
    # SAVE SDS VERSION
    # =========================================================
    def form_valid(self, form):
        latest_version = self.sds.versions.order_by(
            '-version_number'
        ).first()

        if latest_version:
            next_version_number = latest_version.version_number + 1
        else:
            next_version_number = 1

        if self.sds.versions.filter(
            version_number=next_version_number
        ).exists():
            messages.error(
                self.request,
                'The next version number already exists. Please try again.'
            )

            return self.form_invalid(form)

        form.instance.sds = self.sds
        form.instance.version_number = next_version_number
        form.instance.status = 'DRAFT'
        form.instance.uploaded_by = self.request.user

        response = super().form_valid(form)

        # =========================================================
        # CREATE AUDIT LOG
        # =========================================================
        create_sds_audit_log(
            sds=self.sds,
            version=self.object,
            action='VERSION_CREATED',
            user=self.request.user,
            description=(
                f'SDS Version {self.object.version_number} was created.'
            ),
            old_status='',
            new_status='DRAFT'
        )

        messages.success(
            self.request,
            f'Version {self.object.version_number} '
            f'created successfully as DRAFT.'
        )

        return response

    def get_success_url(self):
        return reverse_lazy(
            'sds:sds_detail',
            kwargs={
                'pk': self.sds.pk
            }
        )




# =========================================================
# SDS VERSION STATUS UPDATE
# =========================================================
class SDSVersionStatusUpdateView(LoginRequiredMixin, SDSAccessMixin, View):
    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )

        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        current_status = version.status
        new_status = request.POST.get('status')

        # =========================================================
        # ALLOWED STATUS TRANSITIONS
        # =========================================================
        allowed_transitions = {
            'DRAFT': ['UNDER_REVIEW'],
            'UNDER_REVIEW': ['APPROVED', 'REJECTED'],
            'APPROVED': ['ACTIVE'],
            'REJECTED': ['DRAFT'],
            'ACTIVE': [],
            'SUPERSEDED': [],
        }

        # =========================================================
        # VALIDATE STATUS TRANSITION
        # =========================================================
        if new_status not in allowed_transitions.get(
            current_status,
            []
        ):
            messages.error(
                request,
                f'Invalid status transition from {version.get_status_display()} to {new_status}.'
            )

            return redirect(
                'sds:sds_detail',
                pk=sds.pk
            )

        # =========================================================
        # APPROVAL VALIDATION
        # =========================================================
        if new_status == 'APPROVED':

            # -----------------------------------------------------
            # Check SDS Section Completion
            # -----------------------------------------------------
            if not version.is_section_complete:
                messages.error(
                    request,
                    f'SDS Version {version.version_number} cannot be approved because all 16 SDS sections are not complete.'
                )

                return redirect(
                    'sds:sds_detail',
                    pk=sds.pk
                )

            # -----------------------------------------------------
            # Check Approved Review
            # -----------------------------------------------------
            approved_review_exists = SDSReview.objects.filter(
                sds=sds,
                version=version,
                status='APPROVED'
            ).exists()

            if not approved_review_exists:
                messages.error(
                    request,
                    'This SDS version cannot be approved without an approved review.'
                )

                return redirect(
                    'sds:sds_detail',
                    pk=sds.pk
                )

        # =========================================================
        # REJECTION VALIDATION
        # =========================================================
        if new_status == 'REJECTED':

            rejected_review_exists = SDSReview.objects.filter(
                sds=sds,
                version=version,
                status='REJECTED'
            ).exists()

            if not rejected_review_exists:
                messages.error(
                    request,
                    'This SDS version cannot be rejected without a rejected review.'
                )

                return redirect(
                    'sds:sds_detail',
                    pk=sds.pk
                )

        # =========================================================
        # ACTIVE VALIDATION
        # =========================================================
        if new_status == 'ACTIVE':

            # -----------------------------------------------------
            # Check SDS Section Completion
            # -----------------------------------------------------
            if not version.is_section_complete:
                messages.error(
                    request,
                    f'SDS Version {version.version_number} cannot be activated because all 16 SDS sections are not complete.'
                )

                return redirect(
                    'sds:sds_detail',
                    pk=sds.pk
                )

            # -----------------------------------------------------
            # Check Approved Review
            # -----------------------------------------------------
            approved_review_exists = SDSReview.objects.filter(
                sds=sds,
                version=version,
                status='APPROVED'
            ).exists()

            if not approved_review_exists:
                messages.error(
                    request,
                    'Only a reviewed and approved SDS version can be activated.'
                )

                return redirect(
                    'sds:sds_detail',
                    pk=sds.pk
                )

            # -----------------------------------------------------
            # Find Existing Active Version
            # -----------------------------------------------------
            active_version = SDSVersion.objects.filter(
                sds=sds,
                status='ACTIVE'
            ).exclude(
                pk=version.pk
            ).first()

            # -----------------------------------------------------
            # Supersede Previous Active Version
            # -----------------------------------------------------
            if active_version:
                active_version.status = 'SUPERSEDED'

                active_version.save(
                    update_fields=[
                        'status'
                    ]
                )

                create_sds_audit_log(sds=sds,version=active_version,
                    action='VERSION_SUPERSEDED',user=request.user,
                    description=(
                        f'SDS Version {active_version.version_number} was superseded '
                        f'by Version {version.version_number}.'
                    ),
                    old_status='ACTIVE',
                    new_status='SUPERSEDED'
                )

            # -----------------------------------------------------
            # Activate Selected Version
            # -----------------------------------------------------
            version.status = 'ACTIVE'

            version.save(
                update_fields=[
                    'status'
                ]
            )

            create_sds_audit_log(sds=sds,version=version,action='VERSION_ACTIVATED',
                user=request.user,
                description=(
                    f'SDS Version {version.version_number} was activated.'
                ),
                old_status='APPROVED',
                new_status='ACTIVE'
            )

            # -----------------------------------------------------
            # Synchronize Master SDS
            # -----------------------------------------------------
            sds.status = 'ACTIVE'
            sds.is_active = True
            sds.updated_by = request.user

            sds.save(
                update_fields=[
                    'status',
                    'is_active',
                    'updated_by',
                    'updated_at'
                ]
            )

            messages.success(
                request,
                f'SDS Version {version.version_number} is now the active version.'
            )

            return redirect(
                'sds:sds_detail',
                pk=sds.pk
            )

        # =========================================================
        # RETURN REJECTED VERSION TO DRAFT
        # =========================================================
        if new_status == 'DRAFT':
            version.status = 'DRAFT'

            version.save(
                update_fields=[
                    'status'
                ]
            )

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='VERSION_RETURNED_TO_DRAFT',
                user=request.user,
                description=(
                    f'SDS Version {version.version_number} was returned '
                    f'from Rejected to Draft.'
                ),
                old_status='REJECTED',
                new_status='DRAFT'
            )

            messages.info(
                request,
                f'SDS Version {version.version_number} has been returned to Draft.'
            )

            return redirect(
                'sds:sds_detail',
                pk=sds.pk
            )

        # =========================================================
        # UPDATE VERSION STATUS
        # =========================================================
        old_status_display = version.get_status_display()

        version.status = new_status

        new_status_display = version.get_status_display()

        version.save(update_fields=['status'])

        create_sds_audit_log(sds=sds,version=version,action='VERSION_STATUS_CHANGED',
            user=request.user,
            description=(
                f'SDS Version {version.version_number} status changed '
                f'from {old_status_display} '
                f'to {new_status_display}.'
            ),
            old_status=current_status,
            new_status=new_status
        )

        messages.success(
            request,
            f'SDS Version {version.version_number} status changed to {new_status_display}.'
        )

        return redirect(
            'sds:sds_detail',
            pk=sds.pk
        )

    
# ============================================================
# REVIEW LIST
# ============================================================

class SDSReviewListView(
    LoginRequiredMixin,
    SDSAccessMixin,
    ListView
):
    model = SDSReview
    template_name = 'sds/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        queryset = SDSReview.objects.select_related(
            'sds',
            'version',
            'reviewer',
            'submitted_by',
        )

        if not user.is_superuser and not getattr(
            user,
            'is_admin_user',
            False
        ):
            assigned_plants = user.get_all_plants()

            if assigned_plants:
                queryset = queryset.filter(
                    Q(sds__plant__in=assigned_plants) |
                    Q(sds__plant__isnull=True)
                )
            else:
                queryset = queryset.filter(
                    sds__plant__isnull=True
                )

        status = self.request.GET.get('status')

        if status:
            queryset = queryset.filter(
                status=status
            )

        return queryset.order_by(
            '-created_at'
        )


# =========================================================
# SDS REVIEW CREATE
# =========================================================
class SDSReviewCreateView(LoginRequiredMixin, SDSAccessMixin, CreateView):
    model = SDSReview
    form_class = SDSReviewForm
    template_name = 'sds/sds_review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.sds = get_object_or_404(
            SDS,
            pk=kwargs['sds_id']
        )
        self.version = get_object_or_404(
            SDSVersion,
            pk=kwargs['version_id'],
            sds=self.sds
        )

        self.check_sds_access(self.sds)

        if self.version.status != 'UNDER_REVIEW':
            messages.error(
                request,
                'This SDS version is not currently under review.'
            )
            return redirect(
                'sds:sds_detail',
                pk=self.sds.pk
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sds'] = self.sds
        context['version'] = self.version
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['sds'] = self.sds
        kwargs['version'] = self.version
        return kwargs

    def form_valid(self, form):
        review = form.save(commit=False)

        review.sds = self.sds
        review.version = self.version
        review.submitted_by = self.request.user
        review.submitted_at = timezone.now()

        status = form.cleaned_data.get('status')

        if status in ['IN_REVIEW', 'APPROVED', 'REJECTED']:
            review.reviewed_at = timezone.now()

        review.save()

        create_sds_audit_log(
            sds=self.sds,version=self.version,action='REVIEW_CREATED',
            user=request.user,description=(
                f'{review.get_review_type_display()} review was created '
                f'for SDS Version {self.version.version_number}.'
            )
        )

        create_sds_audit_log(
            sds=self.sds,
            version=self.version,
            action='REVIEW_CREATED',
            user=self.request.user,
            description=(
                f'{review.get_review_type_display()} review was created '
                f'for SDS Version {self.version.version_number}.'
            )
        )
        

        if status == 'APPROVED':
            self.version.status = 'APPROVED'
            self.version.save(update_fields=['status'])
            create_sds_audit_log(
                sds=self.sds,version=self.version,action='REVIEW_APPROVED',
                user=request.user,
                description=(
                    f'Review for SDS Version {self.version.version_number} was approved.'
                )
            )

            messages.success(
                self.request,
                f'SDS Version {self.version.version_number} has been approved.'
            )

        elif status == 'REJECTED':
            self.version.status = 'REJECTED'
            self.version.save(update_fields=['status'])

            create_sds_audit_log(
                sds=self.sds,version=self.version,action='REVIEW_REJECTED',
                user=request.user,
                description=(
                    f'Review for SDS Version {self.version.version_number} was rejected.'
                )
            )

            messages.warning(
                self.request,
                f'SDS Version {self.version.version_number} has been rejected.'
            )

        else:
            messages.info(
                self.request,
                f'Review for SDS Version {self.version.version_number} has been recorded.'
            )

        return redirect(
            'sds:sds_detail',
            pk=self.sds.pk
        )

# ============================================================
# QUICK STATUS ACTIONS
# ============================================================

class SDSStatusUpdateView(
    LoginRequiredMixin,
    SDSAccessMixin,
    View
):
    """
    Handles controlled status changes from the SDS detail screen.
    """

    ALLOWED_STATUS_TRANSITIONS = {
        'DRAFT': ['SUBMITTED'],
        'SUBMITTED': ['UNDER_REVIEW'],
        'UNDER_REVIEW': ['APPROVED', 'REJECTED'],
        'REJECTED': ['DRAFT'],
        'APPROVED': ['ACTIVE'],
        'ACTIVE': ['EXPIRED'],
        'SUPERSEDED': [],
        'EXPIRED': [],
    }

    def post(self, request, pk):
        sds = get_object_or_404(
            SDS,
            pk=pk
        )

        self.check_sds_access(sds)

        new_status = request.POST.get(
            'status'
        )

        allowed = self.ALLOWED_STATUS_TRANSITIONS.get(
            sds.status,
            []
        )

        if new_status not in allowed:
            messages.error(
                request,
                'This SDS status transition is not allowed.'
            )

            return redirect(
                'sds:sds_detail',
                pk=sds.pk
            )

        # =========================================================
        # ACTIVE STATUS VALIDATION
        # =========================================================
        if new_status == 'ACTIVE':

            # -----------------------------------------------------
            # SDS MUST HAVE AN ACTIVE VERSION
            # -----------------------------------------------------
            active_version = SDSVersion.objects.filter(
                sds=sds,
                status='ACTIVE'
            ).first()

            if not active_version:
                messages.error(
                    request,
                    'This SDS cannot be activated because it does not have an active SDS version. Activate an approved SDS version first.'
                )

                return redirect(
                    'sds:sds_detail',
                    pk=sds.pk
                )

        # =========================================================
        # UPDATE SDS STATUS
        # =========================================================
        old_status = sds.status

        sds.status = new_status

        if new_status == 'ACTIVE':
            sds.is_active = True

        elif new_status in [
            'EXPIRED',
            'SUPERSEDED',
        ]:
            sds.is_active = False

        sds.updated_by = request.user

        sds.save(
            update_fields=[
                'status',
                'is_active',
                'updated_by',
                'updated_at'
            ]
        )

        # =========================================================
        # AUDIT LOG
        # =========================================================
        create_sds_audit_log(
            sds=sds,
            action='STATUS_CHANGED',
            user=request.user,
            description=(
                f'SDS status changed from '
                f'{dict(SDS.STATUS_CHOICES).get(old_status, old_status)} '
                f'to '
                f'{dict(SDS.STATUS_CHOICES).get(new_status, new_status)}.'
            ),
            old_status=old_status,
            new_status=new_status
        )

        messages.success(
            request,
            f'SDS status changed to {sds.get_status_display()}.'
        )

        return redirect(
            'sds:sds_detail',
            pk=sds.pk
        )

# ============================================================
# DOWNLOAD SDS DOCUMENT
# ============================================================

class SDSDocumentView(
    LoginRequiredMixin,
    SDSAccessMixin,
    View
):
    """
    Redirects the user to the stored SDS document.

    Access is checked before exposing the file.
    """

    def get(self, request, pk):
        sds = get_object_or_404(
            SDS,
            pk=pk
        )

        self.check_sds_access(sds)

        if not sds.document:
            messages.error(
                request,
                'No SDS document is available.'
            )

            return redirect(
                'sds:sds_detail',
                pk=sds.pk
            )

        return redirect(
            sds.document.url
        )



# =============================================
# SDS Section 1 - Identification
# =============================================
class SDSSection1View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section1_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection1.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection1Form(
                instance=section
            )
        else:
            form = SDSSection1Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection1.objects.get_or_create(
            sds_version=version
        )

        form = SDSSection1Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            section = form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description='SDS Section 1 - Identification was updated.'
            )

            messages.success(
                request,
                'SDS Section 1 has been saved successfully.'
            )

            return redirect(
                'sds:section1',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )


# =============================================
# SDS Section 2 - Hazard(s) Identification
# =============================================
class SDSSection2View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section2_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )

        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection2.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection2Form(
                instance=section
            )
        else:
            form = SDSSection2Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )

        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection2.objects.get_or_create(
            sds_version=version
        )

        form = SDSSection2Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            section = form.save()

            create_sds_audit_log(
                sds=sds,version=version,action='SECTION_UPDATED',
                user=request.user,description='SDS Section 2 - Hazard Identification was updated.'
            )

            messages.success(
                request,
                'SDS Section 2 has been saved successfully.'
            )

            return redirect(
                'sds:section2',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )



# =============================================
# SDS Section 3 - Composition / Information on Ingredients
# =============================================
class SDSSection3View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section3_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )

        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection3.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection3Form(
                instance=section
            )
        else:
            form = SDSSection3Form()

        ingredient_formset = SDSSection3IngredientFormSet(
            instance=section
        )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'ingredient_formset': ingredient_formset,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )

        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )
        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection3.objects.get_or_create(
            sds_version=version
        )

        form = SDSSection3Form(
            request.POST,
            instance=section
        )

        ingredient_formset = SDSSection3IngredientFormSet(
            request.POST,
            instance=section
        )

        form_valid = form.is_valid()
        formset_valid = ingredient_formset.is_valid()

        if form_valid and formset_valid:
            section = form.save()

            ingredient_formset.instance = section
            ingredient_formset.save()

            create_sds_audit_log(
                sds=sds,version=version,action='SECTION_UPDATED',
                user=request.user,description='SDS Section 3 - Composition / Information on Ingredients was updated.'
            )

            messages.success(
                request,
                'SDS Section 3 has been saved successfully.'
            )

            return redirect(
                'sds:section3',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'ingredient_formset': ingredient_formset,
                'section': section,
            }
        )



# =============================================
# SDS Section 4 View - First-Aid Measures
# =============================================
class SDSSection4View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section4_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection4.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection4Form(
                instance=section
            )
        else:
            form = SDSSection4Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection4.objects.get_or_create(
            sds_version=version
        )

        form = SDSSection4Form(
            request.POST,
            instance=section
        )

        # =============================================
        # SDS Section 4 Save
        # =============================================
        if form.is_valid():
            form.save()

            # =============================================
            # SDS Section 4 Audit Log
            # =============================================
            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 4 - First-Aid Measures was updated.'
                )
            )

            messages.success(
                request,
                'SDS Section 4 has been saved successfully.'
            )

            return redirect(
                'sds:section4',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )



# =============================================
# SDS Section 5 View - Fire-Fighting Measures
# =============================================
class SDSSection5View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section5_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection5.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection5Form(
                instance=section
            )
        else:
            form = SDSSection5Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection5.objects.get_or_create(
            sds_version=version
        )

        form = SDSSection5Form(
            request.POST,
            instance=section
        )

        # =============================================
        # Validate and Save Section 5
        # =============================================
        if form.is_valid():
            form.save()

            # =============================================
            # SDS Section 5 Audit Log
            # =============================================
            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 5 - Fire-Fighting Measures was updated.'
                )
            )

            messages.success(
                request,
                'SDS Section 5 has been saved successfully.'
            )

            return redirect(
                'sds:section5',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )
    

# =============================================
# SDS Section 6 View - Accidental Release Measures
# =============================================
class SDSSection6View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section6_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection6.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection6Form(
                instance=section
            )
        else:
            form = SDSSection6Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection6.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection6Form(
            request.POST,
            instance=section
        )

        # =============================================
        # Validate and Save Section 6
        # =============================================
        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 6 - Accidental Release Measures was updated.'
                )
            )

            messages.success(
                request,
                'SDS Section 6 has been saved successfully.'
            )

            return redirect(
                'sds:section6',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )



# =============================================
# SDS Section 7 View - Handling and Storage
# =============================================
class SDSSection7View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section7_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection7.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection7Form(
                instance=section
            )
        else:
            form = SDSSection7Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection7.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection7Form(
            request.POST,
            instance=section
        )

        # =============================================
        # Validate and Save Section 7
        # =============================================
        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 7 - Handling and Storage was updated.'
                )
            )

            messages.success(
                request,
                'SDS Section 7 has been saved successfully.'
            )

            return redirect(
                'sds:section7',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section,
            }
        )



# =============================================
# SDS Section 8 View - Exposure Controls / Personal Protection
# =============================================
class SDSSection8View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section8_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection8.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection8Form(
                instance=section
            )
        else:
            form = SDSSection8Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection8.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection8Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()
            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 8 - Exposure Controls / Personal Protection was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 8 has been saved successfully.'
            )
            return redirect(
                'sds:section8',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )





# =============================================
# SDS Section 9 View - Physical and Chemical Properties
# =============================================
class SDSSection9View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section9_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection9.objects.filter(
            sds_version=version
        ).first()
        if section:
            form = SDSSection9Form(
                instance=section
            )
        else: 
            form = SDSSection9Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection9.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection9Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 9 - Physical and Chemical Properties was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 9 has been saved successfully.'
            )
            return redirect(
                'sds:section9',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )



# =============================================
# SDS Section 10 View - Stability and Reactivity
# =============================================
class SDSSection10View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section10_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection10.objects.filter(
            sds_version=version
        ).first()

        if section: 
            form = SDSSection10Form(
                instance=section
            )
        else:
            form = SDSSection10Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection10.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection10Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()
            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 10 - Stability and Reactivity was updated.'
                )
            )

            messages.success(
                request,
                'SDS Section 10 has been saved successfully.'
            )
            return redirect(
                'sds:section10',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )



# =============================================
# SDS Section 11 View - Toxicological Information
# =============================================
class SDSSection11View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section11_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection11.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection11Form(
                instance=section
            )
        else:
            form = SDSSection11Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection11.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection11Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 11 - Toxicological Information was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 11 has been saved successfully.'
            )
            return redirect(
                'sds:section11',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )




# =============================================
# SDS Section 12 View - Ecological Information
# =============================================
class SDSSection12View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section12_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection12.objects.filter(
            sds_version=version
        ).first()
        if section:
            form = SDSSection12Form(
                instance=section
            )
        else:
            form = SDSSection12Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection12.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection12Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()
            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 12 - Ecological Information was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 12 has been saved successfully.'
            )
            return redirect(
                'sds:section12',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )




# =============================================
# SDS Section 13 View - Disposal Considerations
# =============================================
class SDSSection13View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section13_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection13.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection13Form(
                instance=section
            )
        else:
            form = SDSSection13Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection13.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection13Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()
            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 13 - Disposal Considerations was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 13 has been saved successfully.'
            )
            return redirect(
                'sds:section13',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )



# =============================================
# SDS Section 14 View - Transport Information
# =============================================
class SDSSection14View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section14_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection14.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection14Form(
                instance=section
            )
        else:
            form = SDSSection14Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection14.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection14Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 14 - Transport Information was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 14 has been saved successfully.'
            )
            return redirect(
                'sds:section14',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )



# =============================================
# SDS Section 15 View - Regulatory Information
# =============================================
class SDSSection15View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section15_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection15.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection15Form(
                instance=section
            )
        else:
            form = SDSSection15Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)

        section, created = SDSSection15.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection15Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 15 - Regulatory Information was updated.'
                )
            )

            messages.success(
                request,
                'SDS Section 15 has been saved successfully.'
            )
            return redirect(
                'sds:section15',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )



# =============================================
# SDS Section 16 View - Other Information
# =============================================
class SDSSection16View(LoginRequiredMixin, SDSAccessMixin, View):
    template_name = 'sds/section16_form.html'

    def get(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)

        section = SDSSection16.objects.filter(
            sds_version=version
        ).first()

        if section:
            form = SDSSection16Form(
                instance=section
            )
        else:
            form = SDSSection16Form()

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )

    def post(self, request, sds_id, version_id):
        sds = get_object_or_404(
            SDS,
            pk=sds_id
        )
        version = get_object_or_404(
            SDSVersion,
            pk=version_id,
            sds=sds
        )

        self.check_sds_access(sds)
        self.check_version_edit_access(version)
        
        section, created = SDSSection16.objects.get_or_create(
            sds_version=version
        )
        form = SDSSection16Form(
            request.POST,
            instance=section
        )

        if form.is_valid():
            form.save()

            create_sds_audit_log(
                sds=sds,
                version=version,
                action='SECTION_UPDATED',
                user=request.user,
                description=(
                    'SDS Section 16 - Other Information was updated.'
                )
            )
            messages.success(
                request,
                'SDS Section 16 has been saved successfully.'
            )
            return redirect(
                'sds:section16',
                sds_id=sds.pk,
                version_id=version.pk
            )

        return render(
            request,
            self.template_name,
            {
                'sds': sds,
                'version': version,
                'form': form,
                'section': section
            }
        )