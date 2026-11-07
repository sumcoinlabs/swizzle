import hashlib
from django.db import models
from wagtail.search import index
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

CATEGORIES = [("crypto", "Crypto"), ("markets", "Markets"), ("otc", "OTC Companies"),
              ("technology", "Technology"), ("business", "Business"), ("startups", "Startups")]

class NewsIndexPage(Page):
    template = "newsroom/news_index_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types = ["newsroom.ArticlePage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        articles = ArticlePage.objects.live().public().descendant_of(self).order_by("-first_published_at")
        category = request.GET.get("category", "")
        if category in dict(CATEGORIES):
            articles = articles.filter(category=category)
        context.update(articles=articles[:80], categories=CATEGORIES, current_category=category)
        return context

class ArticlePage(Page):
    KIND_CHOICES = [("editorial", "Editorial"), ("press_release", "Press release")]
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="editorial", db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="business", db_index=True)
    summary = models.TextField(max_length=600)
    body = RichTextField(features=["h2", "h3", "bold", "italic", "ol", "ul", "link"])
    byline = models.CharField(max_length=150, blank=True)
    source_url = models.URLField(max_length=1200, blank=True)
    source_name = models.CharField(max_length=180, blank=True)
    publisher_name = models.CharField(max_length=180, blank=True)
    ticker = models.CharField(max_length=32, blank=True)
    ai_assisted = models.BooleanField(default=False)
    parent_page_types = ["newsroom.NewsIndexPage"]
    subpage_types = []
    template = "newsroom/article_page.html"
    content_panels = Page.content_panels + [
        FieldPanel("kind"), FieldPanel("category"), FieldPanel("summary"),
        FieldPanel("body"), FieldPanel("byline"), FieldPanel("publisher_name"),
        FieldPanel("ticker"), FieldPanel("source_url"), FieldPanel("source_name"),
        FieldPanel("ai_assisted"),
    ]
    search_fields = Page.search_fields + [index.SearchField("summary"), index.SearchField("body")]

    @property
    def is_sponsored(self):
        return self.kind == "press_release"

class ResearchAttempt(models.Model):
    """Conservative per-day Groq reservations; failed calls still consume a slot."""
    candidate = models.ForeignKey("StoryCandidate", on_delete=models.PROTECT, related_name="ai_attempts")
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.CharField(max_length=12, choices=(("manual", "Manual"), ("auto", "Automatic")))
    model = models.CharField(max_length=100)
    reserved_tokens = models.PositiveIntegerField(default=10000)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, default="reserved")
    error_code = models.CharField(max_length=80, blank=True)


class ResearchReview(models.Model):
    """Staff-only evidence and verification notes; never injected into public copy."""
    candidate = models.OneToOneField("StoryCandidate", on_delete=models.PROTECT, related_name="research_review")
    evidence = models.JSONField(default=dict)
    verification = models.JSONField(default=list)
    quality_flags = models.JSONField(default=list)
    topic = models.CharField(max_length=80, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    model = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedSource(models.Model):
    name = models.CharField(max_length=180)
    url = models.URLField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="business")
    is_active = models.BooleanField(default=False, help_text="Explicitly enable vetted feeds only")
    auto_publish = models.BooleanField(default=False, help_text="Requires global auto-publish flag too")
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    def __str__(self):
        return self.name

class StoryCandidate(models.Model):
    STATUS = [("queued", "Queued"), ("draft", "Draft"), ("published", "Published"), ("rejected", "Rejected")]
    source = models.ForeignKey(FeedSource, on_delete=models.PROTECT, related_name="stories")
    url = models.URLField(unique=True, max_length=1200)
    headline = models.CharField(max_length=350)
    excerpt = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="queued", db_index=True)
    article = models.OneToOneField(ArticlePage, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source_published_at = models.DateTimeField(null=True, blank=True, help_text="Original feed's stated date; never the Swizzle publication date")
    error = models.TextField(blank=True)

    def __str__(self):
        return self.headline

def article_slug(headline, url):
    from django.utils.text import slugify
    return f"{slugify(headline, allow_unicode=False)[:55].strip('-') or 'news'}-{hashlib.sha256(url.encode()).hexdigest()[:10]}"
