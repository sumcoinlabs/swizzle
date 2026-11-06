from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from .models import RecoveryCode

class RecoveryCodeTests(TestCase):
    def test_only_digests_are_saved(self):
        user = get_user_model().objects.create_user(username="testrecover", password="long-password-123456")
        codes = RecoveryCode.issue_codes(user)
        self.assertEqual(len(codes), 8)
        self.assertNotEqual(codes[0], RecoveryCode.objects.first().digest)
        self.assertEqual(RecoveryCode.objects.filter(digest=RecoveryCode.digest_code(codes[0])).count(), 1)

    @override_settings(DEBUG=True)
    def test_registration_shows_codes_once_without_persisting_session_plaintext(self):
        response = self.client.post("/account/register/", {
            "username": "customer", "password1": "VerySecretPassword8891!", "password2": "VerySecretPassword8891!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save these recovery codes")
        self.assertEqual(RecoveryCode.objects.filter(user__username="customer").count(), 8)
        self.assertNotIn("fresh_recovery_codes", self.client.session)
