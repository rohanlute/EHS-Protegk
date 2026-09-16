# apps/contractor/pdf_generators.py

import os
import datetime
from io import BytesIO
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
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

from .models import (
    Contractor,
    OnboardingRequest,
    OnboardingDocumentRequirement,
    WorkOrder,
    TrainingSignOff,
    ContractorInspection,
    ContractorPerformanceMetric,
    ContractorPreQualification,
)

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
# Shared page-numbering canvas
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
# Shared header table + draw callback
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


def _safe_file_path(file_field):
    """Return the local filesystem path for a FileField, or None if unavailable."""
    if not file_field:
        return None
    try:
        return file_field.path
    except Exception:
        return None


def _embed_image(elements, file_path, value_style, max_width_mm=70, max_height_mm=50, caption=None):
    """Safely embed an image in the PDF story."""
    if not file_path or not os.path.exists(file_path):
        return

    ext = os.path.splitext(file_path)[1].lower()
    image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')

    if ext not in image_exts:
        return

    try:
        from PIL import Image as PILImage
        with PILImage.open(file_path) as im:
            img_w, img_h = im.size

        max_w = max_width_mm * mm
        max_h = max_height_mm * mm
        ratio = min(max_w / img_w, max_h / img_h, 1.0)
        draw_w = img_w * ratio
        draw_h = img_h * ratio

        if caption:
            elements.append(Paragraph(f"<b>{caption}</b>", value_style))
        elements.append(Image(file_path, width=draw_w, height=draw_h))
        elements.append(Spacer(1, 4))
    except Exception:
        pass


def _get_rating(score):
    if score >= 90:
        return 'Excellent'
    elif score >= 75:
        return 'Good'
    elif score >= 60:
        return 'Needs Improvement'
    else:
        return 'Poor'


