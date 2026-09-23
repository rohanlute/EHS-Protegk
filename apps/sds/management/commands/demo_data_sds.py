# ============================================================
## run to generate data:
## python manage.py demo_data_sds
## Or explicitly for related to employees available:
## python manage.py demo_data_sds --count 13 --records 100
# ============================================================
# ============================================================
# SDS Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================


from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant
from apps.chemicals.models import Chemical
from apps.sds.models import (
    SDS,
    SDSVersion,
    SDSReview,
    SDSAuditLog,
    SDSSection1,
    SDSSection2,
    SDSSection3,
    SDSSection3Ingredient,
    SDSSection4,
    SDSSection5,
    SDSSection6,
    SDSSection7,
    SDSSection8,
    SDSSection9,
    SDSSection10,
    SDSSection11,
    SDSSection12,
    SDSSection13,
    SDSSection14,
    SDSSection15,
    SDSSection16,
)


class Command(BaseCommand):
    help = "Create realistic Industrial EHS SDS demo data for the current financial year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="Number of existing users to use. Default: all active users.",
        )
        parser.add_argument(
            "--records",
            type=int,
            default=100,
            help="Number of SDS master records to create. Default: 100.",
        )

    def handle(self, *args, **options):
        records = options["records"]
        count = options["count"]

        if records <= 0:
            raise CommandError("--records must be greater than 0.")
        if count is not None and count <= 0:
            raise CommandError("--count must be greater than 0.")

        self.today = timezone.localdate()
        self.fy_start = date(
            self.today.year if self.today.month >= 4 else self.today.year - 1,
            4,
            1,
        )
        self.fy_end = self.today
        self.records = records

        users_qs = User.objects.filter(is_active=True).order_by("id")
        if count:
            users = list(users_qs[:count])
        else:
            users = list(users_qs)

        plants = list(Plant.objects.all().order_by("id"))
        chemicals = list(Chemical.objects.all().order_by("id"))

        if not users:
            raise CommandError("No active users found.")
        if not plants:
            raise CommandError("No Plant records found.")
        if not chemicals:
            raise CommandError("No Chemical records found. Create/import Chemical master data first.")

        self.users = users
        self.plants = plants
        self.chemicals = chemicals

        self.stdout.write(
            self.style.WARNING(
                f"SDS demo data: {self.fy_start} to {self.fy_end}"
            )
        )
        self.stdout.write(
            f"Using {len(users)} existing users, {len(plants)} existing plants and "
            f"{len(chemicals)} existing chemicals; creating {records} SDS records."
        )

        with transaction.atomic():
            created = self.seed_sds_records()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("SDS demo data created successfully."))
        self.stdout.write(f"SDS Records       : {created}")
        self.stdout.write(f"SDS Versions      : {SDSVersion.objects.filter(sds__in=created).count() if False else 'created with each SDS'}")
        self.stdout.write("SDS Sections      : 16 sections per version")
        self.stdout.write("SDS Reviews       : created with varied review statuses")
        self.stdout.write("SDS Audit Logs    : created for major SDS/version actions")
        self.stdout.write(f"Financial Year    : {self.fy_start} to {self.fy_end}")
        self.stdout.write("")
        self.stdout.write(
            "Note: rerunning this command appends another demo batch. "
            "It does not delete previous SDS data."
        )

    def demo_date(self, index, offset_days=0):
        total_days = (self.fy_end - self.fy_start).days
        if total_days <= 0:
            return self.fy_start
        if self.records <= 1:
            base = self.fy_start
        else:
            base = self.fy_start + timedelta(
                days=(index * total_days) // (self.records - 1)
            )
        return min(base + timedelta(days=offset_days), self.fy_end)

    def make_pdf(self, product_name, sds_number):
        # Create a small valid-looking demo PDF so FileField records have an actual PDF.
        # It is intentionally marked as demo content, not an official SDS.
        content = (
            "%PDF-1.4\n"
            "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            "2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
            "trailer<</Root 1 0 R>>\n"
            "%%EOF\n"
        ).encode("latin-1")
        return ContentFile(content, name=f"{sds_number}_demo.pdf")

    def text_value(self, field_name, product, index):
        values = {
            "product_identifier": product,
            "recommended_use": "Industrial cleaning, maintenance and controlled process use.",
            "restrictions_on_use": "Use only for the intended industrial application and according to the approved SDS.",
            "manufacturer_name": "Protekg Industrial Chemicals Pvt. Ltd.",
            "manufacturer_address": "Industrial Area, India",
            "manufacturer_phone": "+91 20 4000 1000",
            "manufacturer_email": "safety@example.com",
            "manufacturer_website": "https://example.com",
            "emergency_contact_name": "EHS Emergency Desk",
            "emergency_contact_number": "+91 20 4000 1999",
            "emergency_contact_email": "emergency@example.com",
            "emergency_contact_available": "24 Hours",
            "additional_information": "Demo SDS data created for EHS-360 testing.",
            "hazard_classification": "Classification depends on the product composition; refer to the controlled SDS.",
            "signal_word": "Warning",
            "hazard_statements": "May cause irritation. Use appropriate controls and personal protective equipment.",
            "precautionary_statements": "Avoid inhalation and contact with eyes and skin. Wash thoroughly after handling.",
            "ghs_pictograms": "GHS07",
            "other_hazards": "No additional hazards identified for this demonstration record.",
            "composition_notes": "Mixture containing controlled industrial-use components.",
            "trade_secret_information": "No trade-secret information recorded in this demo.",
            "general_first_aid": "Move affected person away from exposure and obtain medical advice if symptoms persist.",
            "inhalation": "Move to fresh air and monitor breathing.",
            "skin_contact": "Remove contaminated clothing and wash skin with water.",
            "eye_contact": "Rinse cautiously with water for several minutes.",
            "ingestion": "Rinse mouth. Do not induce vomiting unless directed by medical personnel.",
            "most_important_symptoms": "Irritation and discomfort may occur depending on exposure.",
            "medical_attention": "Treat symptomatically and provide the SDS to medical personnel.",
            "first_responder_notes": "Use appropriate PPE and prevent secondary exposure.",
            "suitable_extinguishing_media": "Use extinguishing media suitable for the surrounding fire.",
            "unsuitable_extinguishing_media": "Avoid direct high-pressure water where inappropriate.",
            "specific_hazards": "Heating may produce irritating or hazardous decomposition products.",
            "hazardous_combustion_products": "Carbon oxides and other decomposition products may be generated.",
            "special_protective_equipment": "Firefighters should use suitable protective clothing and respiratory protection.",
            "special_fire_fighting_procedures": "Cool exposed containers and isolate the area.",
            "personal_precautions": "Wear appropriate PPE and restrict access to the affected area.",
            "emergency_procedures": "Stop the source if safe and provide adequate ventilation.",
            "environmental_precautions": "Prevent uncontrolled release to drains, soil and water.",
            "containment_methods": "Contain the release with compatible absorbent material.",
            "cleanup_methods": "Collect material into suitable labeled containers for disposal.",
            "other_section_references": "Refer to Sections 7, 8, 13 and 14.",
            "precautions_for_safe_handling": "Use in accordance with site procedures and avoid unnecessary exposure.",
            "conditions_for_safe_storage": "Store tightly closed in a cool, dry and ventilated area.",
            "incompatible_materials": "Avoid incompatible oxidizing or reactive materials.",
            "storage_temperature": "Ambient controlled storage.",
            "ventilation_requirements": "Provide adequate general or local exhaust ventilation.",
            "specific_end_use": "Industrial process or maintenance application.",
            "occupational_exposure_limits": "Refer to applicable occupational exposure limits.",
            "biological_exposure_limits": "Not established for this demo record.",
            "appropriate_engineering_controls": "Use local exhaust ventilation and containment where required.",
            "respiratory_protection": "Use suitable respiratory protection where engineering controls are insufficient.",
            "hand_protection": "Use chemical-resistant gloves appropriate to the product.",
            "eye_face_protection": "Use safety glasses or chemical splash protection.",
            "skin_body_protection": "Use protective work clothing appropriate to the task.",
            "thermal_hazards_protection": "Use thermal protection where process conditions require it.",
            "hygiene_measures": "Do not eat, drink or smoke while handling. Wash hands after use.",
            "environmental_exposure_controls": "Prevent uncontrolled release and manage waste through approved procedures.",
            "physical_state": "Liquid",
            "appearance": "Clear to slightly colored liquid",
            "color": "Colorless to pale yellow",
            "odor": "Characteristic",
            "odor_threshold": "Not determined",
            "ph": "6-9",
            "melting_freezing_point": "Not determined",
            "boiling_point": "Not determined",
            "flash_point": "> 60 °C",
            "evaporation_rate": "Not determined",
            "flammability": "Not classified for this demo record",
            "explosive_limits": "Not determined",
            "vapor_pressure": "Not determined",
            "vapor_density": "Not determined",
            "relative_density": "Approximately 1.0",
            "solubility": "Partially soluble in water",
            "partition_coefficient": "Not determined",
            "auto_ignition_temperature": "Not determined",
            "decomposition_temperature": "Not determined",
            "viscosity": "Not determined",
            "particle_characteristics": "Not applicable for liquid product",
            "reactivity": "No hazardous reactivity expected under normal conditions.",
            "chemical_stability": "Stable under recommended storage conditions.",
            "possibility_of_hazardous_reactions": "Hazardous polymerization is not expected under normal conditions.",
            "conditions_to_avoid": "Excessive heat and incompatible materials.",
            "hazardous_decomposition_products": "May produce irritating decomposition products under fire conditions.",
            "likely_routes_of_exposure": "Inhalation, skin contact and eye contact.",
            "acute_toxicity": "No acute toxicity value entered in this demo record.",
            "skin_corrosion_irritation": "May cause irritation.",
            "serious_eye_damage_irritation": "May cause eye irritation.",
            "respiratory_skin_sensitization": "No specific sensitization information entered.",
            "germ_cell_mutagenicity": "No specific information entered.",
            "carcinogenicity": "No specific information entered.",
            "reproductive_toxicity": "No specific information entered.",
            "stot_single_exposure": "No specific information entered.",
            "stot_repeated_exposure": "No specific information entered.",
            "aspiration_hazard": "No specific information entered.",
            "symptoms_related_to_exposure": "Irritation, redness or discomfort may occur.",
            "delayed_immediate_effects": "Effects depend on concentration and duration of exposure.",
            "interactive_effects": "No specific interaction information entered.",
            "numerical_measures_of_toxicity": "Not determined.",
            "aquatic_toxicity": "Avoid uncontrolled environmental release.",
            "acute_aquatic_toxicity": "Not determined.",
            "chronic_aquatic_toxicity": "Not determined.",
            "persistence_degradability": "Not determined.",
            "bioaccumulative_potential": "Not determined.",
            "mobility_in_soil": "Not determined.",
            "results_of_pbt_vpvb_assessment": "Not assessed for this demo record.",
            "endocrine_disrupting_properties": "Not assessed for this demo record.",
            "other_adverse_effects": "Avoid uncontrolled environmental release.",
            "waste_treatment_methods": "Dispose through an authorized waste-management route.",
            "product_disposal": "Dispose according to applicable site and regulatory requirements.",
            "contaminated_packaging_disposal": "Dispose or recycle only through approved procedures.",
            "disposal_precautions": "Do not discharge to drains unless specifically authorized.",
            "waste_classification": "Determine classification based on actual product composition and local requirements.",
            "relevant_waste_regulations": "Follow applicable national, state and local waste regulations.",
            "sewer_drain_disposal_restrictions": "Do not discharge uncontrolled material to drains.",
            "environmental_disposal_considerations": "Prevent soil and water contamination.",
            "un_number": "Not assigned",
            "un_proper_shipping_name": "Not regulated for this demonstration record",
            "transport_hazard_class": "Not assigned",
            "packing_group": "Not assigned",
            "environmental_hazards": "Prevent uncontrolled release during transport.",
            "special_precautions": "Transport in secure, labeled and compatible containers.",
            "transport_in_bulk": "Not applicable.",
            "maritime_transport_information": "Refer to applicable transport regulations.",
            "air_transport_information": "Refer to applicable transport regulations.",
            "road_rail_transport_information": "Follow applicable road and rail requirements.",
            "inland_waterway_transport_information": "Refer to applicable inland-waterway requirements.",
            "safety_health_environmental_regulations": "Comply with applicable safety, health and environmental requirements.",
            "chemical_specific_regulations": "Review applicable chemical-specific requirements before use.",
            "national_regulations": "Comply with applicable national legislation.",
            "regional_regulations": "Comply with applicable state and local requirements.",
            "international_regulations": "Consider applicable international requirements for cross-border movement.",
            "chemical_inventory_status": "Inventory status to be verified against the applicable chemical inventory.",
            "restricted_prohibited_use": "Use only for approved industrial purposes.",
            "regulatory_authorities": "Applicable competent authorities and site regulatory requirements.",
            "reporting_notification_requirements": "Follow applicable incident and regulatory reporting requirements.",
            "preparation_date": str(self.demo_date(index)),
            "revision_summary": "Demo SDS revision created for EHS-360 testing.",
            "key_changes_from_previous_version": "Initial controlled demo version.",
            "abbreviations": "PPE - Personal Protective Equipment; SDS - Safety Data Sheet; GHS - Globally Harmonized System.",
            "references": "Manufacturer information, applicable SDS guidance and site procedures.",
            "data_sources": "Demo data for EHS-360 functional testing.",
            "training_information": "Personnel should be trained in safe handling, storage, PPE and emergency response.",
            "disclaimer": "This is demonstration data and must not be used as an official SDS.",
            "prepared_by": "EHS-360 Demo",
            "reviewed_by": "EHS Team",
        }
        if field_name in values:
            return values[field_name]
        return f"Demo information for {field_name.replace('_', ' ')}."

    def create_section(self, section_model, version, product, index):
        kwargs = {"sds_version": version}
        for field in section_model._meta.fields:
            name = field.name
            if name in {"id", "sds_version", "created_at", "updated_at"}:
                continue
            if field.auto_created:
                continue

            if field.get_internal_type() == "DateField":
                if name in {"preparation_date", "revision_date"}:
                    kwargs[name] = self.demo_date(index)
                else:
                    kwargs[name] = self.demo_date(index)
            elif field.get_internal_type() in {
                "CharField", "TextField", "EmailField", "URLField"
            }:
                kwargs[name] = self.text_value(name, product, index)
            elif field.get_internal_type() in {"IntegerField", "PositiveIntegerField"}:
                kwargs[name] = 1

        return section_model.objects.create(**kwargs)

    def seed_sds_sections(self, version, product, index):
        section_models = [
            SDSSection1, SDSSection2, SDSSection3, SDSSection4,
            SDSSection5, SDSSection6, SDSSection7, SDSSection8,
            SDSSection9, SDSSection10, SDSSection11, SDSSection12,
            SDSSection13, SDSSection14, SDSSection15, SDSSection16,
        ]

        created_sections = []
        for model in section_models:
            created_sections.append(self.create_section(model, version, product, index))

        # Section 3 has a separate ingredient table in addition to the main Section 3.
        section3 = next(x for x in created_sections if isinstance(x, SDSSection3))
        SDSSection3Ingredient.objects.create(
            sds_section=section3,
            ingredient_name=product,
            cas_number=f"DEMO-CAS-{index + 1:05d}",
            ec_number="DEMO-EC",
            concentration="10-30%",
            concentration_range="10-30%",
            hazard_classification="Demo component classification.",
            notes="Demo ingredient record.",
            display_order=1,
        )

    def seed_sds_records(self):
        created_sds = []

        for index in range(self.records):
            user = self.users[index % len(self.users)]
            plant = self.plants[index % len(self.plants)]
            chemical = self.chemicals[index % len(self.chemicals)]

            issue_date = self.demo_date(index)
            revision_date = issue_date
            next_review_date = min(
                issue_date + timedelta(days=365),
                self.fy_end,
            )

            # Only one ACTIVE SDS is allowed for a chemical.
            # Check the database as well so the command remains safe when rerun.
            chemical_has_active_sds = SDS.objects.filter(
                chemical=chemical,
                status="ACTIVE",
                is_active=True,
            ).exists()

            if (
                index % 4 == 0
                and not chemical_has_active_sds
            ):
                sds_status = "ACTIVE"
            else:
                status_cycle = [
                    "DRAFT",
                    "SUBMITTED",
                    "UNDER_REVIEW",
                    "APPROVED",
                    "REJECTED",
                    "SUPERSEDED",
                    "EXPIRED",
                ]
                sds_status = status_cycle[index % len(status_cycle)]

            if sds_status == "ACTIVE":
                version_status = "ACTIVE"
            elif sds_status == "APPROVED":
                version_status = "APPROVED"
            elif sds_status == "REJECTED":
                version_status = "REJECTED"
            elif sds_status == "SUPERSEDED":
                version_status = "SUPERSEDED"
            elif sds_status == "EXPIRED":
                version_status = "APPROVED"
            elif sds_status == "UNDER_REVIEW":
                version_status = "UNDER_REVIEW"
            else:
                version_status = "DRAFT"

            product = getattr(chemical, "chemical_name", None) or getattr(
                chemical, "name", None
            ) or f"Industrial Chemical {index + 1}"

            sds = SDS(
                chemical=chemical,
                product_name=product,
                product_identifier=f"CHEM-{chemical.pk}",
                sds_type=["MANUFACTURER", "SUPPLIER", "INTERNAL"][index % 3],
                manufacturer_name="Protekg Industrial Chemicals Pvt. Ltd.",
                manufacturer_address="Industrial Area, India",
                manufacturer_phone="+91 20 4000 1000",
                manufacturer_email="safety@example.com",
                supplier_name="Protekg Industrial Supplies",
                supplier_address="India",
                supplier_phone="+91 20 4000 1100",
                supplier_email="supplier@example.com",
                plant=plant,
                issue_date=issue_date,
                revision_date=revision_date,
                next_review_date=next_review_date,
                status="DRAFT",
                is_active=True,
                remarks="Demo SDS record for EHS-360 testing.",
                created_by=user,
                updated_by=user,
            )
            sds.save()

            # Create the controlled version before activating the SDS.
            version = SDSVersion(
                sds=sds,
                version_number=1,
                revision_number=f"REV-{index + 1:02d}",
                version_title=f"Initial Controlled Version - {product}",
                issue_date=issue_date,
                revision_date=revision_date,
                effective_date=issue_date,
                status=version_status,
                change_summary="Initial demo SDS version created for EHS-360 testing.",
                uploaded_by=user,
            )
            version.document.save(
                f"{sds.sds_number}_v1_demo.pdf",
                self.make_pdf(product, sds.sds_number),
                save=False,
            )
            version.save()

            # Populate all 16 SDS sections.
            self.seed_sds_sections(version, product, index)

            # The SDS model requires an active version before ACTIVE status is valid.
            if sds_status == "ACTIVE":
                sds.status = "ACTIVE"
                sds.save()
            else:
                sds.status = sds_status
                sds.save()

            # Create the main SDS document as a PDF too.
            sds.document.save(
                f"{sds.sds_number}_demo.pdf",
                self.make_pdf(product, sds.sds_number),
                save=False,
            )
            sds.document_name = f"{sds.sds_number} Demo SDS"
            sds.save()

            review_status = {
                "DRAFT": "PENDING",
                "SUBMITTED": "PENDING",
                "UNDER_REVIEW": "IN_REVIEW",
                "APPROVED": "APPROVED",
                "ACTIVE": "APPROVED",
                "REJECTED": "REJECTED",
                "SUPERSEDED": "APPROVED",
                "EXPIRED": "APPROVED",
            }[sds_status]

            review = SDSReview.objects.create(
                sds=sds,
                version=version,
                review_type=["INITIAL", "PERIODIC", "REVISION", "EMERGENCY"][index % 4],
                status=review_status,
                reviewer=user,
                submitted_by=user,
                submitted_at=timezone.now() if review_status != "PENDING" else None,
                reviewed_at=timezone.now() if review_status in {"APPROVED", "REJECTED"} else None,
                review_remarks=(
                    "Demo review completed."
                    if review_status in {"APPROVED", "REJECTED"}
                    else "Demo review pending."
                ),
                rejection_reason="Demo rejection for workflow/status testing."
                if review_status == "REJECTED"
                else "",
            )

            # Audit records reflect the lifecycle of the demo SDS.
            audit_entries = [
                (
                    "SDS_CREATED",
                    "Demo SDS record created.",
                    "",
                    sds.status,
                ),
                (
                    "VERSION_CREATED",
                    "Demo SDS Version 1 created.",
                    "",
                    version.status,
                ),
                (
                    "REVIEW_CREATED",
                    "Demo SDS review created.",
                    "",
                    review.status,
                ),
            ]
            if sds.status == "ACTIVE":
                audit_entries.append(
                    (
                        "VERSION_ACTIVATED",
                        "Demo SDS Version 1 activated.",
                        "APPROVED",
                        "ACTIVE",
                    )
                )

            for action, description, old_status, new_status in audit_entries:
                SDSAuditLog.objects.create(
                    sds=sds,
                    version=version,
                    action=action,
                    description=description,
                    old_status=old_status,
                    new_status=new_status,
                    performed_by=user,
                )

            created_sds.append(sds)

        return created_sds
