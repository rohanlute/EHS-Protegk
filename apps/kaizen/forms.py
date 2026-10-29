from django import forms
from django.core.exceptions import ValidationError
from .models import *
from datetime import date
from apps.organizations.models import *
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class KaizenCategoryForm(forms.ModelForm):
    class Meta:
        model = KaizenCategory
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Occupational Health & Ergonomics'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., OHE',
                'maxlength': '20'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})