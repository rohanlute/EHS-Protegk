from django.db import models
from django.contrib.auth import get_user_model
from apps.organizations.models import *
import datetime
from django.conf import settings
from django.utils import timezone 
from apps.accounts.models import *

user = get_user_model()

# Create your models here.
class KaizenCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text='Full name of Kaizen category')
    code = models.CharField(max_length=100, unique=True, help_text='Unique short code')
    description = models.TextField(blank=True, help_text='Description of the kaizen category')
    is_active = models.BooleanField(default=True,help_text='Is the kaizen category active?')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='kaizen_category_created')

    class Meta:
        ordering = ['name']
        verbose_name = 'Kaizen Category'
        verbose_name_plural = 'Kaizen Categories'
        
    def __str__(self):
        return f"{self.name}({self.code})"