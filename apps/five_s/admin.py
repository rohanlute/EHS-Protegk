from django.contrib import admin

from .models import AuditAnswer

@admin.register(AuditAnswer)
class AuditAnswerAdmin(admin.ModelAdmin):
    list_display = ('audit', 'question', 'answer', 'created_at')
    list_filter = ('answer',)
    search_fields = ('audit__cycle_key', 'question__question_code', 'question__question_text')
    raw_id_fields = ('audit', 'question')