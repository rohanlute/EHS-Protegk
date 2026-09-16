# apps/training/report_spec.py
"""
Training Register + HIRA — full real-data workbook.

Sheets:
  1. Training Dashboard        (compliance + risk KPIs)
  2. Training Register          (real TrainingRecord rows)
  3. Training Actions           (real filtered rows: only records needing action)
  4. Training HIRA Register     (optional — only if TrainingHIRA model exists)
  5. Pivot — Status             (live COUNTIF from Register)
  6. Pivot — Department         (live COUNTIF from Register)
  7. Pivot — Topic              (live COUNTIF from Register)
  8. Pivot — Monthly Trend      (live COUNTIFS from Register)
  9. Pivot — Risk Level         (live COUNTIF from HIRA Register)
 10. Pivot — Hazard Category    (live COUNTIF from HIRA Register)
 11. Risk Matrix                (reference)
 12. Risk Levels                (reference)
 13. Hierarchy of Controls      (reference)
 14. Approval & Revision        (reference)
 15. Review Triggers            (reference)
 16. Industry Activity Master   (reference)
 17. Hazard Master              (reference)
"""
from datetime import date

from apps.reports.services.excel_engine import (
    ReportSpec, DashboardSheet, RegisterSheet,
    Column, KPI, Pivot, StaticTable,
)
from apps.reports.services.shared_sheets import get_master_sheets


REG = "Training Register"
ACTIONS = "Training Actions"
HIRA = "Training HIRA Register"


# ──────────────────────────────────────────────────────────────
# Helper: human-readable issue for a training record
# ──────────────────────────────────────────────────────────────
def _issue_for(record):
    if not record.valid_until:
        return "Refresher required"
    vu = record.valid_until
    if hasattr(vu, "date"):
        vu = vu.date()
    today = date.today()
    days = (vu - today).days
    if days < 0:
        return "Expired"
    if days <= 30:
        return "Expiring within 30 days"
    return "Refresher required"


# ──────────────────────────────────────────────────────────────
# Helper: live pivot sheets built from the Training Register
# ──────────────────────────────────────────────────────────────
def _live_pivot_sheets():
    """Sheets whose cells are COUNTIF/COUNTIFS formulas pointing at
    'Training Register'. They recalculate every time Excel opens."""

    # ── Status pivot ─────────────────────────────────────────
    statuses = ["Completed", "In Progress", "Not Started",
                "Expired", "Failed", "Revoked"]
    status_rows = [
        [s, f'=COUNTIF(\'{REG}\'!M2:M10000,"{s}")']
        for s in statuses
    ]
    status_rows.append(
        ["TOTAL", f"=SUM(B2:B{len(statuses) + 1})"]
    )

    # ── Department pivot ─────────────────────────────────────
    from apps.training.models import TrainingRecord
    dept_names = list(
        TrainingRecord.objects
        .exclude(employee__department__isnull=True)
        .values_list("employee__department__name", flat=True)
        .distinct()
        .order_by("employee__department__name")
    ) or ["(no data)"]

    dept_rows = [
        [d, f'=COUNTIF(\'{REG}\'!D2:D10000,"{d}")']
        for d in dept_names
    ]
    dept_rows.append(
        ["TOTAL", f"=SUM(B2:B{len(dept_rows) + 1})"]
    )

    # ── Topic pivot ──────────────────────────────────────────
    topic_names = list(
        TrainingRecord.objects
        .exclude(topic__isnull=True)
        .values_list("topic__name", flat=True)
        .distinct()
        .order_by("topic__name")
    ) or ["(no data)"]

    topic_rows = [
        [t, f'=COUNTIF(\'{REG}\'!E2:E10000,"{t}")']
        for t in topic_names
    ]
    topic_rows.append(
        ["TOTAL", f"=SUM(B2:B{len(topic_rows) + 1})"]
    )

    # ── Monthly trend (last 6 months) ────────────────────────
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(6):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()

    month_rows = [
        [
            f"{y}-{m:02d}",
            f'=COUNTIFS(\'{REG}\'!G2:G10000,">="&DATE({y},{m},1),'
            f'\'{REG}\'!G2:G10000,"<="&EOMONTH(DATE({y},{m},1),0))'
        ]
        for (y, m) in months
    ]

    return [
        StaticTable(
            name="Pivot — Status",
            headers=["Status", "Count"],
            rows=status_rows,
            widths=[24, 12],
        ),
        StaticTable(
            name="Pivot — Department",
            headers=["Department", "Count"],
            rows=dept_rows,
            widths=[30, 12],
        ),
        StaticTable(
            name="Pivot — Topic",
            headers=["Topic", "Count"],
            rows=topic_rows,
            widths=[40, 12],
        ),
        StaticTable(
            name="Pivot — Monthly Trend",
            headers=["Month (YYYY-MM)", "Completed"],
            rows=month_rows,
            widths=[20, 14],
        ),
    ]


