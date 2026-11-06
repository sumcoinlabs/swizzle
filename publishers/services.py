"""Only paid and independently reviewed releases may enter the public Wagtail tree."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape
from newsroom.models import NewsIndexPage, ArticlePage, article_slug
from .models import PressRelease

class PublicationBlocked(ValueError):
    pass

@transaction.atomic
def publish_paid_release(release_id):
    release = PressRelease.objects.select_for_update().select_related("organization").get(pk=release_id)
    if release.published_page_id:
        return release.published_page
    if not release.can_publish:
        raise PublicationBlocked("Requires completed payment, verified organization, and editorial approval")
    index = NewsIndexPage.objects.first()
    if not index:
        raise PublicationBlocked("News index not initialized")
    body = "".join(f"<p>{escape(p)}</p>" for p in release.body_text.split("\n\n") if p.strip())
    article = index.add_child(instance=ArticlePage(
        title=release.title, slug=article_slug(release.title, f"paid-release:{release.pk}"),
        kind="press_release", category=release.category,
        summary=release.summary, body=body, publisher_name=release.organization.name,
        ticker=release.organization.ticker, byline=release.organization.name,
    ))
    article.save_revision().publish()
    release.published_page = article
    release.published_at = timezone.now()
    release.status = "published"
    release.save(update_fields=["published_page", "published_at", "status"])
    return article


def ai_review_release(release):
    """Advisory-only AI preflight. Never silently edit customer assertions or approve content."""
    import json
    import requests
    from django.conf import settings
    if not settings.GROQ_API_KEY:
        raise PublicationBlocked("Set GROQ_API_KEY to enable AI reviews")
    prompt = (
        "You are a rigorous press-release copy editor and safety reviewer. "
        "Return JSON with suggested_title (string) and flags (array of short strings). "
        "Identify unsupported investment returns, misleading regulatory disclosures, defamation, "
        "unverified superlatives, missing dates/sources and grammar issues. "
        "Do not assume any submitted claim is true; never invent facts."
    )
    payload = {"model": settings.GROQ_MODEL, "temperature": 0.0,
               "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": prompt},
                            {"role": "user", "content": json.dumps({"company": release.organization.name,
                            "headline": release.title, "summary": release.summary, "body": release.body_text[:18000]})}]}
    result = requests.post("https://api.groq.com/openai/v1/chat/completions",
                           json=payload, headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}, timeout=(5, 60))
    result.raise_for_status()
    output = json.loads(result.json()["choices"][0]["message"]["content"])
    if not isinstance(output.get("flags"), list):
        raise PublicationBlocked("AI review did not return usable flags")
    release.ai_suggested_title = str(output.get("suggested_title", ""))[:240]
    release.ai_review_notes = "\n".join(str(x)[:300] for x in output["flags"][:30])[:5000]
    release.save(update_fields=["ai_suggested_title", "ai_review_notes"])
    return output
