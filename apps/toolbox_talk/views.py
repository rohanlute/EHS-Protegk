from urllib import request

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from datetime import timedelta
from django.utils import timezone

import os
from django.conf import settings

from django.core.files.storage import (FileSystemStorage)

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from django.contrib.auth.decorators import login_required
 

from django.http import JsonResponse
from django.db import transaction

from .forms import (
    ToolboxTalkCategoryForm, 
    ToolboxTalkTopicForm,
    ToolboxTalkSessionPlanForm,
    #ToolboxTalkActionItemForm,
    
)

from .models import (
    
    ToolboxTalkCategory,
    ToolboxTalkTopic,
    ToolboxTalkTopicDetail, 
    ToolboxTalkSessionPlan,
    ToolboxSessionAssignment,
    ToolboxTalkConduct,
    ToolboxTalkConductDetail,
    ToolboxTalkAttendance,
    ToolboxTalkAttendanceDetail,
    ToolboxTalkEvidence,
    #ToolboxTalkActionItem,
)

from apps.organizations.models import (
    Zone,
    Location,
    SubLocation,
    Department,
    Plant
)

from apps.accounts.models import User


def toolbox_category_create(request):

    """
    Create Toolbox Talk Category

    Developed by Rajan
    """

    # FORM SUBMIT
    if request.method == 'POST':

        form = ToolboxTalkCategoryForm(
            request.POST
        )

        # VALIDATION
        if form.is_valid():

            category = form.save(commit=False)

            category.created_by = request.user

            category.save()

            messages.success(
                request,
                'Category created successfully.'
            )

            return redirect(
                'toolbox_talk:toolbox_category_list'
            )

    # PAGE LOAD
    else:

        form = ToolboxTalkCategoryForm()

    context = {
        'form': form
    }

    return render(
        request,
        'toolbox_talk/create_category.html',
        context
    )


def toolbox_category_list(request):

    """
    Toolbox Talk Category List

    Developed by Rajan
    """

    categories = ToolboxTalkCategory.objects.all().order_by('-id')

    # SEARCH
    search = request.GET.get('search')

    if search:

        categories = categories.filter(
            Q(category_name__icontains=search) |
            Q(short_code__icontains=search)
        )

    # STATUS FILTER
    status = request.GET.get('status')

    if status == 'active':

        categories = categories.filter(
            status=True
        )

    elif status == 'inactive':

        categories = categories.filter(
            status=False
        )

    # PAGINATION
    paginator = Paginator(categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'page_obj': page_obj,
        'search': search,
        'status': status
    }

    return render(
        request,
        'toolbox_talk/category_list.html',
        context
    )


def toolbox_category_update(request, pk):

    """
    Update Toolbox Talk Category

    Developed by Rajan
    """

    category = get_object_or_404(
        ToolboxTalkCategory,
        pk=pk
    )

    # FORM SUBMIT
    if request.method == 'POST':

        form = ToolboxTalkCategoryForm(
            request.POST,
            instance=category
        )

        # VALIDATION
        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Category updated successfully.'
            )

            return redirect(
                'toolbox_talk:toolbox_category_list'
            )

    # PAGE LOAD
    else:

        form = ToolboxTalkCategoryForm(
            instance=category
        )

    context = {
        'form': form,
        'category': category
    }

    return render(
        request,
        'toolbox_talk/update_category.html',
        context
    )


def toolbox_category_delete(request, pk):

    """
    Delete Toolbox Talk Category

    Developed by Rajan
    """

    category = get_object_or_404(
        ToolboxTalkCategory,
        pk=pk
    )

    # DELETE CONFIRM
    if request.method == 'POST':

        category.delete()

        messages.success(
            request,
            'Category deleted successfully.'
        )

        return redirect(
            'toolbox_talk:toolbox_category_list'
        )

    context = {
        'category': category
    }

    return render(
        request,
        'toolbox_talk/delete_category.html',
        context
    )
    


# Create Toolbox Talk Topic

@login_required
def toolbox_topic_create(request):

    if request.method == 'POST':

        form = ToolboxTalkTopicForm(
            request.POST
        )

        if form.is_valid():

            topic = form.save(
                commit=False
            )

            topic.created_by = request.user

            topic.save()

            safety_points = request.POST.getlist(
                'safety_point'
            )

            learning_objectives = request.POST.getlist(
                'learning_objective'
            )

            reference_documents = request.POST.getlist(
                'reference_document'
            )

            attachment_types = request.POST.getlist(
                'attachment_type'
            )

            attachment_urls = request.POST.getlist(
                'attachment_url'
            )

            attachment_files = request.FILES.getlist(
                'attachment_file'
            )

            file_index = 0

            for index in range(
                len(safety_points)
            ):

                detail = ToolboxTalkTopicDetail()

                detail.topic = topic

                detail.safety_point = (
                    safety_points[index]
                )

                detail.learning_objective = (
                    learning_objectives[index]
                )

                detail.reference_document = (
                    reference_documents[index]
                )

                detail.attachment_type = (
                    attachment_types[index]
                )

                if (
                    attachment_types[index]
                    == 'FILE'
                ):

                    if (
                        file_index
                        < len(attachment_files)
                    ):

                        detail.attachment_file = (
                            attachment_files[
                                file_index
                            ]
                        )

                        file_index += 1

                elif (
                    attachment_types[index]
                    == 'URL'
                ):

                    detail.attachment_url = (
                        attachment_urls[index]
                    )

                detail.display_order = (
                    index + 1
                )

                detail.save()

            messages.success(
                request,
                'Topic created successfully.'
            )

            return redirect(
                'toolbox_talk:topic_list'
            )

    else:

        form = ToolboxTalkTopicForm()

    context = {

        'form': form,

        'page_title':
        'Create Toolbox Talk Topic'
    }

    return render(
        request,
        'toolbox_talk/topic_create.html',
        context
    )






