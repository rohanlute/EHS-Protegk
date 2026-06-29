import re
from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch, Q
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from apps.accounts.models import User
from apps.organizations.models import Department, Location, Plant, SubLocation, Zone
from apps.common.image_utils import compress_image
from apps.notifications.services import NotificationService
from .forms import *
from .models import *
from .utils import generate_emergency_report_pdf
from apps.organizations.models import Plant, Zone, Location, SubLocation


SOS_DEPARTMENT_ALIAS_MAP = {
    "FIRE": ["fire safety department", "fire safety", "fire department", "fire response"],
    "CHEMICAL_SPILL": ["fire safety department", "fire safety", "erm department", "erm"],
    "GAS_LEAK": ["fire safety department", "fire safety", "erm department", "erm"],
    "ELECTRICAL": ["fire safety department", "fire safety"],
    "MEDICAL": ["medical department", "medical"],
    "EXPLOSION": ["fire safety department", "fire safety", "management department", "management"],
    "NATURAL_DISASTER": ["management department", "management", "security department", "security"],
    "OTHER": ["erm department", "erm"],
}


def _normalize_department_name(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _get_sos_department_for_type(emergency_type):
    aliases = SOS_DEPARTMENT_ALIAS_MAP.get(emergency_type, SOS_DEPARTMENT_ALIAS_MAP["OTHER"])
    normalized_aliases = {_normalize_department_name(alias) for alias in aliases}
    for department in Department.objects.filter(is_active=True).order_by("name"):
        if _normalize_department_name(department.name) in normalized_aliases:
            return department
    return None


def _get_department_users_for_report(report, department):
    if not department:
        return User.objects.none()
    return User.objects.filter(
        department=department,
        is_active=True,
        is_active_employee=True,
    ).filter(
        Q(plant=report.plant) | Q(assigned_plants=report.plant)
    ).distinct().order_by("first_name", "last_name", "username")


class EmergencyAccessMixin(LoginRequiredMixin):
    allowed_roles = {"ADMIN", "SAFETY OFFICER", "PLANT HEAD", "HOD"}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def user_can_manage(self):
        role_name = getattr(getattr(self.request.user, "role", None), "name", None)
        return self.request.user.is_superuser or self.request.user.is_admin_user or role_name in self.allowed_roles

    def has_emergency_permission(self, code):
        user = self.request.user
        return user.is_superuser or user.has_permission(code)

    def can_access_emergency_module(self):
        return self.has_emergency_permission("ACCESS_EMERGENCY_MODULE")

    def can_access_emergency_drill_module(self):
        return self.has_emergency_permission("ACCESS_EMERGENCY_DRILL_MODULE")

    def can_schedule_emergency_drill(self):
        return self.has_emergency_permission("SCHEDULE_EMERGENCY_DRILL")

    def can_view_emergency_drill(self):
        return self.has_emergency_permission("VIEW_EMERGENCY_DRILL")

    def can_create_emergency_report(self):
        return self.has_emergency_permission("CREATE_EMERGENCY_REPORT")

    def can_view_emergency_report(self):
        return self.has_emergency_permission("VIEW_EMERGENCY_REPORT")

    def can_edit_emergency_report(self):
        return self.has_emergency_permission("EDIT_EMERGENCY_REPORT")

    def can_download_emergency_report(self):
        return self.has_emergency_permission("DOWNLOAD_EMERGENCY_REPORT")

    def can_create_emergency_investigation(self):
        return self.has_emergency_permission("CREATE_INVESTIGATION_EMERGENCY")

    def can_manage_emergency_capa(self):
        return self.has_emergency_permission("CREATE_CAPA")

    def can_close_emergency(self):
        return self.has_emergency_permission("CLOSE_EMERGENCY")

    def get_session_queryset(self):
        queryset = EmergencySession.objects.select_related(
            "topic",
            "plant",
            "zone",
            "location",
            "sublocation",
            "created_by",
        ).prefetch_related(
            Prefetch(
                "trainers",
                queryset=EmergencySessionTrainer.objects.select_related(
                    "trainer_department",
                    "trainer_user",
                    "trainer_user__department",
                ),
            )
        )
        user = self.request.user
        if user.is_superuser or user.is_admin_user:
            return queryset
        assigned_plants = user.assigned_plants.filter(is_active=True)
        if assigned_plants.exists():
            return queryset.filter(plant__in=assigned_plants).distinct()
        if user.plant:
            return queryset.filter(plant=user.plant)
        return queryset.filter(created_by=user)

    def get_location_context(self):
        user = self.request.user
        context = {
            "user_assigned_plants": user.assigned_plants.filter(is_active=True),
            "user_assigned_zones": user.assigned_zones.none(),
            "user_assigned_locations": user.assigned_locations.none(),
            "user_assigned_sublocations": user.assigned_sublocations.none(),
        }
        if context["user_assigned_plants"].count() == 1:
            plant = context["user_assigned_plants"].first()
            context["user_assigned_zones"] = user.assigned_zones.filter(is_active=True, plant=plant)
            if context["user_assigned_zones"].count() == 1:
                zone = context["user_assigned_zones"].first()
                context["user_assigned_locations"] = user.assigned_locations.filter(is_active=True, zone=zone)
                if context["user_assigned_locations"].count() == 1:
                    location = context["user_assigned_locations"].first()
                    context["user_assigned_sublocations"] = user.assigned_sublocations.filter(
                        is_active=True,
                        location=location,
                    )
        return context

    def can_review_sessions(self):
        return self.can_view_emergency_drill()

    def get_department_questions_for_employee(self, employee):
        if not getattr(employee, "department_id", None):
            return ERTDepartmentQuestion.objects.none()
        return ERTDepartmentQuestion.objects.filter(
            is_active=True,
            department_id=employee.department_id,
        ).order_by("question_code")

    def sync_participant_question_assignments(self, participant):
        questions = list(self.get_department_questions_for_employee(participant.employee))
        if not questions:
            return 0

        existing_question_ids = set(
            participant.question_assignments.values_list("question_id", flat=True)
        )
        assignments_to_create = [
            EmergencySessionQuestionAssignment(participant=participant, question=question)
            for question in questions
            if question.id not in existing_question_ids
        ]
        if assignments_to_create:
            EmergencySessionQuestionAssignment.objects.bulk_create(assignments_to_create, ignore_conflicts=True)
        return len(questions)

    def get_report_queryset(self):
        queryset = EmergencyReport.objects.select_related(
            "plant",
            "zone",
            "location",
            "sublocation",
            "incident_department",
            "department",
            "reported_by",
            "closed_by",
        ).select_related(
            "action_item",
            "investigation_report",
        ).prefetch_related(
            "response_team_members",
            "photos",
            "action_item__assigned_to",
            "action_item__completed_by_users",
            "capas__assigned_to",
            "capas__created_by",
            "capas__closed_by",
        )

        user = self.request.user
        if user.is_superuser or user.is_admin_user:
            return queryset
        if getattr(user, "role", None) and user.role.name == "EMPLOYEE":
            return queryset.filter(reported_by=user)

        user_plants = user.assigned_plants.filter(is_active=True)
        if user_plants.exists():
            return queryset.filter(plant__in=user_plants).distinct()
        if user.plant:
            return queryset.filter(plant=user.plant)
        return queryset.filter(reported_by=user)


class EmergencyHomeView(EmergencyAccessMixin, TemplateView):
    template_name = "emergency/home.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def _get_primary_site(self):
        report = self.get_report_queryset().exclude(status="CLOSED").first()
        if report and report.plant_id:
            return report.plant

        user = self.request.user
        if user.is_superuser or user.is_admin_user:
            return Plant.objects.filter(is_active=True).order_by("name").first()

        assigned_plant = user.assigned_plants.filter(is_active=True).order_by("name").first()
        if assigned_plant:
            return assigned_plant

        if user.plant_id and user.plant.is_active:
            return user.plant

        return None

    def _get_active_incidents(self):
        reports = list(self.get_report_queryset().exclude(status="CLOSED")[:4])
        if not reports:
            return [
                {
                    "number": "INC-2024-081",
                    "title": "Fire/Explosion",
                    "severity": "Critical",
                    "status": "In Progress",
                    "location": "Sarah Chen",
                    "eta": "ETA 25 min",
                    "badge": "critical",
                },
                {
                    "number": "INC-2024-052",
                    "title": "Chemical Spill",
                    "severity": "Critical",
                    "status": "Dispatched",
                    "location": "Michael Vera",
                    "eta": "ETA 12 min",
                    "badge": "critical",
                },
                {
                    "number": "INC-2024-079",
                    "title": "Medical Emergency",
                    "severity": "Medium",
                    "status": "Containment",
                    "location": "David Ross",
                    "eta": "ETA Arrived",
                    "badge": "medium",
                },
                {
                    "number": "INC-2024-078",
                    "title": "Gas Leak",
                    "severity": "High",
                    "status": "Investigation",
                    "location": "Elena G.",
                    "eta": "ETA On Scene",
                    "badge": "high",
                },
            ], False

        incidents = []
        for report in reports:
            incidents.append(
                {
                    "number": report.report_number,
                    "title": report.emergency_title or report.get_emergency_type_display(),
                    "severity": report.get_severity_level_display(),
                    "status": report.get_status_display(),
                    "location": report.location.name if report.location_id else "Location pending",
                    "eta": "ETA On Scene" if report.response_team_members.exists() else "ETA Pending",
                    "badge": report.severity_level,
                    "url": reverse("emergency:report_detail", args=[report.pk]),
                }
            )
        return incidents, True

    def _get_upcoming_drills(self):
        sessions = list(
            self.get_session_queryset()
            .filter(status__in=["SCHEDULED", "ONGOING"], scheduled_date__gte=timezone.localdate())
            .order_by("scheduled_date", "scheduled_time")[:3]
        )
        if not sessions:
            return [
                {"date": "TOMORROW 09:00", "title": "Full Site Evacuation Drill"},
                {"date": "FRI, AUG 23", "title": "Chemical Leak Response"},
            ], False

        drills = []
        for session in sessions:
            drills.append(
                {
                    "date": f"{session.scheduled_date:%d %b} {session.scheduled_time:%H:%M}",
                    "title": session.topic.name if session.topic_id else session.get_drill_type_display(),
                    "url": reverse("emergency:session_detail", args=[session.pk]),
                }
            )
        return drills, True

    def _get_system_logs(self):
        reports = list(self.get_report_queryset().order_by("-updated_at")[:3])
        if not reports:
            return [
                {"time": "14:12", "message": "All Rivers acknowledged INC-001"},
                {"time": "14:05", "message": "ALERT: Parameter alarm Sector G"},
                {"time": "13:58", "message": "Resource R-212 assigned"},
            ], False

        logs = []
        for report in reports:
            logs.append(
                {
                    "time": timezone.localtime(report.updated_at).strftime("%H:%M"),
                    "message": f"{report.report_number} updated to {report.get_status_display()}",
                    "url": reverse("emergency:report_detail", args=[report.pk]),
                }
            )
        return logs, True

    def _get_ready_responders(self, site):
        if not site:
            return []

        return list(
            User.objects.select_related("department", "role")
            .filter(is_active=True, is_active_employee=True, role__name="SAFETY MANAGER")
            .filter(Q(plant=site) | Q(assigned_plants=site))
            .distinct()
            .order_by("first_name", "last_name", "username")[:5]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_incidents, has_incidents = self._get_active_incidents()
        upcoming_drills, has_drills = self._get_upcoming_drills()
        system_logs, has_logs = self._get_system_logs()
        site = self._get_primary_site()
        responders = self._get_ready_responders(site)
        active_count = self.get_report_queryset().exclude(status="CLOSED").count() if has_incidents else 2

        context.update(
            {
                "command_site": site.name if site else "Site A-12",
                "command_clock": timezone.localtime(timezone.now()),
                "command_alert_ref": active_incidents[0]["number"] if active_incidents else "REF: MAJ-402",
                "command_alert_title": active_incidents[0]["title"] if active_incidents else "Chemical Spill - Warehouse Sector B - Main Logistics Hub",
                "command_active_incidents": active_incidents,
                "command_upcoming_drills": upcoming_drills,
                "command_system_logs": system_logs,
                "command_ready_responders": responders,
                "command_active_incident_count": active_count,
                "command_resource_fire": "98% Ready",
                "command_resource_medical": "84% Low",
                "command_average_response": "4.2m",
                "command_actions": [
                    {
                        "label": "Send Mass Alert",
                        "description": "Broadcast via SMS/Email",
                        "icon": "fas fa-bullhorn",
                        "url_name": "emergency:sos_control_panel",
                    },
                    {
                        "label": "Initiate Safety Drill",
                        "description": "Start evacuation exercise",
                        "icon": "fas fa-play-circle",
                        "url_name": "emergency:session_create",
                    },
                    {
                        "label": "Contact Response Team",
                        "description": "Open direct comms line",
                        "icon": "fas fa-phone-volume",
                        "url_name": "emergency:contact_directory",
                    },
                    {
                        "label": "Muster Points Status",
                        "description": "View assembly counts",
                        "icon": "fas fa-map-marker-alt",
                        "url_name": "emergency:muster_point",
                    },
                ],
                "has_command_incidents": has_incidents,
                "has_command_drills": has_drills,
                "has_command_logs": has_logs,
            }
        )
        return context

class EmergencyEvacuationPlanView(EmergencyAccessMixin, TemplateView):
    template_name = "emergency/evacuation_plan.html"
    page_url_name = "emergency:evacuation_plan"
    page_title = "Evacuation Plan"
    visual_board_label = "Visual Evacuation Plan"
    layout_suffix = "Evacuation Layout"
    default_layout_title = "Plant Evacuation Layout"
    layout_subtitle = "Interactive-style evacuation board with marked exits, fire points, hazards, and assembly route guidance."
    image_alt_label = "evacuation plan"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def _get_accessible_plants(self):
        user = self.request.user
        if user.is_superuser or user.is_admin_user:
            return Plant.objects.filter(is_active=True).order_by("name")

        assigned_plants = user.assigned_plants.filter(is_active=True).order_by("name")
        if assigned_plants.exists():
            return assigned_plants

        if user.plant_id and user.plant.is_active:
            return Plant.objects.filter(pk=user.plant_id, is_active=True)

        return Plant.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plants = self._get_accessible_plants()
        selected_plant_id = self.request.GET.get("plant", "").strip()
        selected_plant = None

        if selected_plant_id:
            selected_plant = plants.filter(pk=selected_plant_id).first()
        if not selected_plant and plants.count() == 1:
            selected_plant = plants.first()
            selected_plant_id = str(selected_plant.pk)

        safety_managers = User.objects.none()
        if selected_plant:
            safety_managers = (
                User.objects.select_related("department", "plant", "role")
                .filter(
                    is_active=True,
                    is_active_employee=True,
                    role__name="SAFETY MANAGER",
                )
                .filter(
                    Q(plant=selected_plant) | Q(assigned_plants=selected_plant)
                )
                .distinct()
                .order_by("first_name", "last_name", "username")
            )

        context.update(
            {
                "plants": plants,
                "selected_plant": selected_plant_id,
                "selected_plant_obj": selected_plant,
                "safety_managers": safety_managers,
                "page_url_name": self.page_url_name,
                "page_title": self.page_title,
                "visual_board_label": self.visual_board_label,
                "layout_suffix": self.layout_suffix,
                "default_layout_title": self.default_layout_title,
                "layout_subtitle": self.layout_subtitle,
                "image_alt_label": self.image_alt_label,
            }
        )
        return context


class EmergencyMusterPointView(EmergencyEvacuationPlanView):
    template_name = "emergency/muster_point.html"
    page_url_name = "emergency:muster_point"
    page_title = "Muster Point"
    visual_board_label = "Visual Muster Point Plan"
    layout_suffix = "Muster Point Layout"
    default_layout_title = "Plant Muster Point Layout"
    layout_subtitle = "Interactive-style muster point board with marked exits, fire points, hazards, and assembly route guidance."
    image_alt_label = "muster point plan"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "last_updated": timezone.localtime(timezone.now()),
                "muster_stats": [
                    {
                        "label": "Total Headcount",
                        "value": "256",
                        "meta": "Employees",
                        "icon": "fas fa-users",
                        "tone": "green",
                    },
                    {
                        "label": "Present at Muster Point",
                        "value": "243",
                        "meta": "95.3%",
                        "icon": "far fa-check-circle",
                        "tone": "success",
                    },
                    {
                        "label": "Not Accounted For",
                        "value": "13",
                        "meta": "5.1%",
                        "icon": "fas fa-user-clock",
                        "tone": "warning",
                    },
                    {
                        "label": "Visitors",
                        "value": "0",
                        "meta": "Present",
                        "icon": "fas fa-id-card",
                        "tone": "blue",
                    },
                ],
                "muster_zones": [
                    {"name": "Zone A", "area": "Main Gate Area", "count": "87 / 92", "percent": "94.6%"},
                    {"name": "Zone B", "area": "North Parking Area", "count": "78 / 82", "percent": "95.1%"},
                    {"name": "Zone C", "area": "South Assembly Area", "count": "78 / 82", "percent": "95.1%"},
                ],
                "muster_alerts": [
                    {
                        "title": "13 people not accounted for",
                        "message": "Please initiate headcount verification.",
                        "time": "10:21 AM",
                        "icon": "fas fa-exclamation-circle",
                        "tone": "danger",
                    },
                    {
                        "title": "High winds detected",
                        "message": "Proceed to designated muster points and remain clear of structures.",
                        "time": "10:15 AM",
                        "icon": "fas fa-exclamation-triangle",
                        "tone": "warning",
                    },
                    {
                        "title": "Fire drill in progress",
                        "message": "This is a scheduled drill. Please follow warden instructions.",
                        "time": "10:00 AM",
                        "icon": "fas fa-info-circle",
                        "tone": "info",
                    },
                ],
                "quick_actions": [
                    {
                        "label": "Activate Alarm",
                        "icon": "fas fa-bell",
                        "url_name": "emergency:sos_control_panel",
                        "tone": "danger",
                    },
                    {
                        "label": "Roll Call Headcount",
                        "icon": "fas fa-users",
                        "url_name": "emergency:muster_point",
                        "tone": "success",
                    },
                    {
                        "label": "Report Missing Person",
                        "icon": "fas fa-search",
                        "url_name": "emergency:report_create",
                        "tone": "blue",
                    },
                    {
                        "label": "Evacuation Log",
                        "icon": "fas fa-clipboard-list",
                        "url_name": "emergency:evacuation_plan",
                        "tone": "purple",
                    },
                    {
                        "label": "End Emergency",
                        "icon": "fas fa-shield-alt",
                        "url_name": "emergency:report_list",
                        "tone": "orange",
                    },
                ],
                "default_emergency_contacts": [
                    {"name": "Site Emergency Coordinator", "phone": "+1 234 567 8901", "icon": "fas fa-user", "tone": "success"},
                    {"name": "Security Control Room", "phone": "+1 234 567 8902", "icon": "fas fa-shield-alt", "tone": "blue"},
                    {"name": "Medical Team", "phone": "+1 234 567 8903", "icon": "fas fa-plus", "tone": "danger"},
                    {"name": "Fire Department", "phone": "+1 234 567 8904", "icon": "fas fa-fire", "tone": "orange"},
                ],
            }
        )
        return context


