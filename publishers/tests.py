from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Organization, PressRelease

class PublicationGateTests(TestCase):
    def test_unpaid_unverified_release_is_never_publishable(self):
        user = get_user_model().objects.create_user(username="submitter", password="safe-pass-long-123!")
        org = Organization.objects.create(owner=user, name="Example Issuer", contact_name="Representative")
        rel = PressRelease.objects.create(organization=org, title="New announcement", summary="Example summary",
                                           body_text="text " * 100, status="approved")
        self.assertFalse(rel.can_publish)
