from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.contrib.sitemaps.views import sitemap
from website import views as website_views
from publishers import views as publisher_views
from website.feeds import EditorialFeed, AllArticlesFeed

urlpatterns = [
    path("staff/", admin.site.urls),
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("account/", include("accounts.urls")),
    path("publisher/", include("publishers.urls")),
    path("company/<int:organization_id>/<slug:slug>/", publisher_views.company_profile, name="company_profile"),
    path("billing/", include("billing.urls")),
    path("search/", website_views.search, name="search"),
    path("rss/", AllArticlesFeed(), name="rss_all"),
    path("rss/editorial/", EditorialFeed(), name="rss_editorial"),
    path("sitemap.xml", sitemap, name="sitemap"),
    path("news-sitemap.xml", website_views.news_sitemap, name="news_sitemap"),
    path("robots.txt", website_views.robots, name="robots"),
    path("ads.txt", website_views.ads_txt, name="ads_txt"),
    path("healthz", website_views.healthz, name="healthz"),
    path("", include(wagtail_urls)),
]
