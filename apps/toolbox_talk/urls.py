from django.urls import path

from .views import (
    toolbox_category_create,
    toolbox_category_list,
    toolbox_category_update,
    toolbox_category_delete,
    toolbox_topic_create,
    toolbox_topic_delete_confirm,
    toolbox_topic_list,

    toolbox_topic_update,
    toolbox_topic_view,
    toolbox_session_create,
    toolbox_session_list,
    toolbox_session_view,
    toolbox_session_edit,
    toolbox_session_delete,
    
    get_topics_by_category,
    get_incharges_by_plants,
    get_trainers_by_plants,
    # get_departments_by_plants,
    
    #trainer_session_list,
    #trainer_session_detail,
    my_sessions,
    session_detail,
    conduct_session,
    attendance_session,
    download_session_pdf,
    
    # reports module
    toolbox_reports,
    
    # Dashboard
    toolbox_dashboard,
  
    
    #workflows of trainer 
    accept_session,
    start_session,
    
    
         
   
)

app_name = 'toolbox_talk'


urlpatterns = [

    # Toolbox Talk Category URLs
    path('categories/',toolbox_category_list,name='toolbox_category_list'),
    path('categories/create/',toolbox_category_create,name='toolbox_category_create'),
    path('categories/update/<int:pk>/',toolbox_category_update,name='toolbox_category_update'),
    path('categories/delete/<int:pk>/',toolbox_category_delete,name='toolbox_category_delete'),
    
    #Toolbox Talk Topic URLs
    path('topic/create/',toolbox_topic_create, name='topic_create'),
    path('topic/list/', toolbox_topic_list, name='topic_list'),
    path('topic/view/<int:pk>/', toolbox_topic_view, name='topic_view'),
    path('topic/update/<int:pk>/', toolbox_topic_update, name='topic_update'),
    
    path('topic/delete/confirm/<int:pk>/',toolbox_topic_delete_confirm,name='topic_delete'),
    
    # Toolbox Talk  Session URLs
    path('session/create/', toolbox_session_create, name='session_create'),
    path('session/list/', toolbox_session_list, name='session_list'),
    path('session/view/<int:pk>/', toolbox_session_view, name='session_view'),
    path('session/edit/<int:pk>/', toolbox_session_edit, name='session_edit'),
    path('session/delete/<int:pk>/', toolbox_session_delete, name='session_delete'),
    
    path('ajax/topics_by_category/', get_topics_by_category, name='topics_by_category'),
    #path('ajax/departments_by_plants/', get_departments_by_plants, name='departments_by_plants'),
    path('ajax/trainers/', get_trainers_by_plants, name='get_trainers'),
    path('ajax/incharges/', get_incharges_by_plants, name='get_incharges'),
    
    # Trainer Management URLs  
    #path('trainer/my_sessions/', trainer_session_list, name='trainer_session_list'),
    path('my_sessions/', my_sessions, name='my_sessions'),
    #path('trainer/view/<int:pk>/', trainer_session_detail, name='trainer_session_detail_view'),
    path('session/<int:pk>/',session_detail,name='session_detail'),
    
    #Trainer conducting session management URLS
    path('trainer/conduct/<int:pk>/', conduct_session, name='conduct_session'),
    
    #Incharge Attendence Management URLS
    path('incharge/attendance/<int:pk>/', attendance_session, name='attendance_session'),
    
    #session conduct management workflow URLS
    path('trainer/session/<int:pk>/accept/',accept_session, name='accept_session'),
    path('trainer/session/<int:pk>/start/',start_session, name='start_session'),
    
    #Toolbox Talk PDF Report /official audit document download 
    path('session/pdf/<int:pk>/', download_session_pdf, name='download_session_pdf'),
    
    
    # Action Item Management 
    # path('session/<int:session_pk>/actions/', action_item_list, name='action_item_list'),
    # path('session/<int:session_pk>/actions/create/', action_item_create, name='action_item_create'),
    # path('action/<int:pk>/edit/', action_item_edit, name='action_item_edit'),
    # path('action/<int:pk>/delete/', action_item_delete, name='action_item_delete'),



# Reports
path( 'reports/', toolbox_reports, name='toolbox_reports'),

# Dashboard
path('dashboard/', toolbox_dashboard, name='toolbox_dashboard'),
    
    
    

    
    
   
   

]

