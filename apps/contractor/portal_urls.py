from django.urls import path
from apps.contractor import views

app_name = 'contractor_portal'

urlpatterns = [
    path('login/',views.ContractorPortalLoginView.as_view(),name='login'),
    path('',views.ContractorPortalHomeView.as_view(),name='home'),
    path('logout/',views.ContractorPortalLogoutView.as_view(),name='logout'),
]