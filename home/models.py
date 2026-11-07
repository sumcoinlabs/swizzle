from django.db import models
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel


class HomePage(Page):
    intro = models.TextField(blank=True)
    subpage_types = ["newsroom.NewsIndexPage"]
    content_panels = Page.content_panels + [FieldPanel("intro")]
    template = "home/home_page.html"

    def get_context(self, request, *args, **kwargs):
        from newsroom.models import ArticlePage
        context = super().get_context(request, *args, **kwargs)
        published = ArticlePage.objects.live().public()
        context["latest_editorial"] = published.filter(kind="editorial").order_by("-first_published_at")[:6]
        context["latest_releases"] = published.filter(kind="press_release").order_by("-first_published_at")[:3]
        return context
