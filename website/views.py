from datetime import timedelta
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from django.conf import settings
from django.db import connections
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from newsroom.models import ArticlePage

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NEWS_NS = "http://www.google.com/schemas/sitemap-news/0.9"
register_namespace("", SITEMAP_NS)
register_namespace("news", NEWS_NS)

def search(request):
    q = request.GET.get("q", "").strip()[:120]
    articles = ArticlePage.objects.live().public()
    if q:
        articles = articles.search(q)[:60]
    else:
        articles = articles.order_by("-first_published_at")[:40]
    return render(request, "website/search.html", {"q": q, "articles": articles})

def news_sitemap(request):
    """Only recent independent editorial stories; no guarantees about inclusion."""
    cutoff = timezone.now() - timedelta(hours=48)
    articles = ArticlePage.objects.live().public().filter(kind="editorial", first_published_at__gte=cutoff).order_by("-first_published_at")[:1000]
    root = Element(f"{{{SITEMAP_NS}}}urlset")
    for article in articles:
        url = article.get_full_url(request=request)
        if not url:
            continue
        entry = SubElement(root, f"{{{SITEMAP_NS}}}url")
        SubElement(entry, f"{{{SITEMAP_NS}}}loc").text = url
        item = SubElement(entry, f"{{{NEWS_NS}}}news")
        publication = SubElement(item, f"{{{NEWS_NS}}}publication")
        SubElement(publication, f"{{{NEWS_NS}}}name").text = settings.SITE_NAME
        SubElement(publication, f"{{{NEWS_NS}}}language").text = settings.SITE_LANGUAGE
        SubElement(item, f"{{{NEWS_NS}}}publication_date").text = article.first_published_at.isoformat()
        SubElement(item, f"{{{NEWS_NS}}}title").text = article.title
    return HttpResponse(tostring(root, encoding="utf-8", xml_declaration=True), content_type="application/xml")

def robots(request):
    base = request.build_absolute_uri("/").rstrip("/")
    content = f"User-agent: *\nAllow: /\nDisallow: /staff/\nDisallow: /cms/\nDisallow: /account/\nDisallow: /publisher/\nDisallow: /billing/\nSitemap: {base}/sitemap.xml\nSitemap: {base}/news-sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

def ads_txt(request):
    return HttpResponse(settings.ADS_TXT.strip() + "\n" if settings.ADS_TXT.strip() else "", content_type="text/plain; charset=utf-8")

def healthz(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return HttpResponse("unhealthy\n", status=503, content_type="text/plain")
    return HttpResponse("ok\n", content_type="text/plain")
