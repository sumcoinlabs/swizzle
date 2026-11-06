"""Email-free password recovery, using one-time random codes stored only as hashes."""
import hashlib
import secrets
from django.conf import settings
from django.db import models

class RecoveryCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recovery_codes")
    digest = models.CharField(max_length=64, unique=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def digest_code(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def issue_codes(cls, user, count=8):
        # Return raw codes exactly once; only SHA-256 digests are persisted.
        output = []
        for _ in range(count):
            code = secrets.token_urlsafe(15)
            cls.objects.create(user=user, digest=cls.digest_code(code))
            output.append(code)
        return output
