"""Only select known DGB official release feeds on an isolated development site."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from newsroom.models import FeedSource

# Explicit list from public dgb-newsroom-engine v0.6 sources.json.
APPROVED = {
    "https://github.com/DigiByte-Core/digibyte/releases.atom",
    "https://github.com/sumcoinlabs/digibyte_flutter/releases.atom",
    "https://github.com/sumcoinlabs/digicoinlib/releases.atom",
}


class Command(BaseCommand):
    help = "Enable three known official release feeds only on isolated staging (never auto-publish)"

    def handle(self, *args, **kwargs):
        if not settings.DEBUG or settings.NEWSROOM_AUTO_PUBLISH:
            raise CommandError("Refusing: requires DEBUG staging with automatic publication disabled")
        count = 0
        for source in FeedSource.objects.filter(url__in=APPROVED):
            source.is_active = True
            source.auto_publish = False
            source.save(update_fields=["is_active", "auto_publish"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Enabled {count} vetted releases feeds; automatic publishing OFF"))
