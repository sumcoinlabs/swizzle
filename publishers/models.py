from django.conf import settings
from django.db import models

class Organization(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organizations")
    name = models.CharField(max_length=180)
    website = models.URLField(blank=True)
    ticker = models.CharField(max_length=32, blank=True)
    contact_name = models.CharField(max_length=180)
    contact_role = models.CharField(max_length=120, blank=True)
    jurisdiction = models.CharField(max_length=120, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Staff identity/authorization review required")
    verification_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PressRelease(models.Model):
    STATUS = [("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"),
              ("published", "Published"), ("rejected", "Rejected")]
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="releases")
    title = models.CharField(max_length=240)
    summary = models.TextField(max_length=600)
    body_text = models.TextField(max_length=30000, help_text="Plain text only; no HTML")
    category = models.CharField(max_length=20, default="business")
    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)
    editorial_notes = models.TextField(blank=True)
    ai_review_notes = models.TextField(blank=True)
    ai_suggested_title = models.CharField(max_length=240, blank=True)
    payment_received_at = models.DateTimeField(null=True, blank=True)
    published_page = models.OneToOneField("newsroom.ArticlePage", null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name="paid_release")
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def can_publish(self):
        return bool(self.payment_received_at and self.organization.is_verified and self.status == "approved")