# ──────────────────────────────────────────────────────────────
# Helper: live HIRA pivots (only meaningful if HIRA sheet exists)
# ──────────────────────────────────────────────────────────────
def _hira_pivot_sheets():
    """Pivot sheets that COUNTIF the Training HIRA Register.
    Safe to include even if the HIRA sheet is empty."""
    return [
        StaticTable(
            name="Pivot — Risk Level",
            headers=["Risk Level", "Count"],
            rows=[
                ["Critical", f'=COUNTIF(\'{HIRA}\'!K2:K5000,"Critical")'],
                ["High",     f'=COUNTIF(\'{HIRA}\'!K2:K5000,"High")'],
                ["Medium",   f'=COUNTIF(\'{HIRA}\'!K2:K5000,"Medium")'],
                ["Low",      f'=COUNTIF(\'{HIRA}\'!K2:K5000,"Low")'],
                ["TOTAL",    "=SUM(B2:B5)"],
            ],
            widths=[18, 12],
        ),
        StaticTable(
            name="Pivot — Hazard Category",
            headers=["Hazard Category", "Count"],
            rows=[
                [h, f'=COUNTIF(\'{HIRA}\'!D2:D5000,"{h}")']
                for h in [
                    "Mechanical", "Electrical", "Chemical", "Physical",
                    "Fire / Explosion", "Ergonomic", "Biological",
                    "Atmospheric", "Vehicle", "Environmental", "Structural",
                ]
            ] + [["TOTAL", "=SUM(B2:B12)"]],
            widths=[24, 12],
        ),
    ]


# ──────────────────────────────────────────────────────────────
# Helper: HIRA Register columns (works even if model missing)
# ──────────────────────────────────────────────────────────────
def _hira_columns():
    """Columns for the Training HIRA Register sheet.
    Uses getattr() so the sheet works even if the TrainingHIRA
    model fields are not yet defined — it will simply be empty."""
    return [
        Column("HIRA ID",
               lambda r: f"HIRA-TRN-{r.id:04d}" if getattr(r, "id", None) else "",
               width=14),
        Column("Activity",
               lambda r: getattr(r, "activity", ""),
               width=30),
        Column("Task / Step",
               lambda r: getattr(r, "task", ""),
               width=30),
        Column("Hazard Category",
               lambda r: getattr(r, "hazard_category", ""),
               width=20, fill_by_value=True),
        Column("Hazard Description",
               lambda r: getattr(r, "hazard", ""),
               width=40),
        Column("Who is at Risk",
               lambda r: getattr(r, "who_at_risk", ""),
               width=22),
        Column("Existing Controls",
               lambda r: getattr(r, "existing_controls", ""),
               width=40),
        Column("L (1-5)",
               lambda r: getattr(r, "likelihood", ""),
               width=8),
        Column("S (1-5)",
               lambda r: getattr(r, "severity", ""),
               width=8),
        Column("Risk Score",
               formula=lambda r, rn: f'=IF(OR(H{rn}="",I{rn}=""),"",H{rn}*I{rn})',
               width=10),
        Column("Risk Level",
               formula=lambda r, rn:
                   f'=IF(J{rn}="","",'
                   f'IF(J{rn}<=4,"Low",'
                   f'IF(J{rn}<=9,"Medium",'
                   f'IF(J{rn}<=16,"High","Critical"))))',
               width=12, fill_by_value=True),
        Column("Additional Controls",
               lambda r: getattr(r, "additional_controls", ""),
               width=40),
        Column("Residual L",
               lambda r: getattr(r, "residual_l", ""),
               width=8),
        Column("Residual S",
               lambda r: getattr(r, "residual_s", ""),
               width=8),
        Column("Residual Score",
               formula=lambda r, rn: f'=IF(OR(M{rn}="",N{rn}=""),"",M{rn}*N{rn})',
               width=10),
        Column("Residual Level",
               formula=lambda r, rn:
                   f'=IF(O{rn}="","",'
                   f'IF(O{rn}<=4,"Low",'
                   f'IF(O{rn}<=9,"Medium",'
                   f'IF(O{rn}<=16,"High","Critical"))))',
               width=14, fill_by_value=True),
        Column("Legal Reference",
               lambda r: getattr(r, "legal_reference", ""),
               width=24),
        Column("Action Required",
               lambda r: getattr(r, "action", ""),
               width=40),
        Column("Responsible",
               lambda r: getattr(r, "responsible", ""),
               width=22),
        Column("Target Date",
               lambda r: getattr(r, "target_date", ""),
               width=14),
        Column("Status",
               lambda r: getattr(r, "status", ""),
               width=12, fill_by_value=True),
        Column("Hierarchy Priority",
               lambda r: getattr(r, "hierarchy_priority", ""),
               width=14),
    ]


