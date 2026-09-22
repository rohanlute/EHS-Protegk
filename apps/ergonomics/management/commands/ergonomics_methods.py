from apps.ergonomics.models import ErgonomicAssessmentMethod

data = [
    ("RULA",   "RULA",                    "Rapid Upper Limb Assessment."),
    ("REBA",   "REBA",                    "Rapid Entire Body Assessment."),
    ("NIOSH",  "NIOSH Lifting Equation",  "NIOSH Lifting Equation."),
    ("OWAS",   "OWAS",                    "Ovako Working Posture Analysing System."),
    ("OCRA",   "OCRA",                    "Occupational Repetitive Actions."),
    ("STRAIN_INDEX", "Strain Index",      "Hand/wrist strain assessment."),
    ("SNOOK",  "Snook & Ciriello",        "Acceptable manual handling limits."),
]

for code, name, desc in data:
    obj, made = ErgonomicAssessmentMethod.objects.update_or_create(
        code=code,
        defaults={"name": name, "description": desc, "is_active": True},
    )
    print(("CREATED" if made else "EXISTED"), obj.code, "-", obj.name)

print("Total:", ErgonomicAssessmentMethod.objects.count())