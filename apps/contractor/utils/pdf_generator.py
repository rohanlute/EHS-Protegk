# apps/contractor/utils/pdf_generator.py

import os
from io import BytesIO
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import utils
import logging

logger = logging.getLogger(__name__)

def generate_training_signoff_pdf(signoff, plant_name=None):
    """
    Generate PDF for training sign-off with teal theme and table format.
    
    Args:
        signoff: TrainingSignOff instance
        plant_name: Plant name (optional, will try to fetch from various sources)
    """
    buffer = BytesIO()
    
    # ==========================================================
    # GET PLANT NAME
    # ==========================================================
    if not plant_name:
        plant_name = 'the Plant'  # Default fallback
        
        # Try to get plant name from signoff.work_order
        if hasattr(signoff, 'work_order') and signoff.work_order:
            if hasattr(signoff.work_order, 'plant') and signoff.work_order.plant:
                if hasattr(signoff.work_order.plant, 'name'):
                    plant_name = signoff.work_order.plant.name
        
        # If still no plant name, try to get from contractor
        if plant_name == 'the Plant' and hasattr(signoff, 'contractor') and signoff.contractor:
            if hasattr(signoff.contractor, 'plant') and signoff.contractor.plant:
                if hasattr(signoff.contractor.plant, 'name'):
                    plant_name = signoff.contractor.plant.name
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Teal color scheme
    TEAL_PRIMARY = colors.HexColor('#0d9488')
    TEAL_DARK = colors.HexColor('#0f766e')
    TEAL_LIGHT = colors.HexColor('#ccfbf1')
    TEAL_VERY_LIGHT = colors.HexColor('#f0fdfa')
    TEXT_DARK = colors.HexColor('#0f172a')
    TEXT_MUTED = colors.HexColor('#64748b')
    WHITE = colors.HexColor('#ffffff')
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=TEAL_PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=20,
        fontName='Helvetica-Bold',
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=TEAL_DARK,
        alignment=TA_LEFT,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=TEXT_DARK,
        spaceAfter=4,
        fontName='Helvetica',
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=TEXT_DARK,
        fontName='Helvetica',
    )
    
    cell_bold_style = ParagraphStyle(
        'CellBoldStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=TEXT_DARK,
        fontName='Helvetica-Bold',
    )
    
    declaration_style = ParagraphStyle(
        'DeclarationStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=TEXT_DARK,
        fontName='Helvetica',
        leftIndent=10,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
    )
    
    # Build content
    story = []
    
    # ==========================================================
    # HEADER SECTION
    # ==========================================================
    # Title
    story.append(Paragraph("Training Sign-Off Report", title_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Sign-Off Number
    story.append(Paragraph(
        f"Sign-Off Number: <b>{signoff.signoff_number}</b>", 
        ParagraphStyle(
            'NumberStyle',
            parent=normal_style,
            fontSize=12,
            alignment=TA_CENTER,
            textColor=TEAL_DARK,
        )
    ))
    story.append(Spacer(1, 0.05 * inch))
    
    # Date
    signoff_date = signoff.signoff_date.strftime('%d %B %Y') if signoff.signoff_date else 'N/A'
    signoff_time = signoff.signoff_time.strftime('%H:%M') if signoff.signoff_time else 'N/A'
    story.append(Paragraph(
        f"Date: {signoff_date} at {signoff_time}", 
        ParagraphStyle(
            'DateStyle',
            parent=normal_style,
            fontSize=10,
            alignment=TA_CENTER,
            textColor=TEXT_MUTED,
        )
    ))
    story.append(Spacer(1, 0.2 * inch))
    
    # Decorative line
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL_PRIMARY))
    story.append(Spacer(1, 0.2 * inch))
    
    # ==========================================================
    # SECTION 1: CONTRACTOR INFORMATION
    # ==========================================================
    story.append(Paragraph("1. Contractor Information", header_style))
    
    contractor_data = [
        [
            Paragraph("<b>Contractor</b>", cell_bold_style),
            Paragraph(signoff.contractor.contractor_name if signoff.contractor else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Contractor Code</b>", cell_bold_style),
            Paragraph(signoff.contractor.contractor_code if signoff.contractor else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Work Order</b>", cell_bold_style),
            Paragraph(signoff.work_order.work_order_number if signoff.work_order else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Contract Number</b>", cell_bold_style),
            Paragraph(signoff.work_order.contract_number if signoff.work_order else 'N/A', cell_style)
        ],
    ]
    
    contractor_table = Table(contractor_data, colWidths=[2.5 * inch, 4 * inch])
    contractor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TEAL_VERY_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 0), (0, -1), TEAL_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(contractor_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # ==========================================================
    # SECTION 2: CONTRACTOR REPRESENTATIVE
    # ==========================================================
    story.append(Paragraph("2. Contractor Representative", header_style))
    
    rep_data = [
        [
            Paragraph("<b>Representative</b>", cell_bold_style),
            Paragraph(signoff.contractor_representative or 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Designation</b>", cell_bold_style),
            Paragraph(signoff.contractor_representative_designation or 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Number of Workers</b>", cell_bold_style),
            Paragraph(str(signoff.number_of_workers or 0), cell_style)
        ],
    ]
    
    rep_table = Table(rep_data, colWidths=[2.5 * inch, 4 * inch])
    rep_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TEAL_VERY_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 0), (0, -1), TEAL_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(rep_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # ==========================================================
    # SECTION 3: TRAINING SESSION DETAILS
    # ==========================================================
    story.append(Paragraph("3. Training Session Details", header_style))
    
    # Main session details table
    session_data = [
        [
            Paragraph("<b>Session No</b>", cell_bold_style),
            Paragraph(signoff.session.session_no if signoff.session else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Topic</b>", cell_bold_style),
            Paragraph(signoff.session.topic.topic_title if signoff.session and signoff.session.topic else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Category</b>", cell_bold_style),
            Paragraph(signoff.session.category.category_name if signoff.session and signoff.session.category else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Department</b>", cell_bold_style),
            Paragraph(signoff.session.department.name if signoff.session and signoff.session.department else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Planned Date</b>", cell_bold_style),
            Paragraph(signoff.session.planned_date.strftime('%d %B %Y') if signoff.session and signoff.session.planned_date else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Planned Time</b>", cell_bold_style),
            Paragraph(signoff.session.planned_time.strftime('%H:%M') if signoff.session and signoff.session.planned_time else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Expected Participants</b>", cell_bold_style),
            Paragraph(str(signoff.session.expected_participants or 0) if signoff.session else '0', cell_style)
        ],
    ]
    
    session_table = Table(session_data, colWidths=[2.5 * inch, 4 * inch])
    session_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TEAL_VERY_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 0), (0, -1), TEAL_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(session_table)
    story.append(Spacer(1, 0.15 * inch))
    
    # Trainers and Incharges
    if signoff.session:
        trainers = [t.get_full_name() for t in signoff.session.trainers.all()]
        incharges = [i.get_full_name() for i in signoff.session.incharges.all()]
        
        personnel_data = []
        if trainers:
            personnel_data.append([
                Paragraph("<b>Trainers</b>", cell_bold_style),
                Paragraph(', '.join(trainers), cell_style)
            ])
        if incharges:
            personnel_data.append([
                Paragraph("<b>Incharges</b>", cell_bold_style),
                Paragraph(', '.join(incharges), cell_style)
            ])
        
        if personnel_data:
            personnel_table = Table(personnel_data, colWidths=[2.5 * inch, 4 * inch])
            personnel_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), TEAL_VERY_LIGHT),
                ('BACKGROUND', (1, 0), (1, -1), WHITE),
                ('TEXTCOLOR', (0, 0), (0, -1), TEAL_DARK),
                ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(personnel_table)
            story.append(Spacer(1, 0.15 * inch))
    
    # Topic Description
    if signoff.session and signoff.session.topic and signoff.session.topic.description:
        desc_data = [
            [
                Paragraph("<b>Topic Description</b>", cell_bold_style),
                Paragraph(signoff.session.topic.description[:500], cell_style)
            ]
        ]
        desc_table = Table(desc_data, colWidths=[2.5 * inch, 4 * inch])
        desc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), TEAL_VERY_LIGHT),
            ('BACKGROUND', (1, 0), (1, 0), WHITE),
            ('TEXTCOLOR', (0, 0), (0, 0), TEAL_DARK),
            ('TEXTCOLOR', (1, 0), (1, 0), TEXT_DARK),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(desc_table)
        story.append(Spacer(1, 0.15 * inch))
    
    # Safety Points
    if signoff.session and signoff.session.topic and hasattr(signoff.session.topic, 'details'):
        safety_points = list(signoff.session.topic.details.all())
        if safety_points:
            safety_data = [[Paragraph("<b>Safety Points Covered</b>", cell_bold_style)]]
            for detail in safety_points:
                safety_data.append([Paragraph(f"• {detail.safety_point}", cell_style)])
            
            safety_table = Table(safety_data, colWidths=[6.5 * inch])
            safety_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), TEAL_PRIMARY),
                ('TEXTCOLOR', (0, 0), (0, 0), WHITE),
                ('BACKGROUND', (0, 1), (0, -1), TEAL_VERY_LIGHT),
                ('TEXTCOLOR', (0, 1), (0, -1), TEXT_DARK),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(safety_table)
            story.append(Spacer(1, 0.15 * inch))
    
    # ==========================================================
    # SECTION 4: PLANT SIGN-OFF DECLARATION
    # ==========================================================
    story.append(Paragraph("4. Plant Sign-Off Declaration", header_style))
    
    # Use the plant_name variable here
    plant_declaration_text = f"We, {plant_name}, confirm that the above listed contractor \"{signoff.contractor.contractor_name}\" and its workers have received the required safety training and have been made aware of the applicable EHS requirements."
    
    declaration_data = [
        [
            Paragraph("<b>Declaration</b>", cell_bold_style),
            Paragraph(plant_declaration_text, declaration_style)
        ],
        [
            Paragraph("<b>Representative</b>", cell_bold_style),
            Paragraph(signoff.company_representative.get_full_name() if signoff.company_representative else 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Designation</b>", cell_bold_style),
            Paragraph(signoff.company_representative_designation or 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Signature</b>", cell_bold_style),
            Paragraph('✅ Uploaded' if signoff.company_signature else '⏳ Pending', cell_style)
        ],
        [
            Paragraph("<b>Status</b>", cell_bold_style),
            Paragraph('✅ Confirmed' if signoff.company_declaration else '⏳ Pending', cell_style)
        ],
    ]
    
    declaration_table = Table(declaration_data, colWidths=[2 * inch, 4.5 * inch])
    declaration_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TEAL_VERY_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 0), (0, -1), TEAL_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(declaration_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # ==========================================================
    # SECTION 5: CONTRACTOR SIGN-OFF DECLARATION
    # ==========================================================
    story.append(Paragraph("5. Contractor Sign-Off Declaration", header_style))
    
    contractor_declaration_text = "I confirm that the above listed workers have received the required safety training and have understood the applicable EHS requirements."
    
    contractor_decl_data = [
        [
            Paragraph("<b>Declaration</b>", cell_bold_style),
            Paragraph(contractor_declaration_text, declaration_style)
        ],
        [
            Paragraph("<b>Supervisor</b>", cell_bold_style),
            Paragraph(signoff.contractor_supervisor or 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Designation</b>", cell_bold_style),
            Paragraph(signoff.contractor_supervisor_designation or 'N/A', cell_style)
        ],
        [
            Paragraph("<b>Status</b>", cell_bold_style),
            Paragraph('✅ Confirmed' if signoff.contractor_declaration else '⏳ Pending', cell_style)
        ],
    ]
    
    contractor_decl_table = Table(contractor_decl_data, colWidths=[2 * inch, 4.5 * inch])
    contractor_decl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), TEAL_VERY_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 0), (0, -1), TEAL_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(contractor_decl_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # ==========================================================
    # SECTION 6: SIGNATORIES
    # ==========================================================
    story.append(Paragraph("6. Signatories", header_style))
    
    # Plant Representative
    plant_rep_name = signoff.company_representative.get_full_name() if signoff.company_representative else 'N/A'
    
    signatory_data = [
        [Paragraph("<b>Role</b>", cell_bold_style), Paragraph("<b>Name</b>", cell_bold_style)],
        [
            Paragraph("Plant Representative", cell_style),
            Paragraph(plant_rep_name, cell_style)
        ],
        [
            Paragraph("Contractor Supervisor", cell_style),
            Paragraph(signoff.contractor_supervisor if signoff.contractor_supervisor else 'N/A', cell_style)
        ],
    ]
    
    signatory_table = Table(signatory_data, colWidths=[2.5 * inch, 4 * inch])
    signatory_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), TEAL_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        # Data rows
        ('BACKGROUND', (0, 1), (0, -1), TEAL_VERY_LIGHT),
        ('BACKGROUND', (1, 1), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 1), (0, -1), TEAL_DARK),
        ('TEXTCOLOR', (1, 1), (1, -1), TEXT_DARK),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))
    story.append(signatory_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # ==========================================================
    # FOOTER - SIGNATURE BLOCK ON THE LAST PAGE (BOTTOM RIGHT)
    # ==========================================================
    story.append(Spacer(1, 0.5 * inch))
    
    # Signature block table positioned at bottom right
    signature_block_data = [
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', ''],
        ['', Paragraph("_______________________", ParagraphStyle(
            'SignatureLineStyle',
            parent=normal_style,
            alignment=TA_RIGHT,
            textColor=TEXT_DARK,
            fontName='Helvetica',
            fontSize=14,
        ))],
        ['', Paragraph("<b>Contractor Signature</b>", ParagraphStyle(
            'SignatureLabelStyle',
            parent=normal_style,
            alignment=TA_RIGHT,
            textColor=TEAL_PRIMARY,
            fontName='Helvetica-Bold',
            fontSize=10,
        ))],
        ['', Paragraph(f"Date: {timezone.now().strftime('%d %B %Y')}", ParagraphStyle(
            'SignatureDateStyle',
            parent=normal_style,
            alignment=TA_RIGHT,
            textColor=TEXT_MUTED,
            fontName='Helvetica',
            fontSize=9,
        ))],
    ]
    
    signature_table = Table(signature_block_data, colWidths=[4.5 * inch, 2 * inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(signature_table)
    
    # ==========================================================
    # FOOTER
    # ==========================================================
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL_LIGHT))
    story.append(Spacer(1, 0.05 * inch))
    
    footer_text = f"Generated on {timezone.now().strftime('%d %B %Y at %H:%M')} | EHS-360 Management System"
    story.append(Paragraph(
        footer_text,
        ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=TEXT_MUTED,
            alignment=TA_CENTER,
        )
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer