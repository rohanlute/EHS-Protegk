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
    
    get_topics_by_category,
    get_incharges_by_plants,
    get_trainers_by_plants,
    # get_departments_by_plants,
         
   
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
    
    path('ajax/topics_by_category/', get_topics_by_category, name='topics_by_category'),
    #path('ajax/departments_by_plants/', get_departments_by_plants, name='departments_by_plants'),
    path('ajax/trainers/', get_trainers_by_plants, name='get_trainers'),
    path('ajax/incharges/', get_incharges_by_plants, name='get_incharges'),
    
    
   
   

]

