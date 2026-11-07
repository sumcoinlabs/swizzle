import stripe
from django.conf import settings
from django.contrib import messages
from publishers.decorators import customer_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from publishers.models import PressRelease
from .services import checkout_reader, checkout_release, reader_billing_portal, handle_verified_webhook, BillingError

@customer_required
@require_POST
def pay_release(request, release_id):
    release = get_object_or_404(PressRelease, id=release_id, organization__owner=request.user)
    try:
        url = checkout_release(request, release)
    except (BillingError, stripe.StripeError) as exc:
        messages.error(request, f"Checkout unavailable: {exc}")
        return redirect("publishers:dashboard")
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(url)

@customer_required
@require_POST
def subscribe_reader(request):
    try:
        url = checkout_reader(request)
    except (BillingError, stripe.StripeError) as exc:
        messages.error(request, f"Subscription unavailable: {exc}")
        return redirect("publishers:dashboard")
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(url)

@customer_required
@require_POST
def manage_reader(request):
    try:
        url = reader_billing_portal(request)
    except (BillingError, stripe.StripeError) as exc:
        messages.error(request, f"Billing portal unavailable: {exc}")
        return redirect("publishers:dashboard")
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(url)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    try:
        event = stripe.Webhook.construct_event(
            payload=request.body,
            sig_header=request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponseBadRequest("Invalid signature")
    try:
        handle_verified_webhook(event)
    except Exception:
        # Stripe retries non-2xx; the DB transaction rolls back before returning 500.
        import logging
        logging.getLogger(__name__).exception("Verified Stripe event could not be handled")
        return HttpResponse(status=500)
    return HttpResponse(status=200)
