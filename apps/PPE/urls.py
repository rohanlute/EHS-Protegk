from django.urls import path
from . import views
from .views import stock_create, stock_list, stock_edit, stock_delete
from .views import stock_create, stock_list, stock_edit, stock_delete

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
    path('stock/create/', stock_create, name='stock_create'),
    path('stock/list/', stock_list, name='stock_list'),
    path('stock/edit/<int:pk>/', stock_edit, name='stock_edit'),
    path('stock/delete/<int:pk>/', stock_delete, name='stock_delete'),
    path('stock/<int:pk>/', views.stock_detail, name='stock_detail'),
    
    # PPE Issue Management
    path('IssueManagement/list/', views.IssueManagement_list, name='IssueManagement_list'),
    path('IssueManagement/create/', views.IssueManagement_create, name='IssueManagement_create'),
    path('IssueManagement/edit/<int:pk>/', views.edit_issue,name='edit_issue'),
    path('IssueManagement/<int:pk>/', views.issue_detail,name='issue_detail'),
    path('IssueManagement/delete/<int:pk>/', views.issue_delete,name='issue_delete')
    
    
    
    ]