from django import forms
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from .models import *
from django.db import models
from apps.organizations.models import Department
from django.db.models import Sum
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from .models import (
    PPECategory,
    PPEItem,
    PPEStockTransaction,
    PPEIssueManagement
)
class PPECategoryForm(forms.ModelForm):
    class Meta:
        model = PPECategory
        fields = [
            'category_name',
            'category_code',
            'description',
            'is_active'
        ]
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name (e.g., Head Protection,Eye Protection)'
            }),
            'category_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., HP,EP,FP',
                'maxlength': '12'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description of this category'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    def clean_categorycode(self):
        code = self.cleaned_data.get('category_code')
        if code:
            code = code.upper()
            existing = PPECategory.objects.filter(category_code=code)
            if self.instance.pk:
                existing= existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f'Category Code "{code}" already exist.')
        return code
class PPEItemForm(forms.ModelForm):
    class Meta:
        model = PPEItem
        fields = [
            'name',
            'category',
            'description',
            'manufacturer_brand',
            'model_number',
            'manufacturing_date',
            'expiry_date',
            'inspection_required',
            'replacement_required',
            'size_applicable',
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter PPE Name'
            }),

            'category': forms.Select(attrs={
                'class': 'form-control'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),

            'manufacturer_brand': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Manufacturer / Brand'
            }),

            'model_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Model Number'
            }),

            'manufacturing_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'inspection_required': forms.Select(attrs={
                'class': 'form-control'
            }),

            'replacement_required': forms.Select(attrs={
                'class': 'form-control'
            }),

            'size_applicable': forms.Select(attrs={
                'class': 'form-control'
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    # ---------------------------
    # VALIDATION LOGIC
    # ---------------------------

    def clean(self):
        cleaned_data = super().clean()

        mfg = cleaned_data.get('manufacturing_date')
        exp = cleaned_data.get('expiry_date')

        if mfg and exp:
            if exp <= mfg:
                raise ValidationError(
                    "Expiry date must be greater than Manufacturing date."
                )

        return cleaned_data
class PPEStockTransactionForm(forms.ModelForm):
     #stock transaction form
    class Meta:
        model = PPEStockTransaction

        fields = [
            'ppe_item',
            'transaction_type',   
            'unit',
            'transaction_date',
            'reference_number',
            'remarks',
            'is_active',
        ]

        widgets = {

            'ppe_item': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),

            'transaction_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),

            'unit': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'total': forms.Select(attrs={
                'class': 'form-control',
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),

            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),

            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'unit': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        ppe_item = cleaned_data.get('ppe_item')
        transaction_type = cleaned_data.get('transaction_type')
        size_ids = self.data.getlist('size_id[]') if self.data else []
        qtys = self.data.getlist('qty[]') if self.data else []
        if ppe_item:

            if not size_ids or not qtys:
                raise ValidationError("Size and Quantity are required.")

            has_valid_qty = False

            for qty in qtys:
                try:
                    if int(qty) > 0:
                        has_valid_qty = True
                        break
                except:
                    continue

            if not has_valid_qty:
                raise ValidationError("At least one size quantity must be greater than 0.")

            if transaction_type == 'OPENING':

                exists = PPEStockTransaction.objects.filter(
                    ppe_item=ppe_item,
                    transaction_type='OPENING'
                ).exists()

                if exists:
                    raise ValidationError(
                        "Opening stock already exists for this PPE Item."
                    )

        return cleaned_data
class PPEIssueManagementForm(forms.ModelForm):
    class Meta:
        model = PPEIssueManagement

        fields = [
            'issue_date',
            'ppe_item',
            'issue_to',
            'employee',
            'contractor_name',
            'contractor_department',
            'department',
            'size',
            'quantity_issue',
            'remarks',
        ]

        widgets = {

            'issue_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),

            'ppe_item': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'issue_to': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'employee': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'contractor_name': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'contractor_department': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'department': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'size': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'quantity_issue': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1
                }
            ),

            'remarks': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            )
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['employee'].required = False
        self.fields['contractor_name'].required = False
        self.fields['department'].required = False

        self.fields['employee'].queryset = User.objects.filter(
            is_active=True
        ).select_related(
            'department'
        )

        self.fields['department'].queryset = Department.objects.filter(
            is_active=True
        )

    def clean(self):

        cleaned_data = super().clean()

        issue_to = cleaned_data.get(
            'issue_to'
        )

        employee = cleaned_data.get(
            'employee'
        )

        contractor_name = cleaned_data.get(
            'contractor_name'
        )

        if issue_to == 'EMPLOYEE':

            if not employee:

                raise ValidationError(
                    "Employee is required."
                )

            cleaned_data['department'] = (
                employee.department
            )

        elif issue_to == 'CONTRACTOR':

            if not contractor_name:

                raise ValidationError(
                    "Contractor Name is required."
                )

        return cleaned_data