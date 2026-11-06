from django.core.management.base import BaseCommand
from newsroom.services import run_newsroom

class Command(BaseCommand):
    help = "Collect vetted RSS feeds and prepare AI-assisted editorial drafts"

    def handle(self, *args, **options):
        self.stdout.write(str(run_newsroom()))
