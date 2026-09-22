# apps/ergonomics/ergonomic_pdf_generators.py

import os
import logging
import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from apps.contractor.pdf_generators import (
    NumberedCanvas,
    _header_table,
    _make_draw_header,
    _footer_paragraph,
    _safe_file_path,
    _embed_image,
)

logger = logging.getLogger(__name__)

BORDER_COLOR = colors.HexColor("#DEE2E6")
HEADER_BG_COLOR = colors.HexColor("#F8F9FA")


# =============================================================================
# STYLES
# =============================================================================
def _get_styles():
    styles = getSampleStyleSheet()
    primary = colors.HexColor("#212529")
    secondary = colors.HexColor("#495057")

    styles.add(ParagraphStyle(
        name="HeaderTitle", fontSize=10, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=primary,
    ))
    styles.add(ParagraphStyle(
        name="HeaderInfo", fontSize=9, fontName="Helvetica",
        alignment=TA_LEFT, textColor=secondary, leading=12,
    ))
    styles.add(ParagraphStyle(
        name="FooterText", fontSize=8, fontName="Helvetica",
        textColor=colors.darkgrey, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=11, fontName="Helvetica-Bold",
        alignment=TA_LEFT, textColor=primary, spaceBefore=6,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader", fontSize=10, fontName="Helvetica-Bold",
        textColor=primary, spaceBefore=10, spaceAfter=4, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="SubHeader", fontSize=9, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0d9488"), spaceBefore=6, spaceAfter=3,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="Label", fontSize=9, fontName="Helvetica-Bold",
        textColor=primary, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="Value", fontSize=9, fontName="Helvetica",
        textColor=secondary, alignment=TA_LEFT, leading=12,
    ))
    styles.add(ParagraphStyle(
        name="Small", fontSize=7.5, fontName="Helvetica",
        textColor=colors.HexColor("#334155"), leading=9,
    ))

    styles.add(ParagraphStyle(name="ErgoHeaderTitle", parent=styles["HeaderTitle"]))
    styles.add(ParagraphStyle(name="ErgoHeaderInfo", parent=styles["HeaderInfo"]))
    styles.add(ParagraphStyle(name="ErgoSectionHeader", parent=styles["SectionHeader"]))
    styles.add(ParagraphStyle(name="ErgoSubHeader", parent=styles["SubHeader"]))
    styles.add(ParagraphStyle(name="ErgoLabel", parent=styles["Label"]))
    styles.add(ParagraphStyle(name="ErgoValue", parent=styles["Value"]))
    styles.add(ParagraphStyle(name="ErgoFooterText", parent=styles["FooterText"]))
    styles.add(ParagraphStyle(name="ErgoSmall", parent=styles["Small"]))
    return styles


# =============================================================================
# VALUE NORMALIZER
# =============================================================================
def get_val(value, default="N/A"):
    if value is None:
        return default

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, Decimal):
        try:
            if value == value.to_integral_value():
                return str(int(value))
            return format(value.normalize(), "f")
        except (InvalidOperation, ValueError):
            return str(value)

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        s = value.replace("\n", "<br/>").strip()
        return s if s else default

    if hasattr(value, "strftime"):
        try:
            if hasattr(value, "hour"):
                return value.strftime("%d-%m-%Y %H:%M")
            return value.strftime("%d-%m-%Y")
        except Exception:
            return str(value)

    if isinstance(value, (list, tuple)):
        parts = [get_val(v, default="") for v in value]
        return ", ".join(p for p in parts if p) or default

    if isinstance(value, dict):
        parts = [f"{k}: {get_val(v, default='')}" for k, v in value.items()]
        return "; ".join(parts) or default

    try:
        s = str(value).replace("\n", "<br/>").strip()
        return s or default
    except Exception:
        return default


def _safe(text):
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    return get_val(text, default="")


def _fmt_dt(dt, fmt="%d-%m-%Y %H:%M"):
    if not dt:
        return "—"
    try:
        return dt.strftime(fmt)
    except Exception:
        return str(dt)


def _fmt_d(d):
    if not d:
        return "—"
    try:
        return d.strftime("%d-%m-%Y")
    except Exception:
        return str(d)


def _user(u):
    if not u:
        return "—"
    try:
        return u.get_full_name() or u.username or u.email or "—"
    except Exception:
        return str(u)


def _role_of(user):
    if not user:
        return "—"
    role = getattr(user, "role", None)
    return getattr(role, "name", "—") if role else "—"


# =============================================================================
# TABLE HELPERS
# =============================================================================
_STYLES_REF = {"styles": None}


