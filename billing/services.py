"""Stripe is authoritative: never mark paid from a browser redirect or user-supplied ID."""
import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from publishers.models import PressRelease
from .models import PaymentRecord, ReaderMembership, WebhookEvent

class BillingError(ValueError):
    pass

def require_stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise BillingError("Payments are not configured yet")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def checkout_release(request, release):
    require_stripe()
    if release.payment_received_at:
        raise BillingError("Already paid")
    if release.status not in ("submitted", "approved"):
        raise BillingError("Release is not ready for checkout")
    price = settings.PRESS_RELEASE_PRICE_CENTS
    record, _ = PaymentRecord.objects.get_or_create(
        release=release, defaults={"user": request.user, "amount_cents": price, "currency": "usd"},
    )
    if record.paid_at:
        raise BillingError("Already paid")
    # Price snapshot: a submitted release cannot be repriced after checkout starts.
    price = record.amount_cents
    session = stripe.checkout.Session.create(
        mode="payment", client_reference_id=str(request.user.pk),
        metadata={"type": "press_release", "release_id": str(release.pk)},
        line_items=[{"price_data": {"currency": "usd", "unit_amount": price,
                                      "product_data": {"name": "Press release publication and editorial review"}}, "quantity": 1}],
        success_url=request.build_absolute_uri("/publisher/?checkout=returned"),
        cancel_url=request.build_absolute_uri("/publisher/?checkout=cancelled"),
        customer_creation="always",
    )
    record.stripe_session_id = session.id
    record.save(update_fields=["stripe_session_id"])
    return session.url


def checkout_reader(request):
    require_stripe()
    if not settings.STRIPE_READER_MONTHLY_PRICE_ID:
        raise BillingError("Reader subscriptions are not configured yet")
    session = stripe.checkout.Session.create(
        mode="subscription", client_reference_id=str(request.user.pk),
        metadata={"type": "reader", "user_id": str(request.user.pk)},
        subscription_data={"metadata": {"type": "reader", "user_id": str(request.user.pk)}},
        line_items=[{"price": settings.STRIPE_READER_MONTHLY_PRICE_ID, "quantity": 1}],
        success_url=request.build_absolute_uri("/publisher/?membership=returned"),
        cancel_url=request.build_absolute_uri("/publisher/?membership=cancelled"),
    )
    return session.url


def handle_verified_webhook(event):
    """Idempotent; caller MUST verify Stripe signature before invoking."""
    event_id = event["id"]
    event_type = event["type"]
    obj = event["data"]["object"]
    with transaction.atomic():
        _, created = WebhookEvent.objects.get_or_create(
            stripe_event_id=event_id, defaults={"event_type": event_type},
        )
        if not created:
            return False
        if event_type == "checkout.session.completed":
            if obj.get("mode") == "payment" and obj.get("payment_status") == "paid":
                meta = obj.get("metadata") or {}
                if meta.get("type") == "press_release":
                    try:
                        release_id = int(meta["release_id"])
                    except (KeyError, ValueError):
                        raise BillingError("Missing press release metadata")
                    record = PaymentRecord.objects.select_for_update().select_related("release").get(release_id=release_id)
                    # Do NOT pay an unrelated session, wrong currency or wrong amount.
                    if (record.stripe_session_id != obj.get("id") or
                        record.amount_cents != obj.get("amount_total") or
                        record.currency != obj.get("currency") or
                        str(record.user_id) != str(obj.get("client_reference_id"))):
                        raise BillingError("Stripe payment mismatch")
                    if not record.paid_at:
                        paid = timezone.now()
                        record.paid_at = paid
                        record.stripe_payment_intent_id = obj.get("payment_intent") or None
                        record.save(update_fields=["paid_at", "stripe_payment_intent_id"])
                        PressRelease.objects.filter(pk=release_id, payment_received_at__isnull=True).update(payment_received_at=paid)
            elif obj.get("mode") == "subscription":
                meta = obj.get("metadata") or {}
                if meta.get("type") == "reader" and obj.get("subscription"):
                    from django.contrib.auth import get_user_model
                    user = get_user_model().objects.get(pk=int(obj["client_reference_id"]))
                    member, _ = ReaderMembership.objects.get_or_create(user=user)
                    member.stripe_customer_id = obj.get("customer") or ""
                    member.stripe_subscription_id = obj["subscription"]
                    # Subscription checkout success alone is NOT proof of active entitlement.
                    member.save(update_fields=["stripe_customer_id", "stripe_subscription_id", "updated_at"])
        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            metadata = obj.get("metadata") or {}
            user_id = metadata.get("user_id")
            subscription_id = obj.get("id")
            member = ReaderMembership.objects.filter(stripe_subscription_id=subscription_id).first()
            if not member and user_id:
                from django.contrib.auth import get_user_model
                user = get_user_model().objects.get(pk=int(user_id))
                member, _ = ReaderMembership.objects.get_or_create(user=user)
            if member and (not member.stripe_subscription_id or member.stripe_subscription_id == subscription_id):
                member.stripe_subscription_id = subscription_id
                member.stripe_customer_id = obj.get("customer") or member.stripe_customer_id
                member.status = obj.get("status", "inactive") if event_type == "customer.subscription.updated" else "canceled"
                member.save(update_fields=["stripe_subscription_id", "stripe_customer_id", "status", "updated_at"])
        return True


def reader_billing_portal(request):
    """Hosted Stripe self-service payment method and cancellation controls."""
    require_stripe()
    try:
        membership = request.user.reader_membership
    except ReaderMembership.DoesNotExist:
        raise BillingError("No reader subscription found")
    if not membership.stripe_customer_id:
        raise BillingError("Subscription does not have an associated Stripe customer")
    session = stripe.billing_portal.Session.create(
        customer=membership.stripe_customer_id,
        return_url=request.build_absolute_uri("/publisher/"),
    )
    return session.url
