from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from apps.accounts.models import User
from apps.organizations.models import Plant
from apps.organizations.models import Department
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.contrib.auth import get_user_model

User = get_user_model()

class PPECategory(models.Model):
    """Master PPE Categories"""
    category_name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Category Name"
    )

    category_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Category Code",
        help_text="Example: HEL, GLO, SHOE"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active Status"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ppe_categories"
        ordering = ['category_name']
        verbose_name = "PPE Category"
        verbose_name_plural = "PPE Categories"

    def __str__(self):
        return self.category_name


class PPEItem(models.Model):
    """Master PPE Items"""

    YES_NO_CHOICES = [
        ('YES', 'Yes'),
        ('NO', 'No'),
    ]

    ppe_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="PPE Code"
    )

    name = models.CharField(
        max_length=255,
        verbose_name="PPE Name"
    )

    category = models.ForeignKey(
        'PPECategory',
        on_delete=models.PROTECT,
        related_name='ppe_items',
        verbose_name="Category"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    manufacturer_brand = models.CharField(
        max_length=255,
        verbose_name="Manufacturer / Brand"
    )

    model_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Model Number"
    )

    manufacturing_date = models.DateField(
        verbose_name="Manufacturing Date"
    )

    expiry_date = models.DateField(
        verbose_name="Expiry Date"
    )

    expiry_days = models.PositiveIntegerField(
        default=0,
        editable=False,
        verbose_name="Expiry Days"
    )

    inspection_required = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        default='NO',
        verbose_name="Inspection Required"
    )

    replacement_required = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        default='NO',
        verbose_name="Replacement Required"
    )

    size_applicable = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        default='NO',
        verbose_name="Size Applicable"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active Status"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ppe_items"
        ordering = ['ppe_code']
        verbose_name = "PPE Item"
        verbose_name_plural = "PPE Items"

        indexes = [
            models.Index(fields=['ppe_code']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    def __str__(self):
        return f"{self.ppe_code} - {self.name}"
    def save(self, *args, **kwargs):
        # Auto-generate PPE code
        if not self.ppe_code:
            self.ppe_code = self.generate_ppe_code()
        # Calculate expiry days
        if self.manufacturing_date and self.expiry_date:
            self.expiry_days = (
                self.expiry_date - self.manufacturing_date
            ).days
        else:
            self.expiry_days = 0
        super().save(*args, **kwargs)
    @classmethod
    def generate_ppe_code(cls):
        last_item = cls.objects.order_by('-id').first()
        if last_item and last_item.ppe_code:
            try:
                last_number = int(last_item.ppe_code.replace('PPE', ''))
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
        return f"PPE{new_number:04d}"
class PPESizeQuantity(models.Model):
    ppe_item = models.ForeignKey(
        PPEItem,
        on_delete=models.CASCADE,
        related_name="sizes"
    )
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_plant'
    )
        
    size = models.CharField(max_length=50)
    available_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = (
            "plant",
            "ppe_item",
            "size",
        )
    def __str__(self):
        return f"{self.ppe_item.name} - {self.size}"
class PPEStockTransaction(models.Model):  
    TRANSACTION_CHOICES = (
        ('OPENING', 'Opening Stock'),
        ('STOCK_IN', 'Stock In'),
        ('ADJUSTMENT', 'Stock Adjustment')
    )
    UNIT_CHOICES = (
        ('NOS', 'Nos'),
        ('PAIR', 'Pair'),
    )
    ppe_item = models.ForeignKey(
        'PPEItem',
        on_delete=models.CASCADE,
        related_name='stock_transactions',
        verbose_name="PPE Item"
    )
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_transactions'
    )
    size = models.ForeignKey(
        'PPESizeQuantity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_sizes',
        verbose_name="Size"
    )
    size_quantities = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Size Quantities"
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_CHOICES,
        verbose_name="Transaction Type"
    )
    quantity = models.PositiveIntegerField(
        verbose_name="Quantity"
    )
    unit = models.CharField(
    max_length=10,
    choices=UNIT_CHOICES,
    null=True,
    verbose_name="Unit"
   )
    total = models.PositiveIntegerField(
        verbose_name="total"
    )
    transaction_date = models.DateField(
        verbose_name="Transaction Date"
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Reference Number",
        help_text="GRN, PO Number, Invoice Number, etc."
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        verbose_name="Remarks"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active Status"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_stock_created',
        verbose_name="Created By"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_stock_updated',
        verbose_name="Updated By"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    class Meta:
        db_table = "ppe_stock_transactions"
        ordering = ['-created_at']
        verbose_name = "PPE Stock Transaction"
        verbose_name_plural = "PPE Stock Transactions"
    def __str__(self):
        return f"{self.ppe_item} - {self.transaction_type}"
    @property
    def size_quantity_display(self):
        if self.size_quantities:
            return ", ".join(
                f"{size}={qty}" for size, qty in self.size_quantities.items()
            )
        if self.size:
            return f"{self.size.size}={self.quantity}"
        return "-"

class PPEIssueManagement(models.Model):

    ISSUE_TO_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('CONTRACTOR', 'Contractor'),
    )

    issue_no = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    issue_group_no = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    issue_date = models.DateField()

    plant = models.ForeignKey(
        'organizations.Plant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_issues'
    )
    plant_name = models.CharField(
    max_length=200,
    blank=True,
    null=True
    )

    ppe_item = models.ForeignKey(
        PPEItem,
        on_delete=models.PROTECT,
        related_name='ppe_issues'
    )

    available_quantity = models.PositiveIntegerField(
        default=0
    )

    issue_to = models.CharField(
        max_length=20,
        choices=ISSUE_TO_CHOICES
    )

    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_issue_employee'
    )

    contractor_name = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    contractor_department = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    size = models.ForeignKey(
        PPESizeQuantity,
        on_delete=models.PROTECT
    )

    quantity_issue = models.PositiveIntegerField()

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_issue_created'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'ppe_issue_management'
        ordering = ['-id']

    def save(self, *args, **kwargs):

        if not self.issue_no:
            self.issue_no = self.generate_issue_no()

        # Auto department from employee
        if self.employee:
            self.department = self.employee.department

        super().save(*args, **kwargs)

    @classmethod
    def generate_issue_no(cls):
        last = cls.objects.order_by('-id').first()

        if last:
            try:
                number = int(
                    last.issue_no.replace(
                        'PPE-ISS-',
                        ''
                    )
                ) + 1
            except Exception:
                number = 1
        else:
            number = 1

        return f'PPE-ISS-{number:04d}'

    def __str__(self):
        return self.issue_no

