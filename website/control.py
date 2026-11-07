"""Staff-only operational front door. Wagtail and Django remain specialized tools."""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required(login_url="accounts:login")
def dashboard(request):
    """No management side effects: this page only presents status and safe links."""
    from billing.models import PaymentRecord
    from newsroom.models import ArticlePage, FeedSource, StoryCandidate
    from publishers.models import Organization, PressRelease

    release_queue = PressRelease.objects.filter(status__in=("submitted", "approved")).select_related(
        "organization"
    ).order_by("-created_at")[:6]
    story_queue = StoryCandidate.objects.filter(status__in=("queued", "draft")).select_related(
        "source"
    ).order_by("-created_at")[:6]
    return render(request, "website/control.html", {
        "published_count": ArticlePage.objects.live().count(),
        "draft_count": ArticlePage.objects.filter(live=False).count(),
        "story_count": StoryCandidate.objects.filter(status__in=("queued", "draft")).count(),
        "release_count": PressRelease.objects.filter(status__in=("submitted", "approved")).count(),
        "company_count": Organization.objects.filter(is_verified=False).count(),
        "feed_count": FeedSource.objects.count(),
        "active_feed_count": FeedSource.objects.filter(is_active=True).count(),
        "payment_count": PaymentRecord.objects.count(),
        "release_queue": release_queue,
        "story_queue": story_queue,
    })
