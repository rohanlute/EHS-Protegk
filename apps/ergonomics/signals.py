import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    ErgonomicAssessment,
    ErgonomicAssessmentSchedule,
    ErgonomicCorrectiveAction,
    ErgonomicJobMapping,
    ErgonomicReassessment,
    MSDDiscomfort,
)

# -----------------------------------------------------------------------------
# Notifications
#
# The notifications app may or may not exist in a given deployment, and its
# supported notification codes vary. We never want a missing/broken
# notification to take down the save() chain for an ergonomic record, so all
# calls go through a defensive helper.
# -----------------------------------------------------------------------------
try:
    from apps.notifications.services import NotificationService
except Exception:  # pragma: no cover - defensive: notifications is optional
    NotificationService = None


def _safe_notify(instance, code, module="ERGONOMICS"):
    """
    Fire a notification, but never let an exception propagate.

    - If NotificationService is not importable -> silent no-op.
    - If it doesn't have a `notify` method -> silent no-op.
    - If `notify` itself raises -> silent no-op (log if you have a logger).

    This keeps ergonomic assessments / actions / reassessments / MSD cases
    always savable, regardless of the notifications app's state.
    """
    if NotificationService is None:
        return
    notify = getattr(NotificationService, "notify", None)
    if not callable(notify):
        return
    try:
        notify(instance, code, module=module)
    except Exception:
        # Intentionally swallowed. Plug a logger here if you want visibility.
        pass


HIGH_RISK_REVIEW_DAYS = 90
PERIODIC_REVIEW_DAYS = 365


# =============================================================================
# ERGONOMIC ASSESSMENT -> notifications + auto-schedule + auto job mapping
# =============================================================================
@receiver(post_save, sender=ErgonomicAssessment)
def handle_assessment_saved(sender, instance, created, **kwargs):
    if not instance.risk_level:
        return

    # --- Notifications on high / very high risk -----------------------------
    if instance.risk_level == "VERY_HIGH":
        _safe_notify(instance, "ERGONOMIC_VERY_HIGH_RISK")
    elif instance.risk_level == "HIGH":
        _safe_notify(instance, "ERGONOMIC_HIGH_RISK")

    # --- Auto-schedule next review ------------------------------------------
    if instance.risk_level in {"HIGH", "VERY_HIGH"}:
        due_date = instance.assessment_date + datetime.timedelta(days=HIGH_RISK_REVIEW_DAYS)
        reason = "HIGH_RISK"
    else:
        due_date = instance.assessment_date + datetime.timedelta(days=PERIODIC_REVIEW_DAYS)
        reason = "PERIODIC"

    # Use .save(update_fields=...) instead of queryset.update() so
    # django-simple-history records this change in the audit trail.
    if not instance.next_assessment_date:
        instance.next_assessment_date = due_date
        instance.save(update_fields=["next_assessment_date"])

    open_schedule = ErgonomicAssessmentSchedule.objects.filter(
        assessment=instance,
        reason=reason,
        status__in=["DUE", "UPCOMING", "OVERDUE"],
    ).first()

    if open_schedule:
        open_schedule.due_date = due_date
        open_schedule.assigned_to = instance.assessor
        open_schedule.save(update_fields=["due_date", "assigned_to"])
    else:
        ErgonomicAssessmentSchedule.objects.create(
            assessment=instance,
            plant=instance.plant,
            department=instance.department,
            job=instance.job_role,
            task=instance.task,
            due_date=due_date,
            reason=reason,
            assigned_to=instance.assessor,
        )

    # --- Auto job/worker mapping --------------------------------------------
    if instance.worker_id:
        ErgonomicJobMapping.objects.update_or_create(
            worker=instance.worker,
            job=instance.job_role,
            task=instance.task,
            defaults={
                "department": instance.department,
                "assessment": instance,
                "is_active": True,
            },
        )


# =============================================================================
# CORRECTIVE ACTION -> notifications + auto-schedule reassessment on close
# =============================================================================
@receiver(post_save, sender=ErgonomicCorrectiveAction)
def handle_action_saved(sender, instance, created, **kwargs):
    if created:
        _safe_notify(instance, "ERGONOMIC_ACTION_ASSIGNED")
    elif instance.status == "OVERDUE":
        _safe_notify(instance, "ERGONOMIC_ACTION_OVERDUE")
    elif instance.status in {"COMPLETED", "CLOSED"}:
        # Corrective action closed -> a reassessment becomes due.
        already_open = ErgonomicAssessmentSchedule.objects.filter(
            assessment=instance.assessment,
            reason="CORRECTIVE_ACTION",
            status__in=["DUE", "UPCOMING", "OVERDUE"],
        ).exists()

        if not already_open:
            ErgonomicAssessmentSchedule.objects.create(
                assessment=instance.assessment,
                plant=instance.assessment.plant,
                department=instance.assessment.department,
                job=instance.assessment.job_role,
                task=instance.assessment.task,
                due_date=timezone.now().date() + datetime.timedelta(days=30),
                reason="CORRECTIVE_ACTION",
                assigned_to=instance.responsible_person,
                status="DUE",
            )


# =============================================================================
# REASSESSMENT -> notifications + close schedule + roll-forward score/risk
# =============================================================================
@receiver(post_save, sender=ErgonomicReassessment)
def handle_reassessment_saved(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.control_effectiveness == "NOT_EFFECTIVE":
        _safe_notify(instance, "ERGONOMIC_REASSESSMENT_INEFFECTIVE")

    # Mark the originating schedule entry completed, if any.
    ErgonomicAssessmentSchedule.objects.filter(
        assessment=instance.assessment,
        status__in=["DUE", "UPCOMING", "OVERDUE"],
    ).update(status="COMPLETED")

    # Roll the new score/risk back onto the parent assessment for dashboards.
    # Use .save(update_fields=...) instead of queryset.update() so the change
    # is captured by django-simple-history.
    parent = ErgonomicAssessment.objects.filter(pk=instance.assessment_id).first()
    if parent:
        parent.score = instance.new_score
        parent.risk_level = instance.new_risk
        parent.save(update_fields=["score", "risk_level"])


# =============================================================================
# MSD / DISCOMFORT -> notifications + auto-schedule post-MSD assessment
# =============================================================================
@receiver(post_save, sender=MSDDiscomfort)
def handle_msd_saved(sender, instance, created, **kwargs):
    if not created:
        return

    _safe_notify(instance, "ERGONOMIC_MSD_REPORTED")

    # Post-MSD assessment becomes due if not already linked to one and we
    # can resolve a plant (schedule.plant is a required FK).
    plant = getattr(instance.department, "plant", None) if instance.department_id else None

    if not instance.related_assessment_id and instance.department_id and plant:
        ErgonomicAssessmentSchedule.objects.create(
            plant=plant,
            department=instance.department,
            job=instance.job or "",
            task=instance.task or "",
            due_date=timezone.now().date() + datetime.timedelta(days=14),
            reason="MSD_CASE",
            status="DUE",
        )