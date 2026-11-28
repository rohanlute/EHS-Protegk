
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.hazop.models import (
    HAZOPStudy,
    HAZOPStudyVersion,
)

from apps.hazop.services.version_control import (
    create_study_version,
    compare_study_versions,
)


logger = logging.getLogger(__name__)


# ============================================================
# HELPER: STUDY ACCESS
# ============================================================

def get_accessible_study(study_id, user):
    """
    Return the study if the user has permission to access it.

    Access is allowed for:
    - Superuser
    - Study leader
    - Study team member
    - Study creator, if created_by exists
    """

    study = get_object_or_404(
        HAZOPStudy,
        pk=study_id,
    )

    if user.is_superuser:
        return study

    # Study leader
    if getattr(study, "study_leader_id", None) == user.pk:
        return study

    # Study team members
    try:
        HAZOPStudy._meta.get_field("team_members")

        team_members = getattr(
            study,
            "team_members",
            None,
        )

        if team_members is not None:
            if team_members.filter(pk=user.pk).exists():
                return study

    except Exception:
        logger.debug(
            "HAZOPStudy team_members field is unavailable.",
            exc_info=True,
        )

    # Study creator
    try:
        HAZOPStudy._meta.get_field("created_by")

        if getattr(study, "created_by_id", None) == user.pk:
            return study

    except Exception:
        logger.debug(
            "HAZOPStudy created_by field is unavailable.",
            exc_info=True,
        )

    raise PermissionDenied(
        "You do not have permission to access this HAZOP study."
    )


# ============================================================
# HELPER: FORMAT COMPARISON VALUES
# ============================================================

def format_comparison_value(value):
    """
    Convert values into readable strings for the template.
    """

    if value is None:
        return "-"

    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return str(value)


# ============================================================
# HELPER: PREPARE COMPARISON DATA
# ============================================================

def prepare_comparison_data(comparison):
    """
    Prepare comparison data for the comparison template.

    Expected structure:
    {
        "summary": {
            "added": 0,
            "modified": 0,
            "removed": 0
        },
        "changes": [
            {
                "change_type": "...",
                "record_type": "...",
                "record_key": "...",
                "field_name": "...",
                "old_value": "...",
                "new_value": "..."
            }
        ]
    }
    """

    if not isinstance(comparison, dict):
        return None

    changes = comparison.get("changes", [])

    if not isinstance(changes, list):
        changes = []

    prepared_changes = []

    for change in changes:

        if not isinstance(change, dict):
            continue

        change = change.copy()

        old_value = change.get(
            "old_value",
            change.get("old", change.get("old_display")),
        )

        new_value = change.get(
            "new_value",
            change.get("new", change.get("new_display")),
        )

        change["old_display"] = format_comparison_value(
            old_value
        )

        change["new_display"] = format_comparison_value(
            new_value
        )

        prepared_changes.append(change)

    summary = comparison.get("summary", {})

    if not isinstance(summary, dict):
        summary = {}

    summary = summary.copy()

    added = summary.get("added", 0) or 0
    modified = summary.get("modified", 0) or 0
    removed = summary.get("removed", 0) or 0

    summary["added"] = added
    summary["modified"] = modified
    summary["removed"] = removed

    summary["total"] = summary.get(
        "total",
        added + modified + removed,
    )

    comparison = comparison.copy()

    comparison["changes"] = prepared_changes
    comparison["summary"] = summary

    return comparison


# ============================================================
# VERSION HISTORY
# ============================================================

@login_required
def hazop_version_history(request, study_id):

    study = get_accessible_study(
        study_id,
        request.user,
    )

    versions = (
        HAZOPStudyVersion.objects
        .filter(study=study)
        .select_related(
            "created_by",
            "approved_by",
            "parent_version",
        )
        .order_by("-version_number")
    )

    return render(
        request,
        "hazop/version_control/version_history.html",
        {
            "study": study,
            "versions": versions,
        },
    )


# ============================================================
# CREATE NEW VERSION
# ============================================================

@login_required
@require_POST
def hazop_create_version(request, study_id):

    study = get_accessible_study(
        study_id,
        request.user,
    )

    revision_reason = request.POST.get(
        "revision_reason",
        "",
    ).strip()

    version_title = request.POST.get(
        "version_title",
        "",
    ).strip()

    if not revision_reason:
        messages.error(
            request,
            "Please enter the reason for this revision.",
        )

        return redirect(
            "hazop:version_history",
            study_id=study.pk,
        )

    try:
        version = create_study_version(
            study_id=study.pk,
            user=request.user,
            revision_reason=revision_reason,
            version_title=version_title,
        )

        messages.success(
            request,
            f"Version V{version.version_number} created successfully.",
        )

    except Exception:
        logger.exception(
            "Failed to create HAZOP version for study %s",
            study.pk,
        )

        messages.error(
            request,
            "Unable to create the version. Please check the server log.",
        )

    return redirect(
        "hazop:version_history",
        study_id=study.pk,
    )


# ============================================================
# COMPARE VERSIONS
# ============================================================

@login_required
def hazop_compare_versions(request, study_id):

    study = get_accessible_study(
        study_id,
        request.user,
    )

    versions = (
        HAZOPStudyVersion.objects
        .filter(study=study)
        .select_related(
            "created_by",
            "parent_version",
        )
        .order_by("-version_number")
    )

    selected_from = request.GET.get(
        "from",
        "",
    ).strip()

    selected_to = request.GET.get(
        "to",
        "",
    ).strip()

    comparison = None
    error_message = ""

    # --------------------------------------------------------
    # Validate selection
    # --------------------------------------------------------

    if selected_from and selected_to:

        if selected_from == selected_to:

            error_message = (
                "Please select two different versions to compare."
            )

        else:

            version_from = get_object_or_404(
                HAZOPStudyVersion,
                pk=selected_from,
                study=study,
            )

            version_to = get_object_or_404(
                HAZOPStudyVersion,
                pk=selected_to,
                study=study,
            )

            # ------------------------------------------------
            # Run comparison service
            # ------------------------------------------------

            try:

                comparison_result = compare_study_versions(
                    version_from,
                    version_to,
                )

                if comparison_result is None:

                    error_message = (
                        "No comparison data was returned. "
                        "Please check the version comparison service."
                    )

                else:

                    comparison = prepare_comparison_data(
                        comparison_result
                    )

                    if comparison is None:

                        error_message = (
                            "The comparison service returned invalid data."
                        )

            except Exception:

                logger.exception(
                    "Failed to compare HAZOP versions %s and %s "
                    "for study %s",
                    version_from.pk,
                    version_to.pk,
                    study.pk,
                )

                comparison = None

                error_message = (
                    "Unable to compare these versions. "
                    "Please check the server log."
                )

    elif selected_from or selected_to:

        error_message = (
            "Please select both versions before comparing."
        )

    # --------------------------------------------------------
    # Render comparison page
    # --------------------------------------------------------

    return render(
        request,
        "hazop/version_control/version_compare.html",
        {
            "study": study,
            "versions": versions,
            "comparison": comparison,
            "selected_from": selected_from,
            "selected_to": selected_to,
            "error_message": error_message,
        },
    )
