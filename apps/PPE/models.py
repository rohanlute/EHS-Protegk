from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from apps.accounts.models import User
from apps.organizations.models import Department
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
    size = models.CharField(max_length=50)
    available_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ("ppe_item", "size")
    def __str__(self):
        return f"{self.ppe_item.name} - {self.size}"
class PPEStockTransaction(models.Model):  
    TRANSACTION_CHOICES = (
        ('OPENING', 'Opening Stock'),
        ('STOCK_IN', 'Stock In'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('ISSUE', 'PPE Issue'),
        ('RETURN', 'PPE Return'),
        ('REPLACEMENT', 'PPE Replacement'),
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
            except:
                number = 1
        else:
            number = 1
        return f'PPE-ISS-{number:04d}'
    def __str__(self):
        return self.issue_no