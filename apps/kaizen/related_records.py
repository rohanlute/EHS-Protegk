"""Allowlisted source models used by the Kaizen linked-record picker."""

RELATED_RECORD_MODELS = {
    "incident": ("accidents", "incident"),
    "hazard": ("hazards", "hazard"),
    "capa": ("capa", "capa"),
    "inspection": ("inspections", "inspectionsubmission"),
    "audit": ("audits", "auditschedule"),
    "ergonomics": ("ergonomics", "ergonomicassessment"),
    "hira": ("hira", "hira"),
    "industrialhygiene": ("industrial_hygiene", "exposureassessment"),
}

