import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .models import (
    HAZOPStudy,
    HAZOPNode,
    HAZOPWorksheetEntry,
    HAZOPRiskAssessment,
    HAZOPRiskLevel,
    HAZOPAction,
)


def _get_risk_level(score):
    if score is None:
        return None

    return HAZOPRiskLevel.objects.filter(
        is_active=True,
        minimum_score__lte=score,
        maximum_score__gte=score,
    ).first()


def _risk_name(score):
    level = _get_risk_level(score)
    return level.name if level else "Unclassified"


def _risk_color(score):
    level = _get_risk_level(score)
    return level.color if level else "#64748b"


def _assessment_queryset(request):
    qs = HAZOPRiskAssessment.objects.select_related(
        "worksheet_entry",
        "worksheet_entry__node",
        "worksheet_entry__node__study",
        "worksheet_entry__node__study__plant",
        "matrix",
        "assessor",
        "action_responsible",
    )

    plant_id = request.GET.get("plant")
    study_id = request.GET.get("study")
    node_id = request.GET.get("node")
    status = request.GET.get("status")
    risk_level = request.GET.get("risk_level")
    date_from = parse_date(request.GET.get("date_from", ""))
    date_to = parse_date(request.GET.get("date_to", ""))

    if plant_id:
        qs = qs.filter(
            worksheet_entry__node__study__plant_id=plant_id
        )

    if study_id:
        qs = qs.filter(
            worksheet_entry__node__study_id=study_id
        )

    if node_id:
        qs = qs.filter(
            worksheet_entry__node_id=node_id
        )

    if status:
        qs = qs.filter(status=status)

    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    assessments = list(qs.order_by("-created_at"))

    if risk_level:
        assessments = [
            item for item in assessments
            if _risk_name(item.initial_risk_score) == risk_level
        ]

    return assessments


def _action_queryset(request):
    qs = HAZOPAction.objects.select_related(
        "recommendation",
        "recommendation__worksheet_entry",
        "recommendation__worksheet_entry__node",
        "recommendation__worksheet_entry__node__study",
        "recommendation__worksheet_entry__node__study__plant",
        "assigned_to",
        "department",
    )

    plant_id = request.GET.get("plant")
    study_id = request.GET.get("study")
    node_id = request.GET.get("node")
    action_status = request.GET.get("action_status")
    date_from = parse_date(request.GET.get("date_from", ""))
    date_to = parse_date(request.GET.get("date_to", ""))

    if plant_id:
        qs = qs.filter(
            recommendation__worksheet_entry__node__study__plant_id=plant_id
        )

    if study_id:
        qs = qs.filter(
            recommendation__worksheet_entry__node__study_id=study_id
        )

    if node_id:
        qs = qs.filter(
            recommendation__worksheet_entry__node_id=node_id
        )

    if action_status:
        qs = qs.filter(status=action_status)

    if date_from:
        qs = qs.filter(due_date__gte=date_from)

    if date_to:
        qs = qs.filter(due_date__lte=date_to)

    return list(qs.order_by("due_date"))


@login_required
def hazop_analytics_dashboard(request):
    assessments = _assessment_queryset(request)
    actions = _action_queryset(request)

    today = timezone.localdate()

    total_assessments = len(assessments)

    high_risk_assessments = [
        item for item in assessments
        if _risk_name(item.initial_risk_score).lower()
        in ("high", "very high", "extreme", "critical")
    ]

    open_actions = [
        action for action in actions
        if action.status not in ("VERIFIED", "CANCELLED")
    ]

    overdue_actions = [
        action for action in open_actions
        if action.due_date and action.due_date < today
    ]

    # Risk level distribution
    risk_distribution = {}
    for item in assessments:
        level = _risk_name(item.initial_risk_score)
        risk_distribution[level] = risk_distribution.get(level, 0) + 1

    risk_distribution_labels = list(risk_distribution.keys())
    risk_distribution_values = list(risk_distribution.values())

    # Initial vs residual risk
    initial_scores = []
    residual_scores = []

    for item in assessments:
        initial_scores.append(item.initial_risk_score)
        residual_scores.append(
            item.residual_risk_score
            if item.residual_risk_score is not None
            else 0
        )

    # Action status
    action_status_counts = {}
    for action in actions:
        action_status_counts[action.get_status_display()] = (
            action_status_counts.get(action.get_status_display(), 0) + 1
        )

    # Plant-wise risk
    plant_risk = {}
    for item in assessments:
        plant_name = item.worksheet_entry.node.study.plant.name
        plant_risk.setdefault(plant_name, []).append(
            item.initial_risk_score
        )

    plant_labels = list(plant_risk.keys())
    plant_average_risk = [
        round(sum(scores) / len(scores), 2)
        for scores in plant_risk.values()
    ]

    # Monthly assessment trend
    monthly_counts = {}
    for item in assessments:
        month_key = item.created_at.strftime("%Y-%m")
        monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

    monthly_labels = sorted(monthly_counts.keys())
    monthly_values = [monthly_counts[key] for key in monthly_labels]

    # Recent assessments
    recent_assessments = assessments[:10]

    plants = HAZOPStudy.objects.select_related("plant").values(
        "plant_id", "plant__name"
    ).distinct().order_by("plant__name")

    studies = HAZOPStudy.objects.all().order_by("study_title")
    nodes = HAZOPNode.objects.select_related("study").order_by(
        "node_name"
    )

    context = {
        "total_assessments": total_assessments,
        "high_risk_assessments": len(high_risk_assessments),
        "open_actions": len(open_actions),
        "overdue_actions": len(overdue_actions),

        "assessments": recent_assessments,
        "actions": actions[:10],

        "plants": plants,
        "studies": studies,
        "nodes": nodes,

        "status_choices": HAZOPRiskAssessment.STATUS_CHOICES,
        "action_status_choices": HAZOPAction.STATUS_CHOICES,
        "risk_levels": HAZOPRiskLevel.objects.filter(
            is_active=True
        ).order_by("minimum_score"),

        "selected_plant": request.GET.get("plant", ""),
        "selected_study": request.GET.get("study", ""),
        "selected_node": request.GET.get("node", ""),
        "selected_status": request.GET.get("status", ""),
        "selected_action_status": request.GET.get(
            "action_status", ""
        ),
        "selected_risk_level": request.GET.get("risk_level", ""),
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),

        "charts_json": json.dumps({
            "riskLabels": risk_distribution_labels,
            "riskValues": risk_distribution_values,
            "initialScores": initial_scores,
            "residualScores": residual_scores,
            "actionLabels": list(action_status_counts.keys()),
            "actionValues": list(action_status_counts.values()),
            "plantLabels": plant_labels,
            "plantValues": plant_average_risk,
            "monthLabels": monthly_labels,
            "monthValues": monthly_values,
        }),
    }

    return render(
        request,
        "hazop/analytics/dashboard.html",
        context,
    )