@login_required
def toolbox_topic_list(request):

    topics = (
        ToolboxTalkTopic.objects
        .select_related('category')
        .all()
        .order_by('-created_at')
    )

    search = request.GET.get(
        'search',
        ''
    )

    category = request.GET.get(
        'category',
        ''
    )

    status = request.GET.get(
        'status',
        ''
    )

    if search:

        topics = topics.filter(

            Q(topic_title__icontains=search)

            |

            Q(topic_code__icontains=search)

        )

    if category:

        topics = topics.filter(
            category_id=category
        )

    if status:

        if status == 'active':

            topics = topics.filter(
                is_active=True
            )

        elif status == 'inactive':

            topics = topics.filter(
                is_active=False
            )

    paginator = Paginator(
        topics,
        2
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    categories = (
        ToolboxTalkCategory.objects
        .filter(is_active=True)
        .order_by('category_name')
    )

    context = {

        'page_title':
        'Toolbox Talk Topics',

        'page_obj':
        page_obj,

        'categories':
        categories,

        'search':
        search,

        'selected_category':
        category,

        'selected_status':
        status

    }

    return render(

        request,

        'toolbox_talk/topic_list.html',

        context

    )


@login_required
def toolbox_topic_update(request, pk):
    topic = get_object_or_404(ToolboxTalkTopic, pk=pk)

    if request.method == 'POST':
        form = ToolboxTalkTopicForm(request.POST, instance=topic)

        if form.is_valid():

            topic = form.save()

            # Remove existing detail rows
            topic.details.all().delete()

            safety_points = request.POST.getlist('safety_point')
            learning_objectives = request.POST.getlist('learning_objective')
            reference_documents = request.POST.getlist('reference_document')
            attachment_types = request.POST.getlist('attachment_type')
            attachment_urls = request.POST.getlist('attachment_url')
            attachment_files = request.FILES.getlist('attachment_file')

            total_rows = max(
                len(safety_points),
                len(learning_objectives),
                len(reference_documents),
                len(attachment_types)
            )

            file_index = 0

            for index in range(total_rows):
                safety_point = safety_points[index].strip() if index < len(safety_points) else ''
                learning_objective = learning_objectives[index].strip() if index < len(learning_objectives) else ''
                reference_document = reference_documents[index].strip() if index < len(reference_documents) else ''
                attachment_type = attachment_types[index] if index < len(attachment_types) else ''

                if not any([safety_point, learning_objective, reference_document]):
                    continue

                # Create the detail object
                detail = ToolboxTalkTopicDetail()
                detail.topic = topic
                detail.safety_point = safety_point
                detail.learning_objective = learning_objective
                detail.reference_document = reference_document
                detail.attachment_type = attachment_type
                detail.display_order = index + 1

                if attachment_type == 'FILE':
                    if file_index < len(attachment_files):
                        detail.attachment_file = attachment_files[file_index]
                        file_index += 1
                elif attachment_type == 'URL':
                    if index < len(attachment_urls):
                        detail.attachment_url = attachment_urls[index].strip()

                detail.save()

            messages.success(request, 'Toolbox Talk Topic updated successfully.')
            return redirect('toolbox_talk:topic_list')

    else:
        form = ToolboxTalkTopicForm(instance=topic)

    topic_details = topic.details.all().order_by('display_order')

    context = {
        'form': form,
        'topic': topic,
        'topic_details': topic_details,
        'page_title': 'Update Toolbox Talk Topic'
    }

    return render(request, 'toolbox_talk/topic_update.html', context)
    
    
@login_required
def toolbox_topic_view(request, pk):

    topic = get_object_or_404(
        ToolboxTalkTopic.objects.select_related(
            'category'
        ),
        pk=pk
    )

    topic_details = (
        ToolboxTalkTopicDetail.objects
        .filter(topic=topic)
        .order_by('display_order')
    )
    print("topic_details",topic_details)
    context = {

        'page_title':
        'View Toolbox Talk Topic',

        'topic':
        topic,

        'topic_details':
        topic_details

    }
    print("context",context)

    return render(

        request,

        'toolbox_talk/topic_view.html',

        context

    )
    
    

@login_required
def toolbox_topic_delete_confirm(
    request,
    pk
):

    topic = get_object_or_404(

        ToolboxTalkTopic,

        pk=pk

    )

    if request.method == 'POST':

        try:

            topic.delete()

            messages.success(

                request,

                'Toolbox Talk Topic deleted successfully.'

            )

        except Exception:

            messages.error(

                request,

                'This topic is already linked with Toolbox Talk Sessions and cannot be deleted.'

            )

        return redirect(
            'toolbox_talk:topic_list'
        )

    context = {

        'topic': topic,
        'session_count': 0

    }

    return render(

        request,

        'toolbox_talk/topic_delete.html',

        context

    )  
    
#Session planning create view

@login_required
def toolbox_session_create(request):

    if request.method == 'POST':
        print(request.POST)

        form = ToolboxTalkSessionPlanForm(
            request.POST,
            user=request.user
        )

        selected_plant_ids = request.POST.getlist(
            'selected_plants'
        )

        selected_zone_ids = request.POST.getlist(
            'selected_zones'
        )

        selected_location_ids = request.POST.getlist(
            'selected_locations'
        )

        selected_sublocation_ids = request.POST.getlist(
            'selected_sublocations'
        )

        selected_trainer_ids = request.POST.getlist(
            'selected_trainers'
        )

        selected_incharge_ids = request.POST.getlist(
            'selected_incharges'
        )
        print("TRAINERS:", selected_trainer_ids)
        print("INCHARGES:", selected_incharge_ids)

        if not selected_plant_ids:

            messages.error(
                request,
                'Please select at least one plant.'
            )

        elif not selected_trainer_ids:

            messages.error(
                request,
                'Please select at least one trainer.'
            )

        elif not selected_incharge_ids:

            messages.error(
                request,
                'Please select at least one incharge.'
            )
# backend validation so that trainer and incharge is not the same person 
        elif set(selected_trainer_ids).intersection(
            set(selected_incharge_ids)
        ):

            messages.error(
                request,
                'Same user cannot be Trainer and Incharge.'
            )
            print("FORM VALID:", form.is_valid())
            print("FORM ERRORS:", form.errors)    

        elif form.is_valid():

            try:

                with transaction.atomic():

                    session = form.save(
                        commit=False
                    )

                    session.created_by = (
                        request.user
                    )

                    session.status = (
                        'PLANNED'
                    )

                    session.save()

                    # -------------------------
                    # M2M Relationships
                    # -------------------------

                    session.plants.set(
                        selected_plant_ids
                    )

                    session.zones.set(
                        selected_zone_ids
                    )

                    session.locations.set(
                        selected_location_ids
                    )

                    session.sublocations.set(
                        selected_sublocation_ids
                    )

                    session.trainers.set(
                        selected_trainer_ids
                    )

                    session.incharges.set(
                        selected_incharge_ids
                    )

                    # -------------------------
                    # Assignment Records
                    # -------------------------

                    for trainer_id in selected_trainer_ids:

                        ToolboxSessionAssignment.objects.create(
                            session=session,
                            user_id=trainer_id,
                            role='TRAINER',
                            assigned_by=request.user
                        )

                    for incharge_id in selected_incharge_ids:

                        ToolboxSessionAssignment.objects.create(
                            session=session,
                            user_id=incharge_id,
                            role='INCHARGE',
                            assigned_by=request.user
                        )

                    messages.success(
                        request,
                        'Session created successfully.'
                    )

                    return redirect(
                        'toolbox_talk:session_list'
                    )

            except Exception as e:
                print("ERROR OCCURRED")
                print(str(e))
                import traceback
                traceback.print_exc()
                messages.error(
                    request,
                    f'Error creating session: {str(e)}')
                

        else:

            print(form.errors)

            messages.error(
                request,
                'Please correct the form errors.'
            )

    else:

        form = ToolboxTalkSessionPlanForm(
            user=request.user
        )

    context = {

        'form': form,

        'action': 'Create',

        'title': (
            'Create Toolbox Talk Session'
        )

    }

    return render(
        request,
        'toolbox_talk/session_form.html',
        context
    )



@login_required
def get_topics_by_category(request):

    category_id = request.GET.get(
        'category_id'
    )

    topics = (
        ToolboxTalkTopic.objects
        .filter(
            category_id=category_id
        )
        .values(
            'id',
            'topic_title'
        )
        .order_by(
            'topic_title'
        )
    )

    return JsonResponse(
        list(topics),
        safe=False
    )


# get trainer /Safety Manager based on plant 
@login_required
def get_trainers_by_plants(request):
    """
    AJAX:  Safety Managers for selected plants.
    Used in schedule create form checkbox section.
    """
    plant_ids = request.GET.get('plant_ids', '')
    print(plant_ids);

    if not plant_ids:
        return JsonResponse({'users': []})

    ids = [pid.strip() for pid in plant_ids.split(',') if pid.strip()]

    users = User.objects.filter(
        plant__id__in=ids,
        role__name__in=['SAFETY MANAGER'],
        is_active_employee=True,
        is_active=True
    ).select_related('plant', 'role', 'department').order_by('plant__name', 'first_name')

    users_data = []
    for u in users:
        users_data.append({
            'id': u.id,
            'full_name': u.get_full_name(),
            'role': u.role.name if u.role else '',
            'department': u.department.name if u.department else '',
            'plant_name': u.plant.name if u.plant else '',
            'plant_id': u.plant.id if u.plant else None,
        })

    return JsonResponse({'users': users_data})





@login_required
def get_incharges_by_plants(request):
    """
    AJAX: Get HODs  for selected plants.
    Used in schedule create form checkbox section.
    """
    plant_ids = request.GET.get('plant_ids', '')

    if not plant_ids:
        return JsonResponse({'users': []})

    ids = [pid.strip() for pid in plant_ids.split(',') if pid.strip()]

    users = User.objects.filter(
        plant__id__in=ids,
        role__name__in=['HOD'],
        is_active_employee=True,
        is_active=True
    ).select_related('plant', 'role', 'department').order_by('plant__name', 'first_name')

    users_data = []
    for u in users:
        users_data.append({
            'id': u.id,
            'full_name': u.get_full_name(),
            'role': u.role.name if u.role else '',
            'department': u.department.name if u.department else '',
            'plant_name': u.plant.name if u.plant else '',
            'plant_id': u.plant.id if u.plant else None,
        })

    return JsonResponse({'users': users_data})
    



#session list 
@login_required
def toolbox_session_list(request):
    """List all Toolbox Talk Sessions"""

    sessions = (
        ToolboxTalkSessionPlan.objects
        .select_related(
            'category',
            'topic',
            'department',
            'created_by'
        )
        .prefetch_related(
            'plants',
            'trainers',
            'incharges'
        )
    )

    # User-based filtering
    if request.user.is_superuser or request.user.is_admin_user:
        pass

    elif hasattr(request.user, 'get_all_plants'):
        user_plants = request.user.get_all_plants()

        sessions = sessions.filter(
            plants__in=user_plants
        ).distinct()

    else:
        sessions = sessions.none()

    # Filters
    status = request.GET.get('status')
    plant_id = request.GET.get('plant')
    trainer_id = request.GET.get('trainer')
    incharge_id = request.GET.get('incharge')
    search = request.GET.get('search')

    # Status Filter
    if status:
        sessions = sessions.filter(
            status=status
        )

    # Plant Filter
    if plant_id:
        sessions = sessions.filter(
            plants__id=plant_id
        )

    # Trainer Filter
    if trainer_id:
        sessions = sessions.filter(
            trainers__id=trainer_id
        )

    # Incharge Filter
    if incharge_id:
        sessions = sessions.filter(
            incharges__id=incharge_id
        )

    # Search Filter
    if search:
        sessions = sessions.filter(
            Q(session_no__icontains=search)
            |
            Q(topic__topic_title__icontains=search)
            |
            Q(category__category_name__icontains=search)
            |
            Q(trainers__first_name__icontains=search)
            |
            Q(trainers__last_name__icontains=search)
            |
            Q(incharges__first_name__icontains=search)
            |
            Q(incharges__last_name__icontains=search)
        )

    sessions = sessions.distinct().order_by(
        '-planned_date',
        '-created_at'
    )

    # Pagination
    paginator = Paginator(
        sessions,
        20
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    # Dropdown Data
    plants = Plant.objects.filter(
        is_active=True
    )

    trainers = User.objects.filter(
        is_active_employee=True
    ).order_by(
        'first_name',
        'last_name'
    )

    incharges = User.objects.filter(
        is_active=True
    ).order_by(
        'first_name',
        'last_name'
    )

    context = {
        'page_obj': page_obj,

        'status_choices':
            ToolboxTalkSessionPlan.STATUS_CHOICES,

        'plants': plants,

        'trainers': trainers,

        'incharges': incharges,

        'selected_status': status,

        'selected_plant': plant_id,

        'selected_trainer': trainer_id,

        'selected_incharge': incharge_id,

        'search': search,
    }

    return render(
        request,
        'toolbox_talk/session_list.html',
        context
    )




# toobox session detailed view page  toolbox_session_view
@login_required
def toolbox_session_view(request, pk):
    """View Session Details"""

    session = get_object_or_404(
        ToolboxTalkSessionPlan.objects
        .select_related(
            'category',
            'topic',
            'department',
            'created_by'
        )
        .prefetch_related(
            'plants',
            'zones',
            'locations',
            'sublocations',
            'trainers',
            'incharges'
        ),
        pk=pk
    )

    if not request.user.is_superuser and not request.user.is_admin_user:

        if (
            request.user not in session.trainers.all()
            and
            request.user not in session.incharges.all()
        ):
            messages.error(
                request,
                'You do not have permission to view this session!'
            )

            return redirect(
                'toolbox_talk:session_list'
            )

    context = {

        'session': session,

        'can_edit':
            session.status not in [
                'COMPLETED',
                'CANCELLED'
            ],

        'can_start':
            session.status == 'PLANNED'
            and
            request.user in session.trainers.all(),

        'can_cancel':
            session.status not in [
                'COMPLETED',
                'CANCELLED'
            ],
    }

    return render(
        request,
        'toolbox_talk/session_view.html',
        context
    )
    
    

#

@login_required
def toolbox_session_edit(request, pk):
    """Edit Toolbox Talk Session"""

    session = get_object_or_404(
        ToolboxTalkSessionPlan,
        pk=pk
    )

    if request.method == 'POST':

        form = ToolboxTalkSessionPlanForm(
            request.POST,
            instance=session
        )

        if form.is_valid():

            session = form.save(commit=False)

            session.save()

            # -------------------------
            # Plants
            # -------------------------

            selected_plants = request.POST.getlist(
                'selected_plants'
            )

            session.plants.set(
                Plant.objects.filter(
                    id__in=selected_plants
                )
            )

            # -------------------------
            # Zones
            # -------------------------

            selected_zones = request.POST.getlist(
                'selected_zones'
            )

            session.zones.set(
                Zone.objects.filter(
                    id__in=selected_zones
                )
            )

            # -------------------------
            # Locations
            # -------------------------

            selected_locations = request.POST.getlist(
                'selected_locations'
            )

            session.locations.set(
                Location.objects.filter(
                    id__in=selected_locations
                )
            )

            # -------------------------
            # Sublocations
            # -------------------------

            selected_sublocations = request.POST.getlist(
                'selected_sublocations'
            )

            session.sublocations.set(
                SubLocation.objects.filter(
                    id__in=selected_sublocations
                )
            )

            # -------------------------
            # Trainers
            # -------------------------

            selected_trainers = request.POST.getlist(
                'selected_trainers'
            )

            session.trainers.set(
                User.objects.filter(
                    id__in=selected_trainers
                )
            )

            # -------------------------
            # Incharges
            # -------------------------

            selected_incharges = request.POST.getlist(
                'selected_incharges'
            )

            session.incharges.set(
                User.objects.filter(
                    id__in=selected_incharges
                )
            )

            messages.success(
                request,
                'Session updated successfully.'
            )

            return redirect(
                'toolbox_talk:session_list'
            )

    else:

        form = ToolboxTalkSessionPlanForm(
            instance=session
        )

    context = {

        'form': form,

        'session': session,

        'title': 'Edit Toolbox Talk Session',

        'action': 'Update',

        'is_edit': True,
    }

    return render(
        request,
        'toolbox_talk/session_form.html',
        context
    )



@login_required
def toolbox_session_delete(request, pk):

    session = get_object_or_404(
        ToolboxTalkSessionPlan,
        pk=pk
    )

    if request.method == "POST":

        session.delete()

        messages.success(
            request,
            "Session deleted successfully."
        )

        return redirect(
            'toolbox_talk:session_list'
        )

    context = {
        'session': session
    }

    return render(
        request,
        'toolbox_talk/session_delete.html',
        context
    )  



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.core.paginator import Paginator
from datetime import timedelta

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

from .models import (
    ToolboxSessionAssignment,
    ToolboxTalkSessionPlan,
    ToolboxTalkTopicDetail,
    ToolboxTalkConduct,
    ToolboxTalkConductDetail,
    ToolboxTalkAttendance,
    ToolboxTalkAttendanceDetail,
    ToolboxTalkEvidence,
)
from apps.accounts.models import User


# ─────────────────────────────────────────────────────────────
# HELPER: Annotate assignment with action flags
# Uses only statuses that exist in ToolboxSessionAssignment.STATUS_CHOICES:
# PENDING, ACCEPTED, IN_PROGRESS, COMPLETED, REJECTED
# ─────────────────────────────────────────────────────────────

def _annotate_assignment(assignment):
    """
    Attach boolean action flags to an assignment so the
    template never needs role/status logic.

    Existing STATUS_CHOICES:
        PENDING, ACCEPTED, IN_PROGRESS, COMPLETED, REJECTED

    Existing ROLE_CHOICES:
        TRAINER, INCHARGE
    """
    role   = assignment.role
    status = assignment.status

    # Trainer actions
    assignment.can_accept  = (role == 'TRAINER' and status == 'PENDING')
    assignment.can_start   = (role == 'TRAINER' and status == 'ACCEPTED')
    assignment.can_conduct = (role == 'TRAINER' and status == 'IN_PROGRESS')

    # Incharge actions
    # Incharge can mark attendance as long as the session is not
    # COMPLETED or REJECTED — regardless of what the trainer has done.
    assignment.can_attendance = (
        role == 'INCHARGE'
        and status in ('PENDING', 'ACCEPTED', 'IN_PROGRESS')
    )

    # Both roles can always view and download
    assignment.can_download = True
    assignment.can_view     = True

    # Convenience flags for the template
    assignment.is_trainer  = (role == 'TRAINER')
    assignment.is_incharge = (role == 'INCHARGE')

    return assignment


# ─────────────────────────────────────────────────────────────
# HELPER: Check and complete session if both sides are done
# "Both sides done" means:
#   - A ToolboxTalkConduct record exists  (trainer submitted)
#   - A ToolboxTalkAttendance record exists (incharge submitted)
# Uses only ToolboxTalkSessionPlan.STATUS_CHOICES: PLANNED, COMPLETED, CANCELLED
# ─────────────────────────────────────────────────────────────

def _try_complete_session(session):
    """
    Mark the session COMPLETED only when both conduct and
    attendance have been recorded.
    Called from both conduct_session and attendance_session
    so it doesn't matter which side finishes first.
    """
    conduct_done    = ToolboxTalkConduct.objects.filter(session=session).exists()
    attendance_done = ToolboxTalkAttendance.objects.filter(session=session).exists()

    if conduct_done and attendance_done:
        session.status = 'COMPLETED'
        session.save()
        return True

    return False


# ─────────────────────────────────────────────────────────────
# MY SESSIONS  (generic – Trainer AND Incharge)
# ─────────────────────────────────────────────────────────────

@login_required
def my_sessions(request):
    """
    Single 'My Sessions' page for the logged-in user.
    Shows all assignments regardless of role.
    """

    assignments = (
        ToolboxSessionAssignment.objects
        .filter(user=request.user)
        .select_related(
            'session',
            'session__topic',
            'session__category',
            'session__department',
        )
        .order_by('-created_at')
    )

    # ── Filters ──────────────────────────────────────────────
    selected_status = request.GET.get('status', '')
    selected_role   = request.GET.get('role', '')

    if selected_status:
        assignments = assignments.filter(status=selected_status)

    if selected_role:
        assignments = assignments.filter(role=selected_role)

    # ── Annotate flags ───────────────────────────────────────
    for a in assignments:
        _annotate_assignment(a)

    # ── Pagination ───────────────────────────────────────────
    paginator = Paginator(assignments, 15)
    page_obj  = paginator.get_page(request.GET.get('page'))

    # ── Statistics (use all assignments, not filtered) ───────
    all_assignments = ToolboxSessionAssignment.objects.filter(user=request.user)

    stats = {
        'total':       all_assignments.count(),
        'assigned':    all_assignments.count(),  # Total assigned
        'pending':     all_assignments.filter(status='PENDING').count(),
        'accepted':    all_assignments.filter(status='ACCEPTED').count(),
        'in_progress': all_assignments.filter(status='IN_PROGRESS').count(),
        'completed':   all_assignments.filter(status='COMPLETED').count(),
        'rejected':    all_assignments.filter(status='REJECTED').count(),
    }

    context = {
        'page_obj':        page_obj,
        'stats':           stats,
        'selected_status': selected_status,
        'selected_role':   selected_role,
        'status_choices':  ToolboxSessionAssignment.STATUS_CHOICES,
        'role_choices':    ToolboxSessionAssignment.ROLE_CHOICES,
    }

    return render(request, 'toolbox_talk/my_sessions.html', context)


# ─────────────────────────────────────────────────────────────
# SESSION DETAIL  (generic – Trainer AND Incharge)
# ─────────────────────────────────────────────────────────────

@login_required
def session_detail(request, pk):
    """
    Single detail page for any assignment.
    Template uses annotated flags to show correct action buttons.
    """

    assignment = get_object_or_404(
        ToolboxSessionAssignment.objects.select_related(
            'session',
            'session__category',
            'session__topic',
            'session__department',
            'user',
        ),
        pk=pk,
        user=request.user,
    )

    _annotate_assignment(assignment)

    topic_details = (
        ToolboxTalkTopicDetail.objects
        .filter(topic=assignment.session.topic)
        .order_by('display_order')
    )

    context = {
        'assignment':    assignment,
        'session':       assignment.session,
        'topic_details': topic_details,
    }

    return render(request, 'toolbox_talk/session_detail.html', context)


# ─────────────────────────────────────────────────────────────
# ACCEPT SESSION
# ─────────────────────────────────────────────────────────────

@login_required
def accept_session(request, pk):
    """
    Trainer accepts a PENDING assignment.
    Status: PENDING → ACCEPTED
    """
    print("=" * 50)
    print("Logged in user :", request.user)
    print("User ID :", request.user.id)
    print("Assignment PK :", pk)
    print(
    ToolboxSessionAssignment.objects.filter(pk=pk).values(
        'id',
        'user_id',
        'role',
        'status',
        'session_id'
    )
    )

    assignment = get_object_or_404(
        ToolboxSessionAssignment,
        pk=pk,
        user=request.user,
        #role='',
    )

    if assignment.status != 'PENDING':
        messages.warning(request, 'This session has already been processed.')
        return redirect('toolbox_talk:session_detail', pk=assignment.pk)

    assignment.status      = 'ACCEPTED'
    assignment.accepted_at = timezone.now()
    assignment.save()

    messages.success(request, 'Session accepted successfully.')
    return redirect('toolbox_talk:session_detail', pk=assignment.pk)


# ─────────────────────────────────────────────────────────────
# START SESSION
# ─────────────────────────────────────────────────────────────

@login_required
def start_session(request, pk):
    """
    Trainer starts an ACCEPTED assignment.
    Status: ACCEPTED → IN_PROGRESS
    """

    assignment = get_object_or_404(
        ToolboxSessionAssignment,
        pk=pk,
        user=request.user,
        role='TRAINER',
    )

    if assignment.status != 'ACCEPTED':
        messages.error(request, 'Please accept the session before starting it.')
        return redirect('toolbox_talk:session_detail', pk=assignment.pk)

    assignment.status = 'IN_PROGRESS'
    assignment.save()

    messages.success(request, 'Session started. You can now conduct it.')
    return redirect('toolbox_talk:conduct_session', pk=assignment.pk)


# ─────────────────────────────────────────────────────────────
# CONDUCT SESSION
# ─────────────────────────────────────────────────────────────

@login_required
def conduct_session(request, pk):
    """
    Trainer fills remarks for each topic detail point.
    Editing is allowed from planned_date up to 7 days after.

    On submit:
      - Assignment status → COMPLETED
      - Session status    → COMPLETED only if attendance also exists
                           (handled by _try_complete_session)
    """

    assignment = get_object_or_404(
        ToolboxSessionAssignment,
        pk=pk,
        user=request.user,
        role='TRAINER',
    )

    session = assignment.session
    today = timezone.now().date()

    edit_end_date = session.planned_date + timedelta(days=7)
    can_edit = (session.planned_date <= today <= edit_end_date)
    is_before_session = (today < session.planned_date)
    is_expired = (today > edit_end_date)

    topic_details = (
        ToolboxTalkTopicDetail.objects
        .filter(topic=session.topic)
        .order_by('display_order')
    )

    # Fix: Use get_or_create but handle the unique constraint properly
    try:
        conduct = ToolboxTalkConduct.objects.get(session=session)
    except ToolboxTalkConduct.DoesNotExist:
        conduct = ToolboxTalkConduct.objects.create(
            session=session,
            assignment=assignment,
        )

    if request.method == 'POST':

        if not can_edit:
            messages.error(request, 'The editing window for this session has expired.')
            return redirect('toolbox_talk:session_detail', pk=assignment.pk)

        # Save overall remark
        conduct.overall_remark = request.POST.get('overall_remark', '')
        conduct.save()

        # Save per-point remarks
        for detail in topic_details:
            obj, _ = ToolboxTalkConductDetail.objects.get_or_create(
                conduct=conduct,
                topic_detail=detail,
            )
            obj.trainer_remark = request.POST.get(f'remark_{detail.id}', '')
            obj.save()

        # Mark trainer assignment as COMPLETED
        assignment.status = 'COMPLETED'
        assignment.completed_at = timezone.now()
        assignment.save()

        # Complete the session only if attendance is also done
        session_completed = _try_complete_session(session)

        if session_completed:
            messages.success(request, 'Session conducted and fully completed.')
        else:
            messages.success(
                request,
                'Session conducted successfully. '
                'Waiting for incharge to complete attendance.'
            )

        return redirect('toolbox_talk:my_sessions')

    existing_remarks = {
        x.topic_detail_id: x.trainer_remark
        for x in conduct.details.all()
    }

    context = {
        'assignment': assignment,
        'session': session,
        'topic_details': topic_details,
        'conduct': conduct,
        'existing_remarks': existing_remarks,
        'can_edit': can_edit,
        'is_before_session': is_before_session,
        'is_expired': is_expired,
        'edit_end_date': edit_end_date,
    }

    return render(request, 'toolbox_talk/trainer_conduct_session.html', context)


# ─────────────────────────────────────────────────────────────
# ATTENDANCE SESSION
# ─────────────────────────────────────────────────────────────

@login_required
def attendance_session(request, pk):
    """
    Incharge marks attendance and uploads evidence.

    On submit:
      - Incharge assignment status → COMPLETED
      - Session status             → COMPLETED only if conduct also exists
                                    (handled by _try_complete_session)
    """

    assignment = get_object_or_404(
        ToolboxSessionAssignment,
        pk=pk,
        user=request.user,
        role='INCHARGE',
    )

    session = assignment.session

    # Fix: Use get_or_create with proper handling for OneToOne
    try:
        attendance = ToolboxTalkAttendance.objects.get(session=session)
    except ToolboxTalkAttendance.DoesNotExist:
        attendance = ToolboxTalkAttendance.objects.create(
            session=session,
            created_by=request.user,
        )

    employees = (
        User.objects
        .filter(
            plant__in=session.plants.all(),
            is_active_employee=True,
        )
        .exclude(
            id__in=session.trainers.values_list('id', flat=True)
        )
    )

    if request.method == 'POST':

        # Save overall remark
        attendance.overall_remark = request.POST.get('overall_remark', '')
        attendance.save()

        # Save evidence files
        for file in request.FILES.getlist('evidence_files'):
            ToolboxTalkEvidence.objects.create(
                session=session,
                uploaded_by=request.user,
                evidence_type='DOCUMENT',
                file=file,
            )

        # Save attendance records
        for user_id in request.POST.getlist('attendees'):
            ToolboxTalkAttendanceDetail.objects.get_or_create(
                attendance=attendance,
                user_id=user_id,
                defaults={
                    'marked_by': request.user,
                    'present': True,
                },
            )

        # Mark incharge assignment as COMPLETED
        assignment.status = 'COMPLETED'
        assignment.completed_at = timezone.now()
        assignment.save()

        # Complete the session only if conduct is also done
        session_completed = _try_complete_session(session)

        if session_completed:
            messages.success(request, 'Attendance saved. Session is now fully completed.')
        else:
            messages.success(
                request,
                'Attendance saved successfully. '
                'Waiting for trainer to complete conduct.'
            )

        return redirect('toolbox_talk:my_sessions')

    existing_users = list(
        attendance.attendees.values_list('user_id', flat=True)
    )

    context = {
        'assignment': assignment,
        'session': session,
        'attendance': attendance,
        'employees': employees,
        'existing_users': existing_users,
    }

    return render(request, 'toolbox_talk/incharge_session_attendence.html', context)


# ─────────────────────────────────────────────────────────────
# DOWNLOAD SESSION PDF
# ─────────────────────────────────────────────────────────────

@login_required
def download_session_pdf(request, pk):
    """
    Download a professional PDF report for a session.

    Authorization:
      - User must have an assignment for this session, OR
      - User must be staff / superuser
    """

    session = get_object_or_404(ToolboxTalkSessionPlan, pk=pk)

    # ── Authorization ────────────────────────────────────────
    user_has_assignment = ToolboxSessionAssignment.objects.filter(
        session=session,
        user=request.user,
    ).exists()

    if not user_has_assignment and not request.user.is_staff:
        messages.error(request, 'You are not authorized to download this report.')
        return redirect('toolbox_talk:my_sessions')

    # ── Build PDF ────────────────────────────────────────────
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{session.session_no}.pdf"'
    )

    doc    = SimpleDocTemplate(
        response,
        rightMargin=inch * 0.75,
        leftMargin=inch * 0.75,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Title ────────────────────────────────────────────────
    story.append(Paragraph('Toolbox Talk Session Report', styles['Title']))
    story.append(Spacer(1, 12))

    # ── Session Info Table ───────────────────────────────────
    trainers  = ', '.join(t.get_full_name() for t in session.trainers.all())  or '-'
    incharges = ', '.join(i.get_full_name() for i in session.incharges.all()) or '-'
    plants    = ', '.join(p.name for p in session.plants.all())               or '-'

    info_data = [
        ['Session No',   session.session_no],
        ['Category',     session.category.category_name if session.category else '-'],
        ['Topic',        session.topic.topic_title if session.topic else '-'],
        ['Department',   str(session.department) if session.department else '-'],
        ['Planned Date', str(session.planned_date)],
        ['Planned Time', str(session.planned_time)],
        ['Plants',       plants],
        ['Trainer(s)',   trainers],
        ['Incharge(s)',  incharges],
        ['Status',       session.get_status_display()],
    ]

    info_table = Table(info_data, colWidths=[2 * inch, 4.5 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME',       (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 9),
        ('GRID',           (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('TOPPADDING',     (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 5),
    ]))

    story.append(info_table)
    story.append(Spacer(1, 16))

    # ── Topic Details ────────────────────────────────────────
    story.append(Paragraph('Topic Details', styles['Heading2']))
    story.append(Spacer(1, 6))

    for detail in session.topic.details.all().order_by('display_order'):
        story.append(Paragraph(
            f'<b>Safety Point:</b> {detail.safety_point}', styles['Normal']
        ))
        story.append(Paragraph(
            f'<b>Learning Objective:</b> {detail.learning_objective}', styles['Normal']
        ))
        if detail.reference_document:
            story.append(Paragraph(
                f'<b>Reference:</b> {detail.reference_document}', styles['Normal']
            ))
        story.append(Spacer(1, 8))

    # ── Trainer Conduct Remarks ──────────────────────────────
    # Uses related_name='conduct' (OneToOne on ToolboxTalkConduct)
    if hasattr(session, 'conduct'):
        story.append(Spacer(1, 8))
        story.append(Paragraph('Trainer Remarks', styles['Heading2']))
        story.append(Spacer(1, 4))

        conduct = session.conduct
        story.append(Paragraph(
            f'<b>Overall Remark:</b> {conduct.overall_remark or "-"}',
            styles['Normal']
        ))

        # Uses related_name='details' on ToolboxTalkConductDetail
        for cd in conduct.details.all():
            story.append(Paragraph(
                f'<b>{cd.topic_detail.safety_point}:</b> {cd.trainer_remark or "-"}',
                styles['Normal']
            ))

        story.append(Spacer(1, 8))

    # ── Attendance ───────────────────────────────────────────
    # Uses related_name='attendance' (OneToOne on ToolboxTalkAttendance)
    if hasattr(session, 'attendance'):
        story.append(Paragraph('Attendance', styles['Heading2']))
        story.append(Spacer(1, 4))

        # Uses related_name='attendees' on ToolboxTalkAttendanceDetail
        attendees = session.attendance.attendees.all()

        if attendees.exists():
            att_data = [['#', 'Name', 'Present']]
            for i, att in enumerate(attendees, 1):
                att_data.append([
                    str(i),
                    att.user.get_full_name(),
                    'Yes' if att.present else 'No',
                ])

            att_table = Table(att_data, colWidths=[0.5 * inch, 4 * inch, 2 * inch])
            att_table.setStyle(TableStyle([
                ('BACKGROUND',     (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
                ('TEXTCOLOR',      (0, 0), (-1, 0), colors.white),
                ('FONTNAME',       (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',       (0, 0), (-1, -1), 9),
                ('GRID',           (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
                ('TOPPADDING',     (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING',  (0, 0), (-1, -1), 4),
            ]))
            story.append(att_table)

        if session.attendance.overall_remark:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f'<b>Incharge Remark:</b> {session.attendance.overall_remark}',
                styles['Normal']
            ))

        story.append(Spacer(1, 8))

    # ── Evidence ─────────────────────────────────────────────
    # Uses related_name='evidences' on ToolboxTalkEvidence
    if session.evidences.exists():
        story.append(Paragraph('Evidence Files', styles['Heading2']))
        story.append(Spacer(1, 4))
        for ev in session.evidences.all():
            story.append(Paragraph(f'• {ev.file.name}', styles['Normal']))
        story.append(Spacer(1, 8))

    doc.build(story)
    return response

# Action Module 
'''
@login_required
def action_item_list(request, session_pk):

    session = get_object_or_404(
        ToolboxTalkSessionPlan,
        pk=session_pk
    )

    action_items = session.action_items.all()

    context = {

        'session': session,

        'action_items': action_items,

    }

    return render(

        request,

        'toolbox_talk/action_item_list.html',

        context

    )


#

@login_required
def action_item_create(request, session_pk):

    session = get_object_or_404(
        ToolboxTalkSessionPlan,
        pk=session_pk
    )

    if request.method == 'POST':

        form = ToolboxTalkActionItemForm(
            request.POST
        )

        if form.is_valid():

            action = form.save(
                commit=False
            )

            action.session = session

            action.created_by = request.user

            action.save()

            messages.success(
                request,
                'Action Item created successfully.'
            )

            return redirect(
                'toolbox_talk:action_item_list',
                session.pk
            )

    else:

        form = ToolboxTalkActionItemForm()

    context = {

        'form': form,

        'session': session,

        'action': 'Create'

    }

    return render(

        request,

        'toolbox_talk/action_item_form.html',

        context

    )

#
@login_required
def action_item_edit(request, pk):

    action_item = get_object_or_404(
        ToolboxTalkActionItem,
        pk=pk
    )

    if request.method == 'POST':

        form = ToolboxTalkActionItemForm(

            request.POST,

            instance=action_item

        )

        if form.is_valid():

            action = form.save(
                commit=False
            )

            if (

                action.status == 'COMPLETED'

                and

                not action.closed_at

            ):

                action.closed_by = request.user

                action.closed_at = timezone.now()

            action.save()

            messages.success(

                request,

                'Action Item updated.'

            )

            return redirect(

                'toolbox_talk:action_item_list',

                action.session.pk

            )

    else:

        form = ToolboxTalkActionItemForm(

            instance=action_item

        )

    context = {

        'form': form,

        'session': action_item.session,

        'action': 'Edit'

    }

    return render(

        request,

        'toolbox_talk/action_item_form.html',

        context

    )
    
    
#

@login_required
def action_item_delete(request, pk):

    action_item = get_object_or_404(

        ToolboxTalkActionItem,

        pk=pk

    )

    session_id = action_item.session.pk

    action_item.delete()

    messages.success(

        request,

        'Action Item deleted.'

    )

    return redirect(

        'toolbox_talk:action_item_list',

        session_id

    )
'''                   
    
    
#Report module 

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Count, Prefetch

@login_required
def toolbox_reports(request):

    # ---------------------------------------------------
    # Base Query
    # ---------------------------------------------------

    sessions = (
        ToolboxTalkSessionPlan.objects
        .select_related(
            'category',
            'topic',
            'department'
        )
        .prefetch_related(
            'plants',
            'trainers',
            'incharges',
            
        )
        .order_by('-planned_date')
    )

    # ---------------------------------------------------
    # Filters
    # ---------------------------------------------------

    category = request.GET.get('category')
    topic = request.GET.get('topic')
    department = request.GET.get('department')
    trainer = request.GET.get('trainer')
    status = request.GET.get('status')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    if category:
        sessions = sessions.filter(category_id=category)

    if topic:
        sessions = sessions.filter(topic_id=topic)

    if department:
        sessions = sessions.filter(department_id=department)

    if trainer:
        sessions = sessions.filter(trainers=trainer)

    if status:
        sessions = sessions.filter(status=status)

    if from_date:
        sessions = sessions.filter(planned_date__gte=from_date)

    if to_date:
        sessions = sessions.filter(planned_date__lte=to_date)

    # ---------------------------------------------------
    # Statistics (Before Pagination)
    # ---------------------------------------------------
    '''
    total_action_items = 0
    completed_action_items = 0

    for session in sessions:

        items = session.action_items.all()

        total_action_items += items.count()

        completed_action_items += items.filter(
            status='COMPLETED'
        ).count()
        
    ''' 
        

    stats = {

        'total_sessions': sessions.count(),

        'planned': sessions.filter(
            status='PLANNED'
        ).count(),

        'completed': sessions.filter(
            status='COMPLETED'
        ).count(),

        'cancelled': sessions.filter(
            status='CANCELLED'
        ).count(),

        #'total_action_items': total_action_items,

       # 'completed_actions': completed_action_items,

    }

    # ---------------------------------------------------
    # Pagination
    # ---------------------------------------------------

    paginator = Paginator(
        sessions,
        15
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    # ---------------------------------------------------
    # Context
    # ---------------------------------------------------

    context = {

        'page_obj': page_obj,

        'sessions': page_obj,

        'stats': stats,

        'categories': ToolboxTalkCategory.objects.filter(
            is_active=True
        ),

        'topics': ToolboxTalkTopic.objects.filter(
            is_active=True
        ),

        'departments': Department.objects.all(),

        'trainers': User.objects.filter(
            toolbox_trainer_sessions__isnull=False
        ).distinct(),

        'status_choices': ToolboxTalkSessionPlan.STATUS_CHOICES,

        'selected_category': category,

        'selected_topic': topic,

        'selected_department': department,

        'selected_trainer': trainer,

        'selected_status': status,

        'from_date': from_date,

        'to_date': to_date,

    }

    return render(
        request,
        'toolbox_talk/toolbox_reports.html',
        context
    )
    
    
    
# DASHBOARD
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count

@login_required
def toolbox_dashboard(request):

    # =====================================================
    # Session Query
    # =====================================================

    sessions = (
        ToolboxTalkSessionPlan.objects
        .select_related(
            'category',
            'topic',
            'department'
        )
        .prefetch_related(
            'plants',
            'trainers',
            'incharges'
        )
    )

    # =====================================================
    # Session Statistics
    # =====================================================

    total_sessions = sessions.count()

    planned_sessions = sessions.filter(
        status='PLANNED'
    ).count()

    completed_sessions = sessions.filter(
        status='COMPLETED'
    ).count()

    cancelled_sessions = sessions.filter(
        status='CANCELLED'
    ).count()

    # =====================================================
    # Action Item Statistics
    # =====================================================
    
    '''

    total_action_items = ToolboxTalkActionItem.objects.count()

    open_actions = ToolboxTalkActionItem.objects.filter(
        status='OPEN'
    ).count()

    in_progress_actions = ToolboxTalkActionItem.objects.filter(
        status='IN_PROGRESS'
    ).count()

    completed_actions = ToolboxTalkActionItem.objects.filter(
        status='COMPLETED'
    ).count()

    verified_actions = ToolboxTalkActionItem.objects.filter(
        status='VERIFIED'
    ).count()
    
    '''

    # =====================================================
    # Recent Sessions
    # =====================================================

    recent_sessions = (
        sessions
        .order_by('-created_at')[:10]
    )

    # =====================================================
    # Sessions By Category
    # =====================================================

    sessions_by_category = (
        ToolboxTalkCategory.objects
        .annotate(
            total=Count('session_plans')
        )
        .order_by('-total')
    )

    # =====================================================
    # Latest Action Items
    # =====================================================
    
    '''

    latest_action_items = (
        ToolboxTalkActionItem.objects
        .select_related(
            'assigned_to',
            'session'
        )
        .order_by('-created_at')[:10]
    )
    '''

    # =====================================================
    # Upcoming Sessions
    # =====================================================

    upcoming_sessions = (
        ToolboxTalkSessionPlan.objects
        .filter(
            status='PLANNED'
        )
        .select_related(
            'topic',
            'department'
        )
        .order_by(
            'planned_date',
            'planned_time'
        )[:5]
    )

    # =====================================================
    # Trainer Summary
    # =====================================================

    trainer_summary = (
        User.objects
        .filter(
            toolbox_trainer_sessions__isnull=False
        )
        .annotate(
            session_count=Count(
                'toolbox_trainer_sessions'
            )
        )
        .order_by('-session_count')
    )

    # =====================================================
    # CHART DATA
    # =====================================================

    category_labels = [
        c.category_name
        for c in sessions_by_category
    ]

    category_counts = [
        c.total
        for c in sessions_by_category
    ]
    '''

    action_labels = [
        'Open',
        'In Progress',
        'Completed',
        'Verified'
    ]
    

    action_counts = [
        open_actions,
        in_progress_actions,
        completed_actions,
        verified_actions
    ]
    '''

    months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec'
    ]

    monthly_counts = []

    for month in range(1, 13):

        monthly_counts.append(

            ToolboxTalkSessionPlan.objects.filter(
                planned_date__month=month
            ).count()

        )

    # =====================================================
    # Context
    # =====================================================

    context = {

        # KPI Cards

        'total_sessions': total_sessions,

        'planned_sessions': planned_sessions,

        'completed_sessions': completed_sessions,

        'cancelled_sessions': cancelled_sessions,

        #'total_action_items': total_action_items,

        #'open_actions': open_actions,

        #'in_progress_actions': in_progress_actions,

        #'completed_actions': completed_actions,

        #'verified_actions': verified_actions,

        # Tables

        'recent_sessions': recent_sessions,

        'sessions_by_category': sessions_by_category,

        #'latest_action_items': latest_action_items,

        'upcoming_sessions': upcoming_sessions,

        'trainer_summary': trainer_summary,

        # Charts

        'category_labels': category_labels,

        'category_counts': category_counts,

        #'action_labels': action_labels,

        #'action_counts': action_counts,

        'months': months,

        'monthly_counts': monthly_counts,

    }

    return render(
        request,
        'toolbox_talk/toolbox_dashboard.html',
        context
    )