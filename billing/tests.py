from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from publishers.models import Organization, PressRelease
from .models import PaymentRecord, ReaderMembership
from .services import BillingError, handle_verified_webhook

class BillingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="reader", password="some-long-password-123")
        org = Organization.objects.create(owner=self.user, name="Issuer", contact_name="Representative")
        self.release = PressRelease.objects.create(organization=org, title="Release", summary="Summary",
                                                    body_text="Long release " * 80, status="submitted")
        self.record = PaymentRecord.objects.create(release=self.release, user=self.user, amount_cents=2900,
                                                    stripe_session_id="cs_example")

    def event(self, event_id, amount=2900):
        return {"id": event_id, "type": "checkout.session.completed", "data": {"object": {
            "id": "cs_example", "mode": "payment", "payment_status": "paid", "amount_total": amount,
            "currency": "usd", "client_reference_id": str(self.user.pk), "payment_intent": "pi_example",
            "metadata": {"type": "press_release", "release_id": str(self.release.pk)},
        }}}

    def test_unpaid_release_is_not_publishable(self):
        self.assertFalse(self.release.can_publish)

    def test_payment_mismatch_rolls_back_entire_event(self):
        with self.assertRaises(BillingError):
            handle_verified_webhook(self.event("evt_wrong", amount=1))
        self.release.refresh_from_db()
        self.assertIsNone(self.release.payment_received_at)

    def test_verified_payment_idempotent(self):
        self.assertTrue(handle_verified_webhook(self.event("evt_ok")))
        self.assertFalse(handle_verified_webhook(self.event("evt_ok")))
        self.release.refresh_from_db()
        self.assertIsNotNone(self.release.payment_received_at)
        self.assertFalse(self.release.can_publish)  # identity and approval still required

    def test_bad_webhook_signature_rejected(self):
        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_example"):
            result = self.client.post("/billing/stripe/webhook/", data=b"{}", content_type="application/json",
                                      HTTP_STRIPE_SIGNATURE="invalid")
        self.assertEqual(result.status_code, 400)

    def test_adfree_requires_active_membership(self):
        member = ReaderMembership.objects.create(user=self.user)
        self.assertFalse(member.ad_free)
        member.status = "active"
        self.assertTrue(member.ad_free)
