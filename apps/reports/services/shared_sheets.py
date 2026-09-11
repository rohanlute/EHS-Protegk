# apps/reports/services/shared_sheets.py
"""
Shared master/reference sheets included in every module's Excel export.
Call get_master_sheets() from any ReportSpec to include them.
"""
from apps.reports.services.excel_engine import StaticTable


def get_master_sheets():
    return [
        _risk_matrix(),
        _risk_levels(),
        _hierarchy_of_controls(),
        _approval_revision(),
        _review_triggers(),
        _industry_activity_master(),
        _hazard_master(),
    ]


def _risk_matrix():
    headers = [
        "Likelihood / Severity",
        "1 - Insignificant", "2 - Minor", "3 - Moderate",
        "4 - Major", "5 - Catastrophic",
    ]
    labels = ["1 - Rare", "2 - Unlikely", "3 - Possible", "4 - Likely", "5 - Almost Certain"]
    rows = [[lab] + [i * j for j in range(1, 6)] for i, lab in enumerate(labels, start=1)]
    return StaticTable(
        name="Risk Matrix",
        headers=headers,
        rows=rows,
        widths=[24, 16, 12, 14, 12, 16],
    )


def _risk_levels():
    headers = ["Risk Score", "Risk Level", "Meaning", "Recommended Action"]
    rows = [
        ["1-4", "Low", "Risk generally acceptable with controls maintained",
         "Monitor and maintain controls"],
        ["5-9", "Medium", "Additional improvement may be required",
         "Improve controls where reasonably practicable"],
        ["10-16", "High", "Significant risk requiring prompt action",
         "Implement additional controls and management attention"],
        ["17-25", "Critical", "Unacceptable risk",
         "Stop/restrict activity until adequate controls are implemented"],
    ]
    return StaticTable(name="Risk Levels", headers=headers, rows=rows,
                       widths=[12, 12, 42, 48])


def _hierarchy_of_controls():
    headers = ["Priority", "Control Type", "Description", "Example"]
    rows = [
        [1, "Elimination", "Remove the hazard completely",
         "Eliminate manual work at height by doing the work at ground level"],
        [2, "Substitution", "Replace with a less hazardous option",
         "Replace a hazardous chemical with a less hazardous chemical"],
        [3, "Engineering Control", "Physically isolate people from the hazard",
         "Machine guard, interlock, ventilation, guardrail"],
        [4, "Administrative Control", "Change the way work is performed",
         "SOP, training, permit, job rotation, signage"],
        [5, "PPE", "Protect the worker with personal protective equipment",
         "Helmet, gloves, goggles, respirator, harness"],
    ]
    return StaticTable(name="Hierarchy of Controls", headers=headers, rows=rows,
                       widths=[10, 22, 42, 50])


def _approval_revision():
    headers = ["HIRA Document Information", "Value"]
    rows = [
        ["Company", "ABC Engineering & Manufacturing Pvt. Ltd."],
        ["Site", "Manufacturing Plant"],
        ["Document", "Hazard Identification & Risk Assessment"],
        ["Document No.", "EHS-HIRA-001"],
        ["Revision", "01"],
        ["Assessment Date", "09-Sep-2026"],
        ["Next Review", "09-Sep-2027"],
        ["Review Trigger", "Annual or significant change / incident / process change"],
        ["Prepared By", "EHS Officer"],
        ["Reviewed By", "Department Head"],
        ["Approved By", "Plant Head / EHS Manager"],
        ["Approval Status", "Approved"],
        ["Approval Date", "09-Sep-2026"],
        ["", ""],
        ["Revision History", ""],
        ["Revision", "Date"],
        ["01", "09-Sep-2026  —  Initial HIRA assessment"],
    ]
    return StaticTable(name="Approval & Revision", headers=headers, rows=rows,
                       widths=[32, 65])


