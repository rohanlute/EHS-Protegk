from datetime import datetime
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from apps.organizations.models import Department, Plant
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .models import ErgonomicAssessment, ErgonomicCorrectiveAction, MSDDiscomfort
from django.db.models import Avg, Count, Max, Min, Q
from django.db.models.functions import TruncMonth
from .models import (
    ErgonomicAssessment,
    ErgonomicCorrectiveAction,
    ErgonomicReassessment,
    MSDDiscomfort,
)

def _style(ws):
    thin = Side(style="thin", color="D9E2EC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="0F766E")
        cell.font = Font(color="FFFFFF", bold=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _autosize(ws):
    for column in ws.columns:
        letter = get_column_letter(column[0].column)
        longest = max((len(str(cell.value)) for cell in column if cell.value is not None), default=10)
        ws.column_dimensions[letter].width = min(max(longest + 2, 12), 45)


def build_ergonomics_workbook(assessments):
    assessments = list(assessments)
    actions = ErgonomicCorrectiveAction.objects.select_related("assessment", "responsible_person", "department").filter(assessment__in=assessments)
    msd_cases = MSDDiscomfort.objects.select_related("worker", "department", "related_assessment").filter(related_assessment__in=assessments)

    wb = Workbook()
    summary = wb.active
    summary.title = "Ergonomics Summary"
    summary.append(["Metric", "Value"])
    summary.append(["Total Assessments", len(assessments)])
    summary.append(["High Risk Assessments", len([a for a in assessments if a.risk_level == "HIGH"])])
    summary.append(["Very High Risk Assessments", len([a for a in assessments if a.risk_level == "VERY_HIGH"])])
    summary.append(["Open Corrective Actions", actions.exclude(status__in=["COMPLETED", "CLOSED"]).count()])
    summary.append(["Overdue Actions", actions.filter(status="OVERDUE").count()])
    summary.append(["Completed Actions", actions.filter(status__in=["COMPLETED", "CLOSED"]).count()])
    summary.append(["MSD / Discomfort Cases", msd_cases.count()])
    scores = [float(a.score) for a in assessments if a.score is not None]
    summary.append(["Average Risk Score", round(sum(scores) / len(scores), 2) if scores else 0])
    _style(summary)
    _autosize(summary)

    register = wb.create_sheet("Assessment Register")
    register.append(["Assessment ID", "Site", "Department", "Area", "Job", "Task", "Worker", "Method", "Score", "Risk Level", "Status", "Assessment Date", "Assessor", "Next Assessment"])
    for item in assessments:
        register.append([
            item.assessment_id,
            item.plant.name,
            item.department.name,
            item.area,
            item.job_role,
            item.task,
            item.worker.get_full_name() if item.worker else "",
            item.assessment_method.name,
            item.score,
            item.get_risk_level_display() if item.risk_level else "",
            item.get_status_display(),
            item.assessment_date,
            item.assessor.get_full_name() if item.assessor else "",
            item.next_assessment_date,
        ])
    _style(register)
    _autosize(register)

    action_ws = wb.create_sheet("Corrective Actions")
    action_ws.append(["Action ID", "Assessment", "Risk", "Action", "Responsible", "Department", "Priority", "Target Date", "Status", "Verification"])
    for action in actions:
        action_ws.append([
            action.action_id,
            action.assessment.assessment_id,
            action.assessment.risk_level,
            action.action_description,
            action.responsible_person.get_full_name(),
            action.department.name if action.department else "",
            action.priority,
            action.target_date,
            action.get_status_display(),
            action.verification,
        ])
    _style(action_ws)
    _autosize(action_ws)

    msd_ws = wb.create_sheet("MSD Discomfort")
    msd_ws.append(["Worker", "Employee ID", "Department", "Job", "Task", "Date", "Body Part", "Severity", "Medical Referral", "Work Restriction"])
    for case in msd_cases:
        msd_ws.append([
            case.worker.get_full_name() if case.worker else "",
            case.worker.employee_id if case.worker else "",
            case.department.name if case.department else "",
            case.job,
            case.task,
            case.date_reported,
            case.get_body_part_display(),
            case.get_severity_display(),
            "Yes" if case.medical_referral else "No",
            "Yes" if case.work_restriction else "No",
        ])
    _style(msd_ws)
    _autosize(msd_ws)

    return wb


def workbook_response(assessments):
    buffer = BytesIO()
    build_ergonomics_workbook(assessments).save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="Ergonomics_Report_{datetime.now():%Y%m%d_%H%M}.xlsx"'
    return response


def filter_assessments(request):
    qs = ErgonomicAssessment.objects.select_related(
        "plant", "department", "assessment_method", "worker", "assessor"
    )
    user = request.user
    if not user.is_superuser and hasattr(user, "get_all_plants"):
        plants = user.get_all_plants()
        qs = qs.filter(plant__in=plants) if plants else qs.none()
    if request.GET.get("plant"):
        qs = qs.filter(plant_id=request.GET["plant"])
    if request.GET.get("department"):
        qs = qs.filter(department_id=request.GET["department"])
    if request.GET.get("area"):
        qs = qs.filter(area=request.GET["area"])
    if request.GET.get("method"):
        qs = qs.filter(assessment_method_id=request.GET["method"])
    if request.GET.get("risk_level"):
        qs = qs.filter(risk_level=request.GET["risk_level"])
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("assessor"):
        qs = qs.filter(assessor_id=request.GET["assessor"])
    if request.GET.get("from_date"):
        qs = qs.filter(assessment_date__gte=request.GET["from_date"])
    if request.GET.get("to_date"):
        qs = qs.filter(assessment_date__lte=request.GET["to_date"])
    return qs
def build_department_report(department, assessments):
    """
    Build a single-sheet Excel report for one department.

    `assessments` is a queryset already filtered by the requesting user's
    accessible plants. We further narrow it to this department.
    """
    from django.db.models import Avg, Count

    dept_assessments = assessments.filter(department=department)
    total = dept_assessments.count()

    wb = Workbook()

    # -----------------------------------------------------------------
    # Sheet 1 — Summary
    # -----------------------------------------------------------------
    summary = wb.active
    summary.title = "Summary"
    summary.append(["Department Report"])
    summary.append([department.name])
    summary.append([])
    summary.append(["Metric", "Value"])

    summary.append(["Total Assessments", total])
    summary.append(["High Risk", dept_assessments.filter(risk_level="HIGH").count()])
    summary.append(["Very High Risk", dept_assessments.filter(risk_level="VERY_HIGH").count()])
    summary.append(["Medium Risk", dept_assessments.filter(risk_level="MEDIUM").count()])
    summary.append(["Low Risk", dept_assessments.filter(risk_level="LOW").count()])
    summary.append(["Unscored", dept_assessments.filter(risk_level="").count()])

    # Average score
    avg_score = dept_assessments.exclude(score__isnull=True).aggregate(avg=Avg("score"))["avg"]
    summary.append(["Average Risk Score", round(avg_score, 2) if avg_score else 0])

    # Actions
    actions = ErgonomicCorrectiveAction.objects.filter(assessment__in=dept_assessments)
    summary.append(["Open Actions", actions.exclude(status__in=["COMPLETED", "CLOSED", "REJECTED"]).count()])
    summary.append(["Overdue Actions", actions.filter(status="OVERDUE").count()])
    summary.append(["Completed Actions", actions.filter(status__in=["COMPLETED", "CLOSED"]).count()])

    # MSD cases
    msd_cases = MSDDiscomfort.objects.filter(department=department)
    summary.append(["MSD / Discomfort Cases", msd_cases.count()])

    _style(summary)
    _autosize(summary)

    # -----------------------------------------------------------------
    # Sheet 2 — Assessment Register (this department)
    # -----------------------------------------------------------------
    register = wb.create_sheet("Assessment Register")
    register.append([
        "Assessment ID", "Site", "Area", "Job", "Task", "Worker",
        "Method", "Score", "Risk Level", "Status", "Date", "Assessor",
    ])
    for a in dept_assessments.select_related("plant", "assessment_method", "worker", "assessor"):
        register.append([
            a.assessment_id,
            a.plant.name if a.plant else "",
            a.area,
            a.job_role,
            a.task,
            a.worker.get_full_name() if a.worker else "",
            a.assessment_method.name if a.assessment_method else "",
            float(a.score) if a.score is not None else "",
            a.get_risk_level_display() if a.risk_level else "",
            a.get_status_display(),
            a.assessment_date,
            a.assessor.get_full_name() if a.assessor else "",
        ])
    _style(register)
    _autosize(register)

    # -----------------------------------------------------------------
    # Sheet 3 — High-Risk Tasks
    # -----------------------------------------------------------------
    high_risk = dept_assessments.filter(risk_level__in=["HIGH", "VERY_HIGH"]).order_by("-assessment_date")
    hr_ws = wb.create_sheet("High Risk Tasks")
    hr_ws.append([
        "Assessment ID", "Task", "Job", "Score", "Risk Level", "Date",
    ])
    for a in high_risk:
        hr_ws.append([
            a.assessment_id,
            a.task,
            a.job_role,
            float(a.score) if a.score is not None else "",
            a.get_risk_level_display(),
            a.assessment_date,
        ])
    _style(hr_ws)
    _autosize(hr_ws)

    # -----------------------------------------------------------------
    # Sheet 4 — Open / Overdue Actions
    # -----------------------------------------------------------------
    open_actions = actions.exclude(status__in=["COMPLETED", "CLOSED", "REJECTED"])
    act_ws = wb.create_sheet("Corrective Actions")
    act_ws.append([
        "Action ID", "Assessment", "Description", "Responsible",
        "Priority", "Target Date", "Status",
    ])
    for a in open_actions.select_related("assessment", "responsible_person"):
        act_ws.append([
            a.action_id,
            a.assessment.assessment_id if a.assessment else "",
            a.action_description,
            a.responsible_person.get_full_name() if a.responsible_person else "",
            a.get_priority_display(),
            a.target_date,
            a.get_status_display(),
        ])
    _style(act_ws)
    _autosize(act_ws)

    # -----------------------------------------------------------------
    # Sheet 5 — MSD Cases
    # -----------------------------------------------------------------
    msd_ws = wb.create_sheet("MSD Cases")
    msd_ws.append([
        "Worker", "Employee ID", "Job", "Task", "Date Reported",
        "Body Part", "Severity", "Medical Referral", "Work Restriction",
    ])
    for case in msd_cases.select_related("worker"):
        msd_ws.append([
            case.worker.get_full_name() if case.worker else "",
            case.worker.employee_id if case.worker and hasattr(case.worker, "employee_id") else "",
            case.job,
            case.task,
            case.date_reported,
            case.get_body_part_display(),
            case.get_severity_display(),
            "Yes" if case.medical_referral else "No",
            "Yes" if case.work_restriction else "No",
        ])
    _style(msd_ws)
    _autosize(msd_ws)

    return wb


def department_report_response(assessments, departments):
    """
    Return an HttpResponse with an Excel workbook.
    If `departments` is a single object → one sheet per department (still
    wrapped in a workbook). If multiple departments → one workbook with
    a sheet per department name.
    """
    from datetime import datetime
    from io import BytesIO
    from django.http import HttpResponse

    if not isinstance(departments, (list, tuple)):
        departments = [departments]

    # If only one department, just build its report and return
    if len(departments) == 1:
        wb = build_department_report(departments[0], assessments)
    else:
        # Multiple: build a workbook with a Summary + one sheet per dept
        wb = Workbook()
        summary = wb.active
        summary.title = "Overall Summary"
        summary.append(["Metric", "Value"])
        total = assessments.count()
        summary.append(["Total Departments", len(departments)])
        summary.append(["Total Assessments", total])
        summary.append(["High Risk", assessments.filter(risk_level="HIGH").count()])
        summary.append(["Very High Risk", assessments.filter(risk_level="VERY_HIGH").count()])
        summary.append(["MSD Cases", MSDDiscomfort.objects.count()])
        _style(summary)
        _autosize(summary)

        for dept in departments:
            dept_wb = build_department_report(dept, assessments)
            dept_ws = dept_wb.active
            new_ws = wb.create_sheet(f"Dept-{dept.name[:25]}")
            for row in dept_ws.iter_rows(values_only=True):
                new_ws.append(list(row))
            _style(new_ws)
            _autosize(new_ws)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="Department_Ergonomic_Report_{datetime.now():%Y%m%d_%H%M}.xlsx"'
    )
    return response
def build_management_report(assessments):
    """
    Executive-level ergonomic report.

    Sheets:
        1. Executive Summary        — KPIs & top-line metrics
        2. High-Risk Areas          — grouped by Site + Department
        3. Top Risky Tasks          — top 20 tasks by avg score
        4. Corrective Action Perf.  — status counts, closure rate, avg days to close
        5. Risk Reduction           — before/after from reassessments
        6. MSD Trends               — monthly MSD volume and body-part breakdown
        7. Method Usage             — which scoring methods are used where
    """
    from datetime import date
    from django.db.models import Avg, Count, Min, Max

    wb = Workbook()
    total = assessments.count()

    # =================================================================
    # 1. Executive Summary
    # =================================================================
    ws = wb.active
    ws.title = "Executive Summary"
    ws.append(["Ergonomic Management Report"])
    ws.append([f"Generated: {date.today()}"])
    ws.append([])
    ws.append(["Metric", "Value"])

    total_assessments = total
    high = assessments.filter(risk_level="HIGH").count()
    vhigh = assessments.filter(risk_level="VERY_HIGH").count()
    medium = assessments.filter(risk_level="MEDIUM").count()
    low = assessments.filter(risk_level="LOW").count()
    unscored = assessments.filter(risk_level="").count()

    avg_score = assessments.exclude(score__isnull=True).aggregate(avg=Avg("score"))["avg"]

    ws.append(["Total Assessments", total_assessments])
    ws.append(["High Risk", high])
    ws.append(["Very High Risk", vhigh])
    ws.append(["Medium Risk", medium])
    ws.append(["Low Risk", low])
    ws.append(["Unscored", unscored])
    ws.append(["Average Risk Score", round(avg_score, 2) if avg_score else 0])
    ws.append(["High/Very High %", (
        round((high + vhigh) / total_assessments * 100, 1) if total_assessments else 0
    )])

    # Actions
    actions = ErgonomicCorrectiveAction.objects.filter(assessment__in=assessments)
    total_actions = actions.count()
    open_actions = actions.exclude(status__in=["COMPLETED", "CLOSED", "REJECTED"]).count()
    closed_actions = actions.filter(status__in=["COMPLETED", "CLOSED"]).count()
    overdue_actions = actions.filter(status="OVERDUE").count()

    ws.append([])
    ws.append(["Total Corrective Actions", total_actions])
    ws.append(["Open Actions", open_actions])
    ws.append(["Closed Actions", closed_actions])
    ws.append(["Overdue Actions", overdue_actions])
    ws.append(["Action Closure Rate %", (
        round(closed_actions / total_actions * 100, 1) if total_actions else 0
    )])

    # Reassessment
    reassessments = ErgonomicReassessment.objects.filter(assessment__in=assessments)
    avg_reduction = reassessments.aggregate(avg=Avg("risk_reduction_percent"))["avg"]
    ws.append([])
    ws.append(["Total Reassessments", reassessments.count()])
    ws.append(["Average Risk Reduction %", round(avg_reduction, 2) if avg_reduction else 0])

    # MSD
    msd_all = MSDDiscomfort.objects.filter(related_assessment__in=assessments)
    msd_unlinked = MSDDiscomfort.objects.filter(related_assessment__isnull=True)
    ws.append([])
    ws.append(["MSD / Discomfort Cases (linked)", msd_all.count()])
    ws.append(["MSD Cases (unlinked)", msd_unlinked.count()])
    ws.append(["MSD Cases (total)", msd_all.count() + msd_unlinked.count()])

    _style(ws)
    _autosize(ws)

    # =================================================================
    # 2. High-Risk Areas (Site + Department)
    # =================================================================
    ws2 = wb.create_sheet("High-Risk Areas")
    ws2.append([
        "Site", "Department", "Total Assessments",
        "High", "Very High", "High+Very High %",
    ])

    groups = (
        assessments
        .values("plant__name", "department__name")
        .annotate(
            total=Count("id"),
            high=Count("id", filter=Q(risk_level="HIGH")),
            vhigh=Count("id", filter=Q(risk_level="VERY_HIGH")),
        )
        .order_by("-vhigh", "-high", "-total")
    )
    for g in groups:
        tot = g["total"] or 1
        pct = round(((g["high"] + g["vhigh"]) / tot) * 100, 1)
        ws2.append([
            g["plant__name"] or "—",
            g["department__name"] or "—",
            g["total"],
            g["high"],
            g["vhigh"],
            pct,
        ])
    _style(ws2)
    _autosize(ws2)

    # =================================================================
    # 3. Top Risky Tasks (top 20 by avg score)
    # =================================================================
    ws3 = wb.create_sheet("Top Risky Tasks")
    ws3.append([
        "Task", "Job Role", "Assessments", "Avg Score", "Max Score",
        "High", "Very High", "Max Risk Level",
    ])

    top_tasks = (
        assessments
        .exclude(score__isnull=True)
        .values("task", "job_role")
        .annotate(
            count=Count("id"),
            avg_score=Avg("score"),
            max_score=Max("score"),
            high=Count("id", filter=Q(risk_level="HIGH")),
            vhigh=Count("id", filter=Q(risk_level="VERY_HIGH")),
        )
        .order_by("-avg_score")[:20]
    )
    for t in top_tasks:
        max_score = float(t["max_score"] or 0)
        if max_score > 10:
            max_level = "VERY_HIGH"
        elif max_score > 7:
            max_level = "HIGH"
        elif max_score > 3:
            max_level = "MEDIUM"
        else:
            max_level = "LOW"
        ws3.append([
            t["task"],
            t["job_role"],
            t["count"],
            round(float(t["avg_score"]), 2),
            max_score,
            t["high"],
            t["vhigh"],
            max_level,
        ])
    _style(ws3)
    _autosize(ws3)

    # =================================================================
    # 4. Corrective Action Performance
    # =================================================================
    ws4 = wb.create_sheet("Corrective Actions")
    ws4.append(["Status", "Count", "% of Total"])

    status_counts = actions.values("status").annotate(total=Count("id")).order_by("-total")
    for row in status_counts:
        pct = round(row["total"] / total_actions * 100, 1) if total_actions else 0
        ws4.append([row["status"], row["total"], pct])

    # Avg days to close
    closed = actions.filter(
        status__in=["COMPLETED", "CLOSED"], completion_date__isnull=False
    ).exclude(target_date__isnull=True)

    if closed.exists():
        deltas = []
        for a in closed:
            if a.completion_date and a.target_date:
                deltas.append((a.completion_date - a.target_date).days)
        if deltas:
            avg_days = round(sum(deltas) / len(deltas), 1)
            ws4.append([])
            ws4.append(["Avg days (completion vs target)", avg_days])
            ws4.append(["Min days", min(deltas)])
            ws4.append(["Max days", max(deltas)])

    _style(ws4)
    _autosize(ws4)

    # =================================================================
    # 5. Risk Reduction (from reassessments)
    # =================================================================
    ws5 = wb.create_sheet("Risk Reduction")
    ws5.append([
        "Assessment ID", "Department", "Job", "Task",
        "Prev Score", "New Score", "Reduction %",
        "Previous Risk", "New Risk",
        "Control Effectiveness", "Date",
    ])

    for r in reassessments.select_related("assessment", "assessment__department"):
        a = r.assessment
        ws5.append([
            a.assessment_id if a else "",
            a.department.name if a and a.department else "",
            a.job_role if a else "",
            a.task if a else "",
            float(r.previous_score) if r.previous_score is not None else "",
            float(r.new_score) if r.new_score is not None else "",
            float(r.risk_reduction_percent) if r.risk_reduction_percent is not None else 0,
            r.previous_risk or "",
            r.new_risk or "",
            r.get_control_effectiveness_display() if r.control_effectiveness else "",
            r.reassessment_date,
        ])
    _style(ws5)
    _autosize(ws5)

    # =================================================================
    # 6. MSD Trends
    # =================================================================
    ws6 = wb.create_sheet("MSD Trends")
    ws6.append(["Monthly MSD Volume"])
    ws6.append(["Month", "Cases"])

    msd_all_qs = MSDDiscomfort.objects.all()
    # Restrict to accessible plants via related_assessment if linked
    linked_ids = list(assessments.values_list("id", flat=True))
    msd_all_qs = MSDDiscomfort.objects.filter(
        Q(related_assessment__in=assessments) | Q(related_assessment__isnull=True)
    )

    monthly = (
        msd_all_qs
        .annotate(month=TruncMonth("date_reported"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    for m in monthly:
        ws6.append([m["month"].strftime("%Y-%m") if m["month"] else "", m["total"]])

    ws6.append([])
    ws6.append(["Body Part Breakdown"])
    ws6.append(["Body Part", "Cases"])
    for row in msd_all_qs.values("body_part").annotate(total=Count("id")).order_by("-total"):
        ws6.append([row["body_part"], row["total"]])

    ws6.append([])
    ws6.append(["Severity Breakdown"])
    ws6.append(["Severity", "Cases"])
    for row in msd_all_qs.values("severity").annotate(total=Count("id")).order_by("-total"):
        ws6.append([row["severity"], row["total"]])

    _style(ws6)
    _autosize(ws6)

    # =================================================================
    # 7. Method Usage
    # =================================================================
    ws7 = wb.create_sheet("Method Usage")
    ws7.append(["Method", "Assessments", "Avg Score"])
    methods = (
        assessments
        .values("assessment_method__name")
        .annotate(total=Count("id"), avg_score=Avg("score"))
        .order_by("-total")
    )
    for m in methods:
        ws7.append([
            m["assessment_method__name"] or "—",
            m["total"],
            round(float(m["avg_score"]), 2) if m["avg_score"] is not None else "",
        ])
    _style(ws7)
    _autosize(ws7)

    return wb


def management_report_response(assessments):
    """
    Return an HttpResponse with the executive-level ergonomics workbook.
    """
    from datetime import datetime
    from io import BytesIO
    from django.http import HttpResponse

    wb = build_management_report(assessments)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="Ergonomics_Management_Report_{datetime.now():%Y%m%d_%H%M}.xlsx"'
    )
    return response