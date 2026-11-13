# apps/five_s/utils.py
"""
Shared 5S helpers for the pause/resume ("lock") mechanism.

A 5S schedule is considered *locked* when its status is PAUSED or ENDED.
While locked, every write action that is tied to that schedule must be
refused, both server-side (in views) and client-side (buttons hidden in
templates).  The helpers below are the single source of truth for that
decision so that views, templates, and the CAPA app all agree.

Nothing here mutates data; these are pure read helpers plus one
redirect-returning guard.

Import from views, context processors, and the CAPA app.  Do NOT import
from views.py here (would create a circular import).
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect

from .models import AuditAnswer, CorrectiveAction, FiveSAudit, FiveSSchedule


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

#: Schedule statuses during which all related write actions are disabled.
LOCKED_SCHEDULE_STATUSES = ('PAUSED', 'ENDED')

#: A human-readable label per locked status, used in messages.
LOCKED_STATUS_LABEL = {
    'PAUSED': 'paused',
    'ENDED': 'ended',
}


# ---------------------------------------------------------------------------
# Lock detection
# ---------------------------------------------------------------------------

def schedule_is_locked(schedule) -> bool:
    """True if the schedule is paused or ended (all writes disabled)."""
    return schedule is not None and schedule.status in LOCKED_SCHEDULE_STATUSES


def schedule_is_paused(schedule) -> bool:
    """True only if explicitly paused (not ended). Useful for banners."""
    return schedule is not None and schedule.status == 'PAUSED'


def audit_is_locked(audit) -> bool:
    """True if the audit's parent schedule is locked."""
    return audit is not None and schedule_is_locked(audit.schedule)


def action_is_locked(action) -> bool:
    """True if the corrective action's audit belongs to a locked schedule."""
    return action is not None and audit_is_locked(action.audit)


def capa_is_locked(capa) -> bool:
    """
    Resolve a 5S CAPA back to its schedule and return whether it is locked.

    A 5S CAPA links to either:
      * an AuditAnswer.id   (per-finding CAPA), or
      * a FiveSSchedule.pk  (schedule-wide CAPA)

    Both are stored in ``capa.source_reference`` as a string.  We try the
    schedule first (cheaper, unique pk), then fall back to the answer.
    CAPAs from other apps (source_type != 'FIVE_S') are never locked by
    this module.
    """
    if capa is None or getattr(capa, 'source_type', None) != 'FIVE_S':
        return False

    ref = str(getattr(capa, 'source_reference', '') or '')
    if not ref:
        return False

    # Schedule-wide CAPA
    schedule = FiveSSchedule.objects.filter(pk=ref).only('status', 'schedule_name').first()
    if schedule is not None:
        return schedule_is_locked(schedule)

    # Per-finding CAPA
    answer = (
        AuditAnswer.objects
        .select_related('audit__schedule')
        .filter(pk=ref)
        .first()
    )
    if answer is not None:
        return audit_is_locked(answer.audit)

    # Orphaned CAPA – don't block on it, but don't unlock it either.
    return False


# ---------------------------------------------------------------------------
# Server-side guard
# ---------------------------------------------------------------------------

def block_if_locked(request, schedule, redirect_to='five_s:schedule_list',
                    redirect_kwargs=None, verb='This action'):
    """
    Return a redirect response if the schedule is locked, else None.

    Usage in a POST handler::

        blocked = block_if_locked(request, audit.schedule,
                                  redirect_to='five_s:audit_page',
                                  redirect_kwargs={'pk': audit.pk})
        if blocked:
            return blocked

    ``redirect_to`` may be a URL name or a callable name resolved by
    Django's ``redirect()``.  ``redirect_kwargs`` supplies kwargs for a
    named URL.
    """
    if not schedule_is_locked(schedule):
        return None

    state = LOCKED_STATUS_LABEL.get(schedule.status, schedule.status.lower())
    messages.error(
        request,
        f'Schedule "{schedule.schedule_name}" is {state}. '
        f'{verb} is disabled until it is resumed.',
    )

    if redirect_kwargs:
        return redirect(redirect_to, **redirect_kwargs)
    return redirect(redirect_to)


def block_if_action_locked(request, action, redirect_to='five_s:my_actions',
                           redirect_kwargs=None, verb='This action'):
    """Convenience wrapper for CorrectiveAction POST handlers."""
    if action is None:
        return None
    return block_if_locked(
        request,
        action.audit.schedule,
        redirect_to=redirect_to,
        redirect_kwargs=redirect_kwargs,
        verb=verb,
    )


def block_if_capa_locked(request, capa, redirect_to='capa:list',
                         redirect_kwargs=None, verb='This action'):
    """
    Convenience wrapper for CAPA POST handlers in the ``capa`` app.

    Because CAPAs can be schedule-wide (no single audit), we resolve the
    schedule via ``capa_is_locked``.  We can't redirect to a specific
    schedule here without extra lookups, so callers should pass their
    own ``redirect_to``.
    """
    if not capa_is_locked(capa):
        return None

    messages.error(
        request,
        f'The 5S schedule linked to this CAPA is paused or ended. '
        f'{verb} is disabled until it is resumed.',
    )

    if redirect_kwargs:
        return redirect(redirect_to, **redirect_kwargs)
    return redirect(redirect_to)


# ---------------------------------------------------------------------------
# Template-friendly predicates
# ---------------------------------------------------------------------------
# These are exposed via the context processor so templates can call:
#     {% if fn_schedule_locked schedule %} ... {% endif %}
#     {% if fn_audit_locked audit %} ... {% endif %}
#     {% if fn_action_locked action %} ... {% endif %}
#     {% if fn_capa_locked capa %} ... {% endif %}
#
# The functions above already accept None safely, so templates don't need
# to guard against missing objects.

def template_predicates():
    """Return the dict of callables to register as context processors."""
    return {
        'fn_schedule_locked': schedule_is_locked,
        'fn_schedule_paused': schedule_is_paused,
        'fn_audit_locked': audit_is_locked,
        'fn_action_locked': action_is_locked,
        'fn_capa_locked': capa_is_locked,
    }


# ---------------------------------------------------------------------------
# Optional: raise instead of redirect (for services / DRF / tests)
# ---------------------------------------------------------------------------

class ScheduleLockedError(Exception):
    """Raised by ``assert_schedule_unlocked`` when a write is attempted on a locked schedule."""
    def __init__(self, schedule):
        self.schedule = schedule
        state = LOCKED_STATUS_LABEL.get(schedule.status, schedule.status.lower())
        super().__init__(
            f'Schedule "{schedule.schedule_name}" is {state} and cannot be modified.'
        )


def assert_schedule_unlocked(schedule):
    """
    Raise ``ScheduleLockedError`` if the schedule is locked.

    Use inside service-layer functions, Celery tasks, or anywhere a
    redirect response is not appropriate.
    """
    if schedule_is_locked(schedule):
        raise ScheduleLockedError(schedule)