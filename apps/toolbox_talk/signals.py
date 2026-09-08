from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.alert_engine.services import NotificationService

from .models import ToolboxSessionAssignment


@receiver(pre_save, sender=ToolboxSessionAssignment)
def track_assignment_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )


@receiver(post_save, sender=ToolboxSessionAssignment)
def notify_toolbox_assignment(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify(
            instance,
            "TOOLBOX_SESSION_ASSIGNED",
            module="TOOLBOX_TALK",
            extra_recipients=[instance.user],
        )
    elif (
        instance.status == "COMPLETED"
        and getattr(instance, "_previous_status", None) != "COMPLETED"
    ):
        NotificationService.notify(
            instance,
            "TOOLBOX_SESSION_COMPLETED",
            module="TOOLBOX_TALK",
            extra_recipients=[instance.session.created_by],
        )