def _review_triggers():
    headers = ["Trigger", "When HIRA Must Be Reviewed / Reassessed", "Example"]
    rows = [
        ["New process / activity", "Before introducing a new activity", "New production line"],
        ["New machinery", "Before commissioning or operation", "New CNC machine / press"],
        ["Chemical change", "Before use of new or changed chemical", "New solvent"],
        ["Process change", "When process, layout or operating conditions change",
         "Production capacity increase"],
        ["Incident / near miss", "After an event indicates risk controls may be inadequate",
         "Machine injury / near miss"],
        ["Control failure", "When an existing control is ineffective", "Guard/interlock failure"],
        ["Legal / regulatory change", "When applicable requirements change",
         "New statutory requirement"],
        ["Periodic review", "At defined organizational interval", "Annual HIRA review"],
    ]
    return StaticTable(name="Review Triggers", headers=headers, rows=rows,
                       widths=[28, 48, 30])


def _industry_activity_master():
    headers = ["Industry / Area", "Common Process", "Typical Activities"]
    rows = [
        ["Manufacturing", "Production", "Machine operation; cutting; pressing; assembly; grinding"],
        ["Engineering", "Fabrication", "Welding; gas cutting; grinding; drilling; machining"],
        ["Chemical", "Chemical Operations", "Chemical transfer; mixing; storage; charging"],
        ["Pharmaceutical", "Manufacturing", "Material dispensing; granulation; compression; cleaning"],
        ["Automotive", "Assembly / Paint", "Pressing; welding; painting; vehicle assembly"],
        ["Construction", "Civil / Structural", "Excavation; lifting; scaffolding; concrete; roofing"],
        ["Warehouse & Logistics", "Material Movement",
         "Forklift; loading/unloading; stacking; manual handling"],
        ["Oil & Gas", "Operations / Maintenance", "Hot work; line breaking; confined space; lifting"],
        ["Power / Utilities", "Utilities", "Electrical maintenance; boiler; compressor; generator"],
        ["Food & Beverage", "Processing", "Mixing; cooking; cleaning; packaging; cold storage"],
        ["Mining", "Mining Operations", "Drilling; blasting; hauling; crushing; maintenance"],
        ["Infrastructure", "Projects", "Road work; excavation; lifting; work at height"],
    ]
    return StaticTable(name="Industry Activity Master", headers=headers, rows=rows,
                       widths=[26, 24, 50])


def _hazard_master():
    headers = ["Hazard Category", "Typical Hazards", "Typical Consequences"]
    rows = [
        ["Mechanical", "Moving parts; pinch points; sharp edges; stored energy",
         "Cuts; crush injury; amputation"],
        ["Electrical", "Live parts; arc flash; damaged cables; poor isolation",
         "Shock; burns; fatality; fire"],
        ["Chemical", "Toxic; corrosive; flammable; reactive; splash",
         "Burns; poisoning; inhalation; fire"],
        ["Physical", "Noise; heat; cold; radiation; vibration",
         "Hearing loss; burns; heat stress; exposure"],
        ["Fire / Explosion", "Ignition sources; combustible materials; gas release",
         "Fire; explosion; burns; fatality"],
        ["Ergonomic", "Manual handling; repetitive motion; poor posture",
         "MSD; strains; fatigue"],
        ["Biological", "Bacteria; viruses; contaminated materials",
         "Infection; illness"],
        ["Atmospheric", "Oxygen deficiency; toxic/flammable gases; dust",
         "Asphyxiation; poisoning; explosion"],
        ["Vehicle", "Forklift; truck movement; pedestrian interaction",
         "Collision; crush injury; fatality"],
        ["Environmental", "Spills; emissions; waste; leaks",
         "Pollution; exposure; regulatory impact"],
        ["Structural", "Collapse; excavation; falling objects",
         "Crush injury; fatality"],
    ]
    return StaticTable(name="Hazard Master", headers=headers, rows=rows,
                       widths=[22, 42, 42])