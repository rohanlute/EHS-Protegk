from .models import ErgonomicAuditLog


def log_ergonomic_action(
    *,
    user,
    action,
    instance,
    changes=None,
    message="",
    request=None,
):
    """
    Write an audit entry for an ergonomics record.

    Usage:
        log_ergonomic_action(
            user=request.user,
            action=ErgonomicAuditLog.ACTION_STATUS_CHANGE,
            instance=action_obj,
            changes={"status": ["IN_PROGRESS", "PENDING_VERIFICATION"]},
            message="Submitted evidence.",
            request=request,
        )
    """
    ip = None
    ua = ""

    if request is not None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:255]

    ErgonomicAuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        model_name=instance._meta.model_name,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=changes or {},
        message=message,
        ip_address=ip,
        user_agent=ua,
    )


def get_ergonomic_audit_logs(instance, limit=100):
    """Fetch the audit trail for a single ergonomics object."""
    return (
        ErgonomicAuditLog.objects
        .filter(
            model_name=instance._meta.model_name,
            object_id=str(instance.pk),
        )
        .select_related("user")
        .order_by("-timestamp")[:limit]
    )