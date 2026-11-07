from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.contrib.sitemaps.views import sitemap
from website import views as website_views
from website import control as website_control
from website import ai_control as ai_control_views
from publishers import views as publisher_views
from website.feeds import EditorialFeed, AllArticlesFeed

# Low-level Django administration is an advanced tool; staff start at /control/.
admin.site.site_header = "Swizzle · Advanced data administration"
admin.site.site_title = "Swizzle · Advanced administration"
admin.site.index_title = "Internal records — use the Newsroom Control Center for daily work"
admin.site.site_url = "/control/"

urlpatterns = [
    path("staff/", admin.site.urls),
    path("control/", website_control.dashboard, name="control"),
    path("control/ai/", ai_control_views.status, name="control_ai"),
    path("control/ai/probe/", ai_control_views.probe_key, name="control_ai_probe"),
    path("control/sources/", website_control.sources, name="control_sources"),
    path("control/sources/<int:source_id>/toggle/", website_control.toggle_source, name="control_source_toggle"),
    path("control/sources/<int:source_id>/scan/", website_control.scan_source, name="control_source_scan"),
    path("control/leads/", website_control.leads, name="control_leads"),
    path("control/leads/<int:lead_id>/outline/", website_control.outline_lead, name="control_lead_outline"),
    path("control/leads/<int:lead_id>/ai-draft/", website_control.ai_draft_lead, name="control_lead_ai"),
    path("control/companies/", website_control.companies, name="control_companies"),
    path("control/companies/<int:organization_id>/verify/", website_control.verify_company, name="control_company_verify"),
    path("control/releases/", website_control.releases, name="control_releases"),
    path("control/releases/<int:release_id>/simulate-payment/", website_control.simulate_payment, name="control_release_demo_payment"),
    path("control/releases/<int:release_id>/approve/", website_control.approve_release, name="control_release_approve"),
    path("control/releases/<int:release_id>/publish/", website_control.publish_release, name="control_release_publish"),
    path("control/releases/<int:release_id>/ai-review/", website_control.ai_review_release, name="control_release_ai"),
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
