# apps/five_s/pdf_generators.py
"""
5S PDF reports (same look & feel as the Contractor PDF)

  generate_five_s_audit_pdf(audit, capas_by_finding=None)        -> one audit, start to end
  generate_five_s_schedule_report_pdf(schedule)                  -> whole schedule: summary,
                                                                    audit history, then every
                                                                    completed audit start to end
"""
import os
import datetime
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle,
)

from apps.contractor.pdf_generators import (
    BORDER_COLOR,
    HEADER_BG_COLOR,
    NumberedCanvas,
    _footer_paragraph,
    _get_styles,
    _header_table,
    _make_draw_header,
    _new_doc,
    _safe_file_path,
    get_val,
)

from .models import PILLAR_CHOICES, CorrectiveAction, FiveSAudit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ANSWER_LABEL = {'1': 'Poor', '2': 'Fair', '3': 'Good',
                '4': 'V. Good', '5': 'Excellent', 'NA': 'N/A'}
ANSWER_SCORE = {'1': 1, '2': 3, '3': 5, '4': 5, '5': 5, 'NA': 5}
RATING_COLOR = {'1': '#B42318', '2': '#B54708', '3': '#344054',
                '4': '#067647', '5': '#067647', 'NA': '#667085'}
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
COMPLETED = ['SUBMITTED', 'REVIEWED', 'CLOSED']
PILLAR_NAMES = dict(PILLAR_CHOICES)

