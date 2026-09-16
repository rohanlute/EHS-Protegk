import os
import datetime
from io import BytesIO
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import CAPA, CAPAApproval

BORDER_COLOR = colors.HexColor("#DEE2E6")
HEADER_BG_COLOR = colors.HexColor("#F8F9FA")


class ConditionalStory(list):
    def __init__(self):
        super().__init__()
        self.enabled = True

    def append(self, flowable):
        if self.enabled:
            super().append(flowable)


# =============================================================================
# Shared page-numbering canvas — copied verbatim from the Injury Report's
# NumberedCanvas so both modules render an identical "Page X of Y" footer.
# =============================================================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.darkgrey)
        self.drawRightString(200 * mm, 15 * mm, f"Page {self._pageNumber} of {page_count}")


# =============================================================================
# Shared style sheet
# =============================================================================
def _get_styles():
    styles = getSampleStyleSheet()
    primary_text_color = colors.HexColor("#212529")
    secondary_text_color = colors.HexColor("#495057")
    styles.add(ParagraphStyle(name="HeaderTitle", fontSize=10, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=primary_text_color))
    styles.add(ParagraphStyle(name="HeaderInfo", fontSize=9, fontName="Helvetica", alignment=TA_LEFT, textColor=secondary_text_color, leading=12))
    styles.add(ParagraphStyle(name="ReportTitle", fontSize=11, fontName="Helvetica-Bold", alignment=TA_LEFT, textColor=primary_text_color, spaceBefore=6))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=10, fontName="Helvetica-Bold", textColor=primary_text_color, spaceBefore=10, spaceAfter=4, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Label", fontSize=9, fontName="Helvetica-Bold", textColor=primary_text_color, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Value", fontSize=9, fontName="Helvetica", textColor=secondary_text_color, alignment=TA_LEFT, leading=12))
    styles.add(ParagraphStyle(name="FooterText", fontSize=8, fontName="Helvetica", textColor=colors.darkgrey, alignment=TA_CENTER))
    return styles


# =============================================================================
# Shared header table + draw callback (logo / title / doc-info) — same
# 3-column layout as the Injury Report header, title text swapped per form.
# =============================================================================
def _header_table(styles, drawable_width, doc_no, rev_info, title_line2):
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.jpg")
    logo_img = (
        Image(logo_path, width=2.2 * inch, height=1.6 * inch)
        if os.path.exists(logo_path)
        else Paragraph("<b>COMPANY LOGO</b>", styles["HeaderTitle"])
    )

    header_data = [
        [logo_img, Paragraph("<b>EHS MANAGEMENT SYSTEM [QEMS]</b>", styles["HeaderTitle"]), Paragraph(f"DOC NO: {doc_no}", styles["HeaderInfo"])],
        ["", Paragraph(f"<b>{title_line2}</b>", styles["HeaderTitle"]), Paragraph(rev_info, styles["HeaderInfo"])],
    ]
    header_table = Table(
        header_data,
        colWidths=[drawable_width * 0.2875, drawable_width * 0.4875, drawable_width * 0.225],
        rowHeights=[0.8 * inch, 0.8 * inch],
    )
    header_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("SPAN", (0, 0), (0, 1)),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return header_table


def _make_draw_header(header_table):
    def draw_header(canvas_obj, doc):
        canvas_obj.saveState()
        w, h = header_table.wrap(doc.width, doc.topMargin)
        header_table.drawOn(canvas_obj, doc.leftMargin, doc.height + doc.topMargin - h + 5 * mm)
        canvas_obj.restoreState()
    return draw_header


def _footer_paragraph(styles):
    text = f"Document generated from EHS-360 System on {datetime.datetime.now().strftime('%d-%b-%Y at %H:%M hrs')}"
    return Paragraph(text, styles["FooterText"])


def get_val(value, default="N/A"):
    if value:
        if isinstance(value, str):
            return value.strip().replace("\n", "<br/>")
        return value
    return default


