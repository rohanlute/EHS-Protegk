from django import forms

from .models import (
    ToolboxTalkCategory,
    ToolboxTalkTopic,
    ToolboxTalkSessionPlan,
    
)

from apps.organizations.models import (
    Plant,
    Zone,
    Location,
    SubLocation,
    Department
)

from apps.accounts.models import User



class ToolboxTalkCategoryForm(forms.ModelForm):

    class Meta:

        model = ToolboxTalkCategory

        fields = [
            'category_name',
            'short_code',
            'description',
            'is_active'
        ]

        widgets = {

            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),

            'short_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter short code'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })

        }
        
        


class ToolboxTalkTopicForm(forms.ModelForm):

    class Meta:

        model = ToolboxTalkTopic

        fields = [

            'topic_title',

            'category',

            'description',

            'is_active'

        ]

        widgets = {

            'topic_title': forms.TextInput(

                attrs={

                    'class': 'form-control',

                    'placeholder':
                    'Enter Topic Title'

                }

            ),

            'category': forms.Select(

                attrs={

                    'class': 'form-control'

                }

            ),

            'description': forms.Textarea(

                attrs={

                    'class': 'form-control',

                    'rows': 4,

                    'placeholder':
                    'Enter Topic Description'

                }

            ),

            'is_active': forms.CheckboxInput(

                attrs={

                    'class': 'form-check-input'

                }

            )

        }

    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.fields[
            'category'
        ].queryset = (
            ToolboxTalkCategory.objects
            .filter(
                is_active=True
            )
            .order_by(
                'category_name'
            )
        )

        self.fields[
            'category'
        ].empty_label = (
            '-- Select Category --'
        )

    def clean_topic_title(self):

        topic_title = (
            self.cleaned_data.get(
                'topic_title'
            )
        )

        queryset = (
            ToolboxTalkTopic.objects
            .filter(
                topic_title__iexact=
                topic_title
            )
        )

        if self.instance.pk:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise forms.ValidationError(

                'Topic Title already exists.'

            )

        return topic_title  
    
    
    
# Session Form




class ToolboxTalkSessionPlanForm(forms.ModelForm):

    class Meta:

        model = ToolboxTalkSessionPlan

        fields = [

            'category',

            'topic',

            'planned_date',

            'planned_time',
            
            'department',

            'expected_participants',

            'remarks',

        ]

        widgets = {

            'category': forms.Select(
                attrs={
                    'class': 'form-control',
                    'id': 'id_category'
                }
            ),

            'topic': forms.Select(
                attrs={
                    'class': 'form-control',
                    'id': 'id_topic'
                }
            ),
            
            

            'planned_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),

            'planned_time': forms.TimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'time'
                }
            ),
            
            'department': forms.Select(
                attrs={
                    'class': 'form-control',
                    'id': 'id_department'
                }
            ),

            'expected_participants': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'placeholder': 'Expected Participants'
                }
            ),

            'remarks': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Remarks'
                }
            ),

        }

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop(
            'user',
            None
        )

        super().__init__(
            *args,
            **kwargs
        )

        self.fields[
            'category'
        ].queryset = (
            ToolboxTalkCategory.objects.filter(
                is_active=True
            )
        )

        self.fields[
            'category'
        ].empty_label = (
            'Select Category'
        )

        # AJAX will populate this later
        self.fields[
            'topic'
        ].queryset = (
            ToolboxTalkTopic.objects.none()
        )

        self.fields[
            'topic'
        ].empty_label = (
            'Select Topic'
        )
        
        # simple drop-down for department no ajax based filtering population
        self.fields['department'].queryset = ( Department.objects.filter(is_active=True))

    def clean(self):

        cleaned_data = (
            super().clean()
        )

        category = cleaned_data.get(
            'category'
        )

        topic = cleaned_data.get(
            'topic'
        )

        if (
            category
            and topic
            and topic.category_id != category.id
        ):

            self.add_error(
                'topic',
                'Selected topic does not belong to selected category.'
            )

        return cleaned_data