CAPA_STATUS_COLOR = {
    'ASSIGNED':   '#175CD3',
    'SUBMITTED':  '#B54708',
    'CLOSED':     '#067647',
    'REJECTED':   '#B42318',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_date(d, fmt="%d/%m/%Y"):
    return d.strftime(fmt) if d else "N/A"


def _fmt_dt(d):
    if not d:
        return "N/A"
    try:
        d = timezone.localtime(d)
    except Exception:
        pass
    return d.strftime("%d/%m/%Y %H:%M")


def _user_name(u):
    if not u:
        return "N/A"
    return (u.get_full_name() or u.username or "N/A").strip()


def _join(qs):
    names = [o.name for o in qs]
    return ", ".join(names) if names else "N/A"


def _rating_para(answer, styles):
    label = ANSWER_LABEL.get(answer, answer)
    color = RATING_COLOR.get(answer, '#344054')
    return Paragraph(f"<font color='{color}'><b>{label}</b></font>", styles["Value"])


def _base_style(extra=None):
    cmds = [
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if extra:
        cmds.extend(extra)
    return TableStyle(cmds)


def _kv_table(rows, styles, col4):
    """rows = [(label, value, label, value), ...] -> 4-column grid."""
    data = []
    for l1, v1, l2, v2 in rows:
        data.append([
            Paragraph(f"<b>{l1}:</b>", styles["Label"]),
            Paragraph(str(v1), styles["Value"]),
            Paragraph(f"<b>{l2}:</b>" if l2 else "", styles["Label"]),
            Paragraph(str(v2) if l2 else "", styles["Value"]),
        ])
    t = Table(data, colWidths=[col4] * 4)
    t.setStyle(_base_style())
    return t


def _grid_table(headers, rows, widths, styles):
    data = [[Paragraph(f"<b>{h}</b>", styles["Label"]) for h in headers]]
    data.extend(rows)
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(_base_style([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _fit_image(file_field, max_w, max_h, styles):
    path = _safe_file_path(file_field)
    if not path or not os.path.exists(path):
        return Paragraph("<i>No file available</i>", styles["Value"])
    if os.path.splitext(path)[1].lower() not in IMAGE_EXTS:
        return Paragraph(f"<i>File attached: {os.path.basename(path)}</i>", styles["Value"])
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            w, h = im.size
        ratio = min(max_w / w, max_h / h, 1.0)
        return Image(path, width=w * ratio, height=h * ratio)
    except Exception:
        return Paragraph("<i>Image could not be rendered</i>", styles["Value"])


def _status_badge(display, code):
    color = {'CLOSED': '#067647', 'SUBMITTED': '#B54708',
             'ASSIGNED': '#175CD3', 'REJECTED': '#B42318'}.get(code, '#344054')
    return f"<font color='{color}'><b>{display}</b></font>"


def _capa_badge(capa):
    """Inline HTML badge describing whether/which CAPA is linked."""
    if not capa:
        return "<font color='#B42318'><b>NO CAPA RAISED</b></font>"
    color = CAPA_STATUS_COLOR.get(capa.status, '#344054')
    return (f"<font color='{color}'><b>CAPA CREATED</b></font> "
            f"&nbsp;({capa.get_status_display()})")


def _resolution_badge(act, capa):
    """
    Resolution badge prioritising CAPA over 5S action, so reviewers can
    see at a glance whether the finding has escalated to a CAPA or been
    closed by a 5S CorrectiveAction.
    """
    if capa:
        color = CAPA_STATUS_COLOR.get(capa.status, '#344054')
        return (f"<font color='{color}'><b>CAPA CREATED</b></font> "
                f"&nbsp;({capa.get_status_display()})")
    if act and act.status == 'CLOSED':
        return "<font color='#067647'><b>ACTION CLOSED</b></font>"
    if act:
        return (f"<font color='#B54708'><b>ACTION "
                f"{act.get_status_display().upper()}</b></font>")
    return "<font color='#B42318'><b>NO CAPA RAISED</b></font>"


def _get_capas_for_audit(audit, finding_answer_ids=None):
    """
    Mirror of apps.five_s.views.get_capas_for_audit, kept local so the
    PDF generator does not depend on views (avoids circular import) and
    so the schedule report can resolve CAPAs per-audit inline.

    Returns {answer_id_str: CAPA}. Handles both per-finding CAPAs
    (source_reference == AuditAnswer.id) and schedule-wide CAPAs
    (source_reference == FiveSSchedule.pk) which are fanned out to every
    finding that doesn't already have its own.
    """
    from apps.capa.models import CAPA
    from .models import AuditAnswer

    if finding_answer_ids is None:
        finding_answer_ids = [
            str(aid) for aid in AuditAnswer.objects
            .filter(audit=audit, answer__in=['1', '2'])
            .values_list('id', flat=True)
        ]
    if not finding_answer_ids:
        return {}

    schedule_id_str = str(audit.schedule_id)

    capa_qs = (
        CAPA.objects
        .filter(source_type='FIVE_S')
        .filter(
            Q(source_reference__in=finding_answer_ids) |
            Q(source_reference=schedule_id_str)
        )
        .order_by('-id')
    )

    by_finding = {}
    schedule_wide = None
    for capa in capa_qs:
        ref = str(capa.source_reference)
        if ref == schedule_id_str:
            if schedule_wide is None:
                schedule_wide = capa
        else:
            by_finding.setdefault(ref, capa)

    if schedule_wide is not None:
        for aid in finding_answer_ids:
            by_finding.setdefault(aid, schedule_wide)

    return by_finding


def _ref_strip(left_html, right_html, styles, W):
    t = Table([[Paragraph(left_html, styles["ReportTitle"]),
                Paragraph(right_html, styles["HeaderInfo"])]],
              colWidths=[W * 0.7, W * 0.3])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _pdf_response(buffer, filename):
    pdf = buffer.getvalue()
    buffer.close()
    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write(pdf)
    return resp


# ---------------------------------------------------------------------------
# SHARED: one audit, start to end  (used by both reports)
# ---------------------------------------------------------------------------
def _build_audit_story(audit, styles, W, num, page_breaks=True,
                       full_details=True, capas_by_finding=None):
    """
    Returns a list of flowables:
      details -> pillar scores -> responses -> findings + corrective actions
      (+ CAPA status) -> before/after -> sign-off

    num(i) returns the section label, e.g. "1." or "6.2.1".
    capas_by_finding: optional {answer_id_str: CAPA}. If omitted, resolved
    from the DB via _get_capas_for_audit so the schedule report can just
    call this without threading the dict through.
    """
    col4 = W / 4
    story = []
    schedule = audit.schedule
    template = schedule.template

    answers = list(audit.answers.select_related('question')
                   .order_by('question__pillar', 'question__question_code'))
    actions = {}
    for a in (CorrectiveAction.objects.filter(audit=audit)
              .select_related('assigned_to', 'verifier', 'approved_by')
              .order_by('created_at')):
        actions[a.question_id] = a            # latest per question
    findings = [a for a in answers if a.answer in ('1', '2')]

    # CAPA lookup (used by both the summary and each finding block)
    if capas_by_finding is None:
        capas_by_finding = _get_capas_for_audit(
            audit, finding_answer_ids=[str(f.id) for f in findings]
        )

    overall = audit.overall_score
    min_score = template.min_compliance_score
    if overall is not None:
        ok = overall >= min_score
        result = f"<font color='{'#067647' if ok else '#B42318'}'><b>{'PASS' if ok else 'FAIL'}</b></font>"
        overall_txt = f"<b>{overall}%</b>"
    else:
        result, overall_txt = "N/A", "N/A"

    # ---- Audit details ---------------------------------------------------
    story.append(Paragraph(f"{num(1)} Audit Details", styles["SectionHeader"]))
    rows = []
    if full_details:
        rows += [
            ("Schedule", get_val(schedule.schedule_name), "Frequency", schedule.get_frequency_display() or "N/A"),
            ("Template", get_val(template.template_name), "Template Code",
             f"{template.template_code} v{audit.template_version}"),
            ("Plant", _join(schedule.plant.all()), "Zone", _join(schedule.zone.all())),
            ("Location", _join(schedule.location.all()), "Sub-Location", _join(schedule.sublocation.all())),
        ]

    # CAPA coverage line in Audit Details
    capa_count = len(capas_by_finding)
    finding_count = len(findings)
    if finding_count:
        capa_pct = round(capa_count / finding_count * 100, 1)
        capa_coverage_html = f"<b>{capa_count}</b> of {finding_count} ({capa_pct}%)"
    else:
        capa_coverage_html = "N/A"

    rows += [
        ("Scheduled Date", _fmt_date(audit.scheduled_date), "Due Date", _fmt_date(audit.due_date)),
        ("Started At", _fmt_dt(audit.started_at), "Submitted At", _fmt_dt(audit.submitted_at)),
        ("Inspector", _user_name(audit.user), "Submitted By", _user_name(audit.submitted_by)),
        ("Overall Score", overall_txt, "Minimum Required", f"{min_score}%"),
        ("Result", result, "Total Questions", len(answers)),
        ("Findings (Poor/Fair)", finding_count, "CAPAs Created", capa_coverage_html),
    ]
    story.append(_kv_table(rows, styles, col4))

    # ---- Pillar scores ---------------------------------------------------
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"{num(2)} Pillar-wise Score", styles["SectionHeader"]))
    ps = {c: {'name': n, 'earned': 0, 'max': 0, 'count': 0} for c, n in PILLAR_CHOICES}
    for a in answers:
        p = ps.get(a.question.pillar)
        if p:
            p['earned'] += ANSWER_SCORE.get(a.answer, 5)
            p['max'] += 5
            p['count'] += 1
    p_rows = []
    for p in ps.values():
        if p['max']:
            p_rows.append([
                Paragraph(p['name'], styles["Value"]),
                Paragraph(str(p['count']), styles["Value"]),
                Paragraph(f"{p['earned']} / {p['max']}", styles["Value"]),
                Paragraph(f"<b>{round(p['earned'] / p['max'] * 100, 1)}%</b>", styles["Value"]),
            ])
    if not p_rows:
        p_rows.append([Paragraph("No answers recorded.", styles["Value"]), "", "", ""])
    story.append(_grid_table(["Pillar", "Questions", "Points", "Score"], p_rows,
                             [W * 0.40, W * 0.18, W * 0.22, W * 0.20], styles))

    # ---- Responses -------------------------------------------------------
    if page_breaks:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(f"{num(3)} Inspection Responses", styles["SectionHeader"]))

    by_pillar = {}
    for a in answers:
        by_pillar.setdefault(a.question.pillar, []).append(a)
    for code, _ in PILLAR_CHOICES:
        grp = by_pillar.get(code)
        if not grp:
            continue
        story.append(Paragraph(f"<b>{PILLAR_NAMES[code]}</b>", styles["Label"]))
        story.append(Spacer(1, 1.5 * mm))
        data = []
        for i, a in enumerate(grp, 1):
            data.append([
                Paragraph(str(i), styles["Value"]),
                Paragraph(a.question.question_code, styles["Value"]),
                Paragraph(get_val(a.question.question_text), styles["Value"]),
                _rating_para(a.answer, styles),
                Paragraph(get_val(a.remarks, "—"), styles["Value"]),
            ])
        story.append(_grid_table(["Sr.", "Code", "Question", "Rating", "Remarks"], data,
                                 [W * 0.06, W * 0.11, W * 0.38, W * 0.13, W * 0.32], styles))
        story.append(Spacer(1, 4 * mm))

    # ---- Findings & corrective actions ----------------------------------
    if page_breaks:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"{num(4)} Findings &amp; Corrective Actions", styles["SectionHeader"]))

    if not findings:
        story.append(Paragraph("No findings. All questions were rated Good or above.", styles["Value"]))
    else:
        counts = {}
        for a in actions.values():
            counts[a.status] = counts.get(a.status, 0) + 1

        # Findings without a linked CAPA (uses the resolved dict so schedule-wide
        # CAPAs correctly count as covering the finding).
        finding_ids_str = [str(f.id) for f in findings]
        no_capa = sum(1 for fid in finding_ids_str if fid not in capas_by_finding)

        # Findings without any CorrectiveAction (kept for parity with existing report)
        no_action = sum(1 for f in findings if f.question_id not in actions)

        capa_pct = (
            round(capa_count / finding_count * 100, 1)
            if finding_count else 0
        )
        story.append(_kv_table([
            ("Total Findings", finding_count,
             "CAPAs Created", f"<b>{capa_count}</b>"),
            ("CAPA Coverage", f"<b>{capa_pct}%</b>",
             "Findings Without CAPA",
             f"<font color='{'#B42318' if no_capa else '#067647'}'><b>{no_capa}</b></font>"),
            ("Actions Closed", counts.get('CLOSED', 0),
             "Pending Approval", counts.get('SUBMITTED', 0)),
            ("Assigned (Open)", counts.get('ASSIGNED', 0),
             "Rejected", counts.get('REJECTED', 0)),
            ("Actions Raised", len(actions), "Findings W/O Action", no_action),
        ], styles, col4))
        story.append(Spacer(1, 4 * mm))

    img_w, img_h = (W / 2) - 14 * mm, 55 * mm
    for idx, f in enumerate(findings, 1):
        q = f.question
        act = actions.get(f.question_id)
        capa = capas_by_finding.get(str(f.id))
        block = []

        # Finding header: code + pillar + resolution badge (CAPA / Action / None)
        head = Table([[
            Paragraph(f"<b>Finding #{idx} &nbsp;|&nbsp; {q.question_code}</b>", styles["Label"]),
            Paragraph(f"<b>Pillar:</b> {PILLAR_NAMES.get(q.pillar, q.pillar)}", styles["Value"]),
            Paragraph(_resolution_badge(act, capa), styles["Value"]),
        ]], colWidths=[W * 0.42, W * 0.33, W * 0.25])
        head.setStyle(_base_style([
            ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG_COLOR),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ]))
        block.append(head)

        det = Table([
            [Paragraph("<b>Question:</b>", styles["Label"]),
             Paragraph(get_val(q.question_text), styles["Value"]),
             Paragraph("<b>Rating:</b>", styles["Label"]),
             _rating_para(f.answer, styles)],
            [Paragraph("<b>Inspector Remarks:</b>", styles["Label"]),
             Paragraph(get_val(f.remarks), styles["Value"]),
             Paragraph("<b>Reference:</b>", styles["Label"]),
             Paragraph(get_val(q.reference_standard), styles["Value"])],
        ], colWidths=[col4, col4 * 1.5, col4 * 0.6, col4 * 0.9])
        det.setStyle(_base_style())
        block.append(det)

        # CAPA block (if linked)
        if capa:
            owner = getattr(capa, 'owner', None)
            capa_rows = [
                ("CAPA Status",
                 f"<font color='{CAPA_STATUS_COLOR.get(capa.status, '#344054')}'>"
                 f"<b>{capa.get_status_display()}</b></font>",
                 "CAPA Raised", _fmt_date(getattr(capa, 'created_at', None))),
            ]
            # Reference / number fields vary by CAPA model; only include what exists
            ref_no = getattr(capa, 'capa_number', None) or getattr(capa, 'reference_no', None)
            if ref_no:
                capa_rows.append(("CAPA No.", f"<b>{ref_no}</b>",
                                  "Owner", _user_name(owner)))
            else:
                capa_rows.append(("CAPA Title", get_val(getattr(capa, 'title', None)),
                                  "Owner", _user_name(owner)))
            due = getattr(capa, 'due_date', None)
            if due:
                capa_rows.append(("CAPA Due", _fmt_date(due),
                                  "Closed On", _fmt_date(getattr(capa, 'closed_at', None))))
            block.append(_kv_table(capa_rows, styles, col4))

            desc = (getattr(capa, 'description', None)
                    or getattr(capa, 'problem_statement', None)
                    or getattr(capa, 'title', None))
            if desc:
                capa_txt = Table([
                    [Paragraph("<b>CAPA Description:</b>", styles["Label"]),
                     Paragraph(get_val(desc), styles["Value"])],
                ], colWidths=[col4 * 1.2, col4 * 2.8])
                capa_txt.setStyle(_base_style([
                    ("BACKGROUND", (0, 0), (0, -1), HEADER_BG_COLOR)
                ]))
                block.append(capa_txt)

        # 5S CorrectiveAction block (if raised)
        if act:
            block.append(_kv_table([
                ("Action Status", _status_badge(act.get_status_display(), act.status),
                 "Action Raised", _fmt_date(act.created_at)),
                ("Assigned To", _user_name(act.assigned_to), "Verifier", _user_name(act.verifier)),
                ("Due Date", _fmt_date(act.due_date), "Completion Date", _fmt_date(act.completion_date)),
                ("Approved By", _user_name(act.approved_by) if act.approved_by else "N/A",
                 "Approved At", _fmt_dt(act.approved_at)),
            ], styles, col4))
            tb = Table([
                [Paragraph("<b>Action Instruction:</b>", styles["Label"]),
                 Paragraph(get_val(act.remarks), styles["Value"])],
                [Paragraph("<b>Action Taken (Assignee):</b>", styles["Label"]),
                 Paragraph(get_val(act.completion_remarks), styles["Value"])],
                [Paragraph("<b>Approval Remarks:</b>", styles["Label"]),
                 Paragraph(get_val(act.approval_remarks), styles["Value"])],
            ], colWidths=[col4 * 1.2, col4 * 2.8])
            tb.setStyle(_base_style([("BACKGROUND", (0, 0), (0, -1), HEADER_BG_COLOR)]))
            block.append(tb)
        elif not capa:
            # Neither a CAPA nor a 5S action -> red warning strip
            na = Table([[Paragraph(
                "<b>Resolution:</b> "
                "<font color='#B42318'>No CAPA raised and no corrective action assigned yet.</font>",
                styles["Value"])]], colWidths=[W])
            na.setStyle(_base_style())
            block.append(na)

        before = (_fit_image(f.evidence, img_w, img_h, styles) if f.evidence
                  else Paragraph("<i>No before photo</i>", styles["Value"]))
        after = (_fit_image(act.completion_evidence, img_w, img_h, styles)
                 if (act and act.completion_evidence)
                 else Paragraph("<i>No after photo yet</i>", styles["Value"]))
        ba = Table([
            [Paragraph("<b>BEFORE (Inspector Evidence)</b>", styles["Label"]),
             Paragraph("<b>AFTER (Corrective Action Evidence)</b>", styles["Label"])],
            [before, after],
        ], colWidths=[W / 2, W / 2])
        ba.setStyle(_base_style([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
            ("TOPPADDING", (0, 1), (-1, 1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ]))
        block.append(ba)
        block.append(Spacer(1, 6 * mm))
        story.append(KeepTogether(block))

    # ---- Sign-off --------------------------------------------------------
    story.append(Spacer(1, 3 * mm))
    if audit.inspector_signature:
        sig = _fit_image(audit.inspector_signature, 55 * mm, 22 * mm, styles)
    else:
        sig = Paragraph("&nbsp;<br/>&nbsp;<br/>_________________", styles["Value"])
    blank = Paragraph("&nbsp;<br/>&nbsp;<br/>_________________", styles["Value"])
    sig_tbl = Table([
        [Paragraph("<b>Inspected By</b>", styles["Label"]),
         Paragraph("<b>Reviewed By</b>", styles["Label"]),
         Paragraph("<b>Approved By</b>", styles["Label"])],
        [sig, blank, blank],
        [Paragraph(_user_name(audit.user), styles["Value"]),
         Paragraph("", styles["Value"]), Paragraph("", styles["Value"])],
    ], colWidths=[W / 3] * 3)
    sig_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether([Paragraph(f"{num(5)} Sign-Off", styles["SectionHeader"]), sig_tbl]))
    return story


# ---------------------------------------------------------------------------
# REPORT 1: single audit
# ---------------------------------------------------------------------------
def generate_five_s_audit_pdf(audit, capas_by_finding=None):
    buffer = BytesIO()
    pdf_doc, W = _new_doc(buffer)
    styles = _get_styles()

    header = _header_table(
        styles, W,
        doc_no=f"5S-{audit.cycle_key}",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="5S AUDIT REPORT",
    )
    draw_header = _make_draw_header(header)

    story = [Spacer(1, 4 * mm),
             _ref_strip(f"<b>Audit No.:</b> {audit.cycle_key}",
                        f"<b>Status:</b><br/>{audit.get_status_display()}", styles, W),
             Spacer(1, 2 * mm)]
    story += _build_audit_story(
        audit, styles, W,
        num=lambda i: f"{i}.",
        page_breaks=True,
        capas_by_finding=capas_by_finding,
    )
    story += [Spacer(1, 10 * mm), _footer_paragraph(styles)]

    pdf_doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header,
                  canvasmaker=NumberedCanvas)
    return _pdf_response(buffer, f"5S_Audit_{audit.cycle_key}.pdf")


