from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department


def get_default_ehs():
    return {
        "ghs": [],
        "ppe": []
    }

class Chemical(models.Model):

    STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('expired', 'Expired'),
    ]

    UNIT_CHOICES = [
        ('mL', 'mL'),
        ('L', 'L'),
        ('g', 'g'),
        ('kg', 'kg'),
    ]

    # Chemical Identification
    chemical_name = models.CharField(max_length=255)
    trade_name = models.CharField(max_length=255, blank=True, null=True)
    cas_number = models.CharField(max_length=50, unique=True)
    un_number = models.CharField(max_length=50, blank=True, null=True)

    # Sourcing & Inventory
    supplier = models.CharField(max_length=255, blank=True, null=True)
    lot_number = models.CharField(max_length=100, blank=True, null=True)
    receipt_date = models.DateField()
    expiration_date = models.DateField()

    # Location 
    plant = models.ForeignKey(Plant, on_delete=models.SET_NULL, null=True, related_name='chemicals')
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, related_name='chemicals')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='chemicals')
    sublocation = models.ForeignKey(SubLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='chemicals')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='chemicals')

    # Storage & Custody
    quantity = models.FloatField()
    quantity_unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    storage_location = models.CharField(max_length=100)

    owner = models.CharField(max_length=255)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock')

    # EHS JSON (structured)
    ehs_compliance = models.JSONField(default=get_default_ehs, blank=True)

    # SDS
    sds_file = models.FileField(upload_to='chemical_sds/')

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # =========================================================
    # SDS INTEGRATION
    # =========================================================
    @property
    def active_sds(self):
        return self.sds_records.filter(status='ACTIVE',is_active=True).first()

    @property
    def has_active_sds(self):
        return self.active_sds is not None

    @property
    def active_sds_version(self):
        sds = self.active_sds

        if not sds:
            return None

        return sds.current_version

    def clean(self):
        errors = {}

        if self.zone and self.plant and self.zone.plant != self.plant:
            errors['zone'] = "Zone does not belong to selected Plant."

        if self.location and self.zone and self.location.zone != self.zone:
            errors['location'] = "Location does not belong to selected Zone."

        if self.sublocation and self.location and self.sublocation.location != self.location:
            errors['sublocation'] = "SubLocation does not belong to selected Location."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.chemical_name} ({self.cas_number})"


class ChemicalRequest(models.Model):

    APPROVAL_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    UNIT_CHOICES = [
        ('mL', 'mL'),
        ('L', 'L'),
        ('g', 'g'),
        ('kg', 'kg'),
    ]

    # Chemical Identification
    chemical_name = models.CharField(max_length=255)
    cas_number = models.CharField(max_length=50)
    chemical_formula = models.CharField(max_length=100, blank=True, null=True)
    purity_grade = models.CharField(max_length=100, blank=True, null=True)

    # Supplier
    supplier_name = models.CharField(max_length=255, blank=True, null=True)
    catalog_number = models.CharField(max_length=100, blank=True, null=True)

    # Quantity
    quantity = models.FloatField()
    quantity_unit = models.CharField(max_length=10, choices=UNIT_CHOICES)

    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES)

    # Location 
    plant = models.ForeignKey(Plant, on_delete=models.SET_NULL, null=True, related_name='chemical_requests')
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, related_name='chemical_requests')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='chemical_requests')
    sublocation = models.ForeignKey(SubLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='chemical_requests')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='chemical_requests')

    storage_location = models.CharField(max_length=100)

    # Request Info
    requester_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chemical_requests'
    )
    requester_name = models.CharField(max_length=255)

    justification = models.TextField()

    # Attachments
    attachment = models.FileField(upload_to='chemical_requests/', blank=True, null=True)

    # Approval
    status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default='pending')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_chemical_requests'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Link to inventory
    chemical = models.ForeignKey(
        Chemical,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requests'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}

        if self.zone and self.plant and self.zone.plant != self.plant:
            errors['zone'] = "Zone does not belong to selected Plant."

        if self.location and self.zone and self.location.zone != self.zone:
            errors['location'] = "Location does not belong to selected Zone."

        if self.sublocation and self.location and self.sublocation.location != self.location:
            errors['sublocation'] = "SubLocation does not belong to selected Location."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.requester_user and not self.requester_name:
            self.requester_name = (
                self.requester_user.get_full_name()
                or self.requester_user.username
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.chemical_name} - {self.status}"