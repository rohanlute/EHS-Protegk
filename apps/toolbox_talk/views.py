from urllib import request

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

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
    ToolboxTalkSessionPlanForm
    
)

from .models import (
    
    ToolboxTalkCategory,
    ToolboxTalkTopic,
    ToolboxTalkTopicDetail, 
    ToolboxTalkSessionPlan 
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
def toolbox_topic_update(
    request,
    pk
):

    topic = get_object_or_404(
        ToolboxTalkTopic,
        pk=pk
    )

    if request.method == 'POST':

        form = ToolboxTalkTopicForm(
            request.POST,
            instance=topic
        )

        if form.is_valid():

            topic = form.save()

            # Remove existing detail rows
            topic.details.all().delete()

            safety_points = request.POST.getlist(
                'safety_point'
            )

            learning_objectives = request.POST.getlist(
                'learning_objective'
            )

            reference_documents = request.POST.getlist(
                'reference_document'
            )

            youtube_urls = request.POST.getlist(
                'youtube_url'
            )

            attachments = request.FILES.getlist(
                'attachment'
            )

            total_rows = max(
                len(safety_points),
                len(learning_objectives),
                len(reference_documents),
                len(youtube_urls)
            )

            file_index = 0

            for index in range(total_rows):

                safety_point = (
                    safety_points[index].strip()
                    if index < len(safety_points)
                    else ''
                )

                learning_objective = (
                    learning_objectives[index].strip()
                    if index < len(learning_objectives)
                    else ''
                )

                reference_document = (
                    reference_documents[index].strip()
                    if index < len(reference_documents)
                    else ''
                )

                youtube_url = (
                    youtube_urls[index].strip()
                    if index < len(youtube_urls)
                    else ''
                )

                if not any([
                    safety_point,
                    learning_objective,
                    reference_document,
                    youtube_url
                ]):
                    continue

                attachment = None

                if file_index < len(attachments):

                    attachment = attachments[
                        file_index
                    ]

                    file_index += 1

                ToolboxTalkTopicDetail.objects.create(

                    topic=topic,

                    safety_point=safety_point,

                    learning_objective=learning_objective,

                    reference_document=reference_document,

                    youtube_url=youtube_url,

                    attachment=attachment,

                    display_order=index + 1

                )

            messages.success(

                request,

                'Toolbox Talk Topic updated successfully.'

            )

            return redirect(
                'toolbox_talk:topic_list'
            )

    else:
        
        form = ToolboxTalkTopicForm(
            instance=topic
        )

    topic_details = (
        topic.details
        .all()
        .order_by(
            'display_order'
        )
    )

    context = {

        'form': form,

        'topic': topic,

        'topic_details': topic_details,

        'page_title':
        'Update Toolbox Talk Topic'

    }

    return render(

        request,

        'toolbox_talk/topic_update.html',

        context

    )
    
    
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

        elif set(selected_trainer_ids).intersection(
            set(selected_incharge_ids)
        ):

            messages.error(
                request,
                'Same user cannot be Trainer and Incharge.'
            )

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

                    # Many-to-Many fields
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

                    messages.success(
                        request,
                        'Session created successfully.'
                    )

                    return redirect(
                        'toolbox_talk:session_list'
                    )

            except Exception as e:

                messages.error(
                    request,
                    f'Error creating session: {str(e)}'
                )

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
    AJAX: Get HODs and Safety Managers for selected plants.
    Used in schedule create form checkbox section.
    """
    plant_ids = request.GET.get('plant_ids', '')
    print(plant_ids);

    if not plant_ids:
        return JsonResponse({'users': []})

    ids = [pid.strip() for pid in plant_ids.split(',') if pid.strip()]

    users = User.objects.filter(
        plant__id__in=ids,
        #role__name__in=['SAFETY MANAGER'],
        #is_active_employee=True,
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
    AJAX: Get HODs and Safety Managers for selected plants.
    Used in schedule create form checkbox section.
    """
    plant_ids = request.GET.get('plant_ids', '')

    if not plant_ids:
        return JsonResponse({'users': []})

    ids = [pid.strip() for pid in plant_ids.split(',') if pid.strip()]

    users = User.objects.filter(
        plant__id__in=ids,
        #role__name__in=['HOD'],
        #is_active_employee=True,
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
    