from io import BytesIO
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Border,
    Side,
    Alignment,
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.worksheet.table import Table, TableStyleInfo




from django.db.models import Model, QuerySet
from django.db.models.manager import BaseManager
from datetime import date, datetime
from decimal import Decimal
import json


def excel_safe_value(value):
    """
    Convert Django model values and complex Python objects
    into values that openpyxl can write to Excel.
    """

    if value is None:
        return ""

    # Many-to-many manager, for example study.team_members
    if isinstance(value, BaseManager):
        return ", ".join(
            str(item) for item in value.all()
        )

    # QuerySet
    if isinstance(value, QuerySet):
        return ", ".join(
            str(item) for item in value
        )

    # Django model instance, for example User or Plant
    if isinstance(value, Model):
        return str(value)

    # Dictionary
    if isinstance(value, dict):
        return json.dumps(value, default=str, ensure_ascii=False)

    # List, tuple, or set
    if isinstance(value, (list, tuple, set)):
        return ", ".join(
            str(excel_safe_value(item))
            for item in value
        )

    # Decimal
    if isinstance(value, Decimal):
        return float(value)

    # Date and datetime values are supported by Excel
    if isinstance(value, (date, datetime)):
        return value

    # Normal values such as strings, integers, floats and booleans
    return value


from collections import defaultdict
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Border,
    Side,
    Alignment,
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList


