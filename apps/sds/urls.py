from django.urls import path
from . import views

app_name = 'sds'

urlpatterns = [
    # =========================================================
    # DASHBOARD
    # =========================================================
    path('',views.SDSDashboardView.as_view(),name='dashboard'),
    path('dashboard/',views.SDSDashboardView.as_view(),name='sds_dashboard'),
    path('analytics/',views.SDSAnalyticalDashboardView.as_view(),name='sds_analytical_dashboard'),

    # =========================================================
    # SDS REGISTER
    # =========================================================
    path('list/',views.SDSListView.as_view(),name='sds_list'),
    path('create/',views.SDSCreateView.as_view(),name='sds_create'),
    path('<int:pk>/',views.SDSDetailView.as_view(),name='sds_detail'),
    path('<int:pk>/edit/',views.SDSUpdateView.as_view(),name='sds_update'),
    path('<int:pk>/delete/',views.SDSDeleteView.as_view(),name='sds_delete'),

    # =========================================================
    # SDS DOCUMENT
    # =========================================================
    path('<int:pk>/document/',views.SDSDocumentView.as_view(),name='sds_document'),

    # =========================================================
    # SDS STATUS / WORKFLOW
    # =========================================================
    path('<int:pk>/status/',views.SDSStatusUpdateView.as_view(),name='sds_status_update'),

    # =========================================================
    # SDS VERSION MANAGEMENT
    # =========================================================
    path('<int:sds_id>/versions/create/',views.SDSVersionCreateView.as_view(),name='version_create'),
    path('<int:sds_id>/versions/<int:version_id>/status/',views.SDSVersionStatusUpdateView.as_view(),name='version_status_update'),
    # =============================================
    # SDS Section 1 - Identification
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-1/',views.SDSSection1View.as_view(),name='section1'),
    # =============================================
    # SDS Section 2 - Hazard(s) Identification
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-2/',views.SDSSection2View.as_view(),name='section2'),
    # =============================================
    # SDS Section 3 - Composition / Information on Ingredients
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-3/',views.SDSSection3View.as_view(),name='section3'),
    # =========================================================
    # =============================================
    # SDS Section 4 - Form - First-Aid Measures
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-4/',views.SDSSection4View.as_view(),name='section4'),
    # =============================================
    # SDS Section 5 - Fire-Fighting Measures
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-5/',views.SDSSection5View.as_view(),name='section5'),
    # =============================================
    # SDS Section 6 - Accidental Release Measures
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-6/',views.SDSSection6View.as_view(),name='section6'),
    # =============================================
    # SDS Section 7 - Handling and Storage
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-7/',views.SDSSection7View.as_view(),name='section7'),
    # =============================================
    # SDS Section 8 - Exposure Controls / Personal Protection
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-8/',views.SDSSection8View.as_view(),name='section8'),
    # =============================================
    # SDS Section 9 - Physical and Chemical Properties
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-9/',views.SDSSection9View.as_view(),name='section9'),
    # =============================================
    # SDS Section 10 - Stability and Reactivity
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-10/',views.SDSSection10View.as_view(),name='section10'),
    # =============================================
    # SDS Section 11 - Toxicological Information
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-11/',views.SDSSection11View.as_view(),name='section11'),
    # =============================================
    # SDS Section 12 - Ecological Information
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-12/',views.SDSSection12View.as_view(),name='section12'),
    # =============================================
    # SDS Section 13 - Disposal Considerations
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-13/',views.SDSSection13View.as_view(),name='section13'),
    # =============================================
    # SDS Section 14 - Transport Information
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-14/',views.SDSSection14View.as_view(),name='section14'),
    # =============================================
    # SDS Section 15 - Regulatory Information
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-15/',views.SDSSection15View.as_view(),name='section15'),
    # =============================================
    # SDS Section 16 - Other Information
    # =============================================
    path('<int:sds_id>/versions/<int:version_id>/section-16/',views.SDSSection16View.as_view(),name='section16'),
    # =========================================================
    # SDS REVIEWS
    # =========================================================
    path('reviews/',views.SDSReviewListView.as_view(),name='review_list'),
    path('<int:sds_id>/versions/<int:version_id>/reviews/create/',views.SDSReviewCreateView.as_view(),name='review_create'),
]