"""Staff workspaces; staff-only actions use CSRF-protected POSTs.

Wagtail is retained for rich editorial editing; Django admin is not required for
ordinary daily newsroom operations. None of these routes trust customer-owned IDs.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from newsroom.models import ArticlePage, FeedSource, StoryCandidate
from publishers.models import Organization, PressRelease

staff = staff_member_required(login_url="accounts:login")


@staff
@require_GET
def dashboard(request):
    from billing.models import PaymentRecord
    releases = PressRelease.objects.filter(status__in=("submitted", "approved")).select_related("organization").order_by("-created_at")
    leads = StoryCandidate.objects.filter(status__in=("queued", "draft")).select_related("source").order_by("-created_at")
    return render(request, "website/control.html", {
        "published_count": ArticlePage.objects.live().count(),
        "draft_count": ArticlePage.objects.filter(live=False).count(),
        "story_count": leads.count(), "release_count": releases.count(),
        "company_count": Organization.objects.filter(is_verified=False).count(),
        "feed_count": FeedSource.objects.count(),
        "active_feed_count": FeedSource.objects.filter(is_active=True).count(),
        "payment_count": PaymentRecord.objects.filter(paid_at__isnull=False).count(),
        "release_queue": releases[:6], "story_queue": leads[:6],
        "ai_ready": bool(settings.GROQ_API_KEY),
        "demo_mode": settings.DEBUG and settings.STAGING_DEMO_PAYMENTS,
    })


@staff
@require_GET
def sources(request):
    sources = FeedSource.objects.all().order_by("-is_active", "name")
    return render(request, "control/sources.html", {"sources": sources, "active_count": sources.filter(is_active=True).count()})


@staff
@require_POST
def toggle_source(request, source_id):
    source = get_object_or_404(FeedSource, pk=source_id)
    # Activation never authorizes autonomous publishing.
    source.is_active = not source.is_active
    source.auto_publish = False
    source.save(update_fields=["is_active", "auto_publish"])
    messages.success(request, f"{source.name}: {'monitoring enabled' if source.is_active else 'monitoring disabled'}; automatic publication OFF.")
    return redirect("control_sources")


@staff
@require_POST
def scan_source(request, source_id):
    from newsroom.services import collect_feed, NewsroomError
    source = get_object_or_404(FeedSource, pk=source_id, is_active=True)
    try:
        created = collect_feed(source)  # Exactly one explicitly selected source per request.
        messages.success(request, f"{source.name}: {created} new lead(s). No articles published.")
    except Exception as exc:
        source.last_error = f"{type(exc).__name__}: {str(exc)[:350]}"
        source.last_checked_at = timezone.now()
        source.save(update_fields=["last_error", "last_checked_at"])
        messages.error(request, f"Source scan failed: {type(exc).__name__} (review the feed URL and status).")
    return redirect("control_sources")


@staff
@require_GET
def leads(request):
    stories = StoryCandidate.objects.select_related("source", "article").order_by("-created_at")[:150]
    return render(request, "control/leads.html", {"leads": stories, "ai_ready": bool(settings.GROQ_API_KEY)})


@staff
@require_POST
def outline_lead(request, lead_id):
    from newsroom.services import prepare_candidate_outline, NewsroomError
    candidate = get_object_or_404(StoryCandidate, pk=lead_id)
    try:
        prepare_candidate_outline(candidate)
        messages.success(request, "Unpublished research outline created. Edit and verify it in Story Editor before publishing.")
    except NewsroomError as exc:
        messages.error(request, str(exc))
    return redirect("control_leads")


@staff
@require_POST
def ai_draft_lead(request, lead_id):
    from newsroom.services import draft_candidate, NewsroomError
    candidate = get_object_or_404(StoryCandidate, pk=lead_id)
    if not settings.GROQ_API_KEY:
        messages.error(request, "Groq is not configured; prepare a research outline instead.")
    else:
        try:
            draft_candidate(candidate)
            messages.success(request, "AI-assisted unpublished draft created; verify evidence in Story Editor.")
        except Exception as exc:
            messages.error(request, f"AI drafting unavailable: {type(exc).__name__}. Check source and private server logs.")
    return redirect("control_leads")


@staff
@require_GET
def companies(request):
    organizations = Organization.objects.select_related("owner").order_by("is_verified", "-created_at")[:150]
    return render(request, "control/companies.html", {"companies": organizations})


@staff
@require_POST
def verify_company(request, organization_id):
    org = get_object_or_404(Organization, pk=organization_id)
    notes = request.POST.get("verification_notes", "").strip()
    if request.POST.get("verified") != "yes" or len(notes) < 12:
        messages.error(request, "Confirm independent identity/authority review and enter review notes (12+ characters).")
    elif org.is_verified:
        messages.info(request, "Company is already verified.")
    else:
        org.is_verified = True
        org.verification_notes = notes[:3000]
        org.save(update_fields=["is_verified", "verification_notes"])
        messages.success(request, f"Verified {org.name}. This is a manual staff decision.")
    return redirect("control_companies")


@staff
@require_GET
def releases(request):
    queryset = PressRelease.objects.select_related("organization", "organization__owner", "published_page").order_by("-created_at")[:150]
    return render(request, "control/releases.html", {
        "releases": queryset, "demo_mode": settings.DEBUG and settings.STAGING_DEMO_PAYMENTS,
        "ai_ready": bool(settings.GROQ_API_KEY),
    })


@staff
@require_POST
def simulate_payment(request, release_id):
    from django.db import transaction
    if not (settings.DEBUG and settings.STAGING_DEMO_PAYMENTS):
        messages.error(request, "Simulation unavailable outside isolated staging.")
        return redirect("control_releases")
    with transaction.atomic():
        release = get_object_or_404(PressRelease.objects.select_for_update(), pk=release_id)
        if (release.status == "submitted" and not release.payment_received_at and
                request.POST.get("confirm") == "SIMULATE"):
            release.is_test_payment = True
            release.payment_received_at = timezone.now()
            release.save(update_fields=["is_test_payment", "payment_received_at"])
            messages.success(request, f"SIMULATED ${settings.PRESS_RELEASE_PRICE_CENTS/100:.0f} payment recorded for release #{release.pk}. No actual charge occurred.")
        else:
            messages.error(request, "Only an unpaid submitted release can receive a confirmed simulated payment.")
    return redirect("control_releases")


@staff
@require_POST
def approve_release(request, release_id):
    from django.db import transaction
    with transaction.atomic():
        release = get_object_or_404(PressRelease.objects.select_for_update().select_related("organization"), pk=release_id)
        if (release.status == "submitted" and release.organization.is_verified and
                release.payment_received_at and release.can_publish_after_approval and
                request.POST.get("editor_reviewed") == "yes"):
            release.status = "approved"
            release.editorial_notes = request.POST.get("notes", "")[:3000].strip()
            release.save(update_fields=["status", "editorial_notes"])
            messages.success(request, "Release approved. Publishing is a separate deliberate action.")
        else:
            messages.error(request, "Requires submitted status, verified company and a valid payment (or explicitly enabled staging simulation).")
    return redirect("control_releases")


@staff
@require_POST
def publish_release(request, release_id):
    from publishers.services import publish_paid_release, PublicationBlocked
    try:
        article = publish_paid_release(release_id)
        messages.success(request, f"Published a labeled press release: {article.title}")
    except PublicationBlocked as exc:
        messages.error(request, str(exc))
    return redirect("control_releases")


@staff
@require_POST
def ai_review_release(request, release_id):
    from publishers.services import ai_review_release as review
    release = get_object_or_404(PressRelease, pk=release_id)
    if not settings.GROQ_API_KEY:
        messages.error(request, "Groq is not configured. This AI action is unavailable.")
    else:
        try:
            output = review(release)
            messages.info(request, f"Advisory AI preflight finished: {len(output['flags'])} flag(s); no approval granted.")
        except Exception as exc:
            messages.error(request, f"AI preflight failed: {type(exc).__name__}. Review the private logs.")
    return redirect("control_releases")
