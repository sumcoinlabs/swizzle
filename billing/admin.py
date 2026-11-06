from django.contrib import admin
from .models import PaymentRecord, ReaderMembership, WebhookEvent

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("release", "user", "amount_cents", "paid_at", "created_at")
    readonly_fields = ("release", "user", "stripe_session_id", "stripe_payment_intent_id", "amount_cents", "currency", "paid_at", "created_at")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ReaderMembership)
class ReaderMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "updated_at")
    readonly_fields = ("user", "stripe_customer_id", "stripe_subscription_id", "status", "updated_at")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("stripe_event_id", "event_type", "received_at")
    readonly_fields = ("stripe_event_id", "event_type", "received_at")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
