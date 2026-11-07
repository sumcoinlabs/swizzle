"""v0.5 regression tests: roles, safe editorial drafts and fake payment gating."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from newsroom.models import ArticlePage, FeedSource, StoryCandidate
from publishers.models import Organization, PressRelease


class StaffSeparationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_superuser(username="v05staff", password="test-staff-pass-2034!", email="")
        cls.publisher = get_user_model().objects.create_user(username="v05publisher", password="test-pub-pass-2034!")

    def test_staff_routes_forbidden_to_customer_and_anonymous(self):
        for route in ["control", "control_sources", "control_leads", "control_companies", "control_releases"]:
            self.assertEqual(self.client.get(reverse(route)).status_code, 302)
        self.client.force_login(self.publisher)
        for route in ["control", "control_sources", "control_leads", "control_companies", "control_releases"]:
            self.assertEqual(self.client.get(reverse(route)).status_code, 302)

    def test_login_and_dashboard_separate_roles(self):
        self.client.force_login(self.staff)
        self.assertRedirects(self.client.get(reverse("publishers:dashboard")), reverse("control"), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse("accounts:home")), reverse("control"), fetch_redirect_response=False)
        self.assertNotContains(self.client.get("/"), 'href="/publisher/"', status_code=200)
        self.assertRedirects(self.client.get(reverse("publishers:create_organization")), reverse("control"), fetch_redirect_response=False)
        self.client.force_login(self.publisher)
        self.assertRedirects(self.client.get(reverse("accounts:home")), reverse("publishers:dashboard"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("publishers:dashboard")), "Your publishing desk")

    def test_workflow_mutations_require_post(self):
        self.client.force_login(self.staff)
        source = FeedSource.objects.create(name="Feed", url="https://github.com/example/feed.atom")
        self.assertEqual(self.client.get(reverse("control_source_toggle", args=[source.pk])).status_code, 405)
        source.refresh_from_db()
        self.assertFalse(source.is_active)
        self.client.post(reverse("control_source_toggle", args=[source.pk]))
        source.refresh_from_db()
        self.assertTrue(source.is_active)
        self.assertFalse(source.auto_publish)


class EditorialAndReleaseWorkflowTests(TestCase):
    def setUp(self):
        call_command("bootstrap_site", verbosity=0)
        U = get_user_model()
        self.staff = U.objects.create_superuser(username="manager05", password="test-staff-pass-2034!", email="")
        self.publisher = U.objects.create_user(username="customer05", password="test-pub-pass-2034!")
        self.company = Organization.objects.create(owner=self.publisher, name="Example Research Labs", contact_name="Account Owner")
        self.release = PressRelease.objects.create(organization=self.company, title="Example Company Announces a Public Product Roadmap", summary="This is a fictional test announcement for the private staging environment, not real company news.", body_text="This is a test release for a private application workflow. " * 8, status="submitted")
        self.client.force_login(self.staff)

    def test_outline_is_never_published(self):
        source = FeedSource.objects.create(name="Official Test", url="https://github.com/example/releases.atom", is_active=True)
        candidate = StoryCandidate.objects.create(source=source, headline="Example technology project announces maintenance release", url="https://github.com/example/project/releases/tag/v1.2.3", excerpt="A fictional maintenance release was announced by a fictional project; this is only a test and not a verified fact.")
        self.client.post(reverse("control_lead_outline", args=[candidate.pk]))
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "draft")
        self.assertIsNotNone(candidate.article_id)
        self.assertFalse(candidate.article.live)
        self.assertEqual(ArticlePage.objects.live().count(), 0)

    @override_settings(DEBUG=True, STAGING_DEMO_PAYMENTS=True, NEWSROOM_AUTO_PUBLISH=False)
    def test_full_simulated_release_flow_requires_review(self):
        self.client.post(reverse("control_release_demo_payment", args=[self.release.pk]), {"confirm": "SIMULATE"})
        self.release.refresh_from_db()
        self.assertTrue(self.release.is_test_payment)
        self.assertIsNotNone(self.release.payment_received_at)
        # Company has not yet been verified; approval must fail.
        self.client.post(reverse("control_release_approve", args=[self.release.pk]), {"editor_reviewed": "yes"})
        self.release.refresh_from_db()
        self.assertEqual(self.release.status, "submitted")
        self.client.post(reverse("control_company_verify", args=[self.company.pk]), {
            "verified": "yes", "verification_notes": "Checked independent company authority evidence in test scenario",
        })
        self.company.refresh_from_db()
        self.assertTrue(self.company.is_verified)
        # Approval without an explicit editorial acknowledgement is refused.
        self.client.post(reverse("control_release_approve", args=[self.release.pk]), {})
        self.release.refresh_from_db()
        self.assertEqual(self.release.status, "submitted")
        self.client.post(reverse("control_release_approve", args=[self.release.pk]), {
            "editor_reviewed": "yes", "notes": "Test publication reviewed by staging admin",
        })
        self.release.refresh_from_db()
        self.assertEqual(self.release.status, "approved")
        self.client.post(reverse("control_release_publish", args=[self.release.pk]))
        self.release.refresh_from_db()
        self.assertEqual(self.release.status, "published")
        self.assertIsNotNone(self.release.published_page_id)
        self.assertTrue(self.release.published_page.live)
        self.assertEqual(self.release.published_page.kind, "press_release")
        self.assertContains(self.client.get(self.release.published_page.url), "STAGING DEMO")

    @override_settings(DEBUG=False, STAGING_DEMO_PAYMENTS=False)
    def test_simulated_payment_blocked_outside_staging(self):
        self.client.post(reverse("control_release_demo_payment", args=[self.release.pk]), {"confirm": "SIMULATE"})
        self.release.refresh_from_db()
        self.assertIsNone(self.release.payment_received_at)

    @override_settings(DEBUG=True, STAGING_DEMO_PAYMENTS=True)
    def test_staging_charge_does_not_authorize_production_publication(self):
        self.client.post(reverse("control_release_demo_payment", args=[self.release.pk]), {"confirm": "SIMULATE"})
        self.company.is_verified = True
        self.company.save(update_fields=["is_verified"])
        self.release.refresh_from_db()
        self.release.status = "approved"
        self.release.save(update_fields=["status"])
        self.assertTrue(self.release.can_publish)
        with override_settings(DEBUG=False, STAGING_DEMO_PAYMENTS=False):
            self.release.refresh_from_db()
            self.assertFalse(self.release.can_publish)
            from publishers.services import PublicationBlocked, publish_paid_release
            with self.assertRaises(PublicationBlocked):
                publish_paid_release(self.release.pk)

    def test_customer_cannot_forge_staff_simulation(self):
        self.client.force_login(self.publisher)
        response = self.client.post(reverse("control_release_demo_payment", args=[self.release.pk]), {"confirm": "SIMULATE"})
        self.assertEqual(response.status_code, 302)
        self.release.refresh_from_db()
        self.assertIsNone(self.release.payment_received_at)
