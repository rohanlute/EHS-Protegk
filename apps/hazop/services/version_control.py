
import json
import logging
from decimal import Decimal
from datetime import date, datetime, time
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.hazop.models import (
    HAZOPStudy,
    HAZOPStudyVersion,
    HAZOPNode,
    HAZOPWorksheetEntry,
    HAZOPRiskAssessment,
    HAZOPAction,
)

logger = logging.getLogger(__name__)


# ============================================================
# JSON SAFE VALUE
# ============================================================

def json_safe(value):
    """
    Convert Python and Django values into JSON-compatible values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime, time)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): json_safe(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            json_safe(item)
            for item in value
        ]

    return str(value)


# ============================================================
# SAFE FIELD HELPERS
# ============================================================

def get_value(obj, field, default=None):
    """
    Safely get a model field or property.
    """

    if obj is None:
        return default

    return getattr(obj, field, default)


def related_name(obj):
    """
    Return readable text for a related model object.
    """

    if obj is None:
        return None

    return str(obj)


def get_related_score(obj, score_field):
    """
    Get a score from a related object.

    Supports:
    - Related object containing severity_score/likelihood_score
    - Direct numeric values
    - None
    """

    if obj is None:
        return None

    score = getattr(
        obj,
        score_field,
        None,
    )

    if score is not None:
        return score

    if isinstance(obj, (int, float)):
        return obj

    return None


def get_risk_score(likelihood, severity):
    """
    Calculate risk score safely.
    """

    if likelihood is None or severity is None:
        return None

    try:
        return likelihood * severity
    except (TypeError, ValueError):
        return None


def get_risk_level(score):
    """
    Return risk level name based on configured risk ranges.
    """

    if score is None:
        return None

    try:
        from apps.hazop.models import HAZOPRiskLevel

        risk_level = HAZOPRiskLevel.objects.filter(
            is_active=True,
            minimum_score__lte=score,
            maximum_score__gte=score,
        ).first()

        return risk_level.name if risk_level else None

    except Exception:
        logger.exception(
            "Unable to determine HAZOP risk level for score %s",
            score,
        )
        return None


# ============================================================
# SNAPSHOT RECORD HELPERS
# ============================================================

def add_snapshot_record(
    records,
    record_key,
    record_type,
    data,
):
    """
    Add one record to the snapshot.
    """

    records.append({
        "record_key": str(record_key),
        "record_type": record_type,
        "data": json_safe(data),
    })


# ============================================================
# BUILD STUDY SNAPSHOT
# ============================================================

def build_hazop_snapshot(study):
    """
    Build a snapshot of the current HAZOP study.

    This function does not modify HAZOP records.
    """

    records = []

    # --------------------------------------------------------
    # STUDY
    # --------------------------------------------------------

    add_snapshot_record(
        records,
        "study",
        "Study",
        {
            "study_number": get_value(study, "study_number"),
            "study_title": get_value(study, "study_title"),
            "study_type": related_name(
                get_value(study, "study_type")
            ),
            "methodology": related_name(
                get_value(study, "methodology")
            ),
            "process_type": related_name(
                get_value(study, "process_type")
            ),
            "priority": related_name(
                get_value(study, "priority")
            ),
            "status": related_name(
                get_value(study, "status")
            ),
            "plant": related_name(
                get_value(study, "plant")
            ),
            "zone": related_name(
                get_value(study, "zone")
            ),
            "location": related_name(
                get_value(study, "location")
            ),
            "sub_location": related_name(
                get_value(study, "sub_location")
            ),
            "department": related_name(
                get_value(study, "department")
            ),
            "study_leader": related_name(
                get_value(study, "study_leader")
            ),
            "planned_start_date": get_value(
                study,
                "planned_start_date",
            ),
            "planned_end_date": get_value(
                study,
                "planned_end_date",
            ),
            "actual_start_date": get_value(
                study,
                "actual_start_date",
            ),
            "actual_end_date": get_value(
                study,
                "actual_end_date",
            ),
            "study_scope": get_value(
                study,
                "study_scope",
            ),
            "study_objective": get_value(
                study,
                "study_objective",
            ),
            "reference_documents": get_value(
                study,
                "reference_documents",
            ),
            "remarks": get_value(
                study,
                "remarks",
            ),
            "is_active": get_value(
                study,
                "is_active",
            ),
        },
    )

    # --------------------------------------------------------
    # NODES
    # --------------------------------------------------------

    nodes = (
        HAZOPNode.objects
        .filter(study=study)
        .select_related(
            "node_type",
            "equipment_type",
        )
        .prefetch_related(
            "worksheet_entries",
        )
        .order_by("node_number")
    )

    for node in nodes:

        add_snapshot_record(
            records,
            f"node:{node.pk}",
            "Node",
            {
                "node_number": node.node_number,
                "node_name": node.node_name,
                "node_type": related_name(
                    node.node_type
                ),
                "equipment_type": related_name(
                    node.equipment_type
                ),
                "equipment_tag": node.equipment_tag,
                "description": node.description,
                "design_intent": node.design_intent,
                "operating_conditions": node.operating_conditions,
                "drawing_reference": node.drawing_reference,
                "boundary_description": node.boundary_description,
                "is_active": node.is_active,
            },
        )

        # ----------------------------------------------------
        # WORKSHEET ENTRIES
        # ----------------------------------------------------

        entries = (
            HAZOPWorksheetEntry.objects
            .filter(node=node)
            .select_related(
                "parameter",
                "guide_word",
                "deviation_template",
                "initial_severity",
                "initial_likelihood",
                "residual_severity",
                "residual_likelihood",
            )
            .prefetch_related(
                "causes",
                "consequences",
                "safeguards",
                "recommendations",
                "risk_assessments",
            )
            .order_by("entry_number")
        )

        for entry in entries:

            initial_severity = get_related_score(
                entry.initial_severity,
                "severity_score",
            )

            initial_likelihood = get_related_score(
                entry.initial_likelihood,
                "likelihood_score",
            )

            residual_severity = get_related_score(
                entry.residual_severity,
                "severity_score",
            )

            residual_likelihood = get_related_score(
                entry.residual_likelihood,
                "likelihood_score",
            )

            initial_score = get_risk_score(
                initial_likelihood,
                initial_severity,
            )

            residual_score = get_risk_score(
                residual_likelihood,
                residual_severity,
            )

            add_snapshot_record(
                records,
                f"entry:{entry.pk}",
                "Worksheet Entry",
                {
                    "node_number": node.node_number,
                    "entry_number": entry.entry_number,
                    "parameter": related_name(
                        entry.parameter
                    ),
                    "guide_word": related_name(
                        entry.guide_word
                    ),
                    "deviation_template": related_name(
                        entry.deviation_template
                    ),
                    "deviation_description": (
                        entry.deviation_description
                    ),
                    "possible_causes": entry.possible_causes,
                    "operating_condition": (
                        entry.operating_condition
                    ),
                    "initial_severity": initial_severity,
                    "initial_likelihood": initial_likelihood,
                    "initial_risk_score": initial_score,
                    "initial_risk_level": get_risk_level(
                        initial_score
                    ),
                    "residual_severity": residual_severity,
                    "residual_likelihood": residual_likelihood,
                    "residual_risk_score": residual_score,
                    "residual_risk_level": get_risk_level(
                        residual_score
                    ),
                    "remarks": entry.remarks,
                    "is_active": entry.is_active,
                },
            )

            # ------------------------------------------------
            # CAUSES
            # ------------------------------------------------

            for cause in entry.causes.all():

                add_snapshot_record(
                    records,
                    f"cause:{cause.pk}",
                    "Cause",
                    {
                        "node_number": node.node_number,
                        "entry_number": entry.entry_number,
                        "category": related_name(
                            cause.category
                        ),
                        "cause_description": (
                            cause.cause_description
                        ),
                        "is_active": cause.is_active,
                    },
                )

            # ------------------------------------------------
            # CONSEQUENCES
            # ------------------------------------------------

            for consequence in entry.consequences.all():

                add_snapshot_record(
                    records,
                    f"consequence:{consequence.pk}",
                    "Consequence",
                    {
                        "node_number": node.node_number,
                        "entry_number": entry.entry_number,
                        "category": related_name(
                            consequence.category
                        ),
                        "consequence_description": (
                            consequence.consequence_description
                        ),
                        "is_active": consequence.is_active,
                    },
                )

            # ------------------------------------------------
            # SAFEGUARDS
            # ------------------------------------------------

            for safeguard in entry.safeguards.all():

                add_snapshot_record(
                    records,
                    f"safeguard:{safeguard.pk}",
                    "Safeguard",
                    {
                        "node_number": node.node_number,
                        "entry_number": entry.entry_number,
                        "category": related_name(
                            safeguard.category
                        ),
                        "safeguard_description": (
                            safeguard.safeguard_description
                        ),
                        "is_active": safeguard.is_active,
                    },
                )

            # ------------------------------------------------
            # RISK ASSESSMENTS
            # ------------------------------------------------

            assessments = (
                HAZOPRiskAssessment.objects
                .filter(worksheet_entry=entry)
                .select_related(
                    "matrix",
                    "assessor",
                    "reviewer",
                    "approver",
                    "action_responsible",
                )
            )

            for assessment in assessments:

                add_snapshot_record(
                    records,
                    f"risk:{assessment.pk}",
                    "Risk Assessment",
                    {
                        "node_number": node.node_number,
                        "entry_number": entry.entry_number,
                        "assessment_number": (
                            assessment.assessment_number
                        ),
                        "matrix": related_name(
                            assessment.matrix
                        ),
                        "hazard_title": assessment.hazard_title,
                        "hazard_description": (
                            assessment.hazard_description
                        ),
                        "potential_consequence": (
                            assessment.potential_consequence
                        ),
                        "persons_exposed": (
                            assessment.persons_exposed
                        ),
                        "existing_controls": (
                            assessment.existing_controls
                        ),
                        "initial_likelihood": (
                            assessment.initial_likelihood
                        ),
                        "initial_severity": (
                            assessment.initial_severity
                        ),
                        "initial_risk_score": (
                            assessment.initial_risk_score
                        ),
                        "initial_risk_level": get_risk_level(
                            assessment.initial_risk_score
                        ),
                        "additional_controls": (
                            assessment.additional_controls
                        ),
                        "control_hierarchy": (
                            assessment.control_hierarchy
                        ),
                        "action_required": (
                            assessment.action_required
                        ),
                        "action_responsible": related_name(
                            assessment.action_responsible
                        ),
                        "action_due_date": (
                            assessment.action_due_date
                        ),
                        "residual_likelihood": (
                            assessment.residual_likelihood
                        ),
                        "residual_severity": (
                            assessment.residual_severity
                        ),
                        "residual_risk_score": (
                            assessment.residual_risk_score
                        ),
                        "residual_risk_level": get_risk_level(
                            assessment.residual_risk_score
                        ),
                        "status": assessment.status,
                        "review_comments": (
                            assessment.review_comments
                        ),
                        "assessor": related_name(
                            assessment.assessor
                        ),
                        "reviewer": related_name(
                            assessment.reviewer
                        ),
                        "approver": related_name(
                            assessment.approver
                        ),
                    },
                )

            # ------------------------------------------------
            # RECOMMENDATIONS
            # ------------------------------------------------

            for recommendation in entry.recommendations.all():

                add_snapshot_record(
                    records,
                    f"recommendation:{recommendation.pk}",
                    "Recommendation",
                    {
                        "node_number": node.node_number,
                        "entry_number": entry.entry_number,
                        "category": related_name(
                            recommendation.category
                        ),
                        "recommendation_description": (
                            recommendation.recommendation_description
                        ),
                        "assigned_to": related_name(
                            recommendation.assigned_to
                        ),
                        "target_date": recommendation.target_date,
                        "status": recommendation.status,
                        "completion_remarks": (
                            recommendation.completion_remarks
                        ),
                        "is_active": recommendation.is_active,
                    },
                )

                # --------------------------------------------
                # ACTIONS
                # --------------------------------------------

                for action in recommendation.actions.all():

                    add_snapshot_record(
                        records,
                        f"action:{action.pk}",
                        "Action",
                        {
                            "node_number": node.node_number,
                            "entry_number": entry.entry_number,
                            "recommendation_id": (
                                recommendation.pk
                            ),
                            "action_number": (
                                action.action_number
                            ),
                            "action_description": (
                                action.action_description
                            ),
                            "department": related_name(
                                action.department
                            ),
                            "assigned_to": related_name(
                                action.assigned_to
                            ),
                            "priority": action.priority,
                            "due_date": action.due_date,
                            "status": action.status,
                            "completion_remarks": (
                                action.completion_remarks
                            ),
                            "completed_at": action.completed_at,
                            "verified_at": action.verified_at,
                            "verification_remarks": (
                                action.verification_remarks
                            ),
                            "completed_by": related_name(
                                get_value(action, "completed_by")
                            ),
                            "verified_by": related_name(
                                get_value(action, "verified_by")
                            ),
                            "evidence": get_value(
                                action,
                                "evidence",
                            ),
                        },
                    )

    return {
        "study_id": study.pk,
        "study_number": study.study_number,
        "study_title": study.study_title,
        "captured_at": timezone.now().isoformat(),
        "records": records,
    }


# ============================================================
# SNAPSHOT RECORD LOOKUP
# ============================================================

def snapshot_record_map(snapshot):
    """
    Convert snapshot records into a dictionary keyed by record_key.
    """

    if not isinstance(snapshot, dict):
        return {}

    records = snapshot.get("records", [])

    if not isinstance(records, list):
        return {}

    return {
        record["record_key"]: record
        for record in records
        if isinstance(record, dict)
        and record.get("record_key") is not None
    }


# ============================================================
# COMPARE TWO SNAPSHOTS
# ============================================================

def compare_snapshots(old_snapshot, new_snapshot):
    """
    Return added, removed and modified records.
    """

    old_records = snapshot_record_map(old_snapshot)
    new_records = snapshot_record_map(new_snapshot)

    changes = []

    old_keys = set(old_records.keys())
    new_keys = set(new_records.keys())

    # --------------------------------------------------------
    # ADDED RECORDS
    # --------------------------------------------------------

    for record_key in sorted(new_keys - old_keys):

        record = new_records[record_key]

        changes.append({
            "change_type": "ADDED",
            "record_key": record_key,
            "record_type": record.get("record_type"),
            "field_name": "",
            "old_value": None,
            "new_value": record.get("data"),
        })

    # --------------------------------------------------------
    # REMOVED RECORDS
    # --------------------------------------------------------

    for record_key in sorted(old_keys - new_keys):

        record = old_records[record_key]

        changes.append({
            "change_type": "REMOVED",
            "record_key": record_key,
            "record_type": record.get("record_type"),
            "field_name": "",
            "old_value": record.get("data"),
            "new_value": None,
        })

    # --------------------------------------------------------
    # MODIFIED RECORDS
    # --------------------------------------------------------

    for record_key in sorted(old_keys & new_keys):

        old_record = old_records[record_key]
        new_record = new_records[record_key]

        old_data = old_record.get("data", {})
        new_data = new_record.get("data", {})

        if not isinstance(old_data, dict):
            old_data = {}

        if not isinstance(new_data, dict):
            new_data = {}

        all_fields = (
            set(old_data.keys())
            | set(new_data.keys())
        )

        for field_name in sorted(all_fields):

            old_value = old_data.get(field_name)
            new_value = new_data.get(field_name)

            if old_value != new_value:

                changes.append({
                    "change_type": "MODIFIED",
                    "record_key": record_key,
                    "record_type": (
                        new_record.get("record_type")
                    ),
                    "field_name": field_name,
                    "old_value": old_value,
                    "new_value": new_value,
                })

    return changes


# ============================================================
# CREATE NEW STUDY VERSION
# ============================================================

@transaction.atomic
def create_study_version(
    study_id,
    user,
    revision_reason="",
    version_title="",
):
    """
    Save a new snapshot of the current HAZOP study.

    Version 1 is the first snapshot.
    Each following version compares against the previous version.
    """

    study = (
        HAZOPStudy.objects
        .select_for_update()
        .get(pk=study_id)
    )

    previous_version = (
        HAZOPStudyVersion.objects
        .filter(study=study)
        .order_by("-version_number")
        .first()
    )

    next_version_number = (
        previous_version.version_number + 1
        if previous_version
        else 1
    )

    current_snapshot = build_hazop_snapshot(study)

    if previous_version:
        changes = compare_snapshots(
            previous_version.snapshot_data,
            current_snapshot,
        )
    else:
        changes = []

    version = HAZOPStudyVersion.objects.create(
        study=study,
        version_number=next_version_number,
        version_title=version_title,
        revision_reason=revision_reason,
        snapshot_data=current_snapshot,
        change_summary=changes,
        parent_version=previous_version,
        created_by=user,
    )

    return version


# ============================================================
# COMPARE SAVED VERSIONS
# ============================================================

def compare_study_versions(version_from, version_to):
    """
    Compare two saved versions of the same HAZOP study.

    Returns:
    {
        "version_from": version_from,
        "version_to": version_to,
        "changes": [...],
        "summary": {
            "added": 0,
            "removed": 0,
            "modified": 0,
            "total": 0
        }
    }
    """

    if version_from.study_id != version_to.study_id:
        raise ValueError(
            "Versions must belong to the same HAZOP study."
        )

    changes = compare_snapshots(
        version_from.snapshot_data,
        version_to.snapshot_data,
    )

    summary = {
        "added": sum(
            1 for item in changes
            if item["change_type"] == "ADDED"
        ),
        "removed": sum(
            1 for item in changes
            if item["change_type"] == "REMOVED"
        ),
        "modified": sum(
            1 for item in changes
            if item["change_type"] == "MODIFIED"
        ),
        "total": len(changes),
    }

    return {
        "version_from": version_from,
        "version_to": version_to,
        "changes": changes,
        "summary": summary,
    }
