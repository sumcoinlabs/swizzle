from django.conf import settings
from django.contrib.syndication.views import Feed
from newsroom.models import ArticlePage

class AllArticlesFeed(Feed):
    def title(self):
        return f"{settings.SITE_NAME} — Latest"
    link = "/news/"
    description = "Latest independent news and clearly labeled company announcements"

    def items(self):
        return ArticlePage.objects.live().public().order_by("-first_published_at")[:50]
    def item_title(self, item):
        return item.title
    def item_link(self, item):
        return item.get_url() or "/news/"
    def item_description(self, item):
        return item.summary
    def item_pubdate(self, item):
        return item.first_published_at

class EditorialFeed(AllArticlesFeed):
    def title(self):
        return f"{settings.SITE_NAME} — Editorial"
    description = "Independent newsroom output and original news briefs"
    def items(self):
        return ArticlePage.objects.live().public().filter(kind="editorial").order_by("-first_published_at")[:50]
