from django import forms
from apps.contractor.models import Contractor
import re


class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = [
            # Section A – Basic Information
            'contractor_code', 'contractor_name', 'contractor_type',
            'registration_number', 'pan_number', 'gstin', 'establishment_year',
            
            # Section B – Contact Information
            'contact_person', 'designation', 'mobile', 'email',
            'alternate_mobile', 'address_line1', 'address_line2',
            'country', 'state', 'city', 'pincode',
            
            # Section C – Business Information
            'nature_of_business', 'work_category', 'service_description',
            'years_of_experience', 'number_of_workers',
            
            # Section D – EHS Information
            'ehs_officer_name', 'ehs_designation', 'ehs_mobile', 'ehs_email',
            
            # Status
            'is_active',
            # created_by is NOT included - it's auto-set in the view
        ]
        widgets = {
            'contractor_code': forms.TextInput(attrs={
                'readonly': 'readonly',
                'class': 'form-control',
                'id': 'id_contractor_code'
            }),
            'contractor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_contractor_name',
                'required': 'required'
            }),
            'contractor_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_contractor_type',
                'required': 'required'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_registration_number'
            }),
            'pan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_pan_number',
                'maxlength': '10'
            }),
            'gstin': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_gstin',
                'maxlength': '15'
            }),
            'establishment_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_establishment_year',
                'min': '1900',
                'max': '2100'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_contact_person',
                'required': 'required'
            }),
            'designation': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_designation',
                'required': 'required'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_mobile',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'id_email',
                'required': 'required'
            }),
            'alternate_mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_alternate_mobile'
            }),
            'address_line1': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_address_line1',
                'rows': '2',
                'required': 'required'
            }),
            'address_line2': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_address_line2',
                'rows': '2'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_country',
                'required': 'required'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_state',
                'required': 'required'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_city',
                'required': 'required'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_pincode',
                'required': 'required',
                'maxlength': '6',
                'pattern': '[0-9]{5,6}'
            }),
            'nature_of_business': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_nature_of_business',
                'required': 'required'
            }),
            'work_category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_work_category',
                'required': 'required'
            }),
            'service_description': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_service_description',
                'rows': '3',
                'required': 'required'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_years_of_experience',
                'min': '0'
            }),
            'number_of_workers': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_number_of_workers',
                'min': '0'
            }),
            'ehs_officer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_officer_name',
                'required': 'required'
            }),
            'ehs_designation': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_designation'
            }),
            'ehs_mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_mobile',
                'required': 'required'
            }),
            'ehs_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_email',
                'required': 'required'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'id': 'id_is_active'
            }),
        }
        labels = {
            'contractor_code': 'Contractor Code',
            'contractor_name': 'Contractor Name',
            'contractor_type': 'Contractor Type',
            'registration_number': 'Registration Number',
            'pan_number': 'PAN Number',
            'gstin': 'GSTIN',
            'establishment_year': 'Establishment Year',
            'contact_person': 'Contact Person',
            'designation': 'Designation',
            'mobile': 'Mobile Number',
            'email': 'Email Address',
            'alternate_mobile': 'Alternate Mobile',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2',
            'country': 'Country',
            'state': 'State',
            'city': 'City',
            'pincode': 'Pincode',
            'nature_of_business': 'Nature of Business',
            'work_category': 'Work Category',
            'service_description': 'Service Description',
            'years_of_experience': 'Years of Experience',
            'number_of_workers': 'Number of Workers',
            'ehs_officer_name': 'EHS/Safety Officer Name',
            'ehs_designation': 'Designation',
            'ehs_mobile': 'Mobile Number',
            'ehs_email': 'Email Address',
            'is_active': 'Active',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add "Select" as default option for dropdown fields
        self.fields['contractor_type'].empty_label = "-- Select Contractor Type --"
        self.fields['work_category'].empty_label = "-- Select Work Category --"
        
        # Set default values for add mode
        if not self.instance.pk:
            self.fields['is_active'].initial = True