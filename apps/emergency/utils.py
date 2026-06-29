import datetime
import os
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
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


def generate_emergency_report_pdf(report):
    buffer = BytesIO()

    header_height = 1.6 * inch
    left_margin = 15 * mm
    right_margin = 15 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=header_height + 22 * mm,
        bottomMargin=25 * mm,
    )

    story = []
    drawable_width = A4[0] - left_margin - right_margin

    try:
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
        pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
    except Exception:
        pass

    primary_text_color = colors.HexColor("#212529")
    secondary_text_color = colors.HexColor("#495057")
    header_bg_color = colors.HexColor("#F8F9FA")
    border_color = colors.HexColor("#DEE2E6")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="HeaderTitle",
            fontSize=10,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            textColor=primary_text_color,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeaderInfo",
            fontSize=9,
            fontName="Helvetica",
            alignment=TA_LEFT,
            textColor=secondary_text_color,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            fontSize=11,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
            textColor=primary_text_color,
            spaceBefore=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeader",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=primary_text_color,
            spaceBefore=10,
            spaceAfter=4,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Label",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=primary_text_color,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Value",
            fontSize=9,
            fontName="Helvetica",
            textColor=secondary_text_color,
            alignment=TA_LEFT,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FooterText",
            fontSize=8,
            fontName="Helvetica",
            textColor=colors.darkgrey,
            alignment=TA_CENTER,
        )
    )

    def get_val(value, default="N/A"):
        if value:
            if isinstance(value, str):
                return value.strip().replace("\n", "<br/>")
            return value
        return default

    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.jpg")
    logo_img = (
        Image(logo_path, width=2.2 * inch, height=header_height)
        if os.path.exists(logo_path)
        else Paragraph("<b>COMPANY LOGO</b>", styles["HeaderTitle"])
    )

    header_data = [
        [
            logo_img,
            Paragraph("<b>EMERGENCY MANAGEMENT SYSTEM [EMS]</b>", styles["HeaderTitle"]),
            Paragraph("DOC NO: EIL/EMR/EHS/F-01", styles["HeaderInfo"]),
        ],
        [
            "",
            Paragraph("<b>EMERGENCY REPORT</b>", styles["HeaderTitle"]),
            Paragraph("REV NO: 00 &<br/>DATE: 01-01-2024", styles["HeaderInfo"]),
        ],
    ]
    header_table = Table(
        header_data,
        colWidths=[drawable_width * 0.2875, drawable_width * 0.4875, drawable_width * 0.225],
        rowHeights=[0.8 * inch, 0.8 * inch],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, border_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("SPAN", (0, 0), (0, 1)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    def draw_header(pdf_canvas, pdf_doc):
        pdf_canvas.saveState()
        _, height = header_table.wrap(pdf_doc.width, pdf_doc.topMargin)
        header_table.drawOn(pdf_canvas, pdf_doc.leftMargin, pdf_doc.height + pdf_doc.topMargin - height + 5 * mm)
        pdf_canvas.restoreState()

    story.append(Spacer(1, 4 * mm))
    ref_number_table = Table(
        [
            [
                Paragraph("<b>Emergency Report</b>", styles["ReportTitle"]),
                Paragraph(f"<b>Reference number:</b><br/>{report.report_number}", styles["HeaderInfo"]),
            ]
        ],
        colWidths=[drawable_width * 0.7, drawable_width * 0.3],
    )
    ref_number_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, border_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(ref_number_table)

    story.append(Paragraph("<b>SECTION 1: EMERGENCY & LOCATION DETAILS</b>", styles["SectionHeader"]))

    col_width = drawable_width / 4
    section_one_data = [
        [
            Paragraph("<b>Emergency Title:</b>", styles["Label"]),
            Paragraph(get_val(report.emergency_title), styles["Value"]),
            Paragraph("<b>Incident Date:</b>", styles["Label"]),
            Paragraph(report.incident_date.strftime("%d/%m/%Y"), styles["Value"]),
        ],
        [
            Paragraph("<b>Emergency Type:</b>", styles["Label"]),
            Paragraph(
                get_val(
                    f"{report.get_emergency_type_display()} - {report.other_emergency_type}"
                    if report.other_emergency_type
                    else report.get_emergency_type_display()
                ),
                styles["Value"],
            ),
            Paragraph("<b>Incident Time:</b>", styles["Label"]),
            Paragraph(report.incident_time.strftime("%H:%M hrs"), styles["Value"]),
        ],
        [
            Paragraph("<b>Severity:</b>", styles["Label"]),
            Paragraph(get_val(report.get_severity_level_display()), styles["Value"]),
            Paragraph("<b>Status:</b>", styles["Label"]),
            Paragraph(get_val(report.get_status_display()), styles["Value"]),
        ],
        [
            Paragraph("<b>Plant:</b>", styles["Label"]),
            Paragraph(get_val(report.plant.name if report.plant else ""), styles["Value"]),
            Paragraph("<b>Incident Department:</b>", styles["Label"]),
            Paragraph(get_val(report.incident_department.name if report.incident_department else ""), styles["Value"]),
        ],
        [
            Paragraph("<b>Zone:</b>", styles["Label"]),
            Paragraph(get_val(report.zone.name if report.zone else ""), styles["Value"]),
            Paragraph("<b>Department:</b>", styles["Label"]),
            Paragraph(get_val(report.department.name if report.department else ""), styles["Value"]),
        ],
        [
            Paragraph("<b>Location:</b>", styles["Label"]),
            Paragraph(get_val(report.location.name if report.location else ""), styles["Value"]),
            Paragraph("<b>Reported By:</b>", styles["Label"]),
            Paragraph(get_val(report.reported_by.get_full_name() or report.reported_by.username), styles["Value"]),
        ],
        [
            Paragraph("<b>Sub-Location:</b>", styles["Label"]),
            Paragraph(get_val(report.sublocation.name if report.sublocation else ""), styles["Value"]),
            Paragraph("<b>Reported Date:</b>", styles["Label"]),
            Paragraph(report.reported_date.strftime("%d/%m/%Y %H:%M"), styles["Value"]),
        ],
        [
            Paragraph("<b>Last Updated:</b>", styles["Label"]),
            Paragraph(report.updated_at.strftime("%d/%m/%Y %H:%M"), styles["Value"]),
            Paragraph("<b>Additional Details:</b>", styles["Label"]),
            Paragraph(get_val(report.additional_location_details), styles["Value"]),
        ],
        [
            Paragraph("<b>Days to Close:</b>", styles["Label"]),
            Paragraph(get_val(report.days_to_close if report.days_to_close is not None else ""), styles["Value"]),
            Paragraph("", styles["Label"]),
            Paragraph("", styles["Value"]),
        ],
    ]
    section_one_table = Table(section_one_data, colWidths=[col_width] * 4)
    section_one_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(section_one_table)

    description_table = Table(
        [
            [Paragraph("<b>Emergency Description / Sequence of Events:</b>", styles["Label"])],
            [Paragraph(get_val(report.description), styles["Value"])],
        ],
        colWidths=[drawable_width],
    )
    description_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), header_bg_color),
            ]
        )
    )
    story.append(description_table)

    story.append(Paragraph("<b>SECTION 2: RESPONSE & IMMEDIATE ACTION DETAILS</b>", styles["SectionHeader"]))

    team_names = ", ".join(
        member.get_full_name() or member.username for member in report.response_team_members.all()
    )
    section_two_data = [
        [Paragraph("<b>Immediate Actions Taken:</b>", styles["Label"])],
        [Paragraph(get_val(report.immediate_actions_taken), styles["Value"])],
        [Paragraph("<b>Response Team Members:</b>", styles["Label"])],
        [Paragraph(get_val(team_names), styles["Value"])],
    ]
    section_two_table = Table(section_two_data, colWidths=[drawable_width])
    section_two_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (0, 0), header_bg_color),
                ("BACKGROUND", (0, 2), (0, 2), header_bg_color),
            ]
        )
    )
    story.append(section_two_table)

    action_item = getattr(report, "action_item", None)
    if action_item:
        story.append(Spacer(1, 4 * mm))
        completed_by = ", ".join(
            member.get_full_name() or member.username for member in action_item.completed_by_users.all()
        )
        assigned_to = ", ".join(
            member.get_full_name() or member.username for member in action_item.assigned_to.all()
        )
        action_data = [
            [
                Paragraph("<b>Action Description:</b>", styles["Label"]),
                Paragraph(get_val(action_item.action_description), styles["Value"]),
            ],
            [
                Paragraph("<b>Assigned To:</b>", styles["Label"]),
                Paragraph(get_val(assigned_to), styles["Value"]),
            ],
            [
                Paragraph("<b>Action Status:</b>", styles["Label"]),
                Paragraph(get_val(action_item.get_status_display()), styles["Value"]),
            ],
            [
                Paragraph("<b>Completed By:</b>", styles["Label"]),
                Paragraph(get_val(completed_by), styles["Value"]),
            ],
            [
                Paragraph("<b>Completion Date & Time:</b>", styles["Label"]),
                Paragraph(
                    get_val(
                        action_item.completion_datetime.strftime("%d/%m/%Y %H:%M")
                        if action_item.completion_datetime
                        else ""
                    ),
                    styles["Value"],
                ),
            ],
            [
                Paragraph("<b>Completion Remarks:</b>", styles["Label"]),
                Paragraph(get_val(action_item.completion_remarks), styles["Value"]),
            ],
        ]
        action_table = Table(action_data, colWidths=[drawable_width * 0.25, drawable_width * 0.75])
        action_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, border_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(action_table)

    investigation = getattr(report, "investigation_report", None)
    if investigation:
        story.append(Paragraph("<b>SECTION 3: INVESTIGATION FINDINGS</b>", styles["SectionHeader"]))
        investigation_data = [
            [
                Paragraph("<b>Investigation Date:</b>", styles["Label"]),
                Paragraph(investigation.investigation_date.strftime("%d/%m/%Y"), styles["Value"]),
                Paragraph("<b>Lead Investigator:</b>", styles["Label"]),
                Paragraph(
                    get_val(
                        investigation.investigator.get_full_name()
                        if investigation.investigator
                        else ""
                    ),
                    styles["Value"],
                ),
            ],
            [
                Paragraph("<b>Investigation Team Emails:</b>", styles["Label"]),
                Paragraph(get_val(investigation.investigation_team), styles["Value"]),
                "",
                "",
            ],
            [
                Paragraph("<b>Completed Date:</b>", styles["Label"]),
                Paragraph(investigation.completed_date.strftime("%d/%m/%Y"), styles["Value"]),
                "",
                "",
            ],
        ]
        investigation_table = Table(investigation_data, colWidths=[col_width] * 4)
        investigation_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, border_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("SPAN", (1, 1), (3, 1)),
                    ("SPAN", (1, 2), (3, 2)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(investigation_table)

        investigation_text_table = Table(
            [
                [Paragraph("<b>Sequence of Events:</b>", styles["Label"])],
                [Paragraph(get_val(investigation.sequence_of_events), styles["Value"])],
                [Paragraph("<b>Root Cause Analysis:</b>", styles["Label"])],
                [Paragraph(get_val(investigation.root_cause_analysis), styles["Value"])],
                [Paragraph("<b>Immediate Corrective Actions:</b>", styles["Label"])],
                [Paragraph(get_val(investigation.immediate_corrective_actions), styles["Value"])],
                [Paragraph("<b>Preventive Measures Recommended:</b>", styles["Label"])],
                [Paragraph(get_val(investigation.preventive_measures), styles["Value"])],
                [Paragraph("<b>Witness Statements Summary:</b>", styles["Label"])],
                [Paragraph(get_val(investigation.witness_statements), styles["Value"])],
                [Paragraph("<b>Evidence Collected:</b>", styles["Label"])],
                [Paragraph(get_val(investigation.evidence_collected), styles["Value"])],
            ],
            colWidths=[drawable_width],
        )
        investigation_text_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, border_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (0, 0), header_bg_color),
                    ("BACKGROUND", (0, 2), (0, 2), header_bg_color),
                    ("BACKGROUND", (0, 4), (0, 4), header_bg_color),
                    ("BACKGROUND", (0, 6), (0, 6), header_bg_color),
                    ("BACKGROUND", (0, 8), (0, 8), header_bg_color),
                    ("BACKGROUND", (0, 10), (0, 10), header_bg_color),
                ]
            )
        )
        story.append(investigation_text_table)

    capas = report.capas.all()
    if capas.exists():
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("<b>SECTION 4: CORRECTIVE & PREVENTIVE ACTIONS</b>", styles["SectionHeader"]))
        capa_data = [
            [
                Paragraph("<b>CAPA No.</b>", styles["Label"]),
                Paragraph("<b>Action Required</b>", styles["Label"]),
                Paragraph("<b>Assigned To</b>", styles["Label"]),
                Paragraph("<b>Target Date</b>", styles["Label"]),
                Paragraph("<b>Status</b>", styles["Label"]),
            ]
        ]
        for capa in capas:
            capa_data.append(
                [
                    Paragraph(capa.capa_number, styles["Value"]),
                    Paragraph(get_val(capa.action_required), styles["Value"]),
                    Paragraph(get_val(capa.assigned_to.get_full_name() or capa.assigned_to.username), styles["Value"]),
                    Paragraph(capa.target_date.strftime("%d/%m/%Y"), styles["Value"]),
                    Paragraph(capa.get_status_display(), styles["Value"]),
                ]
            )
            if capa.action_taken or capa.closure_remarks:
                capa_data.append(
                    [
                        Paragraph("<b>Action Taken / Closure Remarks</b>", styles["Label"]),
                        Paragraph(
                            get_val(
                                "Action Taken: {0}<br/>Closure Remarks: {1}".format(
                                    get_val(capa.action_taken, ""),
                                    get_val(capa.closure_remarks, ""),
                                )
                            ),
                            styles["Value"],
                        ),
                        "",
                        "",
                        "",
                    ]
                )
        capa_table = Table(
            capa_data,
            colWidths=[
                drawable_width * 0.16,
                drawable_width * 0.36,
                drawable_width * 0.20,
                drawable_width * 0.14,
                drawable_width * 0.14,
            ],
        )
        capa_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, border_color),
                    ("BACKGROUND", (0, 0), (-1, 0), header_bg_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(capa_table)

    if report.status == "CLOSED":
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("<b>SECTION 5: EMERGENCY CLOSURE DETAILS</b>", styles["SectionHeader"]))
        closure_details_table = Table(
            [
                [
                    Paragraph("<b>Closure Date:</b>", styles["Label"]),
                    Paragraph(
                        get_val(report.closure_date.strftime("%d/%m/%Y %H:%M") if report.closure_date else ""),
                        styles["Value"],
                    ),
                ],
                [
                    Paragraph("<b>Closed By:</b>", styles["Label"]),
                    Paragraph(
                        get_val(report.closed_by.get_full_name() if report.closed_by else ""),
                        styles["Value"],
                    ),
                ],
                [
                    Paragraph("<b>Is Recurrence Possible?</b>", styles["Label"]),
                    Paragraph("Yes" if report.is_recurrence_possible else "No", styles["Value"]),
                ],
            ],
            colWidths=[drawable_width * 0.25, drawable_width * 0.75],
        )
        closure_details_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, border_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(closure_details_table)

        closure_remarks_table = Table(
            [
                [Paragraph("<b>Preventive Measures Implemented:</b>", styles["Label"])],
                [Paragraph(get_val(report.preventive_measures), styles["Value"])],
                [Paragraph("<b>Lessons Learned:</b>", styles["Label"])],
                [Paragraph(get_val(report.lessons_learned), styles["Value"])],
                [Paragraph("<b>Final Closure Remarks:</b>", styles["Label"])],
                [Paragraph(get_val(report.closure_remarks), styles["Value"])],
            ],
            colWidths=[drawable_width],
        )
        closure_remarks_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, border_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (0, 0), header_bg_color),
                    ("BACKGROUND", (0, 2), (0, 2), header_bg_color),
                    ("BACKGROUND", (0, 4), (0, 4), header_bg_color),
                ]
            )
        )
        story.append(closure_remarks_table)

    photos = report.photos.all()
    if photos.exists():
        story.append(Paragraph("<b>SECTION 6: ATTACHED PHOTO EVIDENCE</b>", styles["SectionHeader"]))
        story.append(Spacer(1, 4 * mm))

        photo_data = []
        temp_row = []
        max_img_width = drawable_width / 2.1
        max_img_height = 4.5 * inch

        for photo in photos:
            try:
                img = Image(photo.photo.path)
                img_w, img_h = img.imageWidth, img.imageHeight
                aspect_ratio = img_h / float(img_w)

                new_w = max_img_width
                new_h = new_w * aspect_ratio
                if new_h > max_img_height:
                    new_h = max_img_height
                    new_w = new_h / aspect_ratio

                img.drawWidth = new_w
                img.drawHeight = new_h
                temp_row.append(img)

                if len(temp_row) == 2:
                    photo_data.append(temp_row)
                    temp_row = []
            except Exception:
                temp_row.append(Paragraph(f"Error loading image:<br/>{os.path.basename(photo.photo.name)}", styles["Value"]))

        if temp_row:
            photo_data.append(temp_row)

        if photo_data:
            photo_table = Table(photo_data, colWidths=[drawable_width / 2, drawable_width / 2])
            photo_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )
            story.append(photo_table)

    story.append(Paragraph("<b>SECTION 7: ADMINISTRATIVE DETAILS</b>", styles["SectionHeader"]))
    admin_table = Table(
        [
            [Paragraph("<b>Current Status:</b>", styles["Label"]), Paragraph(report.get_status_display(), styles["Value"])],
            [Paragraph("<b>Reported By:</b>", styles["Label"]), Paragraph(get_val(report.reported_by.get_full_name() or report.reported_by.username), styles["Value"])],
            [Paragraph("<b>Reported Date:</b>", styles["Label"]), Paragraph(report.reported_date.strftime("%d/%m/%Y %H:%M"), styles["Value"])],
            [Paragraph("<b>Last Updated:</b>", styles["Label"]), Paragraph(report.updated_at.strftime("%d/%m/%Y %H:%M"), styles["Value"])],
            [Paragraph("<b>Closure Date:</b>", styles["Label"]), Paragraph(get_val(report.closure_date.strftime("%d/%m/%Y %H:%M") if report.closure_date else ""), styles["Value"])],
            [Paragraph("<b>Closed By:</b>", styles["Label"]), Paragraph(get_val(report.closed_by.get_full_name() if report.closed_by else ""), styles["Value"])],
        ],
        colWidths=[drawable_width * 0.25, drawable_width * 0.75],
    )
    admin_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(admin_table)

    story.append(Spacer(1, 10 * mm))
    footer_text = f"Document generated from EHS-360 System on {datetime.datetime.now().strftime('%d-%b-%Y at %H:%M hrs')}"
    story.append(Paragraph(footer_text, styles["FooterText"]))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Emergency_Report_{report.report_number}.pdf"'
    response.write(pdf)
    return response