class PPEReturnManagement(models.Model):

    RETURN_TO_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('CONTRACTOR', 'Contractor'),
    )

    return_group_no = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        db_index=True
    )

    return_no = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    plant = models.ForeignKey(
        'organizations.Plant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_returns'
    )

    return_date = models.DateField()

    issue = models.ForeignKey(
        'PPEIssueManagement',
        on_delete=models.PROTECT,
        related_name='ppe_returns'
    )

    ppe_item = models.ForeignKey(
        'PPEItem',
        on_delete=models.PROTECT
    )

    available_qty = models.PositiveIntegerField(
        default=0
    )

    return_to = models.CharField(
        max_length=20,
        choices=RETURN_TO_CHOICES
    )

    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_return_employee'
    )

    contractor_name = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    contractor_department = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    size = models.ForeignKey(
        'PPESizeQuantity',
        on_delete=models.PROTECT
    )

    assigned_qty = models.PositiveIntegerField(
        default=0
    )

    return_qty = models.PositiveIntegerField()

    remarks = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_return_created'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_return_updated'
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'ppe_return_management'
        ordering = ['-id']

    def __str__(self):
        return self.return_no or f"Return-{self.pk}"

    # ------------------------------------------------
    # Return Number
    # ------------------------------------------------

    @staticmethod
    def generate_return_no():
        last = PPEReturnManagement.objects.order_by('-id').first()

        if last and last.return_no:
            try:
                num = int(last.return_no.replace('PPE-RET-', '')) + 1
            except ValueError:
                num = 1
        else:
            num = 1

        return f'PPE-RET-{num:03d}'

    # ------------------------------------------------
    # Return Group Number
    # ------------------------------------------------

    @staticmethod
    def generate_return_group_no():

        last = (
            PPEReturnManagement.objects
            .exclude(return_group_no__isnull=True)
            .exclude(return_group_no='')
            .order_by('-id')
            .first()
        )

        if last and last.return_group_no:

            try:
                num = int(
                    last.return_group_no.split('-')[-1]
                ) + 1

            except (
                ValueError,
                IndexError
            ):
                num = 1

        else:
            num = 1

        return f'PPE-RET-{num:04d}'

    # ------------------------------------------------
    # Validation
    # ------------------------------------------------

    def clean(self):

        if not self.issue:
            return

        if self.return_to != self.issue.issue_to:

            raise ValidationError({
                'return_to':
                'Return To must match Issue To.'
            })

        returned_qty = (
            PPEReturnManagement.objects
            .filter(issue=self.issue)
            .exclude(pk=self.pk)
            .aggregate(
                total=Sum('return_qty')
            )['total'] or 0
        )

        balance_qty = (
            self.issue.quantity_issue -
            returned_qty
        )

        if self.return_qty > balance_qty:

            raise ValidationError({
                'return_qty':
                f'Only {balance_qty} quantity can be returned.'
            })

    # ------------------------------------------------
    # Save
    # ------------------------------------------------

    def save(self, *args, **kwargs):

        if not self.return_no:

            self.return_no = (
                self.generate_return_no()
            )

        if self.issue:

            self.plant = self.issue.plant

            self.ppe_item = (
                self.issue.ppe_item
            )

            self.return_to = (
                self.issue.issue_to
            )

            self.employee = (
                self.issue.employee
            )

            self.contractor_name = (
                self.issue.contractor_name
            )

            self.contractor_department = (
                self.issue.contractor_department
            )

            self.department = (
                self.issue.department
            )

            self.size = (
                self.issue.size
            )

            self.assigned_qty = (
                self.issue.quantity_issue
            )

            self.available_qty = (
                PPESizeQuantity.objects
                .filter(
                    ppe_item=self.issue.ppe_item,
                    plant=self.issue.plant
                )
                .aggregate(
                    total=Sum(
                        'available_quantity'
                    )
                )['total'] or 0
            )

        # self.full_clean()

        super().save(*args, **kwargs)

    # ------------------------------------------------
    # Total Returned
    # ------------------------------------------------

    @property
    def total_returned_qty(self):

        return (
            PPEReturnManagement.objects
            .filter(issue=self.issue)
            .aggregate(
                total=Sum('return_qty')
            )['total'] or 0
        )

    # ------------------------------------------------
    # Pending Qty
    # ------------------------------------------------

    @property
    def pending_qty(self):

        return (
            self.issue.quantity_issue -
            self.total_returned_qty
        )
