from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.utils.html import format_html
from django.urls import reverse

# --- Step 1: Inline for history ---
class LogEntryInline(admin.TabularInline):
    model = LogEntry
    fields = ("action_time", "user", "action_flag_label", "change_message_pretty", "object_link")
    readonly_fields = ("action_time", "user", "action_flag_label", "change_message_pretty", "object_link")
    can_delete = False
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("content_type", "user")

    def action_flag_label(self, obj):
        return {1: "Add", 2: "Change", 3: "Delete"}.get(obj.action_flag, obj.action_flag)

    def change_message_pretty(self, obj):
        return format_html("<pre>{}</pre>", obj.change_message or "-")

    def object_link(self, obj):
        try:
            url = reverse(
                f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                args=[obj.object_id],
            )
            return format_html('<a href="{}">{}</a>', url, obj.object_repr)
        except Exception:
            return obj.object_repr
