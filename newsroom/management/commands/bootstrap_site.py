from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site
from home.models import HomePage
from newsroom.models import NewsIndexPage

class Command(BaseCommand):
    help = "Initialize the generic brand-independent Wagtail homepage and news index"

    @transaction.atomic
    def handle(self, *args, **options):
        root = Page.get_first_root_node()
        home = HomePage.objects.first()
        if not home:
            home = root.add_child(instance=HomePage(title="Home", slug="front", intro=settings.SITE_TAGLINE))
            home.save_revision().publish()
        news = NewsIndexPage.objects.first()
        if not news:
            news = home.add_child(instance=NewsIndexPage(title="News", slug="news"))
            news.save_revision().publish()
        existing = Site.objects.filter(is_default_site=True).first()
        if existing:
            existing.hostname = settings.SITE_DOMAIN
            existing.root_page = home
            existing.site_name = settings.SITE_NAME
            existing.port = 8000 if settings.DEBUG else 443
            existing.save()
        else:
            Site.objects.create(hostname=settings.SITE_DOMAIN, root_page=home, site_name=settings.SITE_NAME,
                                port=8000 if settings.DEBUG else 443, is_default_site=True)
        self.stdout.write(self.style.SUCCESS(f"Site initialized: {settings.SITE_NAME} /news/"))
