"""Groq research status only, staff-only, no key material in responses."""
from datetime import timedelta
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from newsroom.models import ResearchAttempt, ResearchReview

staff = staff_member_required(login_url="accounts:login")

@staff
@require_GET
def status(request):
    today = timezone.now().date()
    rows = ResearchAttempt.objects.filter(started_at__date=today)
    return render(request, "control/ai_status.html", {
        "ai_ready": bool(settings.GROQ_API_KEY),
        "ai_model": settings.GROQ_MODEL,
        "daily_calls": rows.count(),
        "daily_tokens": rows.aggregate(v=Sum("reserved_tokens"))["v"] or 0,
        "daily_limit": settings.NEWSROOM_AI_DAILY_REQUEST_LIMIT,
        "token_limit": settings.NEWSROOM_AI_DAILY_RESERVED_TOKEN_LIMIT,
        "auto_draft": settings.NEWSROOM_AUTO_DRAFT,
        "recent_attempts": ResearchAttempt.objects.select_related("candidate").order_by("-started_at")[:15],
        "recent_reviews": ResearchReview.objects.select_related("candidate", "candidate__article").order_by("-updated_at")[:10],
    })

@staff
@require_POST
def probe_key(request):
    if not settings.GROQ_API_KEY:
        messages.error(request, "No private Groq API key is configured. Use the secure Mac command in the setup instructions.")
    else:
        try:
            response = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}, timeout=(3, 12), allow_redirects=False)
            if response.status_code == 200:
                ids = {x.get("id") for x in response.json().get("data", []) if isinstance(x, dict)}
                if settings.GROQ_MODEL in ids:
                    messages.success(request, "Groq key valid and configured model available. No article generated or charged.")
                else:
                    messages.error(request, "Groq key accepted, but selected model is unavailable to this account.")
            else:
                messages.error(request, f"Groq key probe rejected (HTTP {response.status_code}); check account access/limits.")
        except (requests.RequestException, ValueError, TypeError):
            messages.error(request, "Groq connectivity probe failed. No key or network details were displayed.")
    return redirect("control_ai")
