from django.db import models
from django.core.exceptions import ValidationError
from apps.accounts.models import User

from apps.organizations.models import (
    Plant,
    Zone,
    Location,
    SubLocation,
    Department
)



class ToolboxTalkCategory(models.Model):
    """
    Toolbox Talk Category Master

    Developed by Rajan
    """

    category_name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Category Name'
    )

    short_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Short Code'
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Status'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_toolbox_categories'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'toolbox_talk_categories'

        ordering = ['category_name']

        verbose_name = 'Toolbox Talk Category'

        verbose_name_plural = 'Toolbox Talk Categories'

    def __str__(self):

        return f"{self.short_code} - {self.category_name}"
    
# Toolbox Talk Topic Master
class ToolboxTalkTopic(models.Model):

    topic_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Topic Code'
    )

    topic_title = models.CharField(
        max_length=300,
        unique=True,
        verbose_name='Topic Title'
    )

    category = models.ForeignKey(
        ToolboxTalkCategory,
        on_delete=models.PROTECT,
        related_name='topics'
    )

    description = models.TextField(
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
        related_name='created_toolbox_topics'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'toolbox_talk_topics'

        ordering = ['-created_at']

        verbose_name = 'Toolbox Talk Topic'

        verbose_name_plural = 'Toolbox Talk Topics'

    def __str__(self):

        return f"{self.topic_code} - {self.topic_title}"

    @staticmethod
    def generate_topic_code():

        last_topic = (
            ToolboxTalkTopic.objects
            .order_by('-id')
            .first()
        )

        if not last_topic:
            return "TTT0001"

        last_code = last_topic.topic_code

        number = int(
            last_code.replace(
                "TTT",
                ""
            )
        )

        new_number = number + 1

        return f"TTT{new_number:04d}"

    def save(self, *args, **kwargs):

        if not self.topic_code:

            self.topic_code = self.generate_topic_code()

        super().save(*args, **kwargs)
        
        
class ToolboxTalkTopicDetail(models.Model):

    topic = models.ForeignKey(
        ToolboxTalkTopic,
        on_delete=models.CASCADE,
        related_name='details'
    )

    safety_point = models.TextField()

    learning_objective = models.TextField()

    reference_document = models.CharField(
        max_length=500,
        blank=True
    )

    ATTACHMENT_TYPE_CHOICES = (
    ('FILE', 'File'),
    ('URL', 'URL'),
     )


    attachment_type = models.CharField(
    max_length=20,
    choices=ATTACHMENT_TYPE_CHOICES,
    blank=True,
    null=True)

    attachment_file = models.FileField(
    upload_to='toolbox_topics/',
    blank=True,
    null=True)

    attachment_url = models.URLField(
    blank=True,
    null=True)

    display_order = models.PositiveIntegerField(
        default=1)

    created_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:

        db_table = 'toolbox_talk_topic_details'

        ordering = ['display_order']

        verbose_name = 'Toolbox Talk Topic Detail'

        verbose_name_plural = 'Toolbox Talk Topic Details'

    def __str__(self):

        return (
            f"{self.topic.topic_code} - "
            f"{self.safety_point[:50]}"
        ) 
    
    def clean(self):

     if self.attachment_type == 'FILE' and not self.attachment_file:

        raise ValidationError(
            "Please upload a file."
        )

     if self.attachment_type == 'URL' and not self.attachment_url:

        raise ValidationError(
            "Please provide a URL."
        )  
        
# Session Model for Toolbox Talk

class ToolboxTalkSessionPlan(models.Model):

    STATUS_CHOICES = (
        ('PLANNED', 'Planned'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    session_no = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name='Session Number'
    )

    category = models.ForeignKey(
        ToolboxTalkCategory,
        on_delete=models.PROTECT,
        related_name='session_plans',
        verbose_name='Category'
    )

    topic = models.ForeignKey(
        ToolboxTalkTopic,
        on_delete=models.PROTECT,
        related_name='session_plans',
        verbose_name='Topic'
    )

    plants = models.ManyToManyField(
        Plant,
        blank=True,
        related_name='toolbox_session_plans'
    )

    zones = models.ManyToManyField(
        Zone,
        blank=True,
        related_name='toolbox_session_plans'
    )

    locations = models.ManyToManyField(
        Location,
        blank=True,
        related_name='toolbox_session_plans'
    )

    sublocations = models.ManyToManyField(
        SubLocation,
        blank=True,
        related_name='toolbox_session_plans'
    )

    department = models.ForeignKey(
    Department,
    on_delete=models.PROTECT,
    related_name='toolbox_session_plans',
    verbose_name='Department'
    )

    trainers = models.ManyToManyField(
    User,
    blank=True,
    related_name='toolbox_trainer_sessions',
    verbose_name='Trainers'
    )

    incharges = models.ManyToManyField(
    User,
    blank=True,
    related_name='toolbox_incharge_sessions',
    verbose_name='Incharges'
    )
  

    planned_date = models.DateField()

    planned_time = models.TimeField()

    expected_participants = models.PositiveIntegerField()

    remarks = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PLANNED'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_toolbox_sessions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'toolbox_talk_session_plans'

        ordering = [
            '-planned_date',
            '-planned_time'
        ]

        verbose_name = 'Toolbox Talk Session Plan'

        verbose_name_plural = (
            'Toolbox Talk Session Plans'
        )

    def __str__(self):

        return (
            f"{self.session_no} - "
            f"{self.topic.topic_title}"
        )

    @staticmethod
    def generate_session_no():

        last_session = (
            ToolboxTalkSessionPlan.objects
            .order_by('-id')
            .first()
        )

        if not last_session:
            return "SN-TTT-001"

        last_code = last_session.session_no

        number = int(
            last_code.split('-')[-1]
        )

        return (
            f"SN-TTT-{number + 1:03d}"
        )

    def save(self, *args, **kwargs):

        if not self.session_no:

            self.session_no = (
                self.generate_session_no()
            )

        super().save(*args, **kwargs)