# =============================================================================
# 1. Contractor Registration Report
# =============================================================================
def generate_contractor_pdf(contractor):
    """Generate a Contractor Registration Report PDF."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=f"EIL/IRI/EHS/F-08",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="CONTRACTOR REGISTRATION REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    ref_data = [[
        Paragraph(f"<b>Contractor Code:</b> {contractor.contractor_code}", styles["ReportTitle"]),
        Paragraph(f"<b>Status:</b><br/>{contractor.get_status_display()}", styles["HeaderInfo"]),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    # Basic Information
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Basic Information</b>", styles["SectionHeader"]))

    basic_data = [
        [Paragraph("<b>Contractor Name:</b>", styles["Label"]),
         Paragraph(get_val(contractor.contractor_name), styles["Value"]),
         Paragraph("<b>Contractor Type:</b>", styles["Label"]),
         Paragraph(get_val(contractor.get_contractor_type_display()), styles["Value"])],
        [Paragraph("<b>Registration Number:</b>", styles["Label"]),
         Paragraph(get_val(contractor.registration_number), styles["Value"]),
         Paragraph("<b>PAN Number:</b>", styles["Label"]),
         Paragraph(get_val(contractor.pan_number), styles["Value"])],
        [Paragraph("<b>GSTIN:</b>", styles["Label"]),
         Paragraph(get_val(contractor.gstin), styles["Value"]),
         Paragraph("<b>Establishment Year:</b>", styles["Label"]),
         Paragraph(str(contractor.establishment_year) if contractor.establishment_year else "N/A", styles["Value"])],
        [Paragraph("<b>Work Category:</b>", styles["Label"]),
         Paragraph(get_val(contractor.get_work_category_display()), styles["Value"]),
         Paragraph("<b>Years of Experience:</b>", styles["Label"]),
         Paragraph(str(contractor.years_of_experience) if contractor.years_of_experience else "N/A", styles["Value"])],
    ]
    basic_table = Table(basic_data, colWidths=[col4] * 4)
    basic_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(basic_table)

    # Contact Information
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Contact Information</b>", styles["SectionHeader"]))

    contact_data = [
        [Paragraph("<b>Contact Person:</b>", styles["Label"]),
         Paragraph(get_val(contractor.contact_person), styles["Value"]),
         Paragraph("<b>Designation:</b>", styles["Label"]),
         Paragraph(get_val(contractor.designation), styles["Value"])],
        [Paragraph("<b>Mobile:</b>", styles["Label"]),
         Paragraph(get_val(contractor.mobile), styles["Value"]),
         Paragraph("<b>Alternate Mobile:</b>", styles["Label"]),
         Paragraph(get_val(contractor.alternate_mobile), styles["Value"])],
        [Paragraph("<b>Email:</b>", styles["Label"]),
         Paragraph(get_val(contractor.email), styles["Value"]),
         Paragraph("<b>Country:</b>", styles["Label"]),
         Paragraph(get_val(contractor.country), styles["Value"])],
        [Paragraph("<b>Address Line 1:</b>", styles["Label"]),
         Paragraph(get_val(contractor.address_line1), styles["Value"]),
         Paragraph("<b>Address Line 2:</b>", styles["Label"]),
         Paragraph(get_val(contractor.address_line2), styles["Value"])],
        [Paragraph("<b>City:</b>", styles["Label"]),
         Paragraph(get_val(contractor.city), styles["Value"]),
         Paragraph("<b>State:</b>", styles["Label"]),
         Paragraph(get_val(contractor.state), styles["Value"])],
        [Paragraph("<b>Pincode:</b>", styles["Label"]),
         Paragraph(get_val(contractor.pincode), styles["Value"]),
         Paragraph("", styles["Value"]),
         Paragraph("", styles["Value"])],
    ]
    contact_table = Table(contact_data, colWidths=[col4] * 4)
    contact_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(contact_table)

    # Business Information
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Business Information</b>", styles["SectionHeader"]))

    business_data = [
        [Paragraph("<b>Nature of Business:</b>", styles["Label"]),
         Paragraph(get_val(contractor.nature_of_business), styles["Value"]),
         Paragraph("<b>Number of Workers:</b>", styles["Label"]),
         Paragraph(str(contractor.number_of_workers) if contractor.number_of_workers else "N/A", styles["Value"])],
    ]
    business_table = Table(business_data, colWidths=[col4] * 4)
    business_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(business_table)

    # Service Description
    story.append(Spacer(1, 2 * mm))
    scope_table = Table([
        [Paragraph("<b>Service Description:</b>", styles["Label"])],
        [Paragraph(get_val(contractor.service_description), styles["Value"])],
    ], colWidths=[drawable_width])
    scope_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(scope_table)

    # EHS Officer
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>EHS / Responsible Person</b>", styles["SectionHeader"]))

    ehs_data = [
        [Paragraph("<b>EHS Officer Name:</b>", styles["Label"]),
         Paragraph(get_val(contractor.ehs_officer_name), styles["Value"]),
         Paragraph("<b>Designation:</b>", styles["Label"]),
         Paragraph(get_val(contractor.ehs_designation), styles["Value"])],
        [Paragraph("<b>EHS Mobile:</b>", styles["Label"]),
         Paragraph(get_val(contractor.ehs_mobile), styles["Value"]),
         Paragraph("<b>EHS Email:</b>", styles["Label"]),
         Paragraph(get_val(contractor.ehs_email), styles["Value"])],
    ]
    ehs_table = Table(ehs_data, colWidths=[col4] * 4)
    ehs_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(ehs_table)

    # Pre-Qualification
    prequal = ContractorPreQualification.objects.filter(
        contractor=contractor, status='APPROVED'
    ).order_by('-created_at').first()

    if prequal:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Pre-Qualification Assessment</b>", styles["SectionHeader"]))

        prequal_data = [
            [Paragraph("<b>Risk Level:</b>", styles["Label"]),
             Paragraph(get_val(prequal.get_risk_level_display()), styles["Value"]),
             Paragraph("<b>Status:</b>", styles["Label"]),
             Paragraph(get_val(prequal.get_status_display()), styles["Value"])],
            [Paragraph("<b>Years of Experience:</b>", styles["Label"]),
             Paragraph(str(prequal.years_of_experience), styles["Value"]),
             Paragraph("<b>Accident History:</b>", styles["Label"]),
             Paragraph(str(prequal.accident_history), styles["Value"])],
            [Paragraph("<b>Safety Manpower:</b>", styles["Label"]),
             Paragraph(str(prequal.safety_manpower), styles["Value"]),
             Paragraph("<b>Total Manpower:</b>", styles["Label"]),
             Paragraph(str(prequal.total_manpower), styles["Value"])],
            [Paragraph("<b>Safety Policy:</b>", styles["Label"]),
             Paragraph("Yes" if prequal.has_safety_policy else "No", styles["Value"]),
             Paragraph("<b>Insurance:</b>", styles["Label"]),
             Paragraph("Yes" if prequal.has_insurance else "No", styles["Value"])],
        ]
        prequal_table = Table(prequal_data, colWidths=[col4] * 4)
        prequal_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(prequal_table)

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Contractor_Registration_{contractor.contractor_code}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 2. Contractor Work Order Report
# =============================================================================
def generate_work_order_pdf(work_order):
    """Generate a Work Order PDF."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=f"EIL/IRI/EHS/F-09",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="CONTRACTOR WORK ORDER",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    ref_data = [[
        Paragraph(f"<b>Work Order No.:</b> {work_order.work_order_number}", styles["ReportTitle"]),
        Paragraph(f"<b>Status:</b><br/>{work_order.get_status_display()}", styles["HeaderInfo"]),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Work Order Details</b>", styles["SectionHeader"]))

    wo_data = [
        [Paragraph("<b>Contractor:</b>", styles["Label"]),
         Paragraph(get_val(work_order.contractor.contractor_name), styles["Value"]),
         Paragraph("<b>Contract Number:</b>", styles["Label"]),
         Paragraph(get_val(work_order.contract_number), styles["Value"])],
        [Paragraph("<b>Work Category:</b>", styles["Label"]),
         Paragraph(get_val(work_order.get_work_category_display()), styles["Value"]),
         Paragraph("<b>Risk Level:</b>", styles["Label"]),
         Paragraph(get_val(work_order.get_risk_level_display()), styles["Value"])],
        [Paragraph("<b>Plant:</b>", styles["Label"]),
         Paragraph(get_val(work_order.plant.name if work_order.plant else ""), styles["Value"]),
         Paragraph("<b>Department:</b>", styles["Label"]),
         Paragraph(get_val(work_order.department.name if work_order.department else ""), styles["Value"])],
        [Paragraph("<b>Work Location:</b>", styles["Label"]),
         Paragraph(get_val(work_order.location), styles["Value"]),
         Paragraph("<b>Number of Workers:</b>", styles["Label"]),
         Paragraph(str(work_order.number_of_workers), styles["Value"])],
        [Paragraph("<b>Start Date:</b>", styles["Label"]),
         Paragraph(work_order.start_date.strftime("%d/%m/%Y") if work_order.start_date else "N/A", styles["Value"]),
         Paragraph("<b>End Date:</b>", styles["Label"]),
         Paragraph(work_order.end_date.strftime("%d/%m/%Y") if work_order.end_date else "N/A", styles["Value"])],
    ]
    wo_table = Table(wo_data, colWidths=[col4] * 4)
    wo_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(wo_table)

    story.append(Spacer(1, 2 * mm))
    desc_table = Table([
        [Paragraph("<b>Work Description:</b>", styles["Label"])],
        [Paragraph(get_val(work_order.work_description), styles["Value"])],
    ], colWidths=[drawable_width])
    desc_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
    ]))
    story.append(desc_table)

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Supervisor &amp; Representative Details</b>", styles["SectionHeader"]))

    sup_data = [
        [Paragraph("<b>Contractor Supervisor:</b>", styles["Label"]),
         Paragraph(get_val(work_order.contractor_supervisor), styles["Value"]),
         Paragraph("<b>Supervisor Contact:</b>", styles["Label"]),
         Paragraph(get_val(work_order.contractor_supervisor_contact), styles["Value"])],
        [Paragraph("<b>Supervisor Email:</b>", styles["Label"]),
         Paragraph(get_val(work_order.contractor_supervisor_email), styles["Value"]),
         Paragraph("<b>Company Representative:</b>", styles["Label"]),
         Paragraph(get_val(work_order.company_representative.get_full_name() if work_order.company_representative else ""), styles["Value"])],
    ]
    sup_table = Table(sup_data, colWidths=[col4] * 4)
    sup_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sup_table)

    if work_order.worker_details:
        story.append(Spacer(1, 2 * mm))
        worker_table = Table([
            [Paragraph("<b>Worker Details:</b>", styles["Label"])],
            [Paragraph(get_val(work_order.worker_details), styles["Value"])],
        ], colWidths=[drawable_width])
        worker_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
        ]))
        story.append(worker_table)

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Approval Details</b>", styles["SectionHeader"]))

    approval_data = [
        [Paragraph("<b>Created By:</b>", styles["Label"]),
         Paragraph(get_val(work_order.created_by.get_full_name() if work_order.created_by else ""), styles["Value"]),
         Paragraph("<b>Created At:</b>", styles["Label"]),
         Paragraph(work_order.created_at.strftime("%d/%m/%Y") if work_order.created_at else "N/A", styles["Value"])],
        [Paragraph("<b>Approved By:</b>", styles["Label"]),
         Paragraph(get_val(work_order.approved_by.get_full_name() if work_order.approved_by else ""), styles["Value"]),
         Paragraph("<b>Approved At:</b>", styles["Label"]),
         Paragraph(work_order.approved_at.strftime("%d/%m/%Y") if work_order.approved_at else "N/A", styles["Value"])],
    ]
    approval_table = Table(approval_data, colWidths=[col4] * 4)
    approval_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(approval_table)

    if work_order.closure_remarks:
        story.append(Spacer(1, 2 * mm))
        closure_table = Table([
            [Paragraph("<b>Closure Remarks:</b>", styles["Label"])],
            [Paragraph(get_val(work_order.closure_remarks), styles["Value"])],
        ], colWidths=[drawable_width])
        closure_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
        ]))
        story.append(closure_table)

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Work_Order_{work_order.work_order_number}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 3. Training Sign-Off Report — CAPA Style (white + grey)
# =============================================================================
def generate_training_signoff_pdf(signoff):
    """Generate a Training Sign-Off PDF in CAPA white/grey style."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=f"TSO-{signoff.signoff_number}",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="TRAINING SIGN-OFF REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    # ---- Reference strip ----
    ref_data = [[
        Paragraph(f"<b>Sign-Off No.:</b> {signoff.signoff_number}", styles["ReportTitle"]),
        Paragraph(f"<b>Status:</b><br/>{signoff.get_status_display()}", styles["HeaderInfo"]),
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

    # ==========================================================
    # 1. CONTRACTOR DETAILS
    # ==========================================================
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Contractor Details</b>", styles["SectionHeader"]))

    contractor = signoff.contractor
    contractor_data = [
        [Paragraph("<b>Contractor Name:</b>", styles["Label"]),
         Paragraph(get_val(contractor.contractor_name), styles["Value"]),
         Paragraph("<b>Contractor Code:</b>", styles["Label"]),
         Paragraph(get_val(contractor.contractor_code), styles["Value"])],
        [Paragraph("<b>Contractor Type:</b>", styles["Label"]),
         Paragraph(get_val(contractor.get_contractor_type_display()), styles["Value"]),
         Paragraph("<b>Work Category:</b>", styles["Label"]),
         Paragraph(get_val(contractor.get_work_category_display()), styles["Value"])],
        [Paragraph("<b>Contact Person:</b>", styles["Label"]),
         Paragraph(get_val(contractor.contact_person), styles["Value"]),
         Paragraph("<b>Designation:</b>", styles["Label"]),
         Paragraph(get_val(contractor.designation), styles["Value"])],
        [Paragraph("<b>Mobile:</b>", styles["Label"]),
         Paragraph(get_val(contractor.mobile), styles["Value"]),
         Paragraph("<b>Email:</b>", styles["Label"]),
         Paragraph(get_val(contractor.email), styles["Value"])],
        [Paragraph("<b>EHS Officer:</b>", styles["Label"]),
         Paragraph(get_val(contractor.ehs_officer_name), styles["Value"]),
         Paragraph("<b>EHS Contact:</b>", styles["Label"]),
         Paragraph(get_val(contractor.ehs_mobile), styles["Value"])],
        [Paragraph("<b>Address:</b>", styles["Label"]),
         Paragraph(
             get_val(
                 f"{contractor.address_line1}, "
                 f"{contractor.city}, {contractor.state} - {contractor.pincode}"
             ),
             styles["Value"],
         ),
         Paragraph("<b>Country:</b>", styles["Label"]),
         Paragraph(get_val(contractor.country), styles["Value"])],
    ]
    contractor_table = Table(contractor_data, colWidths=[col4] * 4)
    contractor_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(contractor_table)

    # ==========================================================
    # 2. TRAINING DETAILS
    # ==========================================================
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>Training Details</b>", styles["SectionHeader"]))

    topic_title = "N/A"
    session_no = "N/A"
    topic_description = ""
    if signoff.session:
        session_no = signoff.session.session_no
        if hasattr(signoff.session, 'topic') and signoff.session.topic:
            topic_title = signoff.session.topic.topic_title
            topic_description = getattr(signoff.session.topic, 'description', '') or ''

    training_data = [
        [Paragraph("<b>Work Order:</b>", styles["Label"]),
         Paragraph(get_val(signoff.work_order.work_order_number if signoff.work_order else ""), styles["Value"]),
         Paragraph("<b>Session No:</b>", styles["Label"]),
         Paragraph(get_val(session_no), styles["Value"])],
        [Paragraph("<b>Training Topic:</b>", styles["Label"]),
         Paragraph(get_val(topic_title), styles["Value"]),
         Paragraph("<b>Training Date:</b>", styles["Label"]),
         Paragraph(signoff.signoff_date.strftime("%d/%m/%Y") if signoff.signoff_date else "N/A", styles["Value"])],
        [Paragraph("<b>Contractor Representative:</b>", styles["Label"]),
         Paragraph(get_val(signoff.contractor_representative), styles["Value"]),
         Paragraph("<b>Designation:</b>", styles["Label"]),
         Paragraph(get_val(signoff.contractor_representative_designation), styles["Value"])],
        [Paragraph("<b>Number of Workers:</b>", styles["Label"]),
         Paragraph(str(signoff.number_of_workers), styles["Value"]),
         Paragraph("<b>Sign-Off Time:</b>", styles["Label"]),
         Paragraph(signoff.signoff_time.strftime("%H:%M") if signoff.signoff_time else "N/A", styles["Value"])],
    ]
    training_table = Table(training_data, colWidths=[col4] * 4)
    training_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(training_table)

    # Topic description (only if present)
    if topic_description:
        story.append(Spacer(1, 2 * mm))
        desc_table = Table([
            [Paragraph("<b>Topic Description:</b>", styles["Label"])],
            [Paragraph(get_val(topic_description), styles["Value"])],
        ], colWidths=[drawable_width])
        desc_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
        ]))
        story.append(desc_table)

    # ==========================================================
    # 3. DECLARATIONS (Company + Contractor)
    # ==========================================================
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>Company Sign-Off</b>", styles["SectionHeader"]))

    company_data = [
        [Paragraph("<b>Declaration:</b>", styles["Label"]),
         Paragraph(
             "I confirm that the above listed contractor and its workers "
             "have received the required safety training and have been made "
             "aware of the applicable EHS requirements.",
             styles["Value"],
         )],
        [Paragraph("<b>Agreed:</b>", styles["Label"]),
         Paragraph("<b>Yes</b>" if signoff.company_declaration else "No", styles["Value"])],
        [Paragraph("<b>Company Representative:</b>", styles["Label"]),
         Paragraph(get_val(signoff.company_representative.get_full_name() if signoff.company_representative else ""), styles["Value"])],
        [Paragraph("<b>Designation:</b>", styles["Label"]),
         Paragraph(get_val(signoff.company_representative_designation), styles["Value"])],
    ]
    company_table = Table(company_data, colWidths=[col4, col4 * 3])
    company_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(company_table)

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Contractor Sign-Off</b>", styles["SectionHeader"]))

    contractor_declaration = [
        [Paragraph("<b>Declaration:</b>", styles["Label"]),
         Paragraph(
             "I confirm that the above listed workers have received the required "
             "safety training and have understood the applicable EHS requirements.",
             styles["Value"],
         )],
        [Paragraph("<b>Agreed:</b>", styles["Label"]),
         Paragraph("<b>Yes</b>" if signoff.contractor_declaration else "No", styles["Value"])],
        [Paragraph("<b>Supervisor:</b>", styles["Label"]),
         Paragraph(get_val(signoff.contractor_supervisor), styles["Value"])],
        [Paragraph("<b>Designation:</b>", styles["Label"]),
         Paragraph(get_val(signoff.contractor_supervisor_designation), styles["Value"])],
    ]
    contractor_table = Table(contractor_declaration, colWidths=[col4, col4 * 3])
    contractor_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(contractor_table)

    # ==========================================================
    # 4. SIGNATURE BLOCK — anchored bottom-right
    # ==========================================================
    # Spacer to push the signature toward the bottom of the page.
    # Adjust the spacer height to control the vertical position.
    story.append(Spacer(1, 40 * mm))

    # A blank line for the signature to be written on
    signature_cell = Paragraph(
        "&nbsp;<br/>&nbsp;<br/>"
        "<font size='8' color='#6c757d'>_____________________________</font>",
        styles["Value"],
    )

    # Right-aligned signature table:
    #   [ empty | signature area ]
    # This pushes the signature into the right column.
    signature_table = Table(
        [[ "", signature_cell ]],
        colWidths=[drawable_width * 0.55, drawable_width * 0.45],
    )
    signature_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(signature_table)

    # Label under the signature line, also right-aligned
    signature_label = Table(
        [[
            "",
            Paragraph(
                "<b>Authorized Signature</b><br/>"
                "<font size='7.5' color='#6c757d'>EHS Representative</font>",
                styles["Value"],
            ),
        ]],
        colWidths=[drawable_width * 0.55, drawable_width * 0.45],
    )
    signature_label.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(signature_label)

    # ==========================================================
    # 5. SUPPORTING DOCUMENT (optional)
    # ==========================================================
    if signoff.supporting_documents:
        doc_path = _safe_file_path(signoff.supporting_documents)
        if doc_path:
            story.append(Spacer(1, 6 * mm))
            story.append(Paragraph("<b>Supporting Document</b>", styles["SectionHeader"]))
            _embed_image(story, doc_path, styles["Value"], max_width_mm=90, max_height_mm=70)

    # ==========================================================
    # 6. FOOTER
    # ==========================================================
    story.append(Spacer(1, 8 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Training_SignOff_{signoff.signoff_number}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 4. Contractor Inspection Report
# =============================================================================
def generate_inspection_pdf(inspection):
    """Generate a Contractor Inspection Report PDF."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=f"EIL/IRI/EHS/F-11",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="CONTRACTOR INSPECTION REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    ref_data = [[
        Paragraph(f"<b>Inspection Code:</b> {inspection.inspection_code}", styles["ReportTitle"]),
        Paragraph(f"<b>Status:</b><br/>{inspection.get_status_display()}", styles["HeaderInfo"]),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Inspection Details</b>", styles["SectionHeader"]))

    details_data = [
        [Paragraph("<b>Contractor:</b>", styles["Label"]),
         Paragraph(get_val(inspection.contractor.contractor_name), styles["Value"]),
         Paragraph("<b>Work Order:</b>", styles["Label"]),
         Paragraph(get_val(inspection.work_order.work_order_number if inspection.work_order else ""), styles["Value"])],
        [Paragraph("<b>Plant:</b>", styles["Label"]),
         Paragraph(get_val(inspection.plant.name if inspection.plant else ""), styles["Value"]),
         Paragraph("<b>Department:</b>", styles["Label"]),
         Paragraph(get_val(inspection.department.name if inspection.department else ""), styles["Value"])],
        [Paragraph("<b>Zone:</b>", styles["Label"]),
         Paragraph(get_val(inspection.zone.name if inspection.zone else ""), styles["Value"]),
         Paragraph("<b>Location:</b>", styles["Label"]),
         Paragraph(get_val(inspection.location.name if inspection.location else ""), styles["Value"])],
        [Paragraph("<b>Assigned To:</b>", styles["Label"]),
         Paragraph(get_val(inspection.assigned_to.get_full_name() if inspection.assigned_to else ""), styles["Value"]),
         Paragraph("<b>Assigned By:</b>", styles["Label"]),
         Paragraph(get_val(inspection.assigned_by.get_full_name() if inspection.assigned_by else ""), styles["Value"])],
        [Paragraph("<b>Start Date:</b>", styles["Label"]),
         Paragraph(inspection.inspection_start_date.strftime("%d/%m/%Y") if inspection.inspection_start_date else "N/A", styles["Value"]),
         Paragraph("<b>End Date:</b>", styles["Label"]),
         Paragraph(inspection.inspection_end_date.strftime("%d/%m/%Y") if inspection.inspection_end_date else "N/A", styles["Value"])],
        [Paragraph("<b>Number of Workers:</b>", styles["Label"]),
         Paragraph(str(inspection.number_of_workers), styles["Value"]),
         Paragraph("<b>Contractor Supervisor:</b>", styles["Label"]),
         Paragraph(get_val(inspection.contractor_supervisor), styles["Value"])],
    ]
    details_table = Table(details_data, colWidths=[col4] * 4)
    details_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(details_table)

    responses = inspection.responses.select_related('question').all()
    total_questions = inspection.selected_questions.count()
    yes_count = responses.filter(answer='YES').count()
    no_count = responses.filter(answer='NO').count()
    compliance_score = round((yes_count / total_questions) * 100, 1) if total_questions > 0 else 0

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Compliance Summary</b>", styles["SectionHeader"]))

    score_data = [
        [Paragraph("<b>Total Questions:</b>", styles["Label"]),
         Paragraph(str(total_questions), styles["Value"]),
         Paragraph("<b>YES:</b>", styles["Label"]),
         Paragraph(str(yes_count), styles["Value"])],
        [Paragraph("<b>NO:</b>", styles["Label"]),
         Paragraph(str(no_count), styles["Value"]),
         Paragraph("<b>Compliance Score:</b>", styles["Label"]),
         Paragraph(f"<b>{compliance_score}%</b>", styles["Value"])],
        [Paragraph("<b>Rating:</b>", styles["Label"]),
         Paragraph(_get_rating(compliance_score), styles["Value"]),
         Paragraph("", styles["Value"]),
         Paragraph("", styles["Value"])],
    ]
    score_table = Table(score_data, colWidths=[col4] * 4)
    score_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(score_table)

    if responses:
        story.append(PageBreak())
        story.append(Paragraph("<b>Detailed Inspection Responses</b>", styles["SectionHeader"]))

        responses_by_category = {}
        for resp in responses:
            cat = resp.question.get_category_display()
            if cat not in responses_by_category:
                responses_by_category[cat] = []
            responses_by_category[cat].append(resp)

        for cat_name, cat_responses in responses_by_category.items():
            story.append(Paragraph(f"<b>{cat_name}</b>", styles["Label"]))
            story.append(Spacer(1, 2 * mm))

            cat_data = [
                [Paragraph("<b>Sr.</b>", styles["Label"]),
                 Paragraph("<b>Question</b>", styles["Label"]),
                 Paragraph("<b>Answer</b>", styles["Label"]),
                 Paragraph("<b>Remarks</b>", styles["Label"])]
            ]
            for idx, resp in enumerate(cat_responses, 1):
                cat_data.append([
                    Paragraph(str(idx), styles["Value"]),
                    Paragraph(get_val(resp.question.question_text), styles["Value"]),
                    Paragraph(resp.get_answer_display(), styles["Value"]),
                    Paragraph(get_val(resp.remarks), styles["Value"]),
                ])

            cat_table = Table(cat_data, colWidths=[
                drawable_width * 0.05,
                drawable_width * 0.55,
                drawable_width * 0.15,
                drawable_width * 0.25,
            ])
            cat_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(cat_table)
            story.append(Spacer(1, 4 * mm))

            for resp in cat_responses:
                if resp.photo:
                    photo_path = _safe_file_path(resp.photo)
                    if photo_path:
                        _embed_image(
                            story, photo_path, styles["Value"],
                            max_width_mm=60, max_height_mm=45,
                            caption=f"Photo: {resp.question.question_text[:50]}"
                        )

    if inspection.notes:
        story.append(Spacer(1, 4 * mm))
        notes_table = Table([
            [Paragraph("<b>Notes:</b>", styles["Label"])],
            [Paragraph(get_val(inspection.notes), styles["Value"])],
        ], colWidths=[drawable_width])
        notes_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
        ]))
        story.append(notes_table)

    story.append(Spacer(1, 10 * mm))
    sig_data = [
        [Paragraph("<b>Inspected By</b>", styles["Label"]),
         Paragraph("<b>Reviewed By</b>", styles["Label"]),
         Paragraph("<b>Approved By</b>", styles["Label"])],
        [Paragraph("", styles["Value"]), Paragraph("", styles["Value"]), Paragraph("", styles["Value"])],
        [Paragraph("_________________", styles["Value"]),
         Paragraph("_________________", styles["Value"]),
         Paragraph("_________________", styles["Value"])],
        [Paragraph(get_val(inspection.assigned_to.get_full_name() if inspection.assigned_to else ""), styles["Value"]),
         Paragraph("", styles["Value"]),
         Paragraph("", styles["Value"])],
    ]
    sig_table = Table(sig_data, colWidths=[col4 * 1.33] * 3)
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), 'Helvetica-Bold'),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), 'CENTER'),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, 1), 30),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Inspection_{inspection.inspection_code}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 5. Contractor Log Book
# =============================================================================
def generate_contractor_logbook_pdf(year, queryset=None):
    """Generate a Contractor Log Book PDF for a given year."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer, left_margin=10 * mm, right_margin=10 * mm)
    styles = _get_styles()

    header_table = _header_table(
        styles, drawable_width,
        doc_no="EIL/IRI/EHS/F-12",
        rev_info="REV NO: 00 &<br/>DATE: 01-09-2021",
        title_line2="CONTRACTOR LOG BOOK",
    )
    draw_header = _make_draw_header(header_table)

    story = [Spacer(1, 4 * mm)]
    story.append(Paragraph(f"<b>Year:</b> {year}", styles["ReportTitle"]))
    story.append(Spacer(1, 3 * mm))

    qs = queryset if queryset is not None else Contractor.objects.filter(
        created_at__year=year
    ).order_by("created_at")

    log_headers = [
        "Sr.\nNo.", "Date", "Contractor Code", "Contractor Name",
        "Work Category", "Status", "Contact Person", "Mobile", "Sign &\nDate", "Remark",
    ]
    rows = [[Paragraph(f"<b>{h}</b>", styles["Value"]) for h in log_headers]]

    for i, contractor in enumerate(qs, start=1):
        rows.append([
            Paragraph(str(i), styles["Value"]),
            Paragraph(contractor.created_at.strftime("%d/%m/%Y"), styles["Value"]),
            Paragraph(get_val(contractor.contractor_code), styles["Value"]),
            Paragraph(get_val(contractor.contractor_name), styles["Value"]),
            Paragraph(get_val(contractor.get_work_category_display()), styles["Value"]),
            Paragraph(contractor.get_status_display(), styles["Value"]),
            Paragraph(get_val(contractor.contact_person), styles["Value"]),
            Paragraph(get_val(contractor.mobile), styles["Value"]),
            Paragraph("", styles["Value"]),
            Paragraph("", styles["Value"]),
        ])
    if len(rows) == 1:
        rows.append([Paragraph("", styles["Value"])] * 10)

    widths_pct = [0.05, 0.08, 0.10, 0.18, 0.12, 0.08, 0.12, 0.10, 0.06, 0.11]
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
    response["Content-Disposition"] = f'attachment; filename="Contractor_LogBook_{year}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 6. Contractor Performance Report
# =============================================================================
def generate_performance_pdf(contractor):
    """Generate a Contractor Performance Report PDF."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=f"EIL/IRI/EHS/F-13",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="CONTRACTOR PERFORMANCE REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    ref_data = [[
        Paragraph(f"<b>Contractor:</b> {contractor.contractor_name}", styles["ReportTitle"]),
        Paragraph(f"<b>Code:</b><br/>{contractor.contractor_code}", styles["HeaderInfo"]),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    metrics = ContractorPerformanceMetric.objects.filter(
        contractor=contractor
    ).order_by('-period_year', '-period_month')

    latest = metrics.first()

    if latest:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Latest Performance Metrics</b>", styles["SectionHeader"]))

        perf_data = [
            [Paragraph("<b>Period:</b>", styles["Label"]),
             Paragraph(f"{latest.period_month}/{latest.period_year}", styles["Value"]),
             Paragraph("<b>Overall Score:</b>", styles["Label"]),
             Paragraph(f"<b>{latest.overall_performance_score:.1f}%</b>", styles["Value"])],
            [Paragraph("<b>Rating:</b>", styles["Label"]),
             Paragraph(latest.rating, styles["Value"]),
             Paragraph("<b>Risk Level:</b>", styles["Label"]),
             Paragraph(get_val(latest.risk_level), styles["Value"])],
        ]
        perf_table = Table(perf_data, colWidths=[col4] * 4)
        perf_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(perf_table)

        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Score Breakdown</b>", styles["SectionHeader"]))

        breakdown_data = [
            [Paragraph("<b>Onboarding Compliance:</b>", styles["Label"]),
             Paragraph(f"{latest.document_compliance_score:.1f}%", styles["Value"]),
             Paragraph("<b>Training Compliance:</b>", styles["Label"]),
             Paragraph(f"{latest.training_compliance_score:.1f}%", styles["Value"])],
            [Paragraph("<b>Inspection Compliance:</b>", styles["Label"]),
             Paragraph(f"{latest.inspection_compliance_score:.1f}%", styles["Value"]),
             Paragraph("<b>Work Order Completion:</b>", styles["Label"]),
             Paragraph(f"{latest.work_order_completion_score:.1f}%", styles["Value"])],
            [Paragraph("<b>Inspections Count:</b>", styles["Label"]),
             Paragraph(str(latest.inspections_count), styles["Value"]),
             Paragraph("<b>Work Orders Count:</b>", styles["Label"]),
             Paragraph(str(latest.work_orders_count), styles["Value"])],
        ]
        breakdown_table = Table(breakdown_data, colWidths=[col4] * 4)
        breakdown_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(breakdown_table)

    if metrics.count() > 1:
        story.append(PageBreak())
        story.append(Paragraph("<b>Performance History</b>", styles["SectionHeader"]))

        hist_data = [
            [Paragraph("<b>Period</b>", styles["Label"]),
             Paragraph("<b>Overall</b>", styles["Label"]),
             Paragraph("<b>Rating</b>", styles["Label"]),
             Paragraph("<b>Onboarding</b>", styles["Label"]),
             Paragraph("<b>Training</b>", styles["Label"]),
             Paragraph("<b>Inspection</b>", styles["Label"]),
             Paragraph("<b>Work Order</b>", styles["Label"])]
        ]
        for m in metrics[:12]:
            hist_data.append([
                Paragraph(f"{m.period_month}/{m.period_year}", styles["Value"]),
                Paragraph(f"{m.overall_performance_score:.1f}%", styles["Value"]),
                Paragraph(m.rating, styles["Value"]),
                Paragraph(f"{m.document_compliance_score:.1f}%", styles["Value"]),
                Paragraph(f"{m.training_compliance_score:.1f}%", styles["Value"]),
                Paragraph(f"{m.inspection_compliance_score:.1f}%", styles["Value"]),
                Paragraph(f"{m.work_order_completion_score:.1f}%", styles["Value"]),
            ])

        hist_table = Table(hist_data, colWidths=[
            drawable_width * 0.12, drawable_width * 0.14, drawable_width * 0.18,
            drawable_width * 0.14, drawable_width * 0.14, drawable_width * 0.14,
            drawable_width * 0.14,
        ])
        hist_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(hist_table)

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Performance_{contractor.contractor_code}.pdf"'
    response.write(pdf)
    return response


# =============================================================================
# 7. Contractor Onboarding Report
# =============================================================================
def generate_onboarding_pdf(onboarding):
    """Generate an Onboarding Report PDF for a contractor."""
    buffer = BytesIO()
    doc, drawable_width = _new_doc(buffer)
    styles = _get_styles()
    col4 = drawable_width / 4

    header_table = _header_table(
        styles, drawable_width,
        doc_no=f"EIL/IRI/EHS/F-14",
        rev_info=f"REV NO: 00 &amp;<br/>DATE: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        title_line2="CONTRACTOR ONBOARDING REPORT",
    )
    draw_header = _make_draw_header(header_table)

    story = []
    story.append(Spacer(1, 4 * mm))

    ref_data = [[
        Paragraph(f"<b>Contractor:</b> {onboarding.contractor.contractor_name}", styles["ReportTitle"]),
        Paragraph(f"<b>Status:</b><br/>{onboarding.get_status_display()}", styles["HeaderInfo"]),
    ]]
    ref_table = Table(ref_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_table)

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Onboarding Details</b>", styles["SectionHeader"]))

    basic_data = [
        [Paragraph("<b>Contractor Code:</b>", styles["Label"]),
         Paragraph(get_val(onboarding.contractor.contractor_code), styles["Value"]),
         Paragraph("<b>EHS Officer:</b>", styles["Label"]),
         Paragraph(get_val(onboarding.ehs_officer.get_full_name() if onboarding.ehs_officer else ""), styles["Value"])],
        [Paragraph("<b>Submitted By:</b>", styles["Label"]),
         Paragraph(get_val(onboarding.submitted_by.get_full_name() if onboarding.submitted_by else ""), styles["Value"]),
         Paragraph("<b>Submitted At:</b>", styles["Label"]),
         Paragraph(onboarding.submitted_at.strftime("%d/%m/%Y") if onboarding.submitted_at else "N/A", styles["Value"])],
        [Paragraph("<b>Approved By:</b>", styles["Label"]),
         Paragraph(get_val(onboarding.approved_by.get_full_name() if onboarding.approved_by else ""), styles["Value"]),
         Paragraph("<b>Approved At:</b>", styles["Label"]),
         Paragraph(onboarding.approved_at.strftime("%d/%m/%Y") if onboarding.approved_at else "N/A", styles["Value"])],
    ]
    basic_table = Table(basic_data, colWidths=[col4] * 4)
    basic_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(basic_table)

    if onboarding.rejection_reason:
        story.append(Spacer(1, 2 * mm))
        reject_table = Table([
            [Paragraph("<b>Rejection Reason:</b>", styles["Label"])],
            [Paragraph(get_val(onboarding.rejection_reason), styles["Value"])],
        ], colWidths=[drawable_width])
        reject_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), HEADER_BG_COLOR),
        ]))
        story.append(reject_table)

    doc_requirements = onboarding.document_requirements.select_related('document_type').all()

    if doc_requirements:
        story.append(PageBreak())
        story.append(Paragraph("<b>Document Requirements</b>", styles["SectionHeader"]))

        doc_data = [
            [Paragraph("<b>Sr.</b>", styles["Label"]),
             Paragraph("<b>Document Name</b>", styles["Label"]),
             Paragraph("<b>Required</b>", styles["Label"]),
             Paragraph("<b>Status</b>", styles["Label"]),
             Paragraph("<b>Uploaded By</b>", styles["Label"]),
             Paragraph("<b>Verified By</b>", styles["Label"])]
        ]
        for idx, doc in enumerate(doc_requirements, 1):
            doc_data.append([
                Paragraph(str(idx), styles["Value"]),
                Paragraph(get_val(doc.document_type.name), styles["Value"]),
                Paragraph("Yes" if doc.is_required else "No", styles["Value"]),
                Paragraph(doc.get_status_display(), styles["Value"]),
                Paragraph(get_val(doc.uploaded_by.get_full_name() if doc.uploaded_by else ""), styles["Value"]),
                Paragraph(get_val(doc.verified_by.get_full_name() if doc.verified_by else ""), styles["Value"]),
            ])

        doc_table = Table(doc_data, colWidths=[
            drawable_width * 0.05,
            drawable_width * 0.25,
            drawable_width * 0.10,
            drawable_width * 0.15,
            drawable_width * 0.22,
            drawable_width * 0.23,
        ])
        doc_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(doc_table)

        for doc in doc_requirements:
            if doc.document_file:
                file_path = _safe_file_path(doc.document_file)
                if file_path:
                    _embed_image(
                        story, file_path, styles["Value"],
                        max_width_mm=70, max_height_mm=50,
                        caption=f"{doc.document_type.name} ({doc.get_status_display()})"
                    )

    story.append(Spacer(1, 10 * mm))
    story.append(_footer_paragraph(styles))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Onboarding_{onboarding.contractor.contractor_code}.pdf"'
    response.write(pdf)
    return response