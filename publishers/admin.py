from django.contrib import admin, messages
from .models import Organization, PressRelease
from .services import publish_paid_release, PublicationBlocked, ai_review_release

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "ticker", "owner", "is_verified", "created_at")
    list_filter = ("is_verified",)
    search_fields = ("name", "ticker")
    readonly_fields = ("created_at",)

@admin.register(PressRelease)
class PressReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "status", "payment_received_at", "published_at")
    list_filter = ("status",)
    actions = ["ai_review_selected", "approve_paid", "publish_approved"]
    readonly_fields = ("payment_received_at", "published_page", "created_at", "submitted_at", "published_at", "ai_review_notes", "ai_suggested_title")

    @admin.action(description="AI preflight review of selected releases (staff only)")
    def ai_review_selected(self, request, queryset):
        count = 0
        for release in queryset:
            try:
                ai_review_release(release)
                count += 1
            except Exception as exc:
                self.message_user(request, f"AI review failed for {release.pk}: {exc}", messages.WARNING)
        self.message_user(request, f"AI-reviewed {count} releases", messages.INFO)

    @admin.action(description="Approve verified, paid selected releases")
    def approve_paid(self, request, queryset):
        count = 0
        for release in queryset.select_related("organization"):
            if release.payment_received_at and release.organization.is_verified and release.status == "submitted":
                release.status = "approved"
                release.save(update_fields=["status"])
                count += 1
        self.message_user(request, f"Approved {count} paid/verified releases", messages.INFO)

    @admin.action(description="Publish selected approved, paid releases")
    def publish_approved(self, request, queryset):
        count = 0
        for release in queryset:
            try:
                publish_paid_release(release.pk)
                count += 1
            except PublicationBlocked as exc:
                self.message_user(request, f"Blocked release {release.pk}: {exc}", messages.WARNING)
        self.message_user(request, f"Published {count} releases", messages.INFO)
