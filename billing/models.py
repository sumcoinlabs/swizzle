from django.conf import settings
from django.db import models

class PaymentRecord(models.Model):
    release = models.OneToOneField("publishers.PressRelease", on_delete=models.PROTECT, related_name="payment")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    stripe_session_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="usd")
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for release #{self.release_id}"

class ReaderMembership(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reader_membership")
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    status = models.CharField(max_length=32, default="inactive")
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def ad_free(self):
        return self.status in ("active", "trialing")

class WebhookEvent(models.Model):
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    received_at = models.DateTimeField(auto_now_add=True)
