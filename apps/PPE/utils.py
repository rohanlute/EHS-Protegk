import os
import datetime
from io import BytesIO
from collections import defaultdict
from html import escape
from django.conf import settings
from django.http import HttpResponse
from .models import *
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus import Frame, PageTemplate

def generate_ppe_inspection_pdf(schedule):

    buffer = BytesIO()

    header_height = 1.6 * inch
    left_margin = 15 * mm
    right_margin = 15 * mm

    doc = SimpleDocTemplate(
    buffer,
    pagesize=A4,
    rightMargin=right_margin,
    leftMargin=left_margin,
    topMargin=25 * mm,
    bottomMargin=25 * mm
    )
    story = []

    drawable_width = A4[0] - left_margin - right_margin


    # ---------------- STYLES ----------------

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="HeaderTitle",
        fontSize=10,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="HeaderInfo",
        fontSize=9,
        fontName="Helvetica"
    ))

    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=10,
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="Label",
        fontSize=9,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="Value",
        fontSize=9,
        fontName="Helvetica"
    ))


    border_color = colors.HexColor("#DEE2E6")
    header_bg = colors.HexColor("#F8F9FA")



    # ---------------- HEADER ----------------

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "images",
        "logo.jpg"
    )


    logo = (
        Image(
            logo_path,
            width=2.2*inch,
            height=header_height
        )
        if os.path.exists(logo_path)
        else Paragraph(
            "COMPANY LOGO",
            styles["HeaderTitle"]
        )
    )


    header_data = [
        [
            logo,
            Paragraph(
                "<b>PPE INSPECTION MANAGEMENT SYSTEM</b>",
                styles["HeaderTitle"]
            ),
            Paragraph(
                "DOC NO: EIL/IRI/EHS/F-03",
                styles["HeaderInfo"]
            )
        ],
        [
            "",
            Paragraph(
                "<b>PPE INSPECTION REPORT</b>",
                styles["HeaderTitle"]
            ),
            Paragraph(
                f"REV NO:00<br/>DATE:{datetime.datetime.now().strftime('%d-%m-%Y')}",
                styles["HeaderInfo"]
            )
        ]
    ]


    header_table = Table(
        header_data,
        colWidths=[
            drawable_width*0.28,
            drawable_width*0.49,
            drawable_width*0.23
        ]
    )


    header_table.setStyle(
        TableStyle([
            ("GRID",(0,0),(-1,-1),1,border_color),
            ("SPAN",(0,0),(0,1)),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE")
        ])
    )


    def draw_header(canvas_obj, doc_obj):

        canvas_obj.saveState()

        h = header_table.wrap(
            doc_obj.width,
            header_height
        )[1]

        header_table.drawOn(
            canvas_obj,
            doc_obj.leftMargin,
            A4[1] - 25*mm - h
        )

        canvas_obj.restoreState()
   


    # ---------------- SECTION 1 ----------------


    story.append(
        Paragraph(
            "<b>SCHEDULE DETAILS</b>",
            styles["SectionHeader"]
        )
    )


    schedule_rows = [

        [
            Paragraph("<b>Inspection No</b>",styles["Label"]),
            Paragraph(str(schedule.inspection_no),styles["Value"]),

            Paragraph("<b>Status</b>",styles["Label"]),
            Paragraph(
                schedule.get_status_display(),
                styles["Value"]
            )
        ],


        [
            Paragraph("<b>PPE Item</b>",styles["Label"]),
            Paragraph(str(schedule.ppe_item),styles["Value"]),

            Paragraph("<b>Plant</b>",styles["Label"]),
            Paragraph(str(schedule.plant),styles["Value"])
        ],


        [
            Paragraph("<b>Department</b>",styles["Label"]),
            Paragraph(
                str(schedule.department)
                if schedule.department else "-",
                styles["Value"]
            ),

            Paragraph("<b>Assigned User</b>",styles["Label"]),
            Paragraph(
                schedule.assigned_user.get_full_name(),
                styles["Value"]
            )
        ],


        [
            Paragraph("<b>Schedule Date</b>",styles["Label"]),
            Paragraph(
                schedule.scheduled_date.strftime("%d-%m-%Y"),
                styles["Value"]
            ),

            Paragraph("<b>End Date</b>",styles["Label"]),
            Paragraph(
                schedule.scheduled_end_date.strftime("%d-%m-%Y"),
                styles["Value"]
            )
        ]

    ]


    table = Table(
        schedule_rows,
        colWidths=[drawable_width/4]*4
    )


    table.setStyle(
        TableStyle([
            ("GRID",(0,0),(-1,-1),1,border_color)
        ])
    )


    story.append(table)



    # ---------------- SECTION 2 ----------------


    story.append(
        Paragraph(
            "<b>INSPECTION ASSESSMENT</b>",
            styles["SectionHeader"]
        )
    )



    inspection = PPEInspection.objects.filter(
        schedule=schedule
    ).first()



    returns = PPEReturnManagement.objects.filter(
        ppe_item=schedule.ppe_item,
        plant=schedule.plant
    ).order_by("id")



    assessments = {}

    if inspection:

        assessments = {
            x.return_item_id:x
            for x in PPEInspectionAssessment.objects.filter(
                inspection=inspection
            )
        }

    # each return separate block
    for index, ret in enumerate(returns,1):
        assessment = assessments.get(ret.id)
        if ret.return_to=="EMPLOYEE":

            person = (
                ret.employee.get_full_name()
                if ret.employee else "-"
            )
        else:
            person = ret.contractor_name or "-"
        return_rows = [
            [
                Paragraph("<b>Return No</b>",styles["Label"]),
                Paragraph(str(ret.return_no),styles["Value"]),

                Paragraph("<b>Return To</b>",styles["Label"]),
                Paragraph(person,styles["Value"])
            ],
            [
                Paragraph("<b>PPE Item</b>",styles["Label"]),
                Paragraph(str(ret.ppe_item),styles["Value"]),

                Paragraph("<b>Size</b>",styles["Label"]),
                Paragraph(str(ret.size),styles["Value"])
            ],

            [
                Paragraph("<b>Assigned Qty</b>",styles["Label"]),
                Paragraph(str(ret.assigned_qty),styles["Value"]),

                Paragraph("<b>Return Qty</b>",styles["Label"]),
                Paragraph(str(ret.return_qty),styles["Value"])
            ],

            [
                Paragraph("<b>Inspection Status</b>",styles["Label"]),
                Paragraph(
                    assessment.status
                    if assessment else "-",
                    styles["Value"]
                ),

                Paragraph("<b>Remarks</b>",styles["Label"]),
                Paragraph(
                    assessment.remarks
                    if assessment else "-",
                    styles["Value"]
                )
            ]

        ]
        return_table = Table(
            return_rows,
            colWidths=[drawable_width/4]*4
        )
        return_table.setStyle(
            TableStyle([
                ("GRID",(0,0),(-1,-1),1,border_color),
                ("BACKGROUND",(0,0),(-1,0),header_bg)
            ])
        )
        story.append(return_table)
        # photo
        if assessment and assessment.photo:
            story.append(
                Paragraph(
                    "<b>Photo Evidence</b>",
                    styles["Label"]
                )
            )
            try:
                img = Image(
                    assessment.photo.path,
                    width=3*inch,
                    height=3*inch
                )
                story.append(img)
            except:
                pass
        story.append(
            Spacer(1,10*mm)
        )
    # ---------------- BUILD ----------------
    first_page_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height - header_height - 10*mm   # space for header
    )
    normal_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height
    )
    doc.addPageTemplates([
        PageTemplate(
            id="First",
            frames=[first_page_frame],
            onPage=draw_header
        ),
        PageTemplate(
            id="Later",
            frames=[normal_frame]
        )
    ])
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(
        content_type="application/pdf"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="PPE_Inspection_{schedule.inspection_no}.pdf"'
    )
    response.write(pdf)
    return response