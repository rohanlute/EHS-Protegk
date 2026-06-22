from django.contrib import admin

from .models import (
    ToolboxTalkCategory,
    ToolboxTalkTopic,
    ToolboxTalkTopicDetail
    
)


@admin.register(ToolboxTalkCategory)
class ToolboxTalkCategoryAdmin(admin.ModelAdmin):

    list_display = [
        'category_name',
        'short_code',
        'is_active',
        'created_at'
    ]

    search_fields = [
        'category_name',
        'short_code'
    ]

    list_filter = [
        'is_active'
    ]


@admin.register(ToolboxTalkTopic)
class ToolboxTalkTopicAdmin(admin.ModelAdmin):

    list_display = [
        'topic_code',
        'topic_title',
        'category',
        'is_active',
        'created_by',
        'created_at'
    ]

    search_fields = [
        'topic_code',
        'topic_title'
    ]

    list_filter = [
        'category',
        'is_active'
    ]


@admin.register(ToolboxTalkTopicDetail)
class ToolboxTalkTopicDetailAdmin(admin.ModelAdmin):

    list_display = [

        'topic',

        'display_order',

        'safety_point',

        'learning_objective'

    ]

    search_fields = [

        'safety_point',

        'learning_objective',

        'reference_document'

    ]