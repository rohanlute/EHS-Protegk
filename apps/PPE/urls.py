from django.urls import path
from . import views

app_name = 'PPE'

urlpatterns = [
    path('categories/', views.category_list, name='category_list'),
    path('categories/create', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('master-list/', views.master_list, name='master_list'),
    path('master-create/', views.create_ppe, name='create_ppe'),
    path('ppe/<int:pk>/', views.ppe_detail, name='ppe_detail'),
    path('ppe/<int:pk>/delete', views.ppe_delete, name='ppe_delete'),
    path('ppe/<int:pk>/edit', views.master_edit, name='master_edit'),
    path('stock/create/', views.stock_create, name='stock_create'),
    path('stock/list/', views.stock_list, name='stock_list'),
    path('stock/edit/<int:pk>/', views.stock_edit, name='stock_edit'),
    path('stock/delete/<int:pk>/', views.stock_delete, name='stock_delete'),
    path('stock/<int:pk>/', views.stock_detail, name='stock_detail'),
    
    # PPE Issue Management
    path('IssueManagement/list/', views.IssueManagement_list, name='IssueManagement_list'),
    path('IssueManagement/create/', views.IssueManagement_create, name='IssueManagement_create'),
    path('IssueManagement/edit/<int:pk>/', views.edit_issue,name='edit_issue'),
    path('IssueManagement/<int:pk>/', views.issue_detail,name='issue_detail'),
    path('IssueManagement/delete/<int:pk>/', views.issue_delete,name='issue_delete'),
    path('Return/list/', views.return_list, name='return_list'),
    path('Return/create/', views.return_create, name='return_create'),
    path('get-issue-details/',views.get_issue_details,name='get_issue_details'),
    path('Return/delete/<int:pk>/', views.return_delete, name='return_delete'),
    path('Return/edit/<int:pk>/', views.return_edit, name='return_edit'),
    path('Return/<int:pk>/', views.return_detail, name='return_detail'),
    path('Schedule/create/', views.schedule_create, name='schedule_create'),
    path('get_departments/',views.get_departments,name='get_departments'),
    path('get_plant_users/',views.get_plant_users,name='get_plant_users'),
    path('get_ppe_plants/',views.get_ppe_plants,name='get_ppe_plants'),
    path('get_plant_users/',views.get_plant_users,name='get_plant_users'),
    path('get-departments/', views.get_departments,name='get_departments'),
    path('Schedule/List/', views.schedule_list,name='schedule_list'),
    path('Schedule/<int:pk>/',views.schedule_detail,name='schedule_detail'),
    path('Schedule/edit/<int:pk>/',views.schedule_edit,name='schedule_edit'),
    path('Schedule/delete/<int:pk>/',views.schedule_delete,name='schedule_delete'),
    path('myinspection/',views.my_ppe_inspections,name='my_ppe_inspections'),
    path('inspection/start/<int:schedule_id>/',views.start_inspection,name='start_inspection'),
    path('inspection/submit/<int:schedule_id>/',views.submit_ppe_inspection,name='submit_ppe_inspection'),
    path('inspection/<int:schedule_id>/',views.ppe_inspection_pdf_download,name='ppe_inspection_pdf_download'),
    path('dashboard/',views.dashboard,name='dashboard'),
    ]