def _bullet_flowables(items, styles, empty_text="N/A"):
    flowables = [Paragraph(f"\u2022 {item}", styles["Value"]) for item in items if item]
    return flowables or [Paragraph(empty_text, styles["Value"])]


def _new_doc(buffer, left_margin=15 * mm, right_margin=15 * mm, header_height=1.6 * inch):
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=header_height + 22 * mm,
        bottomMargin=25 * mm,
    )
    drawable_width = A4[0] - left_margin - right_margin
    return doc, drawable_width


# =============================================================================
# 1. Annexure-II — Corrective And Preventive Action Report
# =============================================================================
def generate_capa_pdf(capa):
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=capa.doc_no or f"DOC-{capa.capa_number}",
        rev_info=(
            capa.rev_info
            if capa.rev_info and not capa.rev_info.startswith("REV NO: 00")
            else f"REV NO: {capa.capa_number.rsplit('-', 1)[-1]} & DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}"
        ).replace(" & ", " &amp;<br/>", 1),
        title_line2="CORRECTIVE AND PREVENTIVE ACTION REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = ConditionalStory()
    story.append(Spacer(1, 4 * mm))

    investigation_stage_complete = capa.status not in {
        CAPA.Status.OPEN,
        CAPA.Status.INVESTIGATION_IN_PROGRESS,
    }
    action_stage_started = capa.status in {
        CAPA.Status.ACTION_PLAN_IN_PROGRESS,
        CAPA.Status.ACTION_IMPLEMENTATION,
        CAPA.Status.VERIFICATION,
        CAPA.Status.EFFECTIVENESS_REVIEW,
        CAPA.Status.CLOSED,
        CAPA.Status.REOPENED,
    }
    investigation_approval = capa.approvals.filter(
        approval_type=CAPAApproval.Type.INVESTIGATION,
    ).order_by("-approved_at", "-id").first()
    approval_stage_complete = bool(investigation_approval)
    verification_stage_started = capa.status in {
        CAPA.Status.VERIFICATION,
        CAPA.Status.EFFECTIVENESS_REVIEW,
        CAPA.Status.CLOSED,
    }
    effectiveness_stage_complete = hasattr(capa, "effectiveness_review")

    # ---- Reference strip: CAPA No. + Status --------------------------------
    ref_data = [[
        Paragraph(f"<b>CAPA No.:</b> {capa.capa_number}", styles["ReportTitle"]),
        Paragraph(f"<b>Status:</b><br/>{capa.get_status_display()}", styles["HeaderInfo"]),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    # ---- Department / Proposed completion / Source doc ---------------------
    top_data = [
        [Paragraph("<b>Department:</b>", styles["Label"]),
         Paragraph(get_val(capa.department.name if capa.department else ""), styles["Value"]),
         Paragraph("<b>Proposed Completion date:</b>", styles["Label"]),
         Paragraph(capa.target_date.strftime("%d/%m/%Y") if capa.target_date else "N/A", styles["Value"])],
        [Paragraph("<b>Source document:</b>", styles["Label"]),
         Paragraph(capa.get_source_type_display(), styles["Value"]),
         Paragraph("<b>Source document No.:</b>", styles["Label"]),
         Paragraph(get_val(capa.source_reference), styles["Value"])],
    ]
    top_table = Table(top_data, colWidths=[col4] * 4)
    top_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(top_table)

    # ---- Reason for CAPA -----------------------------------------------------
    reason_text = capa.capa_reason or capa.reason_required or capa.description
    reason_table = Table([
        [Paragraph("<b>Reason for CAPA</b>", styles["Label"])],
        [Paragraph(get_val(reason_text), styles["Value"])],
    ], colWidths=[drawable_width])
    reason_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(Spacer(1, 2 * mm))
    story.append(reason_table)

    # ---- Route Cause Analysis / Justification --------------------------------
    investigation = getattr(capa, "investigation", None)
    story.enabled = investigation_stage_complete and bool(investigation)
    # MAPPING: pulled from the CAPAInvestigation record if one exists.
    root_cause_text = ""
    if hasattr(capa, "investigation"):
        inv = capa.investigation
        root_cause_text = inv.final_root_cause or inv.root_cause_details or inv.investigation_conclusion
    rca_table = Table([
        [Paragraph("<b>Route Cause Analysis / Justification:</b>", styles["Label"])],
        [Paragraph(get_val(root_cause_text), styles["Value"])],
    ], colWidths=[drawable_width])
    rca_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(Spacer(1, 2 * mm))
    story.append(rca_table)

    # ---- Investigation information ------------------------------------------
    if investigation:
        investigation_data = [
            [Paragraph("<b>Investigation date:</b>", styles["Label"]),
             Paragraph(investigation.investigation_date.strftime("%d/%m/%Y") if investigation.investigation_date else "N/A", styles["Value"]),
             Paragraph("<b>Lead investigator:</b>", styles["Label"]),
             Paragraph(get_val(investigation.lead_investigator.get_full_name() if investigation.lead_investigator else ""), styles["Value"])],
            [Paragraph("<b>Investigation method:</b>", styles["Label"]),
             Paragraph(investigation.get_investigation_method_display(), styles["Value"]),
             Paragraph("<b>Root cause category:</b>", styles["Label"]),
             Paragraph(get_val(investigation.get_root_cause_category_display() if investigation.root_cause_category else ""), styles["Value"])],
            [Paragraph("<b>Findings:</b>", styles["Label"]),
             Paragraph(get_val(investigation.findings), styles["Value"]),
             Paragraph("<b>Investigation conclusion:</b>", styles["Label"]),
             Paragraph(get_val(investigation.investigation_conclusion), styles["Value"])],
        ]
        investigation_table = Table(investigation_data, colWidths=[col4] * 4)
        investigation_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Investigation Information</b>", styles["SectionHeader"]))
        story.append(investigation_table)

    # ---- CAPA Initiation: Proposed CAPA ---------------------------------------
    story.enabled = action_stage_started
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>CAPA Initiation</b>", styles["SectionHeader"]))
    action_lines = [a.action_description for a in capa.actions.all()]
    proposed_table = Table([
        [Paragraph("<b>Proposed CAPA (Attached additional sheets if required):</b>", styles["Label"])],
        [_bullet_flowables(action_lines, styles)],
    ], colWidths=[drawable_width])
    proposed_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(proposed_table)

    # ---- Department Head sign-off ---------------------------------------------
    # MAPPING: Department has a head_name field; falls back to the CAPA creator.
    dept_head_name = capa.department.head_name if capa.department else ""
    dept_row = [[
        Paragraph("<b>Proposed CAPA by<br/>Head QA / Designee</b>", styles["Label"]),
        Paragraph(f"Name:<br/>{get_val(dept_head_name, capa.created_by.get_full_name() if capa.created_by else 'N/A')}", styles["Value"]),
        Paragraph("Sign:", styles["Value"]),
        Paragraph(f"Date:<br/>{capa.created_at.strftime('%d/%m/%Y')}", styles["Value"]),
    ]]
    dept_table = Table(dept_row, colWidths=[col4] * 4)
    dept_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dept_table)

    # ---- Approval by Head QA / Designee --------------------------------------
    story.enabled = approval_stage_complete
    approval_decision = (investigation_approval.decision or "").upper() if investigation_approval else ""
    if approval_decision in {"APPROVED", "APPROVE", "ACCEPTED"}:
        approved_choice = "Approved"
    elif approval_decision in {"REJECTED", "REJECT", "NOT_APPROVED"}:
        approved_choice = "Not Approved"
    else:
        approved_choice = "Pending"

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Approval by Head QA / Designee:</b>", styles["Label"]))
    story.append(Paragraph(f"Proposed CAPA is <b>{approved_choice}</b>", styles["Value"]))

    head_qa_name, head_qa_date = "", None
    if investigation_approval:
        head_qa_name = investigation_approval.approved_by.get_full_name() if investigation_approval.approved_by else ""
        head_qa_date = investigation_approval.approved_at.date() if investigation_approval.approved_at else None
    head_row = [[
        Paragraph("Approved By", styles["Label"]),
        Paragraph(f"Name:<br/>{get_val(head_qa_name)}", styles["Value"]),
        Paragraph("Sign:", styles["Value"]),
        Paragraph(f"Date:<br/>{head_qa_date.strftime('%d/%m/%Y') if head_qa_date else 'N/A'}", styles["Value"]),
    ]]
    head_table = Table(head_row, colWidths=[col4] * 4)
    head_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(head_table)

    # =========================================================================
    # Page 2 — CAPA Verification and Closure
    # =========================================================================
    story.enabled = verification_stage_started
    story.append(PageBreak())
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"<b>CAPA No.:</b> {capa.capa_number}", styles["ReportTitle"]))
    story.append(Paragraph("<b>CAPA Verification and Closure</b>", styles["SectionHeader"]))

    verif_header = [
        Paragraph("<b>Sr.<br/>No.</b>", styles["Label"]),
        Paragraph("<b>Action taken / Documents closed</b>", styles["Label"]),
        Paragraph("<b>Effective /<br/>Implemented on</b>", styles["Label"]),
        Paragraph("<b>Signature &amp; date</b>", styles["Label"]),
    ]
    verif_rows = [verif_header]
    for i, action in enumerate(capa.actions.all(), start=1):
        verified_on, signer = None, ""
        if hasattr(action, "verification"):
            verified_on = action.verification.verification_date
            signer = action.verification.verified_by.get_full_name() if action.verification.verified_by else ""
        verif_rows.append([
            Paragraph(str(i), styles["Value"]),
            Paragraph(get_val(action.action_description), styles["Value"]),
            Paragraph(verified_on.strftime("%d/%m/%Y") if verified_on else "N/A", styles["Value"]),
            Paragraph(get_val(signer), styles["Value"]),
        ])
    if len(verif_rows) == 1:
        verif_rows.append([Paragraph("", styles["Value"])] * 4)

    verif_table = Table(verif_rows, colWidths=[drawable_width * 0.08, drawable_width * 0.52, drawable_width * 0.2, drawable_width * 0.2])
    verif_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(verif_table)

    # ---- Review of CAPA implemented by Initiating Dept Head --------------------
    story.enabled = verification_stage_started and effectiveness_stage_complete
    story.append(Spacer(1, 6 * mm))
    review_text = ""
    if hasattr(capa, "effectiveness_review"):
        er = capa.effectiveness_review
        review_text = er.observed_improvement or er.review_findings
    review_table = Table([
        [Paragraph("<b>Review of CAPA implemented by Initiating Department Head:</b>", styles["Label"])],
        [Paragraph(get_val(review_text), styles["Value"])],
    ], colWidths=[drawable_width])
    review_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(review_table)

    review_head_name = capa.owner.get_full_name() if capa.owner else ""
    review_head_row = [[
        Paragraph("Reviewed By", styles["Label"]),
        Paragraph(f"Name:<br/>{get_val(review_head_name)}", styles["Value"]),
        Paragraph("Sign:", styles["Value"]),
        Paragraph("Date:", styles["Value"]),
    ]]
    review_head_table = Table(review_head_row, colWidths=[col4] * 4)
    review_head_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(review_head_table)

    # ---- Verification of CAPA implementation ------------------------------------
    story.append(Spacer(1, 2 * mm))
    verification_text = ""
    if hasattr(capa, "effectiveness_review"):
        er = capa.effectiveness_review
        verification_text = er.effectiveness_evidence or er.evidence_description or er.remarks
    verif2_table = Table([
        [Paragraph("<b>Verification of CAPA implementation:</b>", styles["Label"])],
        [Paragraph(get_val(verification_text), styles["Value"])],
    ], colWidths=[drawable_width])
    verif2_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(verif2_table)

    final_head_name, final_head_date = "", None
    if hasattr(capa, "effectiveness_review") and capa.effectiveness_review.reviewed_by:
        final_head_name = capa.effectiveness_review.reviewed_by.get_full_name()
        final_head_date = capa.effectiveness_review.review_date
    final_row = [[
        Paragraph("Verified By", styles["Label"]),
        Paragraph(f"Name:<br/>{get_val(final_head_name)}", styles["Value"]),
        Paragraph("Sign:", styles["Value"]),
        Paragraph(f"Date:<br/>{final_head_date.strftime('%d/%m/%Y') if final_head_date else 'N/A'}", styles["Value"]),
    ]]
    final_table = Table(final_row, colWidths=[col4] * 4)
    final_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(final_table)

    # ---- Additional sheets / closure notes ---------------------------------------
    story.append(Spacer(1, 2 * mm))
    extra_lines = [
        f"<b>Lessons Learned:</b> {get_val(capa.lessons_learned, '')}" if capa.lessons_learned else "",
        f"<b>Final Recommendations:</b> {get_val(capa.final_recommendations, '')}" if capa.final_recommendations else "",
        f"<b>Closure Remarks:</b> {get_val(capa.closure_remarks, '')}" if capa.closure_remarks else "",
    ]
    extra_text = "<br/>".join(filter(None, extra_lines))
    extra_table = Table([[Paragraph(extra_text or "&nbsp;", styles["Value"])]], colWidths=[drawable_width])
    extra_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 40),
    ]))
    story.append(extra_table)

    story.append(Spacer(1, 10 * mm))
    story.enabled = True
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="CAPA_Report_{capa.capa_number}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 2. Annexure-IV — Justification Report For CAPA
#    (generate when capa.is_overdue is True and it's still open)
# =============================================================================
def generate_capa_justification_pdf(capa):
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=capa.doc_no or f"DOC-{capa.capa_number}",
        rev_info=(
            capa.rev_info
            if capa.rev_info and not capa.rev_info.startswith("REV NO: 00")
            else f"REV NO: {capa.capa_number.rsplit('-', 1)[-1]} & DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}"
        ).replace(" & ", " &amp;<br/>", 1),
        title_line2="JUSTIFICATION REPORT FOR CAPA",
    )
    draw_header = _make_draw_header(header_table)

    story = [Spacer(1, 4 * mm)]

    top_data = [
        [Paragraph("<b>CAPA No.:</b>", styles["Label"]), Paragraph(capa.capa_number, styles["Value"]),
         Paragraph("<b>Department:</b>", styles["Label"]), Paragraph(get_val(capa.department.name if capa.department else ""), styles["Value"])],
        [Paragraph("<b>Issue date of CAPA:</b>", styles["Label"]), Paragraph(capa.created_at.strftime("%d/%m/%Y"), styles["Value"]),
         Paragraph("<b>Proposed Completion Date:</b>", styles["Label"]), Paragraph(capa.target_date.strftime("%d/%m/%Y") if capa.target_date else "N/A", styles["Value"])],
    ]
    top_table = Table(top_data, colWidths=[col4] * 4)
    top_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(top_table)

    justification_text = capa.reason_required
    just_table = Table([
        [Paragraph("<b>Reason required / justification:</b>", styles["Label"])],
        [Paragraph(get_val(justification_text, "&nbsp;"), styles["Value"])],
    ], colWidths=[drawable_width])
    just_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 90),
    ]))
    story.append(just_table)

    dept_head_row = [[Paragraph("<b>Department Head/Designee</b>", styles["Label"]), Paragraph("Sign &amp; Date:", styles["Value"])]]
    dept_head_table = Table(dept_head_row, colWidths=[drawable_width * 0.6, drawable_width * 0.4])
    dept_head_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dept_head_table)

    qa_comments = ""
    if hasattr(capa, "investigation"):
        qa_comments = capa.investigation.reviewer_comments
    qa_table = Table([
        [Paragraph("<b>Comments of QA:</b>", styles["Label"])],
        [Paragraph(get_val(qa_comments, "&nbsp;"), styles["Value"])],
    ], colWidths=[drawable_width])
    qa_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 90),
    ]))
    story.append(qa_table)

    qa_head_row = [[Paragraph("<b>QA Head/Designee:</b>", styles["Label"]), Paragraph("Sign &amp; Date:", styles["Value"])]]
    qa_head_table = Table(qa_head_row, colWidths=[drawable_width * 0.6, drawable_width * 0.4])
    qa_head_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(qa_head_table)

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="CAPA_Justification_{capa.capa_number}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 3. Annexure-III — CAPA Log Book (per-department, per-year register)
# =============================================================================
def generate_capa_logbook_pdf(department, year, queryset=None):
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer, left_margin=10 * mm, right_margin=10 * mm)
    styles = _get_styles()

    header_table = _header_table(
        styles, drawable_width,
        doc_no="EIL/IRI/EHS/F-07",  # TODO: replace with your real doc number
        rev_info="REV NO: 00 &<br/>DATE: 01-09-2021",
        title_line2="CAPA LOG BOOK",
    )
    draw_header = _make_draw_header(header_table)

    story = [Spacer(1, 4 * mm)]
    story.append(Paragraph(f"<b>Name of Department:</b> {department.name}&nbsp;&nbsp;&nbsp;&nbsp;<b>Year:</b> {year}", styles["ReportTitle"]))
    story.append(Spacer(1, 3 * mm))

    qs = queryset if queryset is not None else CAPA.objects.filter(department=department, created_at__year=year).order_by("created_at")

    log_headers = [
        "Sr.\nNo.", "Date", "CAPA Number", "Name and Number\nof Source Documents",
        "Details of CAPA", "Approved/\nNot Approved", "Date of\nApproval", "Date of\nClosure", "Sign &\nDate", "Remark",
    ]
    rows = [[Paragraph(f"<b>{h}</b>", styles["Value"]) for h in log_headers]]

    for i, capa in enumerate(qs, start=1):
        approved, approved_date = "N/A", "N/A"
        if hasattr(capa, "investigation") and capa.investigation.review_date:
            approved = "Not Approved" if capa.status == CAPA.Status.INVESTIGATION_REJECTED else "Approved"
            approved_date = capa.investigation.review_date.strftime("%d/%m/%Y")
        rows.append([
            Paragraph(str(i), styles["Value"]),
            Paragraph(capa.created_at.strftime("%d/%m/%Y"), styles["Value"]),
            Paragraph(capa.capa_number, styles["Value"]),
            Paragraph(get_val(capa.source_reference), styles["Value"]),
            Paragraph(get_val(capa.title), styles["Value"]),
            Paragraph(approved, styles["Value"]),
            Paragraph(approved_date, styles["Value"]),
            Paragraph(capa.closed_date.strftime("%d/%m/%Y") if capa.closed_date else "N/A", styles["Value"]),
            Paragraph("", styles["Value"]),
            Paragraph("", styles["Value"]),
        ])
    if len(rows) == 1:
        rows.append([Paragraph("", styles["Value"])] * 10)

    widths_pct = [0.05, 0.08, 0.12, 0.14, 0.22, 0.10, 0.09, 0.09, 0.06, 0.05]
    col_widths = [drawable_width * p for p in widths_pct]
    log_table = Table(rows, colWidths=col_widths, repeatRows=1)
    log_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(log_table)
    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="CAPA_LogBook_{department.code}_{year}.pdf"'
    response.write(pdf)
    return response