# ---------------------------------------------------------------------------
# REPORT 2: whole schedule
# ---------------------------------------------------------------------------
def generate_five_s_schedule_report_pdf(schedule):
    buffer = BytesIO()
    pdf_doc, W = _new_doc(buffer)
    styles = _get_styles()
    col4 = W / 4
    today = timezone.now().date()

    header = _header_table(
        styles, W,
        doc_no=f"5S-SCH-{schedule.pk}",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="5S SCHEDULE REPORT",
    )
    draw_header = _make_draw_header(header)
    template = schedule.template

    audits = list(
        FiveSAudit.objects.filter(schedule=schedule)
        .select_related('user', 'submitted_by')
        .order_by('scheduled_date', 'created_at')
    )
    completed = [a for a in audits if a.status in COMPLETED]
    pending = [a for a in audits if a.status not in COMPLETED]
    overdue = [a for a in pending if a.due_date and a.due_date < today]

    # Per-audit finding / action / CAPA counts
    from .models import AuditAnswer

    stats = {}
    for a in audits:
        stats[a.pk] = {'findings': 0, 'actions': 0, 'closed': 0,
                       'capas': 0, 'without_capa': 0}

    # Findings per audit (also stash the finding IDs per audit for CAPA matching)
    finding_ids_by_audit = {}
    for aa in AuditAnswer.objects.filter(
            audit__schedule=schedule, answer__in=['1', '2']
    ).only('id', 'audit_id'):
        stats[aa.audit_id]['findings'] += 1
        finding_ids_by_audit.setdefault(aa.audit_id, []).append(str(aa.id))

    # 5S CorrectiveActions
    all_actions = list(CorrectiveAction.objects.filter(audit__schedule=schedule))
    for ca in all_actions:
        stats[ca.audit_id]['actions'] += 1
        if ca.status == 'CLOSED':
            stats[ca.audit_id]['closed'] += 1

    # CAPAs per audit (resolved via the shared helper)
    for a in audits:
        fids = finding_ids_by_audit.get(a.pk, [])
        if not fids:
            continue
        capas = _get_capas_for_audit(a, finding_answer_ids=fids)
        covered = sum(1 for fid in fids if fid in capas)
        stats[a.pk]['capas'] = covered
        stats[a.pk]['without_capa'] = len(fids) - covered

    total_findings = sum(s['findings'] for s in stats.values())
    total_actions = len(all_actions)
    closed_actions = sum(1 for c in all_actions if c.status == 'CLOSED')
    open_actions = total_actions - closed_actions
    total_capas = sum(s['capas'] for s in stats.values())
    total_without_capa = sum(s['without_capa'] for s in stats.values())
    capa_coverage = (
        round(total_capas / total_findings * 100, 1) if total_findings else 0
    )

    scores = [float(a.overall_score) for a in completed if a.overall_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    closure_rate = round(closed_actions / total_actions * 100, 1) if total_actions else 0

    story = [Spacer(1, 4 * mm),
             _ref_strip(f"<b>Schedule:</b> {schedule.schedule_name}",
                        f"<b>Status:</b><br/>{schedule.get_status_display()}", styles, W)]

    # ---- 1. Schedule details --------------------------------------------
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("1. Schedule Details", styles["SectionHeader"]))
    story.append(_kv_table([
        ("Schedule Name", get_val(schedule.schedule_name), "Status", schedule.get_status_display()),
        ("Template", get_val(template.template_name), "Template Code", template.template_code),
        ("Frequency", schedule.get_frequency_display() or "N/A",
         "Auto-Schedule", "Enabled" if schedule.enable_auto_schedule else "Disabled"),
        ("Start Date", _fmt_date(schedule.start_date), "End Date", _fmt_date(schedule.end_date)),
        ("Plant", _join(schedule.plant.all()), "Zone", _join(schedule.zone.all())),
        ("Location", _join(schedule.location.all()), "Sub-Location", _join(schedule.sublocation.all())),
        ("Assignees", ", ".join(_user_name(u) for u in schedule.assignee.all()) or "N/A",
         "Created By", _user_name(schedule.created_by)),
        ("Min. Compliance", f"{template.min_compliance_score}%", "Created On", _fmt_date(schedule.created_at)),
    ], styles, col4))

    # ---- 2. Summary ------------------------------------------------------
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("2. Schedule Summary", styles["SectionHeader"]))
    story.append(_kv_table([
        ("Total Audits", len(audits), "Completed", len(completed)),
        ("Pending", len(pending), "Overdue",
         f"<font color='#B42318'><b>{len(overdue)}</b></font>" if overdue else 0),
        ("Average Score", f"<b>{avg_score}%</b>" if avg_score is not None else "N/A",
         "Total Findings", total_findings),
        ("Actions Raised", total_actions, "Actions Closed", closed_actions),
        ("Actions Open", open_actions, "Closure Rate", f"<b>{closure_rate}%</b>"),
        ("CAPAs Created", f"<b>{total_capas}</b>",
         "CAPA Coverage", f"<b>{capa_coverage}%</b>"),
        ("Findings Without CAPA",
         f"<font color='{'#B42318' if total_without_capa else '#067647'}'><b>{total_without_capa}</b></font>",
         "Findings Without Action",
         max(total_findings - total_actions, 0)),
    ], styles, col4))

    # ---- 3. Audit history -----------------------------------------------
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("3. Audit History", styles["SectionHeader"]))
    if not audits:
        story.append(Paragraph("No audits have been generated for this schedule yet.", styles["Value"]))
    else:
        rows = []
        for i, a in enumerate(audits, 1):
            s = stats[a.pk]
            late = a.status not in COMPLETED and a.due_date and a.due_date < today
            status_html = a.get_status_display()
            if late:
                status_html = f"<font color='#B42318'><b>{status_html} (Overdue)</b></font>"

            # Findings/CAPA cell: "n/m", red if any finding lacks a CAPA
            if s['findings']:
                capa_color = '#B42318' if s['without_capa'] else '#067647'
                capa_cell = (f"<font color='{capa_color}'><b>"
                             f"{s['capas']}/{s['findings']}</b></font>")
            else:
                capa_cell = "—"

            rows.append([
                Paragraph(str(i), styles["Value"]),
                Paragraph(a.cycle_key, styles["Value"]),
                Paragraph(_fmt_date(a.scheduled_date), styles["Value"]),
                Paragraph(_fmt_date(a.due_date), styles["Value"]),
                Paragraph(_user_name(a.user), styles["Value"]),
                Paragraph(status_html, styles["Value"]),
                Paragraph(f"{a.overall_score}%" if a.overall_score is not None else "—", styles["Value"]),
                Paragraph(str(s['findings']), styles["Value"]),
                Paragraph(capa_cell, styles["Value"]),
                Paragraph(f"{s['closed']}/{s['actions']}", styles["Value"]),
            ])
        story.append(_grid_table(
            ["Sr.", "Audit No.", "Scheduled", "Due", "Inspector",
             "Status", "Score", "Findings", "CAPAs", "Actions Closed"],
            rows,
            [W * 0.05, W * 0.15, W * 0.09, W * 0.09, W * 0.14,
             W * 0.12, W * 0.07, W * 0.08, W * 0.08, W * 0.13],
            styles,
        ))

    # ---- 4. Pillar performance across all completed audits ---------------
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("4. Pillar Performance (All Completed Audits)", styles["SectionHeader"]))
    ps = {c: {'name': n, 'earned': 0, 'max': 0} for c, n in PILLAR_CHOICES}
    for aa in (AuditAnswer.objects.filter(audit__in=completed).select_related('question')):
        p = ps.get(aa.question.pillar)
        if p:
            p['earned'] += ANSWER_SCORE.get(aa.answer, 5)
            p['max'] += 5
    p_rows = [[Paragraph(p['name'], styles["Value"]),
               Paragraph(f"{p['earned']} / {p['max']}", styles["Value"]),
               Paragraph(f"<b>{round(p['earned'] / p['max'] * 100, 1)}%</b>", styles["Value"])]
              for p in ps.values() if p['max']]
    if not p_rows:
        p_rows = [[Paragraph("No completed audits yet.", styles["Value"]), "", ""]]
    story.append(_grid_table(["Pillar", "Points", "Score"], p_rows,
                             [W * 0.50, W * 0.25, W * 0.25], styles))

    # ---- 5. Detailed audit reports --------------------------------------
    if not completed:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("5. Detailed Audit Reports", styles["SectionHeader"]))
        story.append(Paragraph("No submitted audits yet.", styles["Value"]))
    else:
        for n, audit in enumerate(completed, 1):
            story.append(PageBreak())
            story.append(_ref_strip(
                f"<b>5.{n} &nbsp;Audit:</b> {audit.cycle_key}",
                f"<b>Status:</b><br/>{audit.get_status_display()}", styles, W))
            story.append(Spacer(1, 2 * mm))

            # Resolve CAPAs once per audit; the shared story builder will use it
            fids = finding_ids_by_audit.get(audit.pk, [])
            capas_for_this_audit = _get_capas_for_audit(
                audit, finding_answer_ids=fids
            ) if fids else {}

            story += _build_audit_story(
                audit, styles, W,
                num=lambda i, n=n: f"5.{n}.{i}",
                page_breaks=False,
                full_details=False,
                capas_by_finding=capas_for_this_audit,
            )

    story += [Spacer(1, 10 * mm), _footer_paragraph(styles)]

    pdf_doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header,
                  canvasmaker=NumberedCanvas)
    safe = "".join(c if c.isalnum() else "_" for c in schedule.schedule_name)[:40]
    return _pdf_response(buffer, f"5S_Schedule_Report_{safe}.pdf")