# ──────────────────────────────────────────────────────────────
# Main builder
# ──────────────────────────────────────────────────────────────
def build_training_spec(qs, hira_qs=None, request=None):
    """
    qs       = filtered TrainingRecord queryset (already filtered by
               plant / department / status by the registry).
    hira_qs  = optional TrainingHIRA queryset (may be None).
    request  = Django request (used for filter-aware headers/notes).
    """

    # ────────────────────────────────────────────────────────
    # Training Register columns (real DB data)
    # ────────────────────────────────────────────────────────
    columns = [
        Column("Record ID",     lambda r: r.id, width=10),
        Column("Employee ID",
               lambda r: r.employee.employee_id
                         if r.employee and hasattr(r.employee, "employee_id") else "",
               width=14),
        Column("Employee Name",
               lambda r: r.employee.get_full_name() if r.employee else "",
               width=22),
        Column("Department",
               lambda r: (r.employee.department.name
                          if r.employee and hasattr(r.employee, "department")
                             and r.employee.department else ""),
               width=18),
        Column("Topic",
               lambda r: r.topic.name if r.topic and hasattr(r.topic, "name")
                         else (str(r.topic) if r.topic else ""),
               width=30),
        Column("Session",
               lambda r: str(r.session) if r.session else "",
               width=20),
        Column("Completed Date",
               lambda r: r.completed_date.strftime("%d-%b-%Y")
                         if r.completed_date else "",
               width=14),
        Column("Valid Until",
               lambda r: r.valid_until.strftime("%d-%b-%Y")
                         if r.valid_until else "",
               width=14),
        Column("Days to Expiry",
               formula=lambda r, rn: f'=IF(H{rn}="","",H{rn}-TODAY())',
               width=14),
        Column("Expiring Soon",
               formula=lambda r, rn:
                   f'=IF(AND(I{rn}<>"",I{rn}>0,I{rn}<=30),"YES","NO")',
               width=14),
        Column("Expired?",
               formula=lambda r, rn:
                   f'=IF(AND(H{rn}<>"",H{rn}<TODAY()),"YES","NO")',
               width=10),
        Column("Certificate Number",
               lambda r: r.certificate_number or "", width=20),
        Column("Status",
               lambda r: r.get_status_display()
                         if hasattr(r, "get_status_display") else r.status,
               width=14, fill_by_value=True),
        Column("Added Manually",
               lambda r: "Yes" if r.added_manually else "No", width=14),
        Column("Remarks", lambda r: r.remarks or "", width=30),
        Column("Created",
               lambda r: r.created_at.strftime("%d-%b-%Y")
                         if r.created_at else "",
               width=14),
    ]

    # ────────────────────────────────────────────────────────
    # Training Actions columns (real filtered data)
    # ────────────────────────────────────────────────────────
    action_columns = [
        Column("Action ID", lambda r: f"TRN-ACT-{r.id:04d}", width=16),
        Column("Record ID", lambda r: r.id, width=10),
        Column("Employee",
               lambda r: r.employee.get_full_name() if r.employee else "",
               width=22),
        Column("Topic",
               lambda r: r.topic.name if r.topic and hasattr(r.topic, "name") else "",
               width=28),
        Column("Issue", lambda r: _issue_for(r), width=22, fill_by_value=True),
        Column("Recommended Action",
               lambda r: "Schedule refresher training", width=30),
        Column("Responsible",
               lambda r: (r.employee.department.name + " Head"
                          if r.employee and hasattr(r.employee, "department")
                             and r.employee.department else "EHS Officer"),
               width=20),
        Column("Target Date",
               formula=lambda r, rn: '=TODAY()+30', width=14),
        Column("Priority", lambda r: "High", width=10, fill_by_value=True),
        Column("Status",   lambda r: "Open", width=12, fill_by_value=True),
        Column("Remarks",  lambda r: "", width=30),
    ]

    # ────────────────────────────────────────────────────────
    # Dashboard KPIs (live formulas → Register + HIRA)
    # ────────────────────────────────────────────────────────
    kpis = [
        # ── Compliance KPIs ─────────────────────────────────
        KPI("Total Records",       f"=COUNTA('{REG}'!A2:A10000)",                 fill_color="EAF1F8"),
        KPI("Completed",           f'=COUNTIF(\'{REG}\'!M2:M10000,"Completed")',  fill_color="C6EFCE"),
        KPI("In Progress",         f'=COUNTIF(\'{REG}\'!M2:M10000,"In Progress")', fill_color="FFEB9C"),
        KPI("Not Started",         f'=COUNTIF(\'{REG}\'!M2:M10000,"Not Started")', fill_color="E7E6E6"),
        KPI("Expired",             f'=COUNTIF(\'{REG}\'!M2:M10000,"Expired")',    fill_color="FFC7CE"),
        KPI("Expiring in 30 days", f'=COUNTIF(\'{REG}\'!J2:J10000,"YES")',        fill_color="FFEB9C"),
        KPI("Compliance %",
            f"=IFERROR(COUNTIF('{REG}'!M2:M10000,\"Completed\")"
            f"/COUNTA('{REG}'!A2:A10000),0)",
            fill_color="C6EFCE"),
        KPI("Open Actions", f"=COUNTA('{ACTIONS}'!A2:A10000)", fill_color="FFEB9C"),

        # ── HIRA KPIs (safe even if HIRA sheet is empty) ────
        KPI("Total HIRA Lines",
            f"=COUNTA('{HIRA}'!A2:A5000)", fill_color="EAF1F8"),
        KPI("Critical Risks",
            f'=COUNTIF(\'{HIRA}\'!K2:K5000,"Critical")', fill_color="FF0000"),
        KPI("High Risks",
            f'=COUNTIF(\'{HIRA}\'!K2:K5000,"High")', fill_color="FFC7CE"),
        KPI("Medium Risks",
            f'=COUNTIF(\'{HIRA}\'!K2:K5000,"Medium")', fill_color="FFEB9C"),
        KPI("Low Risks",
            f'=COUNTIF(\'{HIRA}\'!K2:K5000,"Low")', fill_color="C6EFCE"),
        KPI("Residual Risk > 9",
            f'=COUNTIF(\'{HIRA}\'!P2:P5000,">9")', fill_color="FFC7CE"),
    ]

    pivots = [
        Pivot(
            title="Status",
            row_header="Count",
            row_values=["Completed", "In Progress", "Not Started",
                        "Expired", "Failed", "Revoked"],
            col_header="Total",
            col_formula_template=f'=COUNTIF(\'{REG}\'!M2:M10000,"{{value}}")',
        ),
    ]

    # ────────────────────────────────────────────────────────
    # Assemble the workbook
    # ────────────────────────────────────────────────────────
    module_sheets = [
        DashboardSheet(
            name="Training Dashboard",
            title="TRAINING REGISTER DASHBOARD",
            kpis=kpis, pivots=pivots,
            footer_note="Records expiring in 30 days need refresher training. "
                        "HIRA lines must be reviewed when controls fail or processes change.",
        ),
        RegisterSheet(
            name=REG,
            columns=columns,
            queryset=qs.select_related(
                "employee", "topic", "session", "created_by",
            ).order_by("-completed_date"),
            extend_formulas_to=5000,
            dropdowns={13: "Completed,In Progress,Not Started,Expired,Failed,Revoked"},
        ),
        RegisterSheet(
            name=ACTIONS,
            columns=action_columns,
            queryset=qs.exclude(status__in=["Completed", "Revoked"])
                      .select_related("employee", "topic")
                      .order_by("valid_until"),
            extend_formulas_to=2000,
            dropdowns={
                9:  "Low,Medium,High,Critical",
                10: "Open,In Progress,Completed,Closed",
            },
        ),
    ]

    # ── Optional HIRA sheet (only if hira_qs provided) ──────
    hira_sheets = []
    if hira_qs is not None:
        try:
            hira_sheets.append(
                RegisterSheet(
                    name=HIRA,
                    columns=_hira_columns(),
                    queryset=hira_qs,
                    extend_formulas_to=0,
                    dropdowns={
                        3:  "='Hazard Master'!A2:A12",
                        22: "='Hierarchy of Controls'!B2:B6",
                    },
                )
            )
        except Exception:
            # Model fields not present yet — skip HIRA sheet silently
            hira_sheets = []

    live_pivots = _live_pivot_sheets()
    hira_pivots = _hira_pivot_sheets() if hira_sheets else []

    return ReportSpec(
        document_title="Training Register & HIRA",
        file_prefix="Training_HIRA",
        sheets=[
            *module_sheets,        # 1–3   real DB rows + live KPI formulas
            *hira_sheets,          # 4     HIRA Register (optional)
            *live_pivots,          # 5–8   live COUNTIF formulas → Register
            *hira_pivots,          # 9–10  live COUNTIF → HIRA (optional)
            *get_master_sheets(),  # 11–17 7 reference sheets
        ],
    )