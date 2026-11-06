from wagtail.models import Page
from django.db import models
from wagtail.admin.panels import FieldPanel

class HomePage(Page):
    intro = models.TextField(blank=True)
    subpage_types = ["newsroom.NewsIndexPage"]
    content_panels = Page.content_panels + [FieldPanel("intro")]
    template = "home/home_page.html"

    def get_context(self, request, *args, **kwargs):
        from newsroom.models import ArticlePage
        context = super().get_context(request, *args, **kwargs)
        context["latest_articles"] = ArticlePage.objects.live().public().order_by("-first_published_at")[:24]
        return context