def _kv_table(rows, col_widths):
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), HEADER_BG_COLOR),
        ("BACKGROUND", (2, 0), (2, -1), HEADER_BG_COLOR),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _data_table(header_row, data_rows, col_widths, small=False):
    styles = _STYLES_REF["styles"]
    style_name = "ErgoSmall" if small else "ErgoValue"

    rows = [[Paragraph(f"<b>{_safe(h)}</b>", styles[style_name]) for h in header_row]]
    for r in data_rows:
        rows.append([Paragraph(_safe(c), styles[style_name]) for c in r])

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def generate_ergonomic_report_pdf(assessments, request=None):
    """Full-detail Ergonomic PDF report (per-assessment deep-dive)."""
    buffer = BytesIO()
    styles = _get_styles()
    _STYLES_REF["styles"] = styles

    from .models import (
        MSDDiscomfort,
        ErgonomicCorrectiveAction,
        ErgonomicReassessment,
        ErgonomicRiskFactor,
        ErgonomicControl,
        ErgonomicObservation,
        ErgonomicAuditLog,
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=1.6 * inch + 22 * mm,
        bottomMargin=25 * mm,
    )
    drawable_width = A4[0] - 30 * mm
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no="ERG-REPORT",
        rev_info=f"REV NO: 001 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="ERGONOMIC MODULE REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    # =========================================================================
    # COVER STRIP
    # =========================================================================
    ref_data = [[
        Paragraph("<b>Ergonomic Module — Full Detailed Report</b>", styles["ErgoHeaderTitle"]),
        Paragraph(
            f"<b>Generated:</b><br/>{timezone.now().strftime('%d-%m-%Y %H:%M')}",
            styles["ErgoHeaderInfo"],
        ),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    if request:
        bits = []
        for key, label in [
            ("plant", "Site"), ("department", "Department"),
            ("area", "Area"), ("method", "Method"),
            ("risk_level", "Risk Level"), ("status", "Status"),
            ("assessor", "Assessor"),
            ("from_date", "From"), ("to_date", "To"),
        ]:
            val = request.GET.get(key)
            if val:
                bits.append(f"<b>{label}:</b> {_safe(val)}")
        if bits:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(
                "<b>Applied Filters:</b> " + " &nbsp;|&nbsp; ".join(bits),
                styles["ErgoValue"],
            ))

    # =========================================================================
    # MODULE-WIDE SUMMARY
    # =========================================================================
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>📊 MODULE SUMMARY</b>", styles["ErgoSectionHeader"]))

    actions_qs = ErgonomicCorrectiveAction.objects.filter(assessment__in=assessments)
    msd_qs = MSDDiscomfort.objects.filter(
        Q(related_assessment__in=assessments) | Q(related_assessment__isnull=True)
    )
    reassess_qs = ErgonomicReassessment.objects.filter(assessment__in=assessments)
    scores = assessments.exclude(score__isnull=True)
    avg_score = round(scores.aggregate(avg=Avg("score"))["avg"] or 0, 2)

    summary_rows = [
        [
            Paragraph("<b>Total Assessments:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(assessments.count()), styles["ErgoValue"]),
            Paragraph("<b>High Risk:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(assessments.filter(risk_level="HIGH").count()), styles["ErgoValue"]),
            Paragraph("<b>Very High Risk:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(assessments.filter(risk_level="VERY_HIGH").count()), styles["ErgoValue"]),
        ],
        [
            Paragraph("<b>Open Actions:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(actions_qs.exclude(status__in=["COMPLETED", "CLOSED"]).count()), styles["ErgoValue"]),
            Paragraph("<b>Overdue:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(actions_qs.filter(status="OVERDUE").count()), styles["ErgoValue"]),
            Paragraph("<b>Completed:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(actions_qs.filter(status__in=["COMPLETED", "CLOSED"]).count()), styles["ErgoValue"]),
        ],
        [
            Paragraph("<b>MSD Cases:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(msd_qs.count()), styles["ErgoValue"]),
            Paragraph("<b>Avg Risk Score:</b>", styles["ErgoLabel"]),
            Paragraph(_safe(avg_score), styles["ErgoValue"]),
            Paragraph("<b>Risk Reduction:</b>", styles["ErgoLabel"]),
            Paragraph(
                _safe(f"{round(reassess_qs.aggregate(avg=Avg('risk_reduction_percent'))['avg'] or 0, 2)}%"),
                styles["ErgoValue"],
            ),
        ],
    ]
    story.append(_kv_table(summary_rows, [drawable_width / 6] * 6))

    # =========================================================================
    # PER-ASSESSMENT DEEP-DIVE
    # =========================================================================
    total_assessments = assessments.count()
    for idx, assessment in enumerate(assessments, 1):
        story.append(PageBreak())

        header_banner = Table(
            [[
                Paragraph(
                    f"<b>ASSESSMENT {idx} OF {total_assessments}</b>",
                    styles["ErgoHeaderTitle"],
                ),
                Paragraph(
                    f"<b>ID:</b> {_safe(getattr(assessment, 'assessment_id', ''))}",
                    styles["ErgoHeaderInfo"],
                ),
            ]],
            colWidths=[drawable_width * 0.6, drawable_width * 0.4],
        )
        header_banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG_COLOR),
            ("BOX", (0, 0), (-1, -1), 1.2, BORDER_COLOR),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(header_banner)
        story.append(Spacer(1, 3 * mm))

        # ---------------------------------------------------------------
        # A. BASIC DETAILS
        # ---------------------------------------------------------------
        story.append(Paragraph("<b>A. Basic Details</b>", styles["ErgoSubHeader"]))

        basic_rows = [
            [Paragraph("<b>Assessment ID:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "assessment_id", "")), styles["ErgoValue"]),
             Paragraph("<b>Status:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(assessment.get_status_display() if hasattr(assessment, "get_status_display") else getattr(assessment, "status", "")), styles["ErgoValue"])],

            [Paragraph("<b>Site:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(getattr(assessment, "plant", None), "name", "")), styles["ErgoValue"]),
             Paragraph("<b>Department:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(getattr(assessment, "department", None), "name", "")), styles["ErgoValue"])],

            [Paragraph("<b>Area:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "area", "")), styles["ErgoValue"]),
             Paragraph("<b>Shift:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "shift", "")), styles["ErgoValue"])],

            [Paragraph("<b>Job Role:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "job_role", "")), styles["ErgoValue"]),
             Paragraph("<b>Task:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "task", "")), styles["ErgoValue"])],

            [Paragraph("<b>Worker:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(_user(getattr(assessment, "worker", None))), styles["ErgoValue"]),
             Paragraph("<b>Assessor:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(_user(getattr(assessment, "assessor", None))), styles["ErgoValue"])],

            [Paragraph("<b>Assessment Method:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(getattr(assessment, "assessment_method", None), "name", "")), styles["ErgoValue"]),
             Paragraph("<b>Assessment Date:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(_fmt_d(getattr(assessment, "assessment_date", None))), styles["ErgoValue"])],

            [Paragraph("<b>Score:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "score", None)), styles["ErgoValue"]),
             Paragraph("<b>Risk Level:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(assessment.get_risk_level_display() if hasattr(assessment, "get_risk_level_display") else getattr(assessment, "risk_level", "")), styles["ErgoValue"])],

            [Paragraph("<b>Action Level:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "action_level", "")), styles["ErgoValue"]),
             Paragraph("<b>Recommended Action:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "recommended_action", "")), styles["ErgoValue"])],

            [Paragraph("<b>Task Duration:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "task_duration", "")), styles["ErgoValue"]),
             Paragraph("<b>Frequency:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "frequency", "")), styles["ErgoValue"])],

            [Paragraph("<b>Exposure Duration:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "exposure_duration", "")), styles["ErgoValue"]),
             Paragraph("<b>Workers Exposed:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "workers_exposed", "")), styles["ErgoValue"])],

            [Paragraph("<b>Next Assessment:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(_fmt_d(getattr(assessment, "next_assessment_date", None))), styles["ErgoValue"]),
             Paragraph("<b>Assessment Type:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(getattr(assessment, "assessment_type", "")), styles["ErgoValue"])],

            [Paragraph("<b>Created By:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(f"{_user(getattr(assessment, 'created_by', None))} ({_role_of(getattr(assessment, 'created_by', None))})"), styles["ErgoValue"]),
             Paragraph("<b>Created At:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(_fmt_dt(getattr(assessment, "created_at", None))), styles["ErgoValue"])],

            [Paragraph("<b>Updated By:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(f"{_user(getattr(assessment, 'updated_by', None))} ({_role_of(getattr(assessment, 'updated_by', None))})"), styles["ErgoValue"]),
             Paragraph("<b>Updated At:</b>", styles["ErgoLabel"]),
             Paragraph(_safe(_fmt_dt(getattr(assessment, "updated_at", None))), styles["ErgoValue"])],
        ]
        story.append(_kv_table(basic_rows, [col4] * 4))

        if getattr(assessment, "task_description", ""):
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph("<b>Task Description</b>", styles["ErgoSubHeader"]))
            story.append(Table(
                [[Paragraph(_safe(assessment.task_description), styles["ErgoValue"])]],
                colWidths=[drawable_width],
                style=TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]),
            ))

        # ---------------------------------------------------------------
        # B. RISK FACTORS
        # ---------------------------------------------------------------
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>B. Risk Factors</b>", styles["ErgoSubHeader"]))

        risk_factor = getattr(assessment, "risk_factors", None)

        if risk_factor is None:
            story.append(Paragraph(
                "No risk-factor record exists for this assessment.",
                styles["ErgoValue"],
            ))
        else:
            try:
                rf_items = []
                field_map = [
                    ("awkward_posture",   "Awkward Posture"),
                    ("repetitive_motion", "Repetitive Motion"),
                    ("forceful_exertion", "Forceful Exertion"),
                    ("static_posture",    "Static Posture"),
                    ("vibration",         "Vibration"),
                    ("contact_stress",    "Contact Stress"),
                    ("manual_handling",   "Manual Handling"),
                    ("environmental",     "Environmental"),
                ]
                for field_name, label in field_map:
                    if hasattr(risk_factor, field_name):
                        val = getattr(risk_factor, field_name)
                        if val not in (None, "", False):
                            rf_items.append((label, _safe(val)))

                for f in risk_factor._meta.get_fields():
                    fname = getattr(f, "name", None)
                    if not fname or fname in ("id", "assessment") or fname in dict(field_map):
                        continue
                    if not getattr(f, "concrete", False):
                        continue
                    val = getattr(risk_factor, fname, None)
                    if val not in (None, "", False):
                        rf_items.append((fname.replace("_", " ").title(), _safe(val)))

                if rf_items:
                    story.append(_data_table(
                        ["Risk Factor", "Present / Level"],
                        rf_items,
                        [drawable_width * 0.5, drawable_width * 0.5],
                    ))
                else:
                    story.append(Paragraph(
                        "Risk-factor record exists but no factors are populated.",
                        styles["ErgoValue"],
                    ))

            except Exception as exc:
                logger.exception(
                    "Ergonomic PDF: risk_factor render failed for assessment %s",
                    getattr(assessment, "assessment_id", assessment.pk),
                )
                story.append(Paragraph(
                    f"Risk factor render error: {_safe(exc)}",
                    styles["ErgoValue"],
                ))

        # ---------------------------------------------------------------
        # C. METHOD-SPECIFIC SCORING
        # ---------------------------------------------------------------
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>C. Method-Specific Scoring</b>", styles["ErgoSubHeader"]))

        method_rows = []

        rula = getattr(assessment, "rula", None)
        if rula is not None:
            try:
                method_rows.append(("RULA", [
                    ("Upper Arm Score",   getattr(rula, "upper_arm_score", None)),
                    ("Lower Arm Score",   getattr(rula, "lower_arm_score", None)),
                    ("Wrist Score",       getattr(rula, "wrist_score", None)),
                    ("Wrist Twist",       getattr(rula, "wrist_twist", None)),
                    ("Neck Score",        getattr(rula, "neck_score", None)),
                    ("Trunk Score",       getattr(rula, "trunk_score", None)),
                    ("Legs Score",        getattr(rula, "legs_score", None)),
                    ("Muscle Use Score",  getattr(rula, "muscle_use_score", None)),
                    ("Force/Load Score",  getattr(rula, "force_load_score", None)),
                    ("Final RULA Score",  getattr(rula, "final_score", getattr(rula, "final_rula_score", None))),
                    ("Action Level",      getattr(rula, "action_level", None)),
                ]))
            except Exception:
                logger.exception("RULA render failed for %s", assessment.pk)

        reba = getattr(assessment, "reba", None)
        if reba is not None:
            try:
                method_rows.append(("REBA", [
                    ("Trunk Score",      getattr(reba, "trunk_score", None)),
                    ("Neck Score",       getattr(reba, "neck_score", None)),
                    ("Legs Score",       getattr(reba, "legs_score", None)),
                    ("Upper Arm Score",  getattr(reba, "upper_arm_score", None)),
                    ("Lower Arm Score",  getattr(reba, "lower_arm_score", None)),
                    ("Wrist Score",      getattr(reba, "wrist_score", None)),
                    ("Load Score",       getattr(reba, "load_score", None)),
                    ("Coupling Score",   getattr(reba, "coupling_score", None)),
                    ("Activity Score",   getattr(reba, "activity_score", None)),
                    ("Final REBA Score", getattr(reba, "final_score", getattr(reba, "final_reba_score", None))),
                    ("Risk Level",       getattr(reba, "risk_level", None)),
                ]))
            except Exception:
                logger.exception("REBA render failed for %s", assessment.pk)

        niosh = getattr(assessment, "niosh", None)
        if niosh is not None:
            try:
                method_rows.append(("NIOSH Lifting", [
                    ("Load Weight (kg)",         getattr(niosh, "load_weight", None)),
                    ("Horizontal Location (cm)", getattr(niosh, "horizontal_location", None)),
                    ("Vertical Location (cm)",   getattr(niosh, "vertical_location", None)),
                    ("Vertical Travel (cm)",     getattr(niosh, "vertical_travel_distance", None)),
                    ("Frequency (lifts/min)",    getattr(niosh, "frequency_lifts_per_minute", None)),
                    ("Duration (hrs)",           getattr(niosh, "duration_hours", None)),
                    ("RWL",                      getattr(niosh, "recommended_weight_limit", getattr(niosh, "rwl", None))),
                    ("Lifting Index",            getattr(niosh, "lifting_index", None)),
                ]))
            except Exception:
                logger.exception("NIOSH render failed for %s", assessment.pk)

        owas = getattr(assessment, "owas", None)
        if owas is not None:
            try:
                method_rows.append(("OWAS", [
                    ("Back Posture",    getattr(owas, "back_posture", None)),
                    ("Arms Posture",    getattr(owas, "arms_posture", None)),
                    ("Legs Posture",    getattr(owas, "legs_posture", None)),
                    ("Load/Force",      getattr(owas, "load_force", None)),
                    ("OWAS Code",       getattr(owas, "owas_code", None)),
                    ("Action Category", getattr(owas, "action_category", None)),
                ]))
            except Exception:
                logger.exception("OWAS render failed for %s", assessment.pk)

        ocra = getattr(assessment, "ocra", None)
        if ocra is not None:
            try:
                method_rows.append(("OCRA", [
                    ("Frequency (actions/min)", getattr(ocra, "frequency", None)),
                    ("Force Score",             getattr(ocra, "force_score", None)),
                    ("Posture Score",           getattr(ocra, "posture_score", None)),
                    ("Recovery Score",          getattr(ocra, "recovery_score", None)),
                    ("Duration Score",          getattr(ocra, "duration_score", None)),
                    ("OCRA Index",              getattr(ocra, "ocra_index", None)),
                    ("Risk Level",              getattr(ocra, "risk_level", None)),
                ]))
            except Exception:
                logger.exception("OCRA render failed for %s", assessment.pk)

        si = getattr(assessment, "strain_index", None)
        if si is not None:
            try:
                method_rows.append(("Strain Index", [
                    ("Intensity of Exertion", getattr(si, "intensity_of_exertion", None)),
                    ("Duration of Exertion",  getattr(si, "duration_of_exertion", None)),
                    ("Efforts per Minute",    getattr(si, "efforts_per_minute", None)),
                    ("Hand/Wrist Posture",    getattr(si, "hand_wrist_posture", None)),
                    ("Speed of Work",         getattr(si, "speed_of_work", None)),
                    ("Duration per Day",      getattr(si, "duration_per_day", None)),
                    ("Strain Index Score",    getattr(si, "strain_index_score", None)),
                    ("Risk Level",            getattr(si, "risk_level", None)),
                ]))
            except Exception:
                logger.exception("Strain Index render failed for %s", assessment.pk)

        snook = getattr(assessment, "snook_ciriello", None)
        if snook is not None:
            try:
                method_rows.append(("Snook & Ciriello", [
                    ("Actual Load (kg)",     getattr(snook, "actual_load", None)),
                    ("Task Type",            getattr(snook, "task_type", None)),
                    ("Gender",               getattr(snook, "gender", None)),
                    ("Position",             getattr(snook, "position", None)),
                    ("Percentile",           getattr(snook, "percentile", None)),
                    ("Recommended Weight",   getattr(snook, "recommended_weight", None)),
                ]))
            except Exception:
                logger.exception("Snook render failed for %s", assessment.pk)

        if method_rows:
            for method_name, rows in method_rows:
                story.append(Paragraph(f"<b>{method_name}</b>", styles["ErgoLabel"]))
                story.append(Spacer(1, 1.5 * mm))
                story.append(_data_table(
                    ["Field", "Value"],
                    [(label, _safe(val)) for label, val in rows],
                    [drawable_width * 0.6, drawable_width * 0.4],
                ))
                story.append(Spacer(1, 2 * mm))
        else:
            method_name_display = _safe(
                getattr(getattr(assessment, "assessment_method", None), "name", "")
            )
            if method_name_display:
                story.append(Paragraph(
                    f"No detailed scoring row exists yet for this assessment "
                    f"(method: <b>{method_name_display}</b>). "
                    "Enter the method score in the assessment detail page.",
                    styles["ErgoValue"],
                ))
            else:
                story.append(Paragraph(
                    "No method-specific scoring recorded.",
                    styles["ErgoValue"],
                ))

        # ---------------------------------------------------------------
        # D. OBSERVATIONS
        # ---------------------------------------------------------------
        obs_qs = assessment.source_observations.all().order_by("-observation_date")
        if obs_qs.exists():
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("<b>D. Observations</b>", styles["ErgoSubHeader"]))
            obs_rows = []
            for o in obs_qs:
                obs_rows.append([
                    _fmt_d(getattr(o, "observation_date", None)),
                    _safe(getattr(o, "task", "")),
                    _safe(getattr(o, "observation", ""))[:80],
                    _safe(getattr(o, "risk_level", "")),
                    _user(getattr(o, "observer", None)),
                ])
            story.append(_data_table(
                ["Date", "Task", "Observation", "Risk", "Observer"],
                obs_rows,
                [drawable_width * 0.12, drawable_width * 0.20,
                 drawable_width * 0.36, drawable_width * 0.12, drawable_width * 0.20],
                small=True,
            ))

        # ---------------------------------------------------------------
        # E. CORRECTIVE ACTIONS (full traceability)
        # ---------------------------------------------------------------
        ca_qs = (
            assessment.corrective_actions
            .select_related("responsible_person", "created_by", "verified_by", "rejected_by", "department")
            .order_by("-created_at")
        )
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>E. Corrective Actions</b>", styles["ErgoSubHeader"]))

        if ca_qs.exists():
            for ca_idx, ca in enumerate(ca_qs, 1):
                story.append(Paragraph(
                    f"<b>Action {ca_idx}: {_safe(getattr(ca, 'action_id', ''))}</b>",
                    styles["ErgoLabel"],
                ))
                story.append(Spacer(1, 1.5 * mm))

                # Row 1: Description + Root Cause
                story.append(_kv_table([
                    [Paragraph("<b>Action Description:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(getattr(ca, "action_description", "")), styles["ErgoValue"]),
                     Paragraph("<b>Root Cause:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(getattr(ca, "root_cause", "")), styles["ErgoValue"])],
                ], [col4] * 4))

                # Row 2: Control Type + Priority
                story.append(Spacer(1, 1.5 * mm))
                story.append(_kv_table([
                    [Paragraph("<b>Control Type:</b>", styles["ErgoLabel"]),
                     Paragraph(
                         _safe(ca.get_control_type_display() if hasattr(ca, "get_control_type_display") else getattr(ca, "control_type", "")),
                         styles["ErgoValue"],
                     ),
                     Paragraph("<b>Priority:</b>", styles["ErgoLabel"]),
                     Paragraph(
                         _safe(ca.get_priority_display() if hasattr(ca, "get_priority_display") else getattr(ca, "priority", "")),
                         styles["ErgoValue"],
                     )],
                ], [col4] * 4))

                # Row 3: Status + Target Date
                story.append(Spacer(1, 1.5 * mm))
                story.append(_kv_table([
                    [Paragraph("<b>Status:</b>", styles["ErgoLabel"]),
                     Paragraph(
                         _safe(ca.get_status_display() if hasattr(ca, "get_status_display") else getattr(ca, "status", "")),
                         styles["ErgoValue"],
                     ),
                     Paragraph("<b>Target Date:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(_fmt_d(getattr(ca, "target_date", None))), styles["ErgoValue"])],
                ], [col4] * 4))

                # Row 4: Responsible + Department + Completion Date
                story.append(Spacer(1, 1.5 * mm))
                story.append(_kv_table([
                    [Paragraph("<b>Responsible Person:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(_user(getattr(ca, "responsible_person", None))), styles["ErgoValue"]),
                     Paragraph("<b>Responsible Role:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(_role_of(getattr(ca, "responsible_person", None))), styles["ErgoValue"])],

                    [Paragraph("<b>Department:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(getattr(getattr(ca, "department", None), "name", "")), styles["ErgoValue"]),
                     Paragraph("<b>Completion Date:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(_fmt_d(getattr(ca, "completion_date", None))), styles["ErgoValue"])],

                    [Paragraph("<b>Created By:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(f"{_user(getattr(ca, 'created_by', None))} ({_role_of(getattr(ca, 'created_by', None))})"), styles["ErgoValue"]),
                     Paragraph("<b>Created At:</b>", styles["ErgoLabel"]),
                     Paragraph(_safe(_fmt_dt(getattr(ca, "created_at", None))), styles["ErgoValue"])],
                ], [col4] * 4))

                # Remarks
                remarks = getattr(ca, "remarks", "")
                if remarks:
                    story.append(Spacer(1, 1.5 * mm))
                    story.append(Paragraph(
                        f"<b>Remarks:</b> {_safe(remarks)}",
                        styles["ErgoValue"],
                    ))

                # Evidence
                evidence_file = getattr(ca, "evidence", None)
                if evidence_file:
                    story.append(Spacer(1, 1.5 * mm))
                    story.append(Paragraph("<b>Evidence Uploaded</b>", styles["ErgoLabel"]))
                    ev_path = _safe_file_path(evidence_file)
                    if ev_path:
                        _embed_image(story, ev_path, styles["ErgoValue"],
                                     max_width_mm=80, max_height_mm=60,
                                     caption="Evidence")
                    else:
                        name = getattr(evidence_file, "name", "")
                        story.append(Paragraph(
                            f"<i>Evidence attached ({_safe(name)}) — not previewable inline.</i>",
                            styles["ErgoValue"],
                        ))

                # Verification
                if getattr(ca, "verified_by", None) or getattr(ca, "verification_date", None):
                    story.append(Spacer(1, 1.5 * mm))
                    ver_rows = [
                        [Paragraph("<b>Verified By:</b>", styles["ErgoLabel"]),
                         Paragraph(_safe(f"{_user(getattr(ca, 'verified_by', None))} ({_role_of(getattr(ca, 'verified_by', None))})"), styles["ErgoValue"]),
                         Paragraph("<b>Verification Date:</b>", styles["ErgoLabel"]),
                         Paragraph(_safe(_fmt_dt(getattr(ca, "verification_date", None))), styles["ErgoValue"])],
                    ]
                    if getattr(ca, "verification", ""):
                        ver_rows.append([
                            Paragraph("<b>Verification Remark:</b>", styles["ErgoLabel"]),
                            Paragraph(_safe(ca.verification), styles["ErgoValue"]),
                            Paragraph("", styles["ErgoValue"]),
                            Paragraph("", styles["ErgoValue"]),
                        ])
                    story.append(_kv_table(ver_rows, [col4] * 4))

                # Rejection
                if getattr(ca, "rejected_by", None) or getattr(ca, "rejection_remark", ""):
                    story.append(Spacer(1, 1.5 * mm))
                    rej_rows = [
                        [Paragraph("<b>Rejected By:</b>", styles["ErgoLabel"]),
                         Paragraph(_safe(f"{_user(getattr(ca, 'rejected_by', None))} ({_role_of(getattr(ca, 'rejected_by', None))})"), styles["ErgoValue"]),
                         Paragraph("<b>Rejected At:</b>", styles["ErgoLabel"]),
                         Paragraph(_safe(_fmt_dt(getattr(ca, "rejected_at", None))), styles["ErgoValue"])],
                        [Paragraph("<b>Rejection Remark:</b>", styles["ErgoLabel"]),
                         Paragraph(_safe(getattr(ca, "rejection_remark", "")), styles["ErgoValue"]),
                         Paragraph("", styles["ErgoValue"]),
                         Paragraph("", styles["ErgoValue"])],
                    ]
                    story.append(_kv_table(rej_rows, [col4] * 4))

                story.append(Spacer(1, 3 * mm))
        else:
            story.append(Paragraph("No corrective actions recorded.", styles["ErgoValue"]))

        # ---------------------------------------------------------------
        # F. REASSESSMENTS
        # ---------------------------------------------------------------
        ra_qs = assessment.reassessments.all().order_by("-reassessment_date")
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>F. Reassessments</b>", styles["ErgoSubHeader"]))

        if ra_qs.exists():
            ra_rows = []
            for r in ra_qs:
                ra_rows.append([
                    _fmt_d(getattr(r, "reassessment_date", None)),
                    _safe(getattr(r, "previous_score", "")),
                    _safe(getattr(r, "new_score", "")),
                    _safe(f"{get_val(getattr(r, 'risk_reduction_percent', ''))}%"),
                    _safe(r.get_control_effectiveness_display() if hasattr(r, "get_control_effectiveness_display") else getattr(r, "control_effectiveness", "")),
                    _user(getattr(r, "assessor", None)),
                ])
            story.append(_data_table(
                ["Date", "Before", "After", "Reduction", "Effectiveness", "Assessor"],
                ra_rows,
                [drawable_width * 0.13, drawable_width * 0.10, drawable_width * 0.10,
                 drawable_width * 0.12, drawable_width * 0.25, drawable_width * 0.30],
                small=True,
            ))
        else:
            story.append(Paragraph("No reassessments recorded.", styles["ErgoValue"]))

        # ---------------------------------------------------------------
        # G. MSD / DISCOMFORT RECORDS
        # ---------------------------------------------------------------
        msd_assessment_qs = assessment.msd_cases.all().order_by("-date_reported")
        if msd_assessment_qs.exists():
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("<b>G. MSD / Discomfort Records</b>", styles["ErgoSubHeader"]))
            msd_rows = []
            for m in msd_assessment_qs:
                msd_rows.append([
                    _fmt_d(getattr(m, "date_reported", None)),
                    _user(getattr(m, "worker", None)),
                    _safe(getattr(m, "body_part", "")),
                    _safe(getattr(m, "severity", "")),
                    _safe(getattr(m, "description", ""))[:80],
                ])
            story.append(_data_table(
                ["Date", "Worker", "Body Part", "Severity", "Description"],
                msd_rows,
                [drawable_width * 0.12, drawable_width * 0.20, drawable_width * 0.15,
                 drawable_width * 0.13, drawable_width * 0.40],
                small=True,
            ))

        story.append(Spacer(1, 5 * mm))

    # =========================================================================
    # MODULE-WIDE ROLL-UP
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("<b>MODULE ROLL-UP</b>", styles["ErgoSectionHeader"]))

    story.append(Paragraph("<b>Risk Level Distribution</b>", styles["ErgoSubHeader"]))
    risk_dist = assessments.values("risk_level").annotate(total=Count("id")).order_by("-total")
    rd_rows = [(_safe(r["risk_level"] or "Unscored"), r["total"]) for r in risk_dist]
    story.append(_data_table(["Risk Level", "Count"], rd_rows, [drawable_width * 0.5, drawable_width * 0.5]))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Assessments by Department</b>", styles["ErgoSubHeader"]))
    dept_dist = assessments.values("department__name").annotate(total=Count("id")).order_by("-total")[:15]
    story.append(_data_table(
        ["Department", "Count"],
        [(_safe(d["department__name"] or "Unassigned"), d["total"]) for d in dept_dist],
        [drawable_width * 0.7, drawable_width * 0.3],
    ))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Assessments by Site</b>", styles["ErgoSubHeader"]))
    site_dist = assessments.values("plant__name").annotate(total=Count("id")).order_by("-total")
    story.append(_data_table(
        ["Site", "Count"],
        [(_safe(s["plant__name"]), s["total"]) for s in site_dist],
        [drawable_width * 0.7, drawable_width * 0.3],
    ))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Assessment Method Usage</b>", styles["ErgoSubHeader"]))
    method_usage = assessments.values("assessment_method__name").annotate(total=Count("id")).order_by("-total")
    story.append(_data_table(
        ["Method", "Assessments"],
        [(_safe(m["assessment_method__name"]), m["total"]) for m in method_usage],
        [drawable_width * 0.7, drawable_width * 0.3],
    ))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Corrective Action Status (Module-wide)</b>", styles["ErgoSubHeader"]))
    action_status = actions_qs.values("status").annotate(total=Count("id")).order_by("-total")
    story.append(_data_table(
        ["Status", "Count"],
        [(_safe(a["status"]), a["total"]) for a in action_status],
        [drawable_width * 0.7, drawable_width * 0.3],
    ))

    overdue = actions_qs.filter(status="OVERDUE").select_related("assessment", "responsible_person")[:20]
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Overdue Actions</b>", styles["ErgoSubHeader"]))
    if overdue.exists():
        od_rows = [[
            _safe(a.action_id),
            _safe(getattr(a.assessment, "assessment_id", "")),
            _fmt_d(getattr(a, "target_date", None)),
            _user(getattr(a, "responsible_person", None)),
        ] for a in overdue]
        story.append(_data_table(
            ["Action ID", "Assessment", "Target", "Responsible"],
            od_rows,
            [drawable_width * 0.2, drawable_width * 0.25,
             drawable_width * 0.2, drawable_width * 0.35],
            small=True,
        ))
    else:
        story.append(Paragraph("No overdue actions.", styles["ErgoValue"]))

    # =========================================================================
    # SIGNATURE BLOCK
    # =========================================================================
    story.append(Spacer(1, 15 * mm))
    sig_data = [
        [Paragraph("<b>Prepared By</b>", styles["ErgoLabel"]),
         Paragraph("<b>Reviewed By</b>", styles["ErgoLabel"]),
         Paragraph("<b>Approved By</b>", styles["ErgoLabel"])],
        [Paragraph("", styles["ErgoValue"]), Paragraph("", styles["ErgoValue"]), Paragraph("", styles["ErgoValue"])],
        [Paragraph("_________________", styles["ErgoValue"]),
         Paragraph("_________________", styles["ErgoValue"]),
         Paragraph("_________________", styles["ErgoValue"])],
        [Paragraph("EHS Coordinator", styles["ErgoValue"]),
         Paragraph("Lead Safety Engineer", styles["ErgoValue"]),
         Paragraph("Safety Manager", styles["ErgoValue"])],
    ]
    sig_table = Table(sig_data, colWidths=[col4 * 1.33] * 3)
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, 1), 30),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(
        story,
        onFirstPage=draw_header,
        onLaterPages=draw_header,
        canvasmaker=NumberedCanvas,
    )

    pdf = buffer.getvalue()
    buffer.close()
    return pdf