"""
Ergonomics → Benchmarking bridge.

Exposes a single public function, `ergonomics_site_benchmarks()`, which
returns ergonomic KPIs per site (Plant). Intended to be imported by the
EHS-360 Analytics & Benchmarking module.

Metrics returned per site:
    high_risk_tasks     — distinct tasks with at least one HIGH / VERY_HIGH assessment
    average_risk_score  — mean of all scored assessments for that site
    msd_cases           — MSD / discomfort cases linked to assessments in that site
                          plus unlinked MSD cases where the department belongs to
                          the site
    action_closure      — % of corrective actions CLOSED/COMPLETED out of all actions
"""
from django.db.models import Avg, Count, Q

from apps.organizations.models import Plant

from ..models import (
    ErgonomicAssessment,
    ErgonomicCorrectiveAction,
    MSDDiscomfort,
)


def ergonomics_site_benchmarks(plants=None):
    """
    Return a list of dicts, one per site.

    Args:
        plants: optional queryset of Plant. If None, uses all active plants.

    Returns:
        list of {
            "plant_id": int,
            "plant": str,
            "high_risk_tasks": int,
            "average_risk_score": float,
            "msd_cases": int,
            "action_closure": float,   # percentage 0–100
            "total_assessments": int,  # helpful extra
        }
    """
    if plants is None:
        plants = Plant.objects.filter(is_active=True)

    results = []

    for plant in plants:
        assessments = ErgonomicAssessment.objects.filter(plant=plant)

        # ---- High-risk tasks: distinct tasks with HIGH or VERY_HIGH ----
        high_risk_tasks = (
            assessments
            .filter(risk_level__in=["HIGH", "VERY_HIGH"])
            .values("task")
            .distinct()
            .count()
        )

        # ---- Average risk score (numeric) ----
        avg_score = (
            assessments
            .exclude(score__isnull=True)
            .aggregate(avg=Avg("score"))["avg"]
        )
        avg_score = round(float(avg_score), 2) if avg_score is not None else 0.0

       
         # ---- MSD cases ----
        # Only count MSD cases that are linked to an assessment in this
        # plant. Unlinked MSD cases have no reliable plant association in
        # this schema (MSDDiscomfort.department has no direct FK to Plant),
        # so we don't attempt to attribute them here.
        msd_cases = MSDDiscomfort.objects.filter(
            related_assessment__plant=plant
        ).count()

        # ---- Corrective action closure rate ----
        actions = ErgonomicCorrectiveAction.objects.filter(assessment__plant=plant)
        total_actions = actions.count()
        closed_actions = actions.filter(status__in=["COMPLETED", "CLOSED"]).count()
        closure_rate = (
            round(closed_actions / total_actions * 100, 1) if total_actions else 0.0
        )

        results.append({
            "plant_id": plant.pk,
            "plant": plant.name,
            "total_assessments": assessments.count(),
            "high_risk_tasks": high_risk_tasks,
            "average_risk_score": avg_score,
            "msd_cases": msd_cases,
            "action_closure": closure_rate,
        })

    # Sort by risk descending so the worst-performing sites surface first
    results.sort(key=lambda r: (-r["average_risk_score"], -r["high_risk_tasks"]))
    return results