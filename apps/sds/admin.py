from django.contrib import admin
from .models import SDS, SDSVersion, SDSReview, SDSAuditLog, SDSSection1, SDSSection2


@admin.register(SDS)
class SDSAdmin(admin.ModelAdmin):

    list_display = [
        'sds_number',
        'product_name',
        'manufacturer_name',
        'plant',
        'status',
        'issue_date',
        'revision_date',
        'next_review_date',
        'is_active',
        'created_by',
    ]

    list_filter = [
        'status',
        'sds_type',
        'is_active',
        'plant',
        'issue_date',
        'revision_date',
        'next_review_date',
    ]

    search_fields = [
        'sds_number',
        'product_name',
        'product_identifier',
        'manufacturer_name',
        'supplier_name',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
    ]

    list_per_page = 50

    fieldsets = (
        ('SDS Identification', {
            'fields': (
                'sds_number',
                'product_name',
                'product_identifier',
                'sds_type',
                'status',
                'is_active',
            )
        }),

        ('Manufacturer Information', {
            'fields': (
                'manufacturer_name',
                'manufacturer_address',
                'manufacturer_phone',
                'manufacturer_email',
            )
        }),

        ('Supplier Information', {
            'fields': (
                'supplier_name',
                'supplier_address',
                'supplier_phone',
                'supplier_email',
            ),
            'classes': ('collapse',)
        }),

        ('Location / Applicability', {
            'fields': (
                'plant',
                'zone',
                'location',
                'sublocation',
            )
        }),

        ('Document Information', {
            'fields': (
                'document',
                'document_name',
                'document_language',
            )
        }),

        ('Revision & Review Dates', {
            'fields': (
                'issue_date',
                'revision_date',
                'next_review_date',
            )
        }),

        ('Remarks', {
            'fields': (
                'remarks',
            )
        }),

        ('Audit Information', {
            'fields': (
                'created_by',
                'updated_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SDSVersion)
class SDSVersionAdmin(admin.ModelAdmin):

    list_display = [
        'sds',
        'version_number',
        'revision_number',
        'status',
        'issue_date',
        'revision_date',
        'effective_date',
        'uploaded_by',
    ]

    list_filter = [
        'status',
        'issue_date',
        'revision_date',
        'effective_date',
    ]

    search_fields = [
        'sds__sds_number',
        'sds__product_name',
        'revision_number',
        'version_title',
        'change_summary',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    list_per_page = 50

    fieldsets = (
        ('SDS Version', {
            'fields': (
                'sds',
                'version_number',
                'revision_number',
                'version_title',
                'status',
            )
        }),

        ('Document', {
            'fields': (
                'document',
            )
        }),

        ('Dates', {
            'fields': (
                'issue_date',
                'revision_date',
                'effective_date',
            )
        }),

        ('Revision Details', {
            'fields': (
                'change_summary',
            )
        }),

        ('Audit Information', {
            'fields': (
                'uploaded_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SDSReview)
class SDSReviewAdmin(admin.ModelAdmin):

    list_display = [
        'sds',
        'version',
        'review_type',
        'status',
        'reviewer',
        'submitted_at',
        'reviewed_at',
    ]

    list_filter = [
        'review_type',
        'status',
        'submitted_at',
        'reviewed_at',
    ]

    search_fields = [
        'sds__sds_number',
        'sds__product_name',
        'review_remarks',
        'rejection_reason',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    list_per_page = 50

    fieldsets = (
        ('Review Information', {
            'fields': (
                'sds',
                'version',
                'review_type',
                'status',
            )
        }),

        ('Review Assignment', {
            'fields': (
                'reviewer',
                'submitted_by',
            )
        }),

        ('Review Dates', {
            'fields': (
                'submitted_at',
                'reviewed_at',
            )
        }),

        ('Review Remarks', {
            'fields': (
                'review_remarks',
                'rejection_reason',
            )
        }),

        ('Audit Information', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )



# =============================================
# SDS Section 1 - Identification Admin
# =============================================
@admin.register(SDSSection1)
class SDSSection1Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'sds_version',
        'product_identifier',
        'manufacturer_name',
        'emergency_contact_name',
        'created_at',
    )
    search_fields = (
        'product_identifier',
        'manufacturer_name',
        'manufacturer_email',
        'emergency_contact_name',
        'emergency_contact_number',
    )
    list_filter = (
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (
            'SDS Version',
            {
                'fields': (
                    'sds_version',
                )
            }
        ),
        (
            'Product Identification',
            {
                'fields': (
                    'product_identifier',
                    'recommended_use',
                    'restrictions_on_use',
                )
            }
        ),
        (
            'Manufacturer / Supplier Information',
            {
                'fields': (
                    'manufacturer_name',
                    'manufacturer_address',
                    'manufacturer_phone',
                    'manufacturer_email',
                    'manufacturer_website',
                )
            }
        ),
        (
            'Emergency Contact',
            {
                'fields': (
                    'emergency_contact_name',
                    'emergency_contact_number',
                    'emergency_contact_email',
                    'emergency_contact_available',
                )
            }
        ),
        (
            'Additional Information',
            {
                'fields': (
                    'additional_information',
                )
            }
        ),
        (
            'Audit Information',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )



# =============================================
# SDS Section 2 - Hazard Identification Admin
# =============================================
@admin.register(SDSSection2)
class SDSSection2Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'sds_version',
        'signal_word',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'sds_version__sds__sds_number',
        'sds_version__sds__product_name',
        'hazard_classification',
        'signal_word',
        'hazard_statements',
        'precautionary_statements',
    )
    list_filter = (
        'signal_word',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (
            'SDS Version',
            {
                'fields': (
                    'sds_version',
                )
            }
        ),
        (
            'Hazard Classification',
            {
                'fields': (
                    'hazard_classification',
                    'signal_word',
                )
            }
        ),
        (
            'GHS Hazard Information',
            {
                'fields': (
                    'hazard_statements',
                    'precautionary_statements',
                    'ghs_pictograms',
                )
            }
        ),
        (
            'Other Hazards',
            {
                'fields': (
                    'other_hazards',
                    'additional_information',
                )
            }
        ),
        (
            'Audit Information',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )




# =========================================================
# SDS AUDIT LOG ADMIN
# =========================================================
@admin.register(SDSAuditLog)
class SDSAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'sds',
        'version',
        'action',
        'performed_by',
        'created_at',
    )

    list_filter = (
        'action',
        'created_at',
    )

    search_fields = (
        'sds__sds_number',
        'sds__product_name',
        'description',
        'performed_by__username',
        'performed_by__first_name',
        'performed_by__last_name',
    )

    readonly_fields = (
        'sds',
        'version',
        'action',
        'description',
        'old_status',
        'new_status',
        'performed_by',
        'created_at',
    )

    ordering = (
        '-created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False