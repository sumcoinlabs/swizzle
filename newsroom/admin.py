from django.contrib import admin
from .models import FeedSource, StoryCandidate

@admin.register(FeedSource)
class FeedSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "auto_publish", "last_checked_at")
    list_filter = ("is_active", "auto_publish", "category")

@admin.register(StoryCandidate)
class StoryCandidateAdmin(admin.ModelAdmin):
    list_display = ("headline", "source", "status", "created_at")
    list_filter = ("status", "source")
    readonly_fields = ("created_at",)
