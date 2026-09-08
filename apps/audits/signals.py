from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.alert_engine.services import NotificationService

from .models import AuditFinding, AuditResponse, AuditSchedule, CAPA


@receiver(pre_save, sender=AuditSchedule)
def track_audit_schedule_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )


@receiver(post_save, sender=AuditSchedule)
def notify_audit_schedule(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify(
            instance,
            "AUDIT_SCHEDULE_CREATED",
            module="AUDIT",
            extra_recipients=[instance.auditor],
        )
    elif (
        instance.status == AuditSchedule.STATUS_COMPLETED
        and getattr(instance, "_previous_status", None) != AuditSchedule.STATUS_COMPLETED
    ):
        NotificationService.notify(
            instance,
            "AUDIT_COMPLETED",
            module="AUDIT",
            extra_recipients=[instance.auditor],
        )


@receiver(post_save, sender=AuditFinding)
def notify_audit_finding(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify(instance, "AUDIT_FINDING_CREATED", module="AUDIT")


@receiver(post_save, sender=CAPA)
def notify_audit_capa(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify(
            instance,
            "AUDIT_CAPA_ASSIGNED",
            module="AUDIT",
            extra_recipients=[instance.assigned_to],
        )


@receiver(post_save, sender=AuditResponse)
def create_finding_for_failed_response(sender, instance, created, **kwargs):
    if instance.status != AuditResponse.STATUS_FAIL:
        return

    finding_defaults = {
        "observation_detail": instance.comment or instance.question.question_text,
        "risk_score": AuditFinding.RISK_MAJOR,
        "status": AuditFinding.STATUS_DRAFT,
        "manager_review_status": AuditFinding.REVIEW_PENDING,
        "is_archived": False,
    }

    finding, was_created = AuditFinding.objects.get_or_create(
        parent_audit=instance.schedule,
        origin_question=instance.question,
        defaults=finding_defaults,
    )

    if not was_created and finding.is_archived:
        finding.is_archived = False
        finding.archived_at = None
        finding.status = AuditFinding.STATUS_DRAFT
        finding.manager_review_status = AuditFinding.REVIEW_PENDING
        if instance.comment:
            finding.observation_detail = instance.comment
        finding.save(
            update_fields=[
                "is_archived",
                "archived_at",
                "status",
                "manager_review_status",
                "observation_detail",
                "updated_at",
            ]
        )