class EmergencyTopicListView(EmergencyAccessMixin, ListView):
    model = EmergencyTopic
    template_name = "emergency/topic_list.html"
    context_object_name = "topics"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to view emergency topics.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = EmergencyTopic.objects.annotate(session_count=Count("sessions")).order_by("name")
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search) | Q(description__icontains=search)
            )
        category = self.request.GET.get("category", "").strip()
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["category_choices"] = EmergencyTopic.CATEGORY_CHOICES
        return context


class EmergencyTopicCreateView(EmergencyAccessMixin, CreateView):
    model = EmergencyTopic
    form_class = EmergencyTopicForm
    template_name = "emergency/topic_form.html"
    success_url = reverse_lazy("emergency:topic_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        if not self.user_can_manage():
            messages.error(request, "You don't have permission to manage emergency topics.")
            return redirect("emergency:topic_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Emergency topic "{self.object.name}" created successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = "Create"
        return context


class EmergencyTopicUpdateView(EmergencyAccessMixin, UpdateView):
    model = EmergencyTopic
    form_class = EmergencyTopicForm
    template_name = "emergency/topic_form.html"
    success_url = reverse_lazy("emergency:topic_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        if not self.user_can_manage():
            messages.error(request, "You don't have permission to edit emergency topics.")
            return redirect("emergency:topic_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Emergency topic "{self.object.name}" updated successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = "Update"
        return context


class EmergencySessionCreateView(EmergencyAccessMixin, CreateView):
    model = EmergencySession
    form_class = EmergencySessionForm
    template_name = "emergency/session_create.html"
    success_url = reverse_lazy("emergency:session_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        if not self.can_schedule_emergency_drill():
            messages.error(request, "You don't have permission to schedule emergency sessions.")
            return redirect("emergency:session_list")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_trainer_formset(self):
        if self.request.method == "POST":
            return EmergencySessionTrainerFormSet(self.request.POST, prefix="trainers")
        return EmergencySessionTrainerFormSet(prefix="trainers")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_location_context())
        context["trainer_formset"] = kwargs.get("trainer_formset", self.get_trainer_formset())
        context["active_topics"] = EmergencyTopic.objects.filter(is_active=True).order_by("name")
        context["drill_type_choices"] = [
            {
                "value": value,
                "label": label,
                "category": EmergencySession.DRILL_CATEGORY_MAP.get(value, ""),
            }
            for value, label in EmergencySession.DRILL_TYPE_CHOICES
        ]
        context["cancel_url"] = self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or "/"
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        trainer_formset = self.get_trainer_formset()
        if form.is_valid() and trainer_formset.is_valid():
            return self.forms_valid(form, trainer_formset)
        return self.forms_invalid(form, trainer_formset)

    def forms_valid(self, form, trainer_formset):
        session = form.save(commit=False)
        session.created_by = self.request.user
        user = self.request.user

        if user.assigned_plants.count() == 1 and not form.cleaned_data.get("plant"):
            session.plant = user.assigned_plants.first()
        if user.assigned_zones.count() == 1 and not form.cleaned_data.get("zone"):
            session.zone = user.assigned_zones.first()
        if user.assigned_locations.count() == 1 and not form.cleaned_data.get("location"):
            session.location = user.assigned_locations.first()
        if user.assigned_sublocations.count() == 1 and not form.cleaned_data.get("sublocation"):
            session.sublocation = user.assigned_sublocations.first()

        session.save()
        trainer_formset.instance = session
        trainer_formset.save()
        self.object = session
        messages.success(self.request, f'Emergency session "{session.session_number}" scheduled successfully.')
        return redirect("emergency:session_detail", pk=session.pk)

    def forms_invalid(self, form, trainer_formset):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form, trainer_formset=trainer_formset))


class EmergencySessionListView(EmergencyAccessMixin, ListView):
    model = EmergencySession
    template_name = "emergency/session_list.html"
    context_object_name = "sessions"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        if not self.can_view_emergency_drill():
            messages.error(request, "You don't have permission to view emergency sessions.")
            return redirect("emergency:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.get_session_queryset()
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(session_number__icontains=search)
                | Q(topic__name__icontains=search)
                | Q(trainers__trainer_name__icontains=search)
                | Q(trainers__trainer_user__first_name__icontains=search)
                | Q(trainers__trainer_user__last_name__icontains=search)
                | Q(trainers__trainer_user__username__icontains=search)
                | Q(trainers__trainer_user__employee_id__icontains=search)
                | Q(trainers__trainer_department__name__icontains=search)
            ).distinct()

        topic = self.request.GET.get("topic", "").strip()
        if topic:
            queryset = queryset.filter(topic_id=topic)

        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        plant = self.request.GET.get("plant", "").strip()
        if plant:
            queryset = queryset.filter(plant_id=plant)

        drill_type = self.request.GET.get("drill_type", "").strip()
        if drill_type:
            queryset = queryset.filter(drill_type=drill_type)

        date_from = self.request.GET.get("date_from", "").strip()
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)

        date_to = self.request.GET.get("date_to", "").strip()
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)

        return queryset.order_by("-scheduled_date", "-scheduled_time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["topics"] = EmergencyTopic.objects.filter(is_active=True).order_by("name")
        context["plants"] = Plant.objects.filter(is_active=True).order_by("name")
        context["status_choices"] = EmergencySession.STATUS_CHOICES
        context["drill_type_choices"] = EmergencySession.DRILL_TYPE_CHOICES
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_topic"] = self.request.GET.get("topic", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_plant"] = self.request.GET.get("plant", "")
        context["selected_drill_type"] = self.request.GET.get("drill_type", "")
        return context


