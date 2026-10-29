from django.urls import path, include
from . import views

app_name = 'kaizen'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),


    #configurations
    path('category/', views.KaizenCategoryListView.as_view(), name='category_list'),
    path('category/create', views.KaizenCategoryCreateView.as_view(), name='category_create'),
    path('category/<int:pk>/update', views.KaizenCategoryUpdateView.as_view(), name='category_update'),
    path('category/<int:pk>/delete', views.KaizenCategoryDeleteView.as_view(), name='category_delete'),
]