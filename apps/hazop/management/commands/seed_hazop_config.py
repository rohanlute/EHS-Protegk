
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.hazop.models import (
    HAZOPStudyType,
    HAZOPStudyStatus,
    HAZOPParameter,
    HAZOPGuideWord,
    HAZOPDeviationTemplate,
    HAZOPStudyMethodology,
    HAZOPStudyPriority,
    HAZOPProcessType,
    HAZOPNodeType,
    HAZOPEquipmentType,
    HAZOPCauseCategory,
    HAZOPConsequenceCategory,
    HAZOPSafeguardCategory,
    HAZOPRecommendationCategory,
    HAZOPSeverity,
    HAZOPLikelihood,
    HAZOPReviewFrequency,
    HAZOPParameterGuideWordMapping,
)


class Command(BaseCommand):
    help = "Seed default HAZOP configuration masters"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting HAZOP configuration seeding...")
        )

        self.seed_study_types()
        self.seed_study_statuses()
        self.seed_parameters()
        self.seed_guide_words()
        self.seed_deviation_templates()

        self.seed_study_methodologies()
        self.seed_study_priorities()
        self.seed_process_types()
        self.seed_node_types()
        self.seed_equipment_types()

        self.seed_cause_categories()
        self.seed_consequence_categories()
        self.seed_safeguard_categories()
        self.seed_recommendation_categories()

        self.seed_severity_levels()
        self.seed_likelihood_levels()
        self.seed_review_frequencies()

        self.seed_parameter_guideword_mappings()

        self.stdout.write(
            self.style.SUCCESS(
                "HAZOP configuration seeding completed successfully."
            )
        )

    # ---------------------------------------------------------
    # COMMON SEED HELPER
    # ---------------------------------------------------------

    def seed_master(self, model, items):
        """
        Seed models that inherit from HAZOPConfigBase.

        Each item can be:
        (code, name, description)

        Or a dictionary containing:
        code, name, description and any additional model fields.
        """

        for item in items:
            if isinstance(item, dict):
                code = item["code"]
                name = item["name"]
                description = item.get("description", "")

                extra_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in {"code", "name", "description"}
                }
            else:
                code, name, description = item
                extra_fields = {}

            defaults = {
                "name": name,
                "description": description,
                "is_system_default": True,
                "is_active": True,
                **extra_fields,
            }

            obj, created = model.objects.get_or_create(
                code=code,
                defaults=defaults,
            )

            self.print_result(
                model._meta.verbose_name.title(),
                obj.name,
                created,
            )

    # ---------------------------------------------------------
    # STUDY TYPES
    # ---------------------------------------------------------

    def seed_study_types(self):
        self.seed_master(
            HAZOPStudyType,
            [
                (
                    "INITIAL",
                    "Initial HAZOP Study",
                    "Initial HAZOP analysis for a new process or facility.",
                ),
                (
                    "REVALIDATION",
                    "HAZOP Revalidation",
                    "Periodic review and revalidation of an existing HAZOP study.",
                ),
                (
                    "MOC_REVIEW",
                    "Management of Change Review",
                    "HAZOP review associated with a Management of Change.",
                ),
                (
                    "PROCESS_MODIFICATION",
                    "Process Modification Study",
                    "HAZOP study for a process modification or upgrade.",
                ),
            ],
        )

    # ---------------------------------------------------------
    # STUDY STATUSES
    # ---------------------------------------------------------

    def seed_study_statuses(self):
        self.seed_master(
            HAZOPStudyStatus,
            [
                {
                    "code": "DRAFT",
                    "name": "Draft",
                    "sequence": 1,
                    "is_terminal": False,
                },
                {
                    "code": "PLANNED",
                    "name": "Planned",
                    "sequence": 2,
                    "is_terminal": False,
                },
                {
                    "code": "IN_PROGRESS",
                    "name": "In Progress",
                    "sequence": 3,
                    "is_terminal": False,
                },
                {
                    "code": "UNDER_REVIEW",
                    "name": "Under Review",
                    "sequence": 4,
                    "is_terminal": False,
                },
                {
                    "code": "APPROVED",
                    "name": "Approved",
                    "sequence": 5,
                    "is_terminal": False,
                },
                {
                    "code": "REVALIDATION_DUE",
                    "name": "Revalidation Due",
                    "sequence": 6,
                    "is_terminal": False,
                },
                {
                    "code": "CLOSED",
                    "name": "Closed",
                    "sequence": 7,
                    "is_terminal": True,
                },
                {
                    "code": "CANCELLED",
                    "name": "Cancelled",
                    "sequence": 8,
                    "is_terminal": True,
                },
            ],
        )

    # ---------------------------------------------------------
    # PARAMETERS
    # ---------------------------------------------------------

    def seed_parameters(self):
        self.seed_master(
            HAZOPParameter,
            [
                ("FLOW", "Flow", "Movement or rate of process material."),
                ("PRESSURE", "Pressure", "Process pressure."),
                ("TEMPERATURE", "Temperature", "Process temperature."),
                ("LEVEL", "Level", "Liquid or material level."),
                ("COMPOSITION", "Composition", "Chemical or material composition."),
                ("PHASE", "Phase", "Physical phase of the process material."),
                ("SPEED", "Speed", "Rotational or operating speed."),
                ("TIME", "Time", "Process duration or timing."),
                ("VOLTAGE", "Voltage", "Electrical voltage."),
                ("CURRENT", "Current", "Electrical current."),
                ("VIBRATION", "Vibration", "Mechanical vibration."),
                ("UTILITY", "Utility", "Utility availability such as power or cooling."),
                ("REACTION", "Reaction", "Chemical reaction behavior."),
                ("CONTAINMENT", "Containment", "Containment and material integrity."),
            ],
        )

    # ---------------------------------------------------------
    # GUIDE WORDS
    # ---------------------------------------------------------

    def seed_guide_words(self):
        self.seed_master(
            HAZOPGuideWord,
            [
                ("NO", "No", "Complete absence of the intended function or parameter."),
                ("MORE", "More", "Quantitative increase in the parameter."),
                ("LESS", "Less", "Quantitative decrease in the parameter."),
                ("REVERSE", "Reverse", "Opposite direction or reverse action."),
                ("OTHER_THAN", "Other Than", "Something different from the intended condition."),
                ("AS_WELL_AS", "As Well As", "Additional activity or material occurs."),
                ("PART_OF", "Part Of", "Only part of the intended activity or composition occurs."),
                ("EARLY", "Early", "The event or action occurs earlier than intended."),
                ("LATE", "Late", "The event or action occurs later than intended."),
                ("BEFORE", "Before", "An event occurs before the intended sequence."),
                ("AFTER", "After", "An event occurs after the intended sequence."),
            ],
        )

    # ---------------------------------------------------------
    # DEVIATION TEMPLATES
    # ---------------------------------------------------------

    def seed_deviation_templates(self):
        combinations = [
            ("FLOW", "NO", "No Flow"),
            ("FLOW", "MORE", "More Flow"),
            ("FLOW", "LESS", "Less Flow"),
            ("FLOW", "REVERSE", "Reverse Flow"),
            ("FLOW", "OTHER_THAN", "Other Than Intended Flow"),

            ("PRESSURE", "MORE", "More Pressure"),
            ("PRESSURE", "LESS", "Less Pressure"),
            ("PRESSURE", "NO", "No Pressure"),

            ("TEMPERATURE", "MORE", "Higher Temperature"),
            ("TEMPERATURE", "LESS", "Lower Temperature"),

            ("LEVEL", "MORE", "High Level"),
            ("LEVEL", "LESS", "Low Level"),
            ("LEVEL", "NO", "No Level"),

            ("COMPOSITION", "OTHER_THAN", "Other Than Intended Composition"),
            ("COMPOSITION", "AS_WELL_AS", "Additional Component Present"),
            ("COMPOSITION", "PART_OF", "Partial Composition"),

            ("PHASE", "OTHER_THAN", "Other Than Intended Phase"),

            ("SPEED", "MORE", "Higher Speed"),
            ("SPEED", "LESS", "Lower Speed"),
            ("SPEED", "NO", "No Speed"),

            ("TIME", "EARLY", "Early Operation"),
            ("TIME", "LATE", "Late Operation"),
            ("TIME", "BEFORE", "Operation Before Intended Time"),
            ("TIME", "AFTER", "Operation After Intended Time"),

            ("VOLTAGE", "MORE", "Higher Voltage"),
            ("VOLTAGE", "LESS", "Lower Voltage"),
            ("VOLTAGE", "NO", "No Voltage"),

            ("CURRENT", "MORE", "Higher Current"),
            ("CURRENT", "LESS", "Lower Current"),
            ("CURRENT", "NO", "No Current"),

            ("VIBRATION", "MORE", "More Vibration"),
            ("VIBRATION", "LESS", "Less Vibration"),

            ("UTILITY", "NO", "No Utility"),
            ("UTILITY", "LESS", "Reduced Utility"),
            ("UTILITY", "MORE", "Excess Utility"),

            ("REACTION", "MORE", "More Reaction"),
            ("REACTION", "LESS", "Less Reaction"),
            ("REACTION", "NO", "No Reaction"),
            ("REACTION", "OTHER_THAN", "Other Than Intended Reaction"),

            ("CONTAINMENT", "NO", "Loss of Containment"),
            ("CONTAINMENT", "LESS", "Reduced Containment"),
        ]

        parameter_codes = {
            item[0] for item in combinations
        }
        guideword_codes = {
            item[1] for item in combinations
        }

        parameters = {
            obj.code: obj
            for obj in HAZOPParameter.objects.filter(
                code__in=parameter_codes
            )
        }

        guide_words = {
            obj.code: obj
            for obj in HAZOPGuideWord.objects.filter(
                code__in=guideword_codes
            )
        }

        for parameter_code, guideword_code, deviation_text in combinations:
            parameter = parameters.get(parameter_code)
            guide_word = guide_words.get(guideword_code)

            if not parameter or not guide_word:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped {deviation_text}: "
                        "parameter or guide word missing."
                    )
                )
                continue

            code = f"{parameter_code}_{guideword_code}"

            obj, created = HAZOPDeviationTemplate.objects.get_or_create(
                parameter=parameter,
                guide_word=guide_word,
                defaults={
                    "code": code,
                    "deviation_text": deviation_text,
                    "description": "",
                    "is_system_default": True,
                    "is_active": True,
                },
            )

            self.print_result(
                "Deviation Template",
                obj.deviation_text,
                created,
            )

    # ---------------------------------------------------------
    # STUDY METHODOLOGIES
    # ---------------------------------------------------------

    def seed_study_methodologies(self):
        self.seed_master(
            HAZOPStudyMethodology,
            [
                (
                    "IEC_61882",
                    "IEC 61882 HAZOP",
                    "Structured HAZOP methodology based on IEC 61882.",
                ),
                (
                    "WHAT_IF",
                    "What-If Analysis",
                    "Systematic review using What-If questions.",
                ),
                (
                    "CHECKLIST",
                    "Checklist Analysis",
                    "Review using predefined process safety checklists.",
                ),
                (
                    "WHAT_IF_CHECKLIST",
                    "What-If and Checklist",
                    "Combined What-If questioning and checklist review.",
                ),
            ],
        )

    # ---------------------------------------------------------
    # STUDY PRIORITIES
    # ---------------------------------------------------------

    def seed_study_priorities(self):
        self.seed_master(
            HAZOPStudyPriority,
            [
                {
                    "code": "CRITICAL",
                    "name": "Critical",
                    "description": "Highest priority study.",
                    "priority_order": 1,
                },
                {
                    "code": "HIGH",
                    "name": "High",
                    "description": "High priority study.",
                    "priority_order": 2,
                },
                {
                    "code": "MEDIUM",
                    "name": "Medium",
                    "description": "Normal priority study.",
                    "priority_order": 3,
                },
                {
                    "code": "LOW",
                    "name": "Low",
                    "description": "Lower priority study.",
                    "priority_order": 4,
                },
            ],
        )

    # ---------------------------------------------------------
    # PROCESS TYPES
    # ---------------------------------------------------------

    def seed_process_types(self):
        self.seed_master(
            HAZOPProcessType,
            [
                ("CHEMICAL", "Chemical Processing", "Chemical manufacturing and processing."),
                ("PETROCHEMICAL", "Petrochemical", "Petrochemical and refinery operations."),
                ("PHARMACEUTICAL", "Pharmaceutical", "Pharmaceutical manufacturing."),
                ("MANUFACTURING", "Manufacturing", "General manufacturing processes."),
                ("UTILITIES", "Utilities", "Steam, water, air and power systems."),
                ("STORAGE", "Storage and Handling", "Storage and handling of materials."),
                ("WATER_TREATMENT", "Water Treatment", "Water and wastewater treatment."),
                ("FOOD_PROCESSING", "Food Processing", "Food and beverage processing."),
                ("ENERGY", "Energy and Power", "Energy generation and power operations."),
                ("OTHER", "Other Process", "Other process types."),
            ],
        )

    # ---------------------------------------------------------
    # NODE TYPES
    # ---------------------------------------------------------

    def seed_node_types(self):
        self.seed_master(
            HAZOPNodeType,
            [
                ("PROCESS_LINE", "Process Line", "Process piping line or flow path."),
                ("EQUIPMENT", "Equipment", "Specific item of process equipment."),
                ("STORAGE_TANK", "Storage Tank", "Tank or vessel used for storage."),
                ("REACTOR", "Reactor", "Process reactor or reaction vessel."),
                ("PUMPING_SYSTEM", "Pumping System", "Pump and associated piping."),
                ("UTILITY_SYSTEM", "Utility System", "Utility system such as cooling water or steam."),
                ("PACKAGE_UNIT", "Package Unit", "Packaged process or equipment unit."),
                ("CONTROL_SYSTEM", "Control System", "Process control or instrumentation system."),
                ("TRANSFER_SYSTEM", "Transfer System", "Material transfer or loading system."),
                ("OTHER", "Other Node", "Other process node type."),
            ],
        )

    # ---------------------------------------------------------
    # EQUIPMENT TYPES
    # ---------------------------------------------------------

    def seed_equipment_types(self):
        self.seed_master(
            HAZOPEquipmentType,
            [
                ("PUMP", "Pump", "Liquid or process fluid pump."),
                ("VALVE", "Valve", "Manual or automated process valve."),
                ("REACTOR", "Reactor", "Chemical or process reactor."),
                ("VESSEL", "Vessel", "Process vessel or pressure vessel."),
                ("STORAGE_TANK", "Storage Tank", "Material storage tank."),
                ("COMPRESSOR", "Compressor", "Gas or air compressor."),
                ("HEAT_EXCHANGER", "Heat Exchanger", "Equipment for heat transfer."),
                ("BOILER", "Boiler", "Steam or hot water boiler."),
                ("FILTER", "Filter", "Process filtration equipment."),
                ("CONVEYOR", "Conveyor", "Material handling conveyor."),
                ("MOTOR", "Motor", "Electric or process drive motor."),
                ("PIPELINE", "Pipeline", "Process piping or pipeline."),
                ("INSTRUMENT", "Instrument", "Process measurement or control instrument."),
                ("BURNER", "Burner", "Combustion burner or firing system."),
                ("OTHER", "Other Equipment", "Other equipment type."),
            ],
        )

    # ---------------------------------------------------------
    # CAUSE CATEGORIES
    # ---------------------------------------------------------

    def seed_cause_categories(self):
        self.seed_master(
            HAZOPCauseCategory,
            [
                ("EQUIPMENT_FAILURE", "Equipment Failure", "Equipment failure or malfunction."),
                ("INSTRUMENT_FAILURE", "Instrument Failure", "Sensor or instrument failure."),
                ("CONTROL_FAILURE", "Control System Failure", "Control logic or system failure."),
                ("HUMAN_ERROR", "Human Error", "Incorrect human action or operation."),
                ("UTILITY_FAILURE", "Utility Failure", "Loss of supporting utility."),
                ("PROCESS_ERROR", "Process Error", "Incorrect process condition or operation."),
                ("MAINTENANCE_ERROR", "Maintenance Error", "Incorrect maintenance or installation."),
                ("EXTERNAL_EVENT", "External Event", "External event affecting operation."),
                ("BLOCKAGE", "Blockage", "Restriction or blockage in equipment or piping."),
                ("LEAKAGE", "Leakage", "Leak or loss of containment."),
                ("OTHER", "Other Cause", "Other cause category."),
            ],
        )

    # ---------------------------------------------------------
    # CONSEQUENCE CATEGORIES
    # ---------------------------------------------------------

    def seed_consequence_categories(self):
        self.seed_master(
            HAZOPConsequenceCategory,
            [
                ("PERSONNEL_INJURY", "Personnel Injury", "Injury or harm to personnel."),
                ("FATALITY", "Fatality", "Potential fatal injury or loss of life."),
                ("FIRE", "Fire", "Fire resulting from the deviation."),
                ("EXPLOSION", "Explosion", "Explosion or overpressure event."),
                ("TOXIC_RELEASE", "Toxic Release", "Release or exposure to toxic material."),
                ("ENVIRONMENTAL_IMPACT", "Environmental Impact", "Impact to air, water, land or ecosystems."),
                ("EQUIPMENT_DAMAGE", "Equipment Damage", "Damage to equipment or assets."),
                ("PROCESS_SHUTDOWN", "Process Shutdown", "Unplanned shutdown or production interruption."),
                ("QUALITY_IMPACT", "Product Quality Impact", "Impact on product quality or specification."),
                ("FINANCIAL_LOSS", "Financial Loss", "Financial or business impact."),
                ("OTHER", "Other Consequence", "Other consequence category."),
            ],
        )

    # ---------------------------------------------------------
    # SAFEGUARD CATEGORIES
    # ---------------------------------------------------------

    def seed_safeguard_categories(self):
        self.seed_master(
            HAZOPSafeguardCategory,
            [
                ("BASIC_CONTROL", "Basic Process Control", "Normal process control system."),
                ("ALARM", "Alarm", "Operator alarm or warning."),
                ("INTERLOCK", "Interlock", "Process or equipment interlock."),
                ("SIS", "Safety Instrumented System", "Safety instrumented function or system."),
                ("RELIEF_DEVICE", "Relief Device", "Pressure relief valve or relief device."),
                ("CONTAINMENT", "Containment", "Containment or secondary containment."),
                ("DETECTION", "Detection System", "Gas, fire, leak or other detection system."),
                ("PROCEDURE", "Operating Procedure", "Operating or emergency procedure."),
                ("INSPECTION", "Inspection and Maintenance", "Inspection, testing or maintenance."),
                ("PPE", "Personal Protective Equipment", "Personal protective equipment."),
                ("TRAINING", "Training and Competency", "Training or competency-based safeguard."),
                ("OTHER", "Other Safeguard", "Other safeguard category."),
            ],
        )

    # ---------------------------------------------------------
    # RECOMMENDATION CATEGORIES
    # ---------------------------------------------------------

    def seed_recommendation_categories(self):
        self.seed_master(
            HAZOPRecommendationCategory,
            [
                ("ENGINEERING", "Engineering", "Engineering design or modification."),
                ("INSTRUMENTATION", "Instrumentation", "Instrumentation or control improvement."),
                ("SAFETY_SYSTEM", "Safety System", "Safety or protective system improvement."),
                ("PROCEDURE", "Procedure", "Operating or emergency procedure improvement."),
                ("INSPECTION", "Inspection and Maintenance", "Inspection, testing or maintenance action."),
                ("TRAINING", "Training", "Training or competency improvement."),
                ("PPE", "PPE", "Personal protective equipment improvement."),
                ("MANAGEMENT_SYSTEM", "Management System", "Management system or administrative improvement."),
                ("OTHER", "Other Recommendation", "Other recommendation category."),
            ],
        )

    # ---------------------------------------------------------
    # SEVERITY LEVELS
    # ---------------------------------------------------------

    def seed_severity_levels(self):
        self.seed_master(
            HAZOPSeverity,
            [
                {
                    "code": "S1",
                    "name": "Insignificant",
                    "description": "Very minor impact.",
                    "severity_score": 1,
                },
                {
                    "code": "S2",
                    "name": "Minor",
                    "description": "Minor impact.",
                    "severity_score": 2,
                },
                {
                    "code": "S3",
                    "name": "Moderate",
                    "description": "Moderate impact.",
                    "severity_score": 3,
                },
                {
                    "code": "S4",
                    "name": "Major",
                    "description": "Major impact.",
                    "severity_score": 4,
                },
                {
                    "code": "S5",
                    "name": "Catastrophic",
                    "description": "Very severe or catastrophic impact.",
                    "severity_score": 5,
                },
            ],
        )

    # ---------------------------------------------------------
    # LIKELIHOOD LEVELS
    # ---------------------------------------------------------

    def seed_likelihood_levels(self):
        self.seed_master(
            HAZOPLikelihood,
            [
                {
                    "code": "L1",
                    "name": "Rare",
                    "description": "Expected only in exceptional circumstances.",
                    "likelihood_score": 1,
                },
                {
                    "code": "L2",
                    "name": "Unlikely",
                    "description": "Not expected to occur frequently.",
                    "likelihood_score": 2,
                },
                {
                    "code": "L3",
                    "name": "Possible",
                    "description": "Could occur under some circumstances.",
                    "likelihood_score": 3,
                },
                {
                    "code": "L4",
                    "name": "Likely",
                    "description": "Likely to occur in some circumstances.",
                    "likelihood_score": 4,
                },
                {
                    "code": "L5",
                    "name": "Almost Certain",
                    "description": "Expected to occur frequently.",
                    "likelihood_score": 5,
                },
            ],
        )

    # ---------------------------------------------------------
    # REVIEW FREQUENCIES
    # ---------------------------------------------------------

    def seed_review_frequencies(self):
        self.seed_master(
            HAZOPReviewFrequency,
            [
                {
                    "code": "SIX_MONTHS",
                    "name": "Every 6 Months",
                    "description": "Review every six months.",
                    "interval_days": 180,
                },
                {
                    "code": "ANNUAL",
                    "name": "Annual",
                    "description": "Review once every year.",
                    "interval_days": 365,
                },
                {
                    "code": "THREE_YEARS",
                    "name": "Every 3 Years",
                    "description": "Review every three years.",
                    "interval_days": 1095,
                },
                {
                    "code": "FIVE_YEARS",
                    "name": "Every 5 Years",
                    "description": "Review every five years.",
                    "interval_days": 1825,
                },
            ],
        )

    # ---------------------------------------------------------
    # PARAMETER-GUIDE WORD MAPPINGS
    # ---------------------------------------------------------

    def seed_parameter_guideword_mappings(self):
        """
        Create allowed parameter-guideword combinations based on
        active deviation templates.
        """

        templates = HAZOPDeviationTemplate.objects.select_related(
            "parameter",
            "guide_word",
        ).filter(is_active=True)

        for template in templates:
            mapping, created = (
                HAZOPParameterGuideWordMapping.objects.get_or_create(
                    parameter=template.parameter,
                    guide_word=template.guide_word,
                    defaults={"is_active": True},
                )
            )

            self.print_result(
                "Parameter-Guide Word Mapping",
                f"{mapping.parameter.name} - {mapping.guide_word.name}",
                created,
            )

    # ---------------------------------------------------------
    # OUTPUT HELPER
    # ---------------------------------------------------------

    def print_result(self, category, name, created):
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {category}: {name}"
                )
            )
        else:
            self.stdout.write(
                f"Already exists {category}: {name}"
            )