class PPEInspectionSchedule(models.Model):

    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    inspection_no = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    # PPE returned item
    ppe_item = models.ForeignKey(
        PPEItem,
        on_delete=models.PROTECT,
        related_name='inspection_schedules'
    )

    # Return reference
    ppe_return = models.ForeignKey(
        PPEReturnManagement,
        on_delete=models.PROTECT,
        related_name='inspection_schedules'
    )

    plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name='ppe_inspection_schedules'
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ppe_inspections'
    )

    ASSIGNED_TO_CHOICES = (
        ('HOD', 'HOD'),
        ('SAFETY_MANAGER', 'Safety Manager'),
    )

    assigned_role = models.CharField(
        max_length=20,
        choices=ASSIGNED_TO_CHOICES
    )

    assigned_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='assigned_ppe_inspections'
    )

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_ppe_inspections'
    )

    scheduled_date = models.DateField()

    scheduled_end_date = models.DateField()

    assignment_notes = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'ppe_inspection_schedule'
        ordering = ['-id']

    def save(self, *args, **kwargs):

        if not self.inspection_no:
            self.inspection_no = self.generate_inspection_no()

        if (
            self.status not in ['COMPLETED', 'CANCELLED']
            and timezone.now().date() > self.scheduled_end_date
        ):
            self.status = 'OVERDUE'

        super().save(*args, **kwargs)

    @staticmethod
    def generate_inspection_no():

        last = (
            PPEInspectionSchedule.objects
            .order_by('-id')
            .first()
        )

        if last and last.inspection_no:
            try:
                num = int(
                    last.inspection_no.replace(
                        'PPE-ISS-',
                        ''
                    )
                ) + 1
            except ValueError:
                num = 1
        else:
            num = 1

        return f'PPE-ISS-{num:03d}'
class PPEInspection(models.Model):
    STATUS_CHOICES = (
        ('REUSABLE', 'Reusable'),
        ('REPAIR', 'Repair'),
        ('SCRAP', 'Scrap'),
    )

    schedule = models.ForeignKey(
        PPEInspectionSchedule,
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    remarks = models.TextField()

    photo = models.ImageField(
        upload_to='ppe_inspections/'
    )

    inspected_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
class PPEInspectionAssessment(models.Model):

    inspection = models.ForeignKey(
        PPEInspection,
        on_delete=models.CASCADE,
        related_name='assessments'
    )

    return_item = models.ForeignKey(
        PPEReturnManagement,
        on_delete=models.CASCADE
    )


    STATUS_CHOICES = (
        ('REUSABLE', 'Reusable'),
        ('REPAIR', 'Repair'),
        ('SCRAP', 'Scrap'),
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )
    remarks = models.TextField(
        blank=True,
        null=True
    )
    photo = models.ImageField(
    upload_to='ppe_inspections/',
    blank=True,
    null=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.inspection.id} - {self.return_item}"