class EmergencyReportListView(EmergencyAccessMixin, ListView):
    model = EmergencyReport
    template_name = "emergency/report_list.html"
    context_object_name = "reports"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not self.can_view_emergency_report():
            messages.error(request, "You don't have permission to view emergency reports.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.get_report_queryset().order_by("-incident_date", "-incident_time", "-id")
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(report_number__icontains=search)
                | Q(emergency_title__icontains=search)
                | Q(description__icontains=search)
            )

        emergency_type = self.request.GET.get("emergency_type", "").strip()
        if emergency_type:
            queryset = queryset.filter(emergency_type=emergency_type)

        severity = self.request.GET.get("severity", "").strip()
        if severity:
            queryset = queryset.filter(severity_level=severity)

        plant = self.request.GET.get("plant", "").strip()
        if plant:
            queryset = queryset.filter(plant_id=plant)

        date_from = self.request.GET.get("date_from", "").strip()
        if date_from:
            queryset = queryset.filter(incident_date__gte=date_from)

        date_to = self.request.GET.get("date_to", "").strip()
        if date_to:
            queryset = queryset.filter(incident_date__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plants"] = Plant.objects.filter(is_active=True).order_by("name")
        context["emergency_type_choices"] = EmergencyReport.EMERGENCY_TYPE_CHOICES
        context["severity_choices"] = EmergencyReport.SEVERITY_CHOICES
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_emergency_type"] = self.request.GET.get("emergency_type", "")
        context["selected_severity"] = self.request.GET.get("severity", "")
        context["selected_plant"] = self.request.GET.get("plant", "")
        return context


class EmergencyReportCreateView(EmergencyAccessMixin, CreateView):
    model = EmergencyReport
    form_class = EmergencyReportForm
    template_name = "emergency/report_create.html"
    success_url = reverse_lazy("emergency:report_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_create_emergency_report():
            messages.error(request, "You don't have permission to create emergency reports.")
            return redirect("emergency:report_list")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_location_context())
        context["cancel_url"] = self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or "/"
        return context

    def form_valid(self, form):
        report = form.save(commit=False)
        report.reported_by = self.request.user

        user = self.request.user
        if user.assigned_plants.count() == 1 and not form.cleaned_data.get("plant"):
            report.plant = user.assigned_plants.first()
        if user.assigned_zones.count() == 1 and not form.cleaned_data.get("zone"):
            report.zone = user.assigned_zones.first()
        if user.assigned_locations.count() == 1 and not form.cleaned_data.get("location"):
            report.location = user.assigned_locations.first()
        if user.assigned_sublocations.count() == 1 and not form.cleaned_data.get("sublocation"):
            report.sublocation = user.assigned_sublocations.first()

        response_team_members = list(form.cleaned_data.get("response_team_members") or [])
        if response_team_members:
            report.status = "ACTION_PENDING"
        report.save()
        form.save_m2m()
        self.object = report

        NotificationService.notify(
            content_object=report,
            notification_type="EMERGENCY_REPORTED",
            module="EMERGENCY",
            extra_recipients=[report.reported_by],
        )

        if response_team_members:
            action_description = (report.immediate_actions_taken or "").strip() or f"Respond to emergency: {report.emergency_title}"
            action_item = EmergencyActionItem.objects.create(
                report=report,
                action_description=action_description,
                created_by=self.request.user,
            )
            action_item.assigned_to.set(response_team_members)
            NotificationService.notify(
                content_object=action_item,
                notification_type="EMERGENCY_ACTION_ASSIGNED",
                module="EMERGENCY",
                extra_recipients=response_team_members + [report.reported_by],
            )

        for photo in self.request.FILES.getlist("photos"):
            compressed_photo = compress_image(photo)
            EmergencyReportPhoto.objects.create(
                report=report,
                photo=compressed_photo,
                uploaded_by=self.request.user,
            )

        messages.success(self.request, f"Emergency report {report.report_number} submitted successfully.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class EmergencySOSControlPanelView(EmergencyAccessMixin, CreateView):
    model = EmergencyReport
    form_class = EmergencySOSReportForm
    template_name = "emergency/sos_control_panel.html"
    success_url = reverse_lazy("emergency:report_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_location_context())
        context["cancel_url"] = self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or reverse("emergency:home")
        return context

    def form_valid(self, form):
        report = form.save(commit=False)
        report.reported_by = self.request.user
        report.incident_date = timezone.localdate()
        report.incident_time = timezone.localtime().time().replace(second=0, microsecond=0)
        report.immediate_actions_taken = ""
        report.additional_location_details = ""

        user = self.request.user
        if user.assigned_plants.count() == 1 and not form.cleaned_data.get("plant"):
            report.plant = user.assigned_plants.first()
        elif not user.assigned_plants.exists() and user.plant_id and not form.cleaned_data.get("plant"):
            report.plant = user.plant
        if user.assigned_zones.count() == 1 and not form.cleaned_data.get("zone"):
            report.zone = user.assigned_zones.first()
        if user.assigned_locations.count() == 1 and not form.cleaned_data.get("location"):
            report.location = user.assigned_locations.first()
        if user.assigned_sublocations.count() == 1 and not form.cleaned_data.get("sublocation"):
            report.sublocation = user.assigned_sublocations.first()

        target_department = _get_sos_department_for_type(report.emergency_type)
        report.department = target_department
        recipients = list(_get_department_users_for_report(report, target_department))
        if recipients:
            report.status = "ACTION_PENDING"
        report.save()
        self.object = report

        if recipients:
            report.response_team_members.set(recipients)
            action_item = EmergencyActionItem.objects.create(
                report=report,
                action_description=f"SOS emergency response required: {report.emergency_title}",
                created_by=self.request.user,
            )
            action_item.assigned_to.set(recipients)
            NotificationService.notify(
                content_object=report,
                notification_type="EMERGENCY_REPORTED",
                module="EMERGENCY",
                extra_recipients=[report.reported_by],
            )
            NotificationService.notify(
                content_object=action_item,
                notification_type="EMERGENCY_ACTION_ASSIGNED",
                module="EMERGENCY",
                extra_recipients=recipients + [report.reported_by],
            )
        else:
            NotificationService.notify(
                content_object=report,
                notification_type="EMERGENCY_REPORTED",
                module="EMERGENCY",
                extra_recipients=[report.reported_by],
            )

        messages.success(self.request, f"SOS alert {report.report_number} reported successfully.")
        if target_department and not recipients:
            messages.warning(
                self.request,
                f"The alert was mapped to {target_department.name}, but no active users were found for the selected plant.",
            )
        elif not target_department:
            messages.warning(
                self.request,
                "The alert was saved, but no matching response department was found for this emergency type.",
            )
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class EmergencyReportDetailView(EmergencyAccessMixin, DetailView):
    model = EmergencyReport
    template_name = "emergency/report_detail.html"
    context_object_name = "report"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_view_emergency_report():
            messages.error(request, "You don't have permission to view emergency reports.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_report_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or reverse("emergency:report_list")
        action_item = getattr(self.object, "action_item", None)
        investigation_report = getattr(self.object, "investigation_report", None)
        can_create_capa, capa_message = self.object.can_create_capa
        can_close, closure_message = self.object.can_be_closed
        context["action_item"] = action_item
        context["investigation_report"] = investigation_report
        context["capas"] = self.object.capas.select_related("assigned_to", "created_by", "closed_by")
        context["latest_capa"] = self.object.latest_capa
        context["can_create_capa"] = can_create_capa and self.can_manage_emergency_capa()
        context["capa_message"] = capa_message
        context["show_closure_action"] = self.can_close_emergency()
        context["can_close_report"] = can_close and self.can_close_emergency()
        context["closure_message"] = closure_message
        context["user_can_complete_action"] = bool(
            action_item
            and self.request.user in action_item.assigned_to.all()
            and self.request.user not in action_item.completed_by_users.all()
            and action_item.status != "ACTION_PERFORMED"
        )
        context["can_investigate"] = (
            self.object.status == "ACTION_PERFORMED"
            and investigation_report is None
            and self.can_create_emergency_investigation()
        )
        return context


class EmergencyReportUpdateView(EmergencyAccessMixin, UpdateView):
    model = EmergencyReport
    form_class = EmergencyReportForm
    template_name = "emergency/report_create.html"
    context_object_name = "report"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.can_edit_emergency_report():
            messages.error(request, "You do not have permission to edit this emergency report.")
            return redirect("emergency:report_detail", pk=self.object.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_report_queryset()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_location_context())
        context["cancel_url"] = self.request.GET.get("next") or reverse("emergency:report_detail", kwargs={"pk": self.object.pk})
        context["is_edit"] = True
        return context

    def get_success_url(self):
        return reverse("emergency:report_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        self.object = form.save()
        for photo in self.request.FILES.getlist("photos"):
            compressed_photo = compress_image(photo)
            EmergencyReportPhoto.objects.create(
                report=self.object,
                photo=compressed_photo,
                uploaded_by=self.request.user,
            )
        messages.success(self.request, f"Emergency report {self.object.report_number} updated successfully.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class EmergencyReportPDFView(EmergencyAccessMixin, View):
    def get(self, request, pk):
        if not self.can_download_emergency_report():
            messages.error(request, "You don't have permission to download emergency reports.")
            return redirect("emergency:report_detail", pk=pk)
        report = get_object_or_404(self.get_report_queryset(), pk=pk)
        return generate_emergency_report_pdf(report)


class EmergencyMyActionItemsView(EmergencyAccessMixin, ListView):
    model = EmergencyActionItem
    template_name = "emergency/my_action_items.html"
    context_object_name = "action_items"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not self.can_view_emergency_report():
            messages.error(request, "You don't have permission to view emergency action items.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = EmergencyActionItem.objects.filter(
            assigned_to=self.request.user
        ).select_related(
            "report",
            "report__plant",
            "report__location",
            "created_by",
        ).prefetch_related(
            "completed_by_users",
            "assigned_to",
        ).order_by("-created_at")

        status_filter = self.request.GET.get("status", "").strip()
        severity_filter = self.request.GET.get("severity", "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if severity_filter:
            queryset = queryset.filter(report__severity_level=severity_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_items = self.get_queryset()
        my_completed = all_items.filter(completed_by_users=self.request.user)
        my_pending = all_items.exclude(completed_by_users=self.request.user)

        context["total_assigned"] = all_items.count()
        context["completed_count"] = my_completed.count()
        context["pending_count"] = my_pending.count()
        context["overdue_count"] = 0
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_severity"] = self.request.GET.get("severity", "")
        context["status_choices"] = EmergencyActionItem.STATUS_CHOICES
        context["severity_choices"] = EmergencyReport.SEVERITY_CHOICES

        for item in context["action_items"]:
            item.user_has_completed = self.request.user in item.completed_by_users.all()

        return context


class EmergencyActionItemCompleteView(EmergencyAccessMixin, UpdateView):
    model = EmergencyActionItem
    form_class = EmergencyActionItemCompletionForm
    template_name = "emergency/action_item_complete.html"
    context_object_name = "action_item"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user not in self.object.assigned_to.all():
            messages.error(request, "You are not assigned to this emergency action item.")
            return redirect("emergency:my_action_items")
        if self.object.status == "ACTION_PERFORMED":
            messages.info(request, "This emergency action has already been completed.")
            return redirect("emergency:my_action_items")
        if request.user in self.object.completed_by_users.all():
            messages.info(request, "You have already completed this emergency action.")
            return redirect("emergency:my_action_items")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.object.report
        return context

    def form_valid(self, form):
        action_item = form.save(commit=False)
        action_item.completion_datetime = form.cleaned_data["completion_datetime"]
        action_item.completion_remarks = form.cleaned_data["completion_remarks"]
        if form.cleaned_data.get("attachment"):
            action_item.attachment = form.cleaned_data["attachment"]
        action_item.save()
        action_item.completed_by_users.add(self.request.user)
        action_item.save()

        report = action_item.report
        report.status = "ACTION_PERFORMED"
        report.save(update_fields=["status", "updated_at"])

        NotificationService.notify(
            content_object=action_item,
            notification_type="EMERGENCY_ACTION_COMPLETED",
            module="EMERGENCY",
            extra_recipients=[report.reported_by] + list(report.response_team_members.all()) + list(action_item.assigned_to.all()),
        )
        messages.success(self.request, "Emergency action marked as completed successfully.")
        return redirect("emergency:my_action_items")


class EmergencyInvestigationCreateView(EmergencyAccessMixin, CreateView):
    model = EmergencyInvestigationReport
    form_class = EmergencyInvestigationReportForm
    template_name = "emergency/investigation_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(self.get_report_queryset(), pk=self.kwargs["report_pk"])
        if self.report.status != "ACTION_PERFORMED":
            messages.error(request, "Investigation can start only after action is performed.")
            return redirect("emergency:report_detail", pk=self.report.pk)
        if hasattr(self.report, "investigation_report"):
            messages.info(request, "Investigation report already exists for this emergency.")
            return redirect("emergency:investigation_detail", pk=self.report.investigation_report.pk)
        if not self.can_create_emergency_investigation():
            messages.error(request, "You don't have permission to investigate this emergency.")
            return redirect("emergency:report_detail", pk=self.report.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.report
        context["cancel_url"] = self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or reverse("emergency:report_detail", args=[self.report.pk])
        return context

    def form_valid(self, form):
        investigation = form.save(commit=False)
        investigation.report = self.report
        investigation.investigator = self.request.user
        investigation.save()

        self.report.status = "INVESTIGATION_COMPLETED"
        self.report.save(update_fields=["status", "updated_at"])

        NotificationService.notify(
            content_object=investigation,
            notification_type="EMERGENCY_INVESTIGATION_COMPLETED",
            module="EMERGENCY",
            extra_recipients=[self.report.reported_by, self.request.user] + list(self.report.response_team_members.all()),
        )
        messages.success(self.request, "Emergency investigation submitted successfully.")
        return redirect("emergency:report_detail", pk=self.report.pk)


class EmergencyInvestigationDetailView(EmergencyAccessMixin, DetailView):
    model = EmergencyInvestigationReport
    template_name = "emergency/investigation_detail.html"
    context_object_name = "investigation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.object.report
        context["cancel_url"] = self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or reverse("emergency:report_detail", args=[self.object.report.pk])
        return context

class EmergencyCAPACreateView(EmergencyAccessMixin, CreateView):
    model = EmergencyCAPA
    form_class = EmergencyCAPACreateForm
    template_name = "emergency/capa_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(self.get_report_queryset(), pk=kwargs["report_pk"])
        if not self.can_manage_emergency_capa():
            messages.error(request, "You don't have permission to create CAPA for this emergency.")
            return redirect("emergency:report_detail", pk=self.report.pk)
        can_create, message = self.report.can_create_capa
        if not can_create:
            messages.error(request, message)
            return redirect("emergency:report_detail", pk=self.report.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.report
        context["previous_capas"] = self.report.capas.select_related("assigned_to")
        context["cancel_url"] = reverse("emergency:report_detail", args=[self.report.pk])
        return context

    def form_valid(self, form):
        form.instance.report = self.report
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        NotificationService.notify(
            content_object=self.object,
            notification_type="EMERGENCY_CAPA_CREATED",
            module="EMERGENCY",
            extra_recipients=[self.report.reported_by, self.request.user, self.object.assigned_to] + list(self.report.response_team_members.all()),
        )
        messages.success(self.request, "Emergency CAPA created successfully.")
        return response

    def get_success_url(self):
        return reverse("emergency:report_detail", kwargs={"pk": self.report.pk})


class EmergencyCAPAUpdateView(EmergencyAccessMixin, UpdateView):
    model = EmergencyCAPA
    form_class = EmergencyCAPAUpdateForm
    template_name = "emergency/capa_update.html"
    context_object_name = "capa"

    def get_queryset(self):
        return EmergencyCAPA.objects.select_related("report", "assigned_to", "created_by", "closed_by")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not (
            self.can_manage_emergency_capa()
            or request.user == self.object.assigned_to
            or request.user == self.object.report.reported_by
        ):
            messages.error(request, "You don't have permission to update this CAPA.")
            return redirect("emergency:report_detail", pk=self.object.report.pk)
        if self.object.report.status == "CLOSED":
            messages.error(request, "CAPA cannot be updated after the emergency has been closed.")
            return redirect("emergency:report_detail", pk=self.object.report.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        capa = form.save(commit=False)
        if capa.status == EmergencyCAPA.STATUS_CLOSED:
            capa.closed_by = self.request.user
            capa.closed_at = timezone.now()
        else:
            capa.closed_by = None
            capa.closed_at = None
        capa.save()
        capa_recipients = [capa.report.reported_by, capa.assigned_to, capa.created_by]
        if capa.closed_by:
            capa_recipients.append(capa.closed_by)
        capa_recipients.extend(list(capa.report.response_team_members.all()))
        NotificationService.notify(
            content_object=capa,
            notification_type="EMERGENCY_CAPA_UPDATED",
            module="EMERGENCY",
            extra_recipients=capa_recipients,
        )
        messages.success(self.request, "Emergency CAPA updated successfully.")
        return redirect("emergency:report_detail", pk=capa.report.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.object.report
        context["cancel_url"] = reverse("emergency:report_detail", args=[self.object.report.pk])
        return context


class EmergencyClosureCheckView(EmergencyAccessMixin, View):
    template_name = "emergency/closure_check.html"

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(self.get_report_queryset(), pk=kwargs["pk"])
        if not self.can_close_emergency():
            messages.error(request, "You don't have permission to close this emergency.")
            return redirect("emergency:report_detail", pk=self.report.pk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        can_close, closure_message = self.report.can_be_closed
        context = {
            "report": self.report,
            "action_item": getattr(self.report, "action_item", None),
            "investigation": getattr(self.report, "investigation_report", None),
            "capas": self.report.capas.select_related("assigned_to", "closed_by"),
            "can_close": can_close,
            "closure_message": closure_message,
        }
        return render(request, self.template_name, context)


class EmergencyClosureView(EmergencyAccessMixin, UpdateView):
    model = EmergencyReport
    form_class = EmergencyClosureForm
    template_name = "emergency/closure_form.html"
    context_object_name = "report"

    def get_queryset(self):
        return self.get_report_queryset()

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.can_close_emergency():
            messages.error(request, "You don't have permission to close this emergency.")
            return redirect("emergency:report_detail", pk=self.object.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_close, closure_message = self.object.can_be_closed
        context["can_close"] = can_close
        context["closure_message"] = closure_message
        return context

    def form_valid(self, form):
        report = form.save(commit=False)
        can_close, closure_message = report.can_be_closed
        if not can_close:
            messages.error(self.request, closure_message)
            return redirect("emergency:closure_check", pk=report.pk)

        report.status = "CLOSED"
        report.closure_date = timezone.now()
        report.closed_by = self.request.user
        report.save()
        NotificationService.notify(
            content_object=report,
            notification_type="EMERGENCY_CLOSED",
            module="EMERGENCY",
            extra_recipients=[report.reported_by, self.request.user] + list(report.response_team_members.all()),
        )
        messages.success(self.request, f"Emergency report {report.report_number} has been closed successfully.")
        return redirect("emergency:report_detail", pk=report.pk)


class EmergencyDepartmentUsersAjaxView(EmergencyAccessMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        department_id = request.GET.get("department_id")
        plant_id = request.GET.get("plant_id")

        users = User.objects.filter(
            is_active=True,
            is_active_employee=True,
            department__isnull=False,
            department__is_active=True,
        ).select_related("department").order_by("first_name", "last_name", "username")

        if department_id:
            users = users.filter(department_id=department_id)
        if plant_id:
            users = users.filter(
                Q(plant_id=plant_id) | Q(assigned_plants__id=plant_id)
            ).distinct()

        data = [
            {
                "id": user.id,
                "name": user.get_full_name() or user.username,
                "employee_id": user.employee_id or "",
                "department_id": user.department_id,
                "department_name": user.department.name if user.department else "",
            }
            for user in users
        ]
        return JsonResponse(data, safe=False)


class EmergencyGetZonesAjaxView(EmergencyAccessMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        plant_id = request.GET.get("plant_id")
        zones = Zone.objects.filter(plant_id=plant_id, is_active=True).values("id", "name", "code")
        return JsonResponse(list(zones), safe=False)


class EmergencyGetLocationsAjaxView(EmergencyAccessMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        zone_id = request.GET.get("zone_id")
        locations = Location.objects.filter(zone_id=zone_id, is_active=True).values("id", "name", "code")
        return JsonResponse(list(locations), safe=False)


class EmergencyGetSublocationsAjaxView(EmergencyAccessMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        location_id = request.GET.get("location_id")
        sublocations = SubLocation.objects.filter(location_id=location_id, is_active=True).values(
            "id",
            "name",
            "code",
        )
        return JsonResponse(list(sublocations), safe=False)


class ERTQuestionListView(EmergencyAccessMixin, View):
    template_name = "emergency/question_list.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to view ERT department questions.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        questions = ERTDepartmentQuestion.objects.select_related("department").filter(is_active=True)
        filter_form = ERTDepartmentQuestionFilterForm(request.GET or None)

        if filter_form.is_valid():
            department = filter_form.cleaned_data.get("department")
            question_type = filter_form.cleaned_data.get("question_type")
            is_critical = filter_form.cleaned_data.get("is_critical")
            search = filter_form.cleaned_data.get("search")

            if department:
                questions = questions.filter(department=department)
            if question_type:
                questions = questions.filter(question_type=question_type)
            if is_critical == "true":
                questions = questions.filter(is_critical=True)
            elif is_critical == "false":
                questions = questions.filter(is_critical=False)
            if search:
                questions = questions.filter(
                    Q(question_text__icontains=search)
                    | Q(question_code__icontains=search)
                    | Q(department__name__icontains=search)
                )

        questions = questions.order_by("department__name", "question_code")
        paginator = Paginator(questions, 25)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(
            request,
            self.template_name,
            {
                "filter_form": filter_form,
                "page_obj": page_obj,
                "total_questions": questions.count(),
            },
        )


class ERTQuestionCreateView(EmergencyAccessMixin, CreateView):
    model = ERTDepartmentQuestion
    form_class = ERTDepartmentQuestionForm
    template_name = "emergency/question_form.html"
    success_url = reverse_lazy("emergency:question_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        if not self.user_can_manage():
            messages.error(request, "You don't have permission to manage ERT department questions.")
            return redirect("emergency:question_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.save()
        messages.success(self.request, f'Question "{self.object.question_code}" created successfully.')
        if self.request.POST.get("action_type") == "save_and_add":
            return redirect("emergency:question_create")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add ERT Department Question"
        context["action"] = "Create"
        return context


class ERTQuestionUpdateView(EmergencyAccessMixin, UpdateView):
    model = ERTDepartmentQuestion
    form_class = ERTDepartmentQuestionForm
    template_name = "emergency/question_form.html"
    success_url = reverse_lazy("emergency:question_list")

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        if not self.user_can_manage():
            messages.error(request, "You don't have permission to edit ERT department questions.")
            return redirect("emergency:question_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user
        self.object.save()
        messages.success(self.request, f'Question "{self.object.question_code}" updated successfully.')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Question: {self.object.question_code}"
        context["action"] = "Update"
        context["question"] = self.object
        return context


class ERTQuestionDeleteView(EmergencyAccessMixin, View):
    template_name = "emergency/question_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_module():
            messages.error(request, "You don't have permission to access the emergency module.")
            return redirect("dashboards:home")
        if not self.user_can_manage():
            messages.error(request, "You don't have permission to delete ERT department questions.")
            return redirect("emergency:question_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, *args, **kwargs):
        question = get_object_or_404(ERTDepartmentQuestion, pk=pk)
        return render(request, self.template_name, {"question": question})

    def post(self, request, pk, *args, **kwargs):
        question = get_object_or_404(ERTDepartmentQuestion, pk=pk)
        question.is_active = False
        question.updated_by = request.user
        question.save(update_fields=["is_active", "updated_by", "updated_at"])
        messages.success(request, f'Question "{question.question_code}" deleted successfully.')
        return redirect("emergency:question_list")


class ContactDirectoryView(EmergencyAccessMixin, TemplateView):
    template_name = "emergency/contact_directory.html"

    department_sections = [
        ("Medical Department", ["medical department", "medical"]),
        ("Fire Safety Department", ["fire safety department", "fire safety", "fire department", "fire response"]),
        ("Logistic Department", ["logistic department", "logistics department", "logistic", "logistics"]),
        ("Management Department", ["management department", "management"]),
        ("Security Department", ["security department", "security"]),
        ("ERM Department", ["erm department", "erm", "emergency response management"]),
    ]

    def _normalize_department_name(self, value):
        return _normalize_department_name(value)

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        employees = list(
            User.objects.select_related("department", "plant")
            .filter(
                is_active=True,
                is_active_employee=True,
                department__isnull=False,
                department__is_active=True,
            )
            .order_by("department__name", "first_name", "last_name", "username")
        )

        employees_by_department = {}
        for employee in employees:
            normalized_name = self._normalize_department_name(employee.department.name)
            employees_by_department.setdefault(normalized_name, []).append(employee)

        contact_sections = []
        for section_name, aliases in self.department_sections:
            allowed_names = {self._normalize_department_name(section_name)}
            allowed_names.update(self._normalize_department_name(alias) for alias in aliases)

            section_employees = []
            for normalized_name, department_employees in employees_by_department.items():
                if normalized_name in allowed_names:
                    section_employees.extend(department_employees)

            contact_sections.append(
                {
                    "name": section_name,
                    "employees": section_employees,
                    "employee_count": len(section_employees),
                }
            )
        context["plants"] = (Plant.objects.filter(is_active=True).order_by("name"))
        context["contact_sections"] = contact_sections
        return context

class EmergencySessionDetailView(EmergencyAccessMixin, DetailView):
    model = EmergencySession
    template_name = "emergency/session_detail.html"
    context_object_name = "session"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        if not self.can_view_emergency_drill():
            messages.error(request, "You don't have permission to view emergency sessions.")
            return redirect("emergency:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_session_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        context["trainers"] = session.trainers.select_related(
            "trainer_department",
            "trainer_user",
            "trainer_user__department",
        ).all()
        context["trainer_count"] = context["trainers"].count()
        context["participants"] = session.participants.select_related(
            "employee",
            "submission",
            "reviewed_by",
        ).all()
        context["participant_count"] = context["participants"].count()
        context["completed_participants"] = session.participants.select_related(
            "employee",
            "submission",
            "submission__reviewed_by",
        ).filter(submission__isnull=False)
        context["can_review"] = self.can_review_sessions()
        context["cancel_url"] = (
            self.request.GET.get("next")
            or self.request.META.get("HTTP_REFERER")
            or reverse_lazy("emergency:session_list")
        )
        return context


class EmergencyAddParticipantsView(EmergencyAccessMixin, View):
    template_name = "emergency/add_participants.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        self.session = get_object_or_404(self.get_session_queryset(), pk=kwargs["pk"])
        if self.session.status in ["COMPLETED", "CANCELLED"]:
            messages.error(request, "Cannot add participants to a completed or cancelled session.")
            return redirect("emergency:session_detail", pk=self.session.pk)
        if not self.can_schedule_emergency_drill():
            messages.error(request, "You don't have permission to add participants.")
            return redirect("emergency:session_detail", pk=self.session.pk)
        return super().dispatch(request, *args, **kwargs)

    def _available_employees(self, search=""):
        already_added = self.session.participants.values_list("employee_id", flat=True)
        employees = User.objects.filter(
            is_active=True,
            is_active_employee=True,
        ).filter(
            Q(plant=self.session.plant) | Q(assigned_plants=self.session.plant)
        ).exclude(id__in=already_added).select_related("department", "role").distinct()

        if search:
            employees = employees.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(employee_id__icontains=search)
            )
        return employees

    def get(self, request, *args, **kwargs):
        search = request.GET.get("search", "").strip()
        context = {
            "session": self.session,
            "available_employees": self._available_employees(search),
            "current_participants": self.session.participants.select_related("employee", "submission").all(),
            "search_query": search,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        employee_ids = request.POST.getlist("employee_ids")
        added_count = 0
        synced_count = 0

        for employee in User.objects.filter(id__in=employee_ids, is_active=True):
            participant, created = EmergencySessionParticipant.objects.get_or_create(
                session=self.session,
                employee=employee,
            )
            synced_questions = self.sync_participant_question_assignments(participant)
            if created:
                added_count += 1
            if synced_questions:
                synced_count += 1

        if added_count:
            messages.success(
                request,
                f"{added_count} participant(s) added successfully and department questions assigned to {synced_count} participant(s).",
            )
        else:
            messages.info(request, "No new participants were added.")
        return redirect("emergency:session_detail", pk=self.session.pk)


class MyEmergencySessionsView(EmergencyAccessMixin, ListView):
    model = EmergencySessionParticipant
    template_name = "emergency/my_sessions.html"
    context_object_name = "participants"
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = EmergencySessionParticipant.objects.filter(
            employee=self.request.user
        ).select_related(
            "session",
            "session__topic",
            "session__plant",
            "session__location",
            "submission",
        )
        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-session__scheduled_date", "-session__scheduled_time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "").strip()
        context["status_choices"] = EmergencySessionParticipant.STATUS_CHOICES
        context["stats"] = {
            "all": EmergencySessionParticipant.objects.filter(employee=self.request.user).count(),
            "assigned": EmergencySessionParticipant.objects.filter(employee=self.request.user, status="ASSIGNED").count(),
            "in_progress": EmergencySessionParticipant.objects.filter(employee=self.request.user, status="IN_PROGRESS").count(),
            "completed": EmergencySessionParticipant.objects.filter(employee=self.request.user, status="COMPLETED").count(),
            "approved": EmergencySessionParticipant.objects.filter(employee=self.request.user, status="APPROVED").count(),
            "rejected": EmergencySessionParticipant.objects.filter(employee=self.request.user, status="REJECTED").count(),
        }
        return context


class EmergencySessionStartView(EmergencyAccessMixin, View):
    template_name = "emergency/session_start.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        self.participant = get_object_or_404(
            EmergencySessionParticipant.objects.select_related(
                "session",
                "session__topic",
                "session__plant",
                "session__location",
                "employee",
            ),
            pk=kwargs["participant_id"],
            employee=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.participant.has_submission and self.participant.status in ["COMPLETED", "APPROVED"]:
            return redirect("emergency:submission_review", submission_id=self.participant.submission.id)

        assigned_question_count = self.sync_participant_question_assignments(self.participant)
        if not assigned_question_count and self.participant.employee.department_id:
            messages.warning(
                request,
                f"No active department questions are available for {self.participant.employee.department.name}.",
            )

        if self.participant.status == "ASSIGNED":
            self.participant.status = "IN_PROGRESS"
            self.participant.started_at = timezone.now()
            self.participant.save(update_fields=["status", "started_at"])
            if self.participant.session.status == "SCHEDULED":
                self.participant.session.status = "ONGOING"
                self.participant.session.save(update_fields=["status", "updated_at"])

        assignments = self.participant.question_assignments.select_related(
            "question",
            "question__department",
        )
        existing_submission = getattr(self.participant, "submission", None)
        existing_responses = {}
        if existing_submission:
            existing_responses = {
                response.assignment_id: response
                for response in existing_submission.responses.select_related("question", "question__department")
            }

        questions_by_department = defaultdict(list)
        for assignment in assignments:
            questions_by_department[assignment.question.department].append(assignment)

        context = {
            "participant": self.participant,
            "session": self.participant.session,
            "questions_by_department": dict(questions_by_department),
            "total_questions": assignments.count(),
            "existing_responses": existing_responses,
        }
        return render(request, self.template_name, context)


class EmergencySessionSubmitView(EmergencyAccessMixin, View):
    def post(self, request, participant_id):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        participant = get_object_or_404(
            EmergencySessionParticipant.objects.select_related("session", "employee"),
            pk=participant_id,
            employee=request.user,
        )
        if participant.has_submission and participant.status in ["COMPLETED", "APPROVED"]:
            messages.info(request, "This submission is already completed and is available in read-only mode.")
            return redirect("emergency:submission_review", submission_id=participant.submission.id)

        assignments = participant.question_assignments.select_related("question")
        if not assignments.exists():
            self.sync_participant_question_assignments(participant)
            assignments = participant.question_assignments.select_related("question")
        if not assignments.exists():
            messages.error(request, "No questions are assigned for this session.")
            return redirect("emergency:my_sessions")

        with transaction.atomic():
            submission, _ = EmergencySessionSubmission.objects.get_or_create(
                participant=participant,
                defaults={
                    "submitted_by": request.user,
                    "overall_remarks": "",
                },
            )
            if submission.submitted_by_id != request.user.id:
                submission.submitted_by = request.user
            submission.overall_remarks = ""
            existing_responses = {response.assignment_id: response for response in submission.responses.all()}

            missing_answers = []
            for assignment in assignments:
                question = assignment.question
                answer = request.POST.get(f"question_{assignment.id}", "").strip()
                remarks = request.POST.get(f"remarks_{assignment.id}", "").strip()
                photo = request.FILES.get(f"photo_{assignment.id}")
                existing_response = existing_responses.get(assignment.id)
                has_existing_photo = bool(existing_response and existing_response.photo)

                if not answer:
                    missing_answers.append(question.question_code)
                    continue

                if question.is_remarks_mandatory and not remarks:
                    missing_answers.append(f"{question.question_code} remarks")
                    continue

                if question.is_photo_required and not photo and not has_existing_photo:
                    missing_answers.append(f"{question.question_code} photo")
                    continue

                response_defaults = {
                    "question": question,
                    "answer": answer,
                    "remarks": remarks,
                }
                if photo:
                    response_defaults["photo"] = photo
                elif existing_response and existing_response.photo:
                    response_defaults["photo"] = existing_response.photo

                EmergencySessionResponse.objects.update_or_create(
                    submission=submission,
                    assignment=assignment,
                    defaults=response_defaults,
                )

            if missing_answers:
                transaction.set_rollback(True)
                messages.error(request, f"Please complete all required fields: {', '.join(missing_answers[:5])}")
                return redirect("emergency:session_start", participant_id=participant.id)

            stale_assignment_ids = set(existing_responses.keys()) - set(assignments.values_list("id", flat=True))
            if stale_assignment_ids:
                submission.responses.filter(assignment_id__in=stale_assignment_ids).delete()

            submission.compliance_score = submission.calculate_compliance_score()
            submission.review_status = "PENDING"
            submission.reviewed_by = None
            submission.reviewed_at = None
            submission.reviewer_remarks = ""
            submission.save()

            participant.status = "COMPLETED"
            participant.completed_at = timezone.now()
            participant.save(update_fields=["status", "completed_at"])

            if participant.session.participants.exclude(status__in=["COMPLETED", "APPROVED"]).exists():
                participant.session.status = "ONGOING"
            else:
                participant.session.status = "COMPLETED"
            participant.session.save(update_fields=["status", "updated_at"])

        messages.success(request, "Your session answers were submitted successfully.")
        return redirect("emergency:my_sessions")


class EmergencySubmissionReviewView(EmergencyAccessMixin, View):
    template_name = "emergency/session_review.html"

    def dispatch(self, request, submission_id, *args, **kwargs):
        if not self.can_access_emergency_drill_module():
            messages.error(request, "You don't have permission to access the emergency drill module.")
            return redirect("dashboards:home")
        self.submission = get_object_or_404(
            EmergencySessionSubmission.objects.select_related(
                "participant",
                "participant__session",
                "participant__employee",
                "submitted_by",
            ).prefetch_related(
                "responses__question",
                "responses__question__department",
            ),
            pk=submission_id,
        )
        can_view = (
            request.user == self.submission.submitted_by
            or self.can_review_sessions()
            or request.user.is_superuser
        )
        if not can_view:
            messages.error(request, "You are not authorized to view this submission.")
            return redirect("emergency:my_sessions")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self):
        responses_by_department = defaultdict(list)
        for response in self.submission.responses.select_related("question", "question__department"):
            responses_by_department[response.question.department].append(response)
        return {
            "submission": self.submission,
            "participant": self.submission.participant,
            "session": self.submission.participant.session,
            "responses_by_department": dict(responses_by_department),
            "can_review": self.can_review_sessions(),
            "is_owner": self.request.user == self.submission.submitted_by,
            "show_review_actions": self.can_review_sessions() and self.submission.review_status == "PENDING",
            'cancel_url' : (self.request.GET.get('next') or self.request.META.get('HTTP_REFERER') or '/')
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        if not self.can_review_sessions():
            messages.error(request, "You don't have permission to review this submission.")
            return redirect("emergency:submission_review", submission_id=self.submission.id)

        action = request.POST.get("action")
        remarks = request.POST.get("reviewer_remarks", "").strip()
        if action not in ["approve", "reject"]:
            messages.error(request, "Invalid review action.")
            return redirect("emergency:submission_review", submission_id=self.submission.id)

        self.submission.review_status = "APPROVED" if action == "approve" else "REJECTED"
        self.submission.reviewer_remarks = remarks
        self.submission.reviewed_by = request.user
        self.submission.reviewed_at = timezone.now()
        self.submission.save(update_fields=["review_status", "reviewer_remarks", "reviewed_by", "reviewed_at"])

        participant = self.submission.participant
        participant.status = "APPROVED" if action == "approve" else "REJECTED"
        participant.reviewed_by = request.user
        participant.reviewed_at = timezone.now()
        participant.save(update_fields=["status", "reviewed_by", "reviewed_at"])

        messages.success(request, f"Submission {self.submission.review_status.lower()} successfully.")
        return redirect("emergency:submission_review", submission_id=self.submission.id)
