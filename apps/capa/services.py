from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.capa.models import (
    CAPA,
    CAPAAuditLog,
    CAPAAction,
    CAPAActionCompletion,
    CAPAActionVerification,
    CAPAEffectivenessReview,
    CAPAInvestigation,
)


class CAPAService:
    @staticmethod
    def _notify(capa, event_type, extra_recipients=None):
        """Keep notifications best-effort so workflow writes are not lost to email config."""
        try:
            from apps.notifications.services import NotificationService

            NotificationService.notify(
                capa,
                event_type,
                module="CAPA",
                extra_recipients=extra_recipients,
            )
        except Exception:
            # Notification failures must not roll back a valid CAPA transition.
            return

    @staticmethod
    def _audit(capa, user, action, old_value="", new_value="", comments=""):
        CAPAAuditLog.objects.create(
            capa=capa,
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action,
            old_value=str(old_value)[:4000],
            new_value=str(new_value)[:4000],
            comments=comments[:4000],
        )

    @staticmethod
    def _ensure_can(user, permission_code):
        if not (user and (user.is_superuser or user.has_permission(permission_code))):
            raise PermissionDenied("You do not have permission to perform this action.")

    @staticmethod
    def _set_status(capa, new_status, user=None, action="STATUS_CHANGED", comments=""):
        old_status = capa.status
        capa.status = new_status
        capa.updated_by = user
        capa.save(update_fields=["status", "updated_by", "updated_at", "closed_date", "reopened_date"])
        CAPAService._audit(capa, user, action, old_status, new_status, comments)

    @staticmethod
    def _source_payload(source_obj):
        if not source_obj:
            return {}, None, None

        ctype = ContentType.objects.get_for_model(source_obj, for_concrete_model=False)
        payload = {
            "str": str(source_obj),
        }
        for field in ("report_number", "hazard_title", "title", "description", "plant_id", "zone_id", "location_id", "sublocation_id"):
            if hasattr(source_obj, field):
                payload[field] = getattr(source_obj, field)
        return payload, ctype, getattr(source_obj, "pk", None)

    @staticmethod
    @transaction.atomic
    def create_capa(*, user, title, description, plant, source_type=CAPA.SourceType.MANUAL, source_reference="", zone=None, location=None, sublocation=None, department=None, category="", severity=CAPA.Severity.MEDIUM, priority=CAPA.Priority.MEDIUM, owner=None, target_date=None, reason_required="", capa_recommended=False, capa_reason="", source_obj=None, status=CAPA.Status.OPEN):
        CAPAService._ensure_can(user, "CAPA_CREATE")
        capa = CAPA(
            title=title,
            description=description,
            plant=plant,
            zone=zone,
            location=location,
            sublocation=sublocation,
            department=department,
            category=category,
            severity=severity,
            priority=priority,
            owner=owner,
            target_date=target_date,
            reason_required=reason_required,
            capa_recommended=capa_recommended,
            capa_reason=capa_reason,
            source_type=source_type,
            source_reference=source_reference,
            created_by=user,
            updated_by=user,
            status=status,
        )
        if source_obj is not None:
            payload, ctype, object_id = CAPAService._source_payload(source_obj)
            capa.source_content_type = ctype
            capa.source_object_id = object_id
            capa.source_snapshot = payload
        capa.save()
        CAPAService._audit(capa, user, "CAPA_CREATED", "", capa.capa_number)
        CAPAService._notify(capa, "CAPA_CREATED", [owner] if owner else None)
        return capa

    @staticmethod
    def create_from_incident(*, user, incident, **kwargs):
        title = kwargs.pop("title", f"CAPA for {incident.report_number}")
        description = kwargs.pop("description", incident.description)
        source_reference = kwargs.pop("source_reference", incident.report_number)
        department = kwargs.pop("department", incident.affected_person_department or getattr(incident.reported_by, "department", None))
        return CAPAService.create_capa(
            user=user,
            title=title,
            description=description,
            plant=incident.plant,
            zone=incident.zone,
            location=incident.location,
            sublocation=incident.sublocation,
            department=department,
            source_type=CAPA.SourceType.INCIDENT,
            source_reference=source_reference,
            source_obj=incident,
            **kwargs,
        )

    @staticmethod
    def create_from_hazard(*, user, hazard, **kwargs):
        title = kwargs.pop("title", f"CAPA for {hazard.report_number}")
        description = kwargs.pop("description", hazard.hazard_description)
        source_reference = kwargs.pop("source_reference", hazard.report_number)
        department = kwargs.pop("department", hazard.behalf_person_dept)
        return CAPAService.create_capa(
            user=user,
            title=title,
            description=description,
            plant=hazard.plant,
            zone=hazard.zone,
            location=hazard.location,
            sublocation=hazard.sublocation,
            department=department,
            source_type=CAPA.SourceType.HAZARD,
            source_reference=source_reference,
            source_obj=hazard,
            **kwargs,
        )

    @staticmethod
    def submit_investigation(*, user, capa, investigation):
        CAPAService._ensure_can(user, "CAPA_INVESTIGATE")
        if capa.status not in {CAPA.Status.OPEN, CAPA.Status.DRAFT, CAPA.Status.INVESTIGATION_IN_PROGRESS, CAPA.Status.INVESTIGATION_REJECTED, CAPA.Status.REOPENED}:
            raise ValidationError("Investigation cannot be submitted in the current CAPA status.")
        if investigation.completed_date and capa.status != CAPA.Status.INVESTIGATION_REJECTED:
            raise ValidationError("This investigation has already been submitted.")
        investigation.completed_by = user
        investigation.completed_date = timezone.localdate()
        investigation.save()
        CAPAService._set_status(capa, CAPA.Status.INVESTIGATION_SUBMITTED, user, "INVESTIGATION_SUBMITTED")
        CAPAService._notify(capa, "CAPA_INVESTIGATION_SUBMITTED", [investigation.lead_investigator] if investigation.lead_investigator else None)
        return investigation

    @staticmethod
    def approve_investigation(*, user, capa, remarks=""):
        CAPAService._ensure_can(user, "CAPA_APPROVE_INVESTIGATION")
        if capa.status != CAPA.Status.INVESTIGATION_SUBMITTED:
            raise ValidationError("Only a submitted investigation can be approved.")
        if not hasattr(capa, "investigation"):
            raise ValidationError("Investigation is required before approval.")
        capa.investigation.reviewer = user
        capa.investigation.review_date = timezone.localdate()
        capa.investigation.reviewer_comments = remarks
        capa.investigation.save()
        CAPAService._set_status(capa, CAPA.Status.INVESTIGATION_APPROVED, user, "INVESTIGATION_APPROVED", remarks)
        CAPAService._notify(capa, "CAPA_INVESTIGATION_APPROVED", [capa.owner] if capa.owner else None)

    @staticmethod
    def reject_investigation(*, user, capa, remarks):
        CAPAService._ensure_can(user, "CAPA_APPROVE_INVESTIGATION")
        if capa.status != CAPA.Status.INVESTIGATION_SUBMITTED:
            raise ValidationError("Only a submitted investigation can be rejected.")
        if not remarks:
            raise ValidationError("Rejection reason is required.")
        if not hasattr(capa, "investigation"):
            raise ValidationError("Investigation is required before rejection.")
        capa.investigation.reviewer = user
        capa.investigation.review_date = timezone.localdate()
        capa.investigation.reviewer_comments = remarks
        capa.investigation.completed_by = None
        capa.investigation.completed_date = None
        capa.investigation.save(update_fields=["reviewer", "review_date", "reviewer_comments", "completed_by", "completed_date", "updated_at"])
        CAPAService._set_status(capa, CAPA.Status.INVESTIGATION_REJECTED, user, "INVESTIGATION_REJECTED", remarks)
        CAPAService._notify(capa, "CAPA_INVESTIGATION_REJECTED", [capa.owner] if capa.owner else None)

    @staticmethod
    @transaction.atomic
    def create_action(*, user, capa, **kwargs):
        CAPAService._ensure_can(user, "CAPA_MANAGE_ACTIONS")
        if capa.status not in {
            CAPA.Status.INVESTIGATION_APPROVED,
            CAPA.Status.ACTION_PLAN_IN_PROGRESS,
            CAPA.Status.ACTION_IMPLEMENTATION,
            CAPA.Status.REOPENED,
        }:
            raise ValidationError("Action plan cannot be created before investigation approval.")
        action = CAPAAction.objects.create(capa=capa, created_by=user, **kwargs)
        if capa.status == CAPA.Status.INVESTIGATION_APPROVED:
            CAPAService._set_status(capa, CAPA.Status.ACTION_PLAN_IN_PROGRESS, user, "ACTION_ADDED")
        CAPAService._notify(action.capa, "CAPA_ACTION_ASSIGNED", [action.assigned_to] if action.assigned_to else None)
        return action

    @staticmethod
    def complete_action(*, user, action, completion_remarks="", evidence=None):
        if not action.assigned_to_id:
            raise ValidationError("Assign this action before submitting it for verification.")
        if action.assigned_to_id != user.pk:
            raise PermissionDenied("Only the user assigned to this action can complete it.")
        if action.status not in {CAPAAction.Status.PENDING, CAPAAction.Status.IN_PROGRESS, CAPAAction.Status.REJECTED}:
            raise ValidationError("Only an open action can be submitted for verification.")
        if action.capa.status not in {CAPA.Status.ACTION_PLAN_IN_PROGRESS, CAPA.Status.ACTION_IMPLEMENTATION, CAPA.Status.REOPENED}:
            raise ValidationError("Action completion is not available at this CAPA stage.")
        completion, _ = CAPAActionCompletion.objects.get_or_create(action=action)
        completion.completed_by = user
        completion.completion_date = timezone.localdate()
        completion.completion_remarks = completion_remarks
        if evidence is not None:
            completion.evidence = evidence
        completion.submitted_for_verification = True
        completion.save()
        action.completion_remarks = completion_remarks
        action.status = CAPAAction.Status.PENDING_VERIFICATION
        action.save(update_fields=["completion_remarks", "status", "updated_at"])
        CAPAService._audit(action.capa, user, "ACTION_COMPLETED", "", action.pk, completion_remarks)
        if action.capa.status in {CAPA.Status.ACTION_PLAN_IN_PROGRESS, CAPA.Status.REOPENED}:
            CAPAService._set_status(action.capa, CAPA.Status.ACTION_IMPLEMENTATION, user, "ACTION_IMPLEMENTATION_STARTED")
        CAPAService._notify(action.capa, "CAPA_ACTION_SUBMITTED", [action.assigned_to] if action.assigned_to else None)
        return completion

    @staticmethod
    def verify_action(*, user, action, result, remarks="", **data):
        CAPAService._ensure_can(user, "CAPA_VERIFY_ACTION")
        if action.status != CAPAAction.Status.PENDING_VERIFICATION:
            raise ValidationError("Only an action submitted for verification can be verified.")
        if not hasattr(action, "completion"):
            raise ValidationError("Cannot verify an action that was not completed.")
        if not action.completion.submitted_for_verification:
            raise ValidationError("Cannot verify an action that has not been submitted for verification.")
        verification, _ = CAPAActionVerification.objects.get_or_create(action=action)
        for key, value in data.items():
            if hasattr(verification, key):
                setattr(verification, key, value)
        verification.verified_by = user
        verification.verification_date = timezone.localdate()
        verification.result = result
        verification.verification_findings = remarks
        verification.save()
        if result == CAPAActionVerification.Result.REJECTED:
            action.status = CAPAAction.Status.IN_PROGRESS
            action.verified_remarks = remarks
        elif result == CAPAActionVerification.Result.PARTIALLY_VERIFIED:
            action.status = CAPAAction.Status.PENDING_VERIFICATION
            action.verified_remarks = remarks
        else:
            action.status = CAPAAction.Status.VERIFIED
            action.verified_remarks = remarks
        action.save(update_fields=["status", "verified_remarks", "updated_at"])
        CAPAService._audit(action.capa, user, "ACTION_VERIFIED", "", result, remarks)
        CAPAService._notify(action.capa, "CAPA_ACTION_VERIFIED", [action.assigned_to] if action.assigned_to else None)
        if result == CAPAActionVerification.Result.VERIFIED and not action.capa.actions.exclude(status=CAPAAction.Status.VERIFIED).exists():
            CAPAService._set_status(action.capa, CAPA.Status.VERIFICATION, user, "VERIFICATION_READY")
        return verification

    @staticmethod
    def start_effectiveness_review(*, user, capa):
        CAPAService._ensure_can(user, "CAPA_EFFECTIVENESS")
        if capa.status != CAPA.Status.VERIFICATION:
            raise ValidationError("Effectiveness review requires all actions to be verified.")
        if not capa.actions.exists() or capa.actions.exclude(status=CAPAAction.Status.VERIFIED).exists():
            raise ValidationError("All actions must be verified before effectiveness review.")
        CAPAService._set_status(capa, CAPA.Status.EFFECTIVENESS_REVIEW, user, "EFFECTIVENESS_REVIEW_STARTED")

    @staticmethod
    def complete_effectiveness_review(*, user, capa, review):
        CAPAService._ensure_can(user, "CAPA_EFFECTIVENESS")
        if capa.status not in {CAPA.Status.VERIFICATION, CAPA.Status.EFFECTIVENESS_REVIEW}:
            raise ValidationError("Effectiveness review is not available at this CAPA stage.")
        if not capa.actions.exists() or capa.actions.exclude(status=CAPAAction.Status.VERIFIED).exists():
            raise ValidationError("All actions must be verified before effectiveness review.")
        review.reviewed_by = user
        review.review_date = timezone.localdate()
        review.save()
        CAPAService._audit(capa, user, "EFFECTIVENESS_COMPLETED", "", review.result)
        if review.result != CAPAEffectivenessReview.Result.EFFECTIVE:
            CAPAService._set_status(capa, CAPA.Status.REOPENED, user, "CAPA_REOPENED", "Effectiveness failed")
            CAPAService._notify(capa, "CAPA_EFFECTIVENESS_FAILED", [capa.owner] if capa.owner else None)
        return review

    @staticmethod
    def close_capa(*, user, capa, closure_remarks="", lessons_learned="", final_recommendations=""):
        CAPAService._ensure_can(user, "CAPA_CLOSE")
        if not hasattr(capa, "investigation"):
            raise ValidationError("Investigation must be completed before closure.")
        if capa.status != CAPA.Status.EFFECTIVENESS_REVIEW:
            raise ValidationError("CAPA must progress through investigation, action, verification and effectiveness review before closure.")
        if capa.actions.filter(status__in=[CAPAAction.Status.PENDING, CAPAAction.Status.IN_PROGRESS, CAPAAction.Status.SUBMITTED, CAPAAction.Status.REJECTED, CAPAAction.Status.PENDING_VERIFICATION]).exists():
            raise ValidationError("Cannot close CAPA with pending or unverified actions.")
        try:
            review = capa.effectiveness_review
        except CAPAEffectivenessReview.DoesNotExist:
            raise ValidationError("Effectiveness review is required before closure.")
        if review.result != CAPAEffectivenessReview.Result.EFFECTIVE:
            raise ValidationError("CAPA cannot be closed unless effectiveness is Effective.")
        capa.closure_remarks = closure_remarks
        capa.lessons_learned = lessons_learned
        capa.final_recommendations = final_recommendations
        CAPAService._set_status(capa, CAPA.Status.CLOSED, user, "CAPA_CLOSED", closure_remarks)
        capa.closed_by = user
        capa.save(update_fields=["closure_remarks", "lessons_learned", "final_recommendations", "closed_by", "updated_at", "status", "closed_date"])
        CAPAService._notify(capa, "CAPA_CLOSED", [capa.owner] if capa.owner else None)
        return capa

    @staticmethod
    def reopen_capa(*, user, capa, reason=""):
        CAPAService._ensure_can(user, "CAPA_REOPEN")
        if not reason:
            raise ValidationError("Reason is required to reopen a CAPA.")
        capa.reopened_by = user
        capa.reopened_date = timezone.now()
        capa.save(update_fields=["reopened_by", "reopened_date", "updated_at"])
        CAPAService._set_status(capa, CAPA.Status.REOPENED, user, "CAPA_REOPENED", reason)
        CAPAService._notify(capa, "CAPA_REOPENED", [capa.owner] if capa.owner else None)
        return capa
