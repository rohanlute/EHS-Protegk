"""Generate the Kaizen final PDF"""

import os
from html import escape
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class NumberedCanvas(canvas.Canvas):
    """Canvas that prints Injury-style ``Page X of Y`` numbering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(page_count)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 9)
        self.setFillColor(colors.darkgrey)
        self.drawRightString(200 * mm, 15 * mm, f'Page {self._pageNumber} of {page_count}')
        self.restoreState()


def generate_kaizen_final_report(kaizen):
    buffer = BytesIO()
    header_height = 1.6 * inch
    left_margin = 15 * mm
    right_margin = 15 * mm
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=header_height + 22 * mm,
        bottomMargin=25 * mm,
        title=f'Kaizen Final Report - {kaizen.kaizen_id or kaizen.pk}',
        author='EHS-360',
    )
    drawable_width = A4[0] - left_margin - right_margin

    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
    bold_font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf')
    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('KaizenDejaVu', font_path))
            font_name = 'KaizenDejaVu'
        if os.path.exists(bold_font_path):
            pdfmetrics.registerFont(TTFont('KaizenDejaVu-Bold', bold_font_path))
            font_bold = 'KaizenDejaVu-Bold'
        elif font_name == 'KaizenDejaVu':
            font_bold = font_name
    except Exception:
        font_name, font_bold = 'Helvetica', 'Helvetica-Bold'

    primary_text = colors.HexColor('#212529')
    secondary_text = colors.HexColor('#495057')
    header_background = colors.HexColor('#F8F9FA')
    border = colors.HexColor('#DEE2E6')
    teal = colors.HexColor('#0D9488')
    report_title = 'KAIZEN FINAL REPORT' if kaizen.status == kaizen.StatusChoices.CLOSED else 'KAIZEN PROGRESS REPORT'

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='KZHeaderTitle', fontName=font_bold, fontSize=10,
        alignment=TA_CENTER, textColor=primary_text, leading=13,
    ))
    styles.add(ParagraphStyle(
        name='KZHeaderInfo', fontName=font_name, fontSize=8,
        alignment=TA_LEFT, textColor=secondary_text, leading=11,
    ))
    styles.add(ParagraphStyle(
        name='KZReportTitle', fontName=font_bold, fontSize=11,
        alignment=TA_LEFT, textColor=primary_text, leading=14,
    ))
    styles.add(ParagraphStyle(
        name='KZSectionHeader', fontName=font_bold, fontSize=10,
        alignment=TA_LEFT, textColor=primary_text, leading=13,
        spaceBefore=10, spaceAfter=4, keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name='KZLabel', fontName=font_bold, fontSize=8.5,
        alignment=TA_LEFT, textColor=primary_text, leading=11,
    ))
    styles.add(ParagraphStyle(
        name='KZValue', fontName=font_name, fontSize=8.5,
        alignment=TA_LEFT, textColor=secondary_text, leading=12,
    ))
    styles.add(ParagraphStyle(
        name='KZFooterText', fontName=font_name, fontSize=8,
        alignment=TA_CENTER, textColor=colors.darkgrey,
    ))

    def printable(value, default='N/A'):
        if value is None or value == '':
            return default
        if hasattr(value, 'strftime'):
            value = value.strftime('%d/%m/%Y')
        return str(value)

    def para(value, style='KZValue'):
        safe = escape(printable(value)).replace('\n', '<br/>')
        return Paragraph(safe, styles[style])

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.jpg')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.2 * inch, height=header_height)
    else:
        logo = Paragraph('<b>EHS-360</b>', styles['KZHeaderTitle'])
    header_data = [
        [logo, para('EHS-360 KAIZEN MANAGEMENT SYSTEM', 'KZHeaderTitle'), para('DOC NO: EHS/KZN/FR-01', 'KZHeaderInfo')],
        ['', para(report_title, 'KZHeaderTitle'), Paragraph('REV NO: 00<br/>DATE: 02-11-2026', styles['KZHeaderInfo'])],
    ]
    header_table = Table(
        header_data,
        colWidths=[drawable_width * 0.2875, drawable_width * 0.4875, drawable_width * 0.225],
        rowHeights=[0.8 * inch, 0.8 * inch],
    )
    header_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('SPAN', (0, 0), (0, 1)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    def draw_header(pdf_canvas, doc):
        pdf_canvas.saveState()
        _, height = header_table.wrap(doc.width, doc.topMargin)
        header_table.drawOn(pdf_canvas, doc.leftMargin, doc.height + doc.topMargin - height + 5 * mm)
        pdf_canvas.restoreState()

    story = [Spacer(1, 4 * mm)]
    reference_table = Table(
        [[
            para(report_title.title(), 'KZReportTitle'),
            Paragraph(
                f'<b>Reference number:</b><br/>{escape(str(kaizen.kaizen_id or f"KZN-{kaizen.pk}"))}',
                styles['KZHeaderInfo'],
            ),
        ]],
        colWidths=[drawable_width * 0.7, drawable_width * 0.3],
    )
    reference_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(reference_table)

    def section(title, pairs=None):
        story.append(Paragraph(f'<b>{escape(title.upper())}</b>', styles['KZSectionHeader']))
        if not pairs:
            return
        rows = [[para(label, 'KZLabel'), para(value)] for label, value in pairs]
        table = Table(rows, colWidths=[drawable_width * 0.28, drawable_width * 0.72], repeatRows=0)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, border),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, -1), header_background),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    def records(title, entries, get_rows, empty_text='No records were entered.'):
        story.append(Paragraph(f'<b>{escape(title.upper())}</b>', styles['KZSectionHeader']))
        entries = list(entries)
        if not entries:
            story.append(para(empty_text))
            return
        for index, entry in enumerate(entries, 1):
            rows = [[para(label, 'KZLabel'), para(value)] for label, value in get_rows(entry)]
            table = Table(rows, colWidths=[drawable_width * 0.28, drawable_width * 0.72])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, border),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, 0), header_background),
                ('BACKGROUND', (0, 1), (0, -1), header_background),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(table)
            story.append(Spacer(1, 2 * mm))

    if kaizen.has_related_record:
        try:
            related_source = kaizen.related_record or (
                f'{kaizen.get_related_module_display()} record #{kaizen.related_object_id}'
            )
        except Exception:
            related_source = f'{kaizen.get_related_module_display()} record #{kaizen.related_object_id}'
    else:
        related_source = kaizen.manual_source_reference

    section('Section 1: Idea and Personnel Details', [
        ('Idea title', kaizen.title),
        ('Current status', kaizen.get_status_display()),
        ('Category', kaizen.category),
        ('Submitted by', kaizen.submitted_by),
        ('Submission date', kaizen.submission_date or kaizen.created_at),
        ('Plant / department', f'{kaizen.plant or "N/A"} / {kaizen.department or "N/A"}'),
        ('Zone / location', f'{kaizen.zone or "N/A"} / {kaizen.location_record or kaizen.location or "N/A"}'),
        ('Sub-location', kaizen.sublocation),
        ('Additional location details', kaizen.additional_location_details),
        ('Priority / benefit type', f'{kaizen.get_priority_display()} / {kaizen.get_benefit_type_display()}'),
        ('Related source', related_source),
        ('Description', kaizen.description),
        ('Problem statement', kaizen.problem_statement),
        ('Proposed solution', kaizen.proposed_solution),
        ('Expected benefits', kaizen.expected_benefits),
        ('Estimated cost', kaizen.estimated_cost),
    ])

    initial_reviews = list(kaizen.initial_reviews.all())
    if initial_reviews:
        records('Section 2: Initial Review', initial_reviews, lambda item: [
        ('Decision', item.get_decision_display()),
        ('Reviewer / date', f'{item.reviewed_by} / {item.review_date:%d/%m/%Y %H:%M}'),
        ('Comments', item.review_comments),
        ('Clarification required', item.clarification_required),
        ])

    technical_evaluations = list(kaizen.technical_evaluations.all())
    if technical_evaluations:
        records('Section 3: Technical Evaluation', technical_evaluations, lambda item: [
        ('Decision / feasibility', f'{item.get_decision_display()} / {item.get_feasibility_display()}'),
        ('Evaluator / date', f'{item.evaluated_by} / {item.evaluation_date:%d/%m/%Y %H:%M}'),
        ('Technical comments', item.technical_comments),
        ('Safety impact', item.safety_impact),
        ('Operational impact', item.operational_impact),
        ('Resource requirements', item.resource_requirements),
        ('Estimated cost / completion', f'{item.estimated_implementation_cost or "N/A"} / {item.estimated_completion_date or "N/A"}'),
        ('Recommendation', item.recommendation),
        ])

    approvals = list(kaizen.approvals.all())
    if approvals:
        records('Section 4: Approval Details', approvals, lambda item: [
        ('Decision', item.get_decision_display()),
        ('Approver / date', f'{item.approved_by} / {item.approval_date:%d/%m/%Y %H:%M}'),
        ('Comments', item.approval_comments),
        ])

    implementations = list(kaizen.implementations.all())
    if implementations:
        records('Section 5: Implementation Details', implementations, lambda item: [
        ('Owner / status', f'{item.implementation_owner} / {item.get_implementation_status_display()}'),
        ('Planned schedule', f'{item.planned_start_date or "N/A"} to {item.planned_end_date or "N/A"}'),
        ('Actual schedule', f'{item.actual_start_date or "N/A"} to {item.actual_end_date or "N/A"}'),
        ('Implementation plan', item.implementation_actions),
        ('Resources used', item.resources_used),
        ('Actual cost', item.actual_cost),
        ('Completion / implementation remarks', item.implementation_remarks),
        ])

    verifications = list(kaizen.verifications.all())
    if verifications:
        records('Section 6: Verification Details', verifications, lambda item: [
        ('Result', item.get_result_display()),
        ('Rework required', 'Yes' if item.rework_required else 'No' if item.rework_required is False else '—'),
        ('Verifier / date', f'{item.verified_by} / {item.verification_date:%d/%m/%Y %H:%M}'),
        ('Verification method', item.verification_method),
        ('Before improvement', item.before_improvement),
        ('After improvement', item.after_improvement),
        ('Actual benefits', item.actual_benefits),
        ('Evidence details', item.evidence_details),
        ('Comments', item.verification_comments),
        ])

    closure = getattr(kaizen, 'closure', None)
    if closure:
        section('Section 7: Kaizen Closure Details', [
            ('Final outcome', closure.final_outcome),
            ('Actual benefits', closure.actual_benefits),
            ('Actual implementation cost', closure.actual_implementation_cost),
            ('Lessons learned', closure.lessons_learned),
            ('Closure comments', closure.closure_comments),
            ('Closed by / date', f'{closure.closed_by} / {closure.closure_date:%d/%m/%Y %H:%M}'),
        ])

    story.append(Spacer(1, 10 * mm))
    generated_at = timezone.localtime(timezone.now()).strftime('%d-%b-%Y at %H:%M hrs')
    story.append(Paragraph(
        f'Document generated from EHS-360 System on {generated_at}',
        styles['KZFooterText'],
    ))

    def draw_footer(pdf_canvas, doc):
        pdf_canvas.saveState()
        pdf_canvas.setStrokeColor(border)
        pdf_canvas.line(15 * mm, 13 * mm, 195 * mm, 13 * mm)
        pdf_canvas.setFont('Helvetica', 7)
        pdf_canvas.setFillColor(colors.darkgrey)
        pdf_canvas.drawString(15 * mm, 8 * mm, f'EHS-360 | Kaizen {kaizen.kaizen_id or kaizen.pk}')
        pdf_canvas.restoreState()

    document.build(
        story,
        onFirstPage=lambda pdf_canvas, doc: (draw_header(pdf_canvas, doc), draw_footer(pdf_canvas, doc)),
        onLaterPages=lambda pdf_canvas, doc: (draw_header(pdf_canvas, doc), draw_footer(pdf_canvas, doc)),
        canvasmaker=NumberedCanvas,
    )
    buffer.seek(0)
    return buffer