@login_required
def hazop_analytics_export_excel(request):

    # =========================================================
    # DATA
    # =========================================================

    assessments = list(_assessment_queryset(request))
    actions = list(_action_queryset(request))

    today = timezone.localdate()
    generated_at = timezone.localtime()

    wb = Workbook()

    # =========================================================
    # THEME
    # =========================================================

    NAVY = "12304A"
    TEAL = "0F766E"
    LIGHT_BLUE = "DCE6F1"
    WHITE = "FFFFFF"
    GREY = "64748B"
    RED = "C00000"
    ORANGE = "F4B183"
    YELLOW = "FFE699"
    GREEN = "C6E0B4"
    LIGHT_RED = "FCE4D6"
    LIGHT_YELLOW = "FFF2CC"

    thin_grey = Side(
        style="thin",
        color="D9E2F3",
    )

    border = Border(
        left=thin_grey,
        right=thin_grey,
        top=thin_grey,
        bottom=thin_grey,
    )

    title_fill = PatternFill(
        "solid",
        fgColor=NAVY,
    )

    header_fill = PatternFill(
        "solid",
        fgColor=TEAL,
    )

    section_fill = PatternFill(
        "solid",
        fgColor=LIGHT_BLUE,
    )

    warning_fill = PatternFill(
        "solid",
        fgColor=LIGHT_YELLOW,
    )

    # =========================================================
    # HELPERS
    # =========================================================

    def safe_text(value):
        if value is None:
            return ""

        return str(value).strip()

    def person_name(person):
        if not person:
            return ""

        return str(person)

    def date_value(value):
        if not value:
            return None

        if hasattr(value, "date"):
            return value.date()

        return value

    def display(obj, field):
        if not obj:
            return ""

        method = getattr(
            obj,
            f"get_{field}_display",
            None,
        )

        if callable(method):
            return method()

        return safe_text(getattr(obj, field, ""))

    def risk_name(score):
        if score is None:
            return "Unclassified"

        return _risk_name(score)

    def risk_color(score):
        if score is None:
            return GREY

        color = _risk_color(score)

        if color:
            return str(color).replace("#", "").upper()

        return GREY

    def high_risk(score):
        return risk_name(score).lower() in (
            "high",
            "very high",
            "extreme",
            "critical",
        )

    def active_related_text(entry, related_name, description_field):
        """
        Get active related records such as causes, consequences
        and safeguards. Fall back to a direct text field if
        there are no active related records.
        """

        related_manager = getattr(
            entry,
            related_name,
            None,
        )

        if related_manager is not None:
            records = related_manager.filter(
                is_active=True
            )

            values = [
                safe_text(getattr(record, description_field, ""))
                for record in records
            ]

            values = [
                value for value in values
                if value
            ]

            if values:
                return "\n".join(
                    f"• {value}" for value in values
                )

        return ""

    def get_causes(entry):
        related_causes = active_related_text(
            entry,
            "causes",
            "cause_description",
        )

        if related_causes:
            return related_causes

        # The model also contains possible_causes directly.
        return safe_text(
            getattr(entry, "possible_causes", "")
        )

    def get_consequences(entry, assessment):
        related_consequences = active_related_text(
            entry,
            "consequences",
            "consequence_description",
        )

        assessment_consequence = safe_text(
            getattr(
                assessment,
                "potential_consequence",
                "",
            )
        )

        values = []

        if related_consequences:
            values.append(related_consequences)

        if assessment_consequence:
            values.append(assessment_consequence)

        return "\n".join(values)

    def get_safeguards(entry, assessment):
        related_safeguards = active_related_text(
            entry,
            "safeguards",
            "safeguard_description",
        )

        assessment_controls = safe_text(
            getattr(
                assessment,
                "existing_controls",
                "",
            )
        )

        values = []

        if related_safeguards:
            values.append(related_safeguards)

        if assessment_controls:
            values.append(assessment_controls)

        return "\n".join(values)

    def style_title(ws, title, subtitle, last_column):
        ws.merge_cells(
            start_row=1,
            start_column=1,
            end_row=1,
            end_column=last_column,
        )

        cell = ws.cell(1, 1, title)
        cell.fill = title_fill
        cell.font = Font(
            bold=True,
            color=WHITE,
            size=16,
        )
        cell.alignment = Alignment(
            vertical="center",
        )

        ws.row_dimensions[1].height = 32

        ws.merge_cells(
            start_row=2,
            start_column=1,
            end_row=2,
            end_column=last_column,
        )

        cell = ws.cell(2, 1, subtitle)
        cell.font = Font(
            italic=True,
            color=GREY,
            size=10,
        )
        cell.alignment = Alignment(
            vertical="center",
            wrap_text=True,
        )

        ws.row_dimensions[2].height = 30

    def style_headers(ws, row_number, start_col, end_col):
        for col in range(start_col, end_col + 1):
            cell = ws.cell(
                row_number,
                col,
            )

            cell.fill = header_fill
            cell.font = Font(
                bold=True,
                color=WHITE,
                size=10,
            )
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )
            cell.border = border

        ws.row_dimensions[row_number].height = 42

    def style_data(ws, start_row, end_row, start_col, end_col):
        if end_row < start_row:
            return

        for row in ws.iter_rows(
            min_row=start_row,
            max_row=end_row,
            min_col=start_col,
            max_col=end_col,
        ):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True,
                )

    def set_widths(ws, widths):
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

    def add_table(ws, table_name, ref):
        if ws.max_row < 2:
            return

        from openpyxl.worksheet.table import Table, TableStyleInfo

        table = Table(
            displayName=table_name,
            ref=ref,
        )

        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )

        ws.add_table(table)

    def write_row(ws, row_number, values, start_col=1):
        for col, value in enumerate(
            values,
            start=start_col,
        ):
            ws.cell(
                row_number,
                col,
                excel_safe_value(value),
            )

    # =========================================================
    # LOOKUPS
    # =========================================================

    assessments_by_entry = defaultdict(list)

    for assessment in assessments:
        assessments_by_entry[
            assessment.worksheet_entry_id
        ].append(assessment)

    actions_by_entry = defaultdict(list)

    for action in actions:
        recommendation = action.recommendation

        if not recommendation:
            continue

        entry_id = recommendation.worksheet_entry_id

        actions_by_entry[entry_id].append(action)

    recommendations_by_entry = defaultdict(list)

    for assessment in assessments:
        entry = assessment.worksheet_entry

        recommendations = (
            entry.recommendations
            .filter(is_active=True)
            .order_by("created_at")
        )

        recommendations_by_entry[entry.pk] = list(
            recommendations
        )

    # =========================================================
    # 1. STUDY SUMMARY
    # =========================================================

    summary = wb.active
    summary.title = "Study Summary"

    style_title(
        summary,
        "HAZOP STUDY REPORT",
        (
            "Filtered HAZOP report generated from the "
            "HAZOP Analytics Dashboard. Verify all data "
            "before formal approval."
        ),
        6,
    )

    # Determine study information from the filtered records.
    studies = []

    for assessment in assessments:
        study = assessment.worksheet_entry.node.study

        if study.pk not in [
            item.pk for item in studies
        ]:
            studies.append(study)

    study_names = [
        safe_text(getattr(item, "study_title", ""))
        for item in studies
    ]

    plant_names = [
        safe_text(getattr(item.plant, "name", ""))
        for item in studies
        if getattr(item, "plant", None)
    ]

    study_title = (
        ", ".join(filter(None, study_names))
        if study_names
        else "No filtered study"
    )

    plant_title = (
        ", ".join(sorted(set(filter(None, plant_names))))
        if plant_names
        else ""
    )

    study_data = [
        ("Project / Facility", plant_title),
        ("Study Title", study_title),
        (
            "Study Reference",
            ", ".join(
                safe_text(getattr(item, "study_number", ""))
                for item in studies
                if getattr(item, "study_number", "")
            ),
        ),
        ("Report Generated Date", generated_at.strftime("%d-%b-%Y")),
        (
            "Study Leader",
            ", ".join(
                safe_text(getattr(item, "study_leader", ""))
                for item in studies
                if getattr(item, "study_leader", "")
            ),
        ),
        (
            "Recorder",
            ", ".join(
                safe_text(getattr(item, "recorder", ""))
                for item in studies
                if getattr(item, "recorder", "")
            ),
        ),
        (
            "Scope",
            "\n".join(
                safe_text(getattr(item, "scope", ""))
                for item in studies
                if getattr(item, "scope", "")
            ),
        ),
        (
            "Design Documents",
            "\n".join(
                safe_text(getattr(item, "design_documents", ""))
                for item in studies
                if getattr(item, "design_documents", "")
            ),
        ),
        (
            "Generated By",
            request.user.get_full_name()
            or request.user.username,
        ),
        (
            "Generated At",
            generated_at.strftime("%d-%b-%Y %H:%M"),
        ),
    ]

    for row_number, (label, value) in enumerate(
        study_data,
        start=4,
    ):
        summary.cell(
            row_number,
            1,
            label,
        )

        summary.cell(
            row_number,
            2,
            value,
        )

        summary.cell(
            row_number,
            1,
        ).font = Font(
            bold=True,
            color=NAVY,
        )

        summary.cell(
            row_number,
            1,
        ).fill = section_fill

        for col in range(1, 3):
            summary.cell(
                row_number,
                col,
            ).border = border

    # Summary metrics
    summary["A16"] = "HAZOP Risk Snapshot"
    summary["A16"].fill = title_fill
    summary["A16"].font = Font(
        bold=True,
        color=WHITE,
    )

    open_actions = [
        action for action in actions
        if action.status not in (
            "VERIFIED",
            "CANCELLED",
        )
    ]

    overdue_actions = [
        action for action in open_actions
        if action.due_date
        and action.due_date < today
    ]

    completed_actions = [
        action for action in actions
        if action.status == "VERIFIED"
    ]

    summary_metrics = [
        ("Total Risk Assessments", len(assessments)),
        (
            "High / Very High / Extreme Initial Risk",
            sum(
                1 for item in assessments
                if high_risk(item.initial_risk_score)
            ),
        ),
        ("Total Actions", len(actions)),
        ("Open Actions", len(open_actions)),
        ("Overdue Actions", len(overdue_actions)),
        ("Verified Actions", len(completed_actions)),
    ]

    for row_number, (label, value) in enumerate(
        summary_metrics,
        start=17,
    ):
        summary.cell(
            row_number,
            1,
            label,
        )

        summary.cell(
            row_number,
            2,
            value,
        )

        summary.cell(
            row_number,
            1,
        ).font = Font(
            bold=True,
            color=NAVY,
        )

        for col in range(1, 3):
            summary.cell(
                row_number,
                col,
            ).border = border

    # Data quality checks
    summary["A25"] = "Data Quality Checks"
    summary["A25"].fill = title_fill
    summary["A25"].font = Font(
        bold=True,
        color=WHITE,
    )

    quality_headers = [
        "Check",
        "Result",
    ]

    write_row(
        summary,
        26,
        quality_headers,
    )

    style_headers(
        summary,
        26,
        1,
        2,
    )

    missing_causes = 0
    missing_consequences = 0
    missing_safeguards = 0
    missing_recommendations = 0
    verified_without_completion = 0

    for assessment in assessments:
        entry = assessment.worksheet_entry

        if not get_causes(entry):
            missing_causes += 1

        if not get_consequences(entry, assessment):
            missing_consequences += 1

        if not get_safeguards(entry, assessment):
            missing_safeguards += 1

        if not recommendations_by_entry.get(entry.pk):
            missing_recommendations += 1

    for action in actions:
        if (
            action.status == "VERIFIED"
            and not action.completed_at
        ):
            verified_without_completion += 1

    quality_rows = [
        (
            "Findings without possible causes",
            missing_causes,
        ),
        (
            "Findings without consequences",
            missing_consequences,
        ),
        (
            "Findings without safeguards",
            missing_safeguards,
        ),
        (
            "Findings without recommendations",
            missing_recommendations,
        ),
        (
            "Verified actions missing completion date",
            verified_without_completion,
        ),
    ]

    for row_number, row_data in enumerate(
        quality_rows,
        start=27,
    ):
        write_row(
            summary,
            row_number,
            row_data,
        )

        if row_data[1]:
            summary.cell(
                row_number,
                2,
            ).fill = warning_fill

    # Applied filters
    filter_start = 34

    summary.cell(
        filter_start,
        1,
        "Applied Dashboard Filters",
    )

    summary.cell(
        filter_start,
        1,
    ).fill = title_fill

    summary.cell(
        filter_start,
        1,
    ).font = Font(
        bold=True,
        color=WHITE,
    )

    write_row(
        summary,
        filter_start + 1,
        ["Filter", "Selected Value"],
    )

    style_headers(
        summary,
        filter_start + 1,
        1,
        2,
    )

    filters = [
        ("Plant", "plant"),
        ("Study", "study"),
        ("Node", "node"),
        ("Assessment Status", "status"),
        ("Risk Level", "risk_level"),
        ("Action Status", "action_status"),
        ("Date From", "date_from"),
        ("Date To", "date_to"),
    ]

    for row_number, (label, key) in enumerate(
        filters,
        start=filter_start + 2,
    ):
        write_row(
            summary,
            row_number,
            [
                label,
                request.GET.get(key) or "All",
            ],
        )

    style_data(
        summary,
        4,
        summary.max_row,
        1,
        2,
    )

    set_widths(
        summary,
        {
            "A": 45,
            "B": 75,
            "C": 18,
            "D": 18,
            "E": 18,
            "F": 18,
        },
    )

    summary.freeze_panes = "A4"

    # =========================================================
    # 2. HAZOP WORKSHEET
    # =========================================================

    worksheet = wb.create_sheet("HAZOP Worksheet")

    style_title(
        worksheet,
        "HAZOP WORKSHEET",
        (
            "Filtered HAZOP findings with linked causes, "
            "consequences, safeguards, recommendations and actions."
        ),
        21,
    )

    worksheet_headers = [
        "HAZOP ID",
        "Node / Equipment",
        "Design Intent",
        "Parameter",
        "Guide Word",
        "Deviation",
        "Possible Causes",
        "Potential Consequences",
        "Existing Safeguards / Controls",
        "Initial Likelihood",
        "Initial Severity",
        "Initial Risk Score",
        "Initial Risk Level",
        "Recommended Actions",
        "Action Owner",
        "Residual Likelihood",
        "Residual Severity",
        "Residual Risk Score",
        "Residual Risk Level",
        "Action IDs",
        "Study Notes",
    ]

    write_row(
        worksheet,
        5,
        worksheet_headers,
    )

    style_headers(
        worksheet,
        5,
        1,
        len(worksheet_headers),
    )

    for row_number, assessment in enumerate(
        assessments,
        start=6,
    ):
        entry = assessment.worksheet_entry
        node = entry.node

        linked_actions = actions_by_entry.get(
            entry.pk,
            [],
        )

        recommendations = recommendations_by_entry.get(
            entry.pk,
            [],
        )

        recommendation_text = "\n".join(
            f"• {recommendation.recommendation_description}"
            for recommendation in recommendations
            if recommendation.recommendation_description
        )

        if not recommendation_text:
            recommendation_text = safe_text(
                assessment.additional_controls
            )

        action_ids = "\n".join(
            action.action_number
            for action in linked_actions
            if action.action_number
        )

        action_owners = "\n".join(
            person_name(action.assigned_to)
            for action in linked_actions
            if action.assigned_to
        )

        row_values = [
            assessment.assessment_number,
            node.node_name,
            getattr(node, "design_intent", ""),
            str(entry.parameter),
            str(entry.guide_word),
            entry.deviation_description,
            get_causes(entry),
            get_consequences(entry, assessment),
            get_safeguards(entry, assessment),
            assessment.initial_likelihood,
            assessment.initial_severity,
            assessment.initial_risk_score,
            risk_name(assessment.initial_risk_score),
            recommendation_text,
            action_owners or person_name(
                assessment.action_responsible
            ),
            assessment.residual_likelihood,
            assessment.residual_severity,
            assessment.residual_risk_score,
            risk_name(assessment.residual_risk_score),
            action_ids,
            assessment.review_comments,
        ]

        write_row(
            worksheet,
            row_number,
            row_values,
        )

        worksheet.cell(
            row_number,
            13,
        ).fill = PatternFill(
            "solid",
            fgColor=risk_color(
                assessment.initial_risk_score
            ),
        )

        worksheet.cell(
            row_number,
            19,
        ).fill = PatternFill(
            "solid",
            fgColor=risk_color(
                assessment.residual_risk_score
            ),
        )

        # Highlight missing causes or safeguards.
        if not get_causes(entry):
            worksheet.cell(
                row_number,
                7,
            ).fill = warning_fill

        if not get_safeguards(entry, assessment):
            worksheet.cell(
                row_number,
                9,
            ).fill = warning_fill

    style_data(
        worksheet,
        6,
        max(worksheet.max_row, 6),
        1,
        len(worksheet_headers),
    )

    worksheet.freeze_panes = "A6"

    worksheet.auto_filter.ref = (
        f"A5:U{max(worksheet.max_row, 5)}"
    )

    set_widths(
        worksheet,
        {
            "A": 18,
            "B": 28,
            "C": 35,
            "D": 18,
            "E": 18,
            "F": 35,
            "G": 45,
            "H": 45,
            "I": 45,
            "J": 16,
            "K": 16,
            "L": 18,
            "M": 18,
            "N": 50,
            "O": 25,
            "P": 18,
            "Q": 18,
            "R": 18,
            "S": 18,
            "T": 22,
            "U": 40,
        },
    )

    # =========================================================
    # 3. RISK MATRIX
    # =========================================================

    matrix = wb.create_sheet("Risk Matrix")

    style_title(
        matrix,
        "5 × 5 RISK MATRIX",
        (
            "Risk score = Likelihood × Severity. "
            "Risk bands use the active HAZOP risk level "
            "configuration in the database."
        ),
        7,
    )

    matrix["A4"] = "Risk score = Likelihood × Severity"
    matrix["A4"].font = Font(
        bold=True,
        color=NAVY,
    )

    matrix["A6"] = "Likelihood \\ Severity"

    for severity in range(1, 6):
        matrix.cell(
            6,
            severity + 1,
            severity,
        )

    for likelihood in range(1, 6):
        matrix.cell(
            likelihood + 6,
            1,
            likelihood,
        )

        for severity in range(1, 6):
            score = likelihood * severity

            cell = matrix.cell(
                likelihood + 6,
                severity + 1,
                score,
            )

            cell.fill = PatternFill(
                "solid",
                fgColor=risk_color(score),
            )

            cell.font = Font(
                bold=True,
                color=WHITE if risk_name(score).lower()
                in ("extreme", "critical")
                else "000000",
            )

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
            )

            cell.border = border

    style_headers(
        matrix,
        6,
        1,
        6,
    )

    matrix["A14"] = "Configured Risk Bands"
    matrix["A14"].fill = title_fill
    matrix["A14"].font = Font(
        bold=True,
        color=WHITE,
    )

    risk_levels = list(
        HAZOPRiskLevel.objects
        .filter(is_active=True)
        .order_by("minimum_score")
    )

    write_row(
        matrix,
        15,
        [
            "Minimum Score",
            "Maximum Score",
            "Risk Level",
            "Requires Action",
        ],
    )

    style_headers(
        matrix,
        15,
        1,
        4,
    )

    for row_number, level in enumerate(
        risk_levels,
        start=16,
    ):
        write_row(
            matrix,
            row_number,
            [
                level.minimum_score,
                level.maximum_score,
                level.name,
                "Yes" if level.requires_action else "No",
            ],
        )

        matrix.cell(
            row_number,
            3,
        ).fill = PatternFill(
            "solid",
            fgColor=str(level.color).replace("#", "").upper(),
        )

    matrix["A24"] = "Likelihood Scale"
    matrix["D24"] = "Severity Scale"

    matrix["A24"].fill = title_fill
    matrix["A24"].font = Font(
        bold=True,
        color=WHITE,
    )

    matrix["D24"].fill = title_fill
    matrix["D24"].font = Font(
        bold=True,
        color=WHITE,
    )

    likelihood_scale = [
        (1, "Rare"),
        (2, "Unlikely"),
        (3, "Possible"),
        (4, "Likely"),
        (5, "Almost certain"),
    ]

    severity_scale = [
        (1, "Insignificant"),
        (2, "Minor"),
        (3, "Moderate"),
        (4, "Major"),
        (5, "Catastrophic"),
    ]

    for row_number, (number, label) in enumerate(
        likelihood_scale,
        start=25,
    ):
        write_row(
            matrix,
            row_number,
            [number, label],
        )

    for row_number, (number, label) in enumerate(
        severity_scale,
        start=25,
    ):
        write_row(
            matrix,
            row_number,
            [number, label],
            start_col=4,
        )

    style_data(
        matrix,
        15,
        max(matrix.max_row, 15),
        1,
        4,
    )

    set_widths(
        matrix,
        {
            "A": 28,
            "B": 28,
            "C": 35,
            "D": 28,
            "E": 28,
            "F": 18,
            "G": 18,
        },
    )

    # =========================================================
    # 4. ACTION TRACKER
    # =========================================================

    action_ws = wb.create_sheet("Action Tracker")

    style_title(
        action_ws,
        "HAZOP ACTION TRACKER",
        (
            "Actions are linked through the recommendation "
            "and worksheet entry relationship. Multiple "
            "actions may belong to one HAZOP finding."
        ),
        12,
    )

    action_headers = [
        "Action ID",
        "HAZOP ID",
        "Recommendation",
        "Action Description",
        "Priority",
        "Responsible Department",
        "Action Owner",
        "Target Date",
        "Completion Date",
        "Verified Date",
        "Status",
        "Evidence / Closure Notes",
    ]

    write_row(
        action_ws,
        5,
        action_headers,
    )

    style_headers(
        action_ws,
        5,
        1,
        len(action_headers),
    )

    for row_number, action in enumerate(
        actions,
        start=6,
    ):
        recommendation = action.recommendation
        entry = recommendation.worksheet_entry

        linked_assessments = assessments_by_entry.get(
            entry.pk,
            [],
        )

        # If filters exclude the linked assessment, use the
        # actual related assessment IDs from the database.
        assessment_numbers = [
            item.assessment_number
            for item in linked_assessments
            if item.assessment_number
        ]

        if not assessment_numbers:
            assessment_numbers = list(
                entry.risk_assessments
                .values_list(
                    "assessment_number",
                    flat=True,
                )
            )

        hazop_ids = "\n".join(
            item for item in assessment_numbers
            if item
        )

        is_overdue = (
            action.due_date
            and action.due_date < today
            and action.status not in (
                "VERIFIED",
                "CANCELLED",
            )
        )

        completion_date = (
            date_value(action.completed_at)
            if action.completed_at
            else None
        )

        verified_date = (
            date_value(action.verified_at)
            if action.verified_at
            else None
        )

        row_values = [
            action.action_number,
            hazop_ids,
            recommendation.recommendation_description,
            action.action_description,
            display(action, "priority"),
            person_name(action.department),
            person_name(action.assigned_to),
            date_value(action.due_date),
            completion_date,
            verified_date,
            display(action, "status"),
            "\n".join(
                filter(
                    None,
                    [
                        safe_text(action.completion_remarks),
                        safe_text(action.verification_remarks),
                        safe_text(action.evidence),
                    ],
                )
            ),
        ]

        write_row(
            action_ws,
            row_number,
            row_values,
        )

        for col in (8, 9, 10):
            action_ws.cell(
                row_number,
                col,
            ).number_format = "dd-mmm-yyyy"

        if is_overdue:
            for cell in action_ws[row_number]:
                cell.fill = PatternFill(
                    "solid",
                    fgColor=LIGHT_RED,
                )

        # Verified action without completion timestamp.
        if (
            action.status == "VERIFIED"
            and not action.completed_at
        ):
            action_ws.cell(
                row_number,
                9,
            ).fill = warning_fill

    style_data(
        action_ws,
        6,
        max(action_ws.max_row, 6),
        1,
        len(action_headers),
    )

    action_ws.freeze_panes = "A6"

    action_ws.auto_filter.ref = (
        f"A5:L{max(action_ws.max_row, 5)}"
    )

    set_widths(
        action_ws,
        {
            "A": 18,
            "B": 22,
            "C": 45,
            "D": 50,
            "E": 16,
            "F": 25,
            "G": 25,
            "H": 18,
            "I": 18,
            "J": 18,
            "K": 25,
            "L": 45,
        },
    )

    # =========================================================
    # 5. DASHBOARD
    # =========================================================

    dashboard = wb.create_sheet("Dashboard")

    style_title(
        dashboard,
        "HAZOP ANALYTICAL DASHBOARD",
        (
            "Summary and risk distribution based on "
            "the filtered HAZOP report."
        ),
        10,
    )

    dashboard["A4"] = "Key Indicators"
    dashboard["D4"] = "Initial Risk Distribution"

    for cell_ref in ("A4", "D4"):
        dashboard[cell_ref].fill = title_fill
        dashboard[cell_ref].font = Font(
            bold=True,
            color=WHITE,
        )

    write_row(
        dashboard,
        5,
        ["Metric", "Value"],
    )

    write_row(
        dashboard,
        5,
        ["Risk Level", "Count"],
        start_col=4,
    )

    style_headers(
        dashboard,
        5,
        1,
        2,
    )

    style_headers(
        dashboard,
        5,
        4,
        5,
    )

    open_count = sum(
        1 for action in actions
        if action.status not in (
            "VERIFIED",
            "CANCELLED",
        )
    )

    in_progress_count = sum(
        1 for action in actions
        if action.status in (
            "IN_PROGRESS",
            "REOPENED",
            "SUBMITTED_FOR_VERIFICATION",
        )
    )

    verified_count = sum(
        1 for action in actions
        if action.status == "VERIFIED"
    )

    dashboard_metrics = [
        ("Total HAZOP Findings", len(assessments)),
        (
            "High / Very High / Extreme Initial Risk",
            sum(
                1 for item in assessments
                if high_risk(item.initial_risk_score)
            ),
        ),
        ("Open Actions", open_count),
        ("In Progress / Reopened / Verification", in_progress_count),
        ("Verified Actions", verified_count),
        (
            "Overdue Actions",
            len(overdue_actions),
        ),
    ]

    for row_number, (label, value) in enumerate(
        dashboard_metrics,
        start=6,
    ):
        write_row(
            dashboard,
            row_number,
            [label, value],
        )

    # Use configured risk levels instead of hardcoded bands.
    risk_counts = defaultdict(int)

    for assessment in assessments:
        risk_counts[
            risk_name(assessment.initial_risk_score)
        ] += 1

    configured_levels = [
        level.name for level in risk_levels
    ]

    for row_number, level_name in enumerate(
        configured_levels,
        start=6,
    ):
        write_row(
            dashboard,
            row_number,
            [
                level_name,
                risk_counts.get(level_name, 0),
            ],
            start_col=4,
        )

    # Risk distribution chart
    if configured_levels:
        doughnut = DoughnutChart()

        doughnut.title = "Initial Risk Distribution"
        doughnut.height = 8
        doughnut.width = 13
        doughnut.holeSize = 55

        doughnut.add_data(
            Reference(
                dashboard,
                min_col=5,
                min_row=5,
                max_row=5 + len(configured_levels),
            ),
            titles_from_data=True,
        )

        doughnut.set_categories(
            Reference(
                dashboard,
                min_col=4,
                min_row=6,
                max_row=5 + len(configured_levels),
            )
        )

        doughnut.dataLabels = DataLabelList()
        doughnut.dataLabels.showPercent = True

        dashboard.add_chart(
            doughnut,
            "G4",
        )

    # Action status summary
    dashboard["D15"] = "Action Status"
    dashboard["D15"].fill = title_fill
    dashboard["D15"].font = Font(
        bold=True,
        color=WHITE,
    )

    write_row(
        dashboard,
        16,
        ["Status", "Count"],
        start_col=4,
    )

    style_headers(
        dashboard,
        16,
        4,
        5,
    )

    status_counts = defaultdict(int)

    for action in actions:
        status_label = display(
            action,
            "status",
        )

        status_counts[status_label] += 1

    action_status_rows = [
        ("Open", status_counts.get("Open", 0)),
        (
            "In Progress",
            status_counts.get("In Progress", 0),
        ),
        (
            "Submitted for Verification",
            status_counts.get(
                "Submitted for Verification",
                0,
            ),
        ),
        ("Verified", status_counts.get("Verified", 0)),
        ("Reopened", status_counts.get("Reopened", 0)),
        ("Cancelled", status_counts.get("Cancelled", 0)),
    ]

    for row_number, row_data in enumerate(
        action_status_rows,
        start=17,
    ):
        write_row(
            dashboard,
            row_number,
            row_data,
            start_col=4,
        )

    action_chart = BarChart()

    action_chart.type = "bar"
    action_chart.style = 10
    action_chart.title = "Action Status"
    action_chart.y_axis.title = "Status"
    action_chart.x_axis.title = "Count"
    action_chart.height = 8
    action_chart.width = 13

    action_chart.add_data(
        Reference(
            dashboard,
            min_col=5,
            min_row=16,
            max_row=22,
        ),
        titles_from_data=True,
    )

    action_chart.set_categories(
        Reference(
            dashboard,
            min_col=4,
            min_row=17,
            max_row=22,
        )
    )

    dashboard.add_chart(
        action_chart,
        "G19",
    )

    # Risk interpretation
    dashboard["A15"] = "Risk Interpretation"
    dashboard["A15"].fill = title_fill
    dashboard["A15"].font = Font(
        bold=True,
        color=WHITE,
    )

    interpretations = [
        "Risk score is calculated as Likelihood × Severity.",
        "Initial risk is assessed before additional controls.",
        "Residual risk is assessed after agreed controls.",
        "Risk bands must follow approved company criteria.",
        "All technical ratings require review by the study team.",
    ]

    for row_number, text_value in enumerate(
        interpretations,
        start=16,
    ):
        dashboard.merge_cells(
            start_row=row_number,
            start_column=1,
            end_row=row_number,
            end_column=2,
        )

        dashboard.cell(
            row_number,
            1,
            f"• {text_value}",
        )

    style_data(
        dashboard,
        6,
        max(dashboard.max_row, 6),
        1,
        5,
    )

    set_widths(
        dashboard,
        {
            "A": 42,
            "B": 18,
            "C": 5,
            "D": 30,
            "E": 18,
            "F": 5,
            "G": 18,
            "H": 18,
            "I": 18,
            "J": 18,
        },
    )

    dashboard.freeze_panes = "A5"

    # =========================================================
    # 6. GUIDE WORDS
    # =========================================================

    guide = wb.create_sheet("Guide Words")

    style_title(
        guide,
        "HAZOP GUIDE WORDS",
        (
            "Guide words are prompts for systematic "
            "deviation identification. Use combinations "
            "relevant to the node and design intent."
        ),
        4,
    )

    guide_headers = [
        "Guide Word",
        "Meaning / Prompt",
        "Example Parameter",
        "Example Deviation",
    ]

    write_row(
        guide,
        5,
        guide_headers,
    )

    style_headers(
        guide,
        5,
        1,
        4,
    )

    guide_words = [
        ("NO / NOT", "Complete negation of design intent", "Flow", "No flow"),
        ("MORE", "Quantitative increase", "Pressure", "More pressure"),
        ("LESS", "Quantitative decrease", "Flow", "Less flow"),
        ("AS WELL AS", "Additional condition or material present", "Composition", "Solvent plus water"),
        ("PART OF", "Only part of intended material or function", "Composition", "Wrong concentration"),
        ("REVERSE", "Opposite direction or sequence", "Flow", "Reverse flow"),
        ("OTHER THAN", "Substitution or different material/action", "Material", "Wrong chemical"),
        ("EARLY", "Occurs earlier than intended", "Timing", "Valve opens early"),
        ("LATE", "Occurs later than intended", "Timing", "Alarm occurs late"),
        ("BEFORE", "Step occurs before intended sequence", "Sequence", "Pump starts before line-up"),
        ("AFTER", "Step occurs after intended sequence", "Sequence", "Isolation occurs after transfer"),
    ]

    for row_number, row_data in enumerate(
        guide_words,
        start=6,
    ):
        write_row(
            guide,
            row_number,
            row_data,
        )

    style_data(
        guide,
        6,
        5 + len(guide_words),
        1,
        4,
    )

    guide.freeze_panes = "A6"

    guide.auto_filter.ref = (
        f"A5:D{5 + len(guide_words)}"
    )

    set_widths(
        guide,
        {
            "A": 24,
            "B": 45,
            "C": 25,
            "D": 40,
        },
    )

    # =========================================================
    # FINAL FORMATTING
    # =========================================================

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False

        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cell.alignment = Alignment(
                        vertical="top",
                        wrap_text=True,
                    )

    # =========================================================
    # RETURN EXCEL FILE
    # =========================================================

    output = BytesIO()

    wb.save(output)
    output.seek(0)

    filename = (
        "HAZOP_Company_Style_Report_"
        f"{generated_at.strftime('%Y%m%d_%H%M')}.xlsx"
    )

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    return response