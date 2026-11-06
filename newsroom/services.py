"""Small, source-attributed newsroom engine; does not copy article bodies from feeds."""
import html
import json
import logging
import ipaddress
from urllib.parse import urlparse

import bleach
import feedparser
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape
from .models import ArticlePage, FeedSource, NewsIndexPage, StoryCandidate, article_slug

logger = logging.getLogger(__name__)
MAX_FEED_BYTES = 1_500_000

class NewsroomError(RuntimeError):
    pass

def collect_feed(source):
    """Only staff-controlled active feed sources can be polled; no public URL input."""
    if not source.is_active:
        return 0
    parsed = urlparse(source.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise NewsroomError("Feed URL must be a safe HTTPS URL")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise NewsroomError("IP literal feed URLs are not permitted")
    # Never automatically follow to an unvetted host or an internal service.
    response = requests.get(source.url, timeout=(5, 15), stream=True, allow_redirects=False,
                            headers={"User-Agent": "SwizzleEditorialRSS/0.2"})
    if 300 <= response.status_code < 400:
        response.close()
        raise NewsroomError("Feed redirected; verify canonical HTTPS URL manually")
    response.raise_for_status()
    chunks = []
    size = 0
    for chunk in response.iter_content(65536):
        size += len(chunk)
        if size > MAX_FEED_BYTES:
            raise NewsroomError("Feed exceeded maximum size")
        chunks.append(chunk)
    response.close()
    raw = b"".join(chunks)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise NewsroomError("DTD and XML entities are not accepted in feeds")
    feed = feedparser.parse(raw)
    made = 0
    for entry in feed.entries[:40]:
        url = str(entry.get("link", ""))[:1200]
        if urlparse(url).scheme not in ("http", "https"):
            continue
        headline = bleach.clean(str(entry.get("title", "")), tags=[], strip=True).strip()[:350]
        excerpt = bleach.clean(str(entry.get("summary", "")), tags=[], strip=True).strip()[:1400]
        if len(headline) < 12 or len(excerpt) < 40:
            continue
        _, created = StoryCandidate.objects.get_or_create(
            url=url, defaults={"source": source, "headline": html.unescape(headline), "excerpt": html.unescape(excerpt)},
        )
        made += int(created)
    source.last_checked_at = timezone.now()
    source.last_error = ""
    source.save(update_fields=["last_checked_at", "last_error"])
    return made

def generate_ai_brief(candidate):
    """Generate *grounded draft* from feed headline/excerpt; never fabricate a quote or source."""
    if not settings.GROQ_API_KEY:
        raise NewsroomError("GROQ_API_KEY is missing; story remains queued")
    if settings.AI_PROVIDER != "groq":
        raise NewsroomError("Unknown AI provider")
    instruction = (
        "You are a financial-news copy editor. Use ONLY the supplied RSS headline and excerpt as evidence. "
        "If the excerpt is insufficient, respond with a nonempty warnings array and do not extrapolate. "
        "Never invent a quote, number, price, date, company statement, filing, or independent verification. "
        "Use attribution (according to the source). Respond with a JSON object containing keys "
        "headline (string), summary (string), paragraphs (array of 2-3 short strings), warnings (array of strings). "
        "Do not copy the source excerpt verbatim except named entities; keep paragraphs brief."
    )
    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps({"source": candidate.source.name, "headline": candidate.headline,
                                                    "excerpt": candidate.excerpt, "url": candidate.url})},
        ],
        "response_format": {"type": "json_object"},
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload,
                             headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}, timeout=(5, 60))
    response.raise_for_status()
    result = json.loads(response.json()["choices"][0]["message"]["content"])
    if not isinstance(result, dict) or not isinstance(result.get("paragraphs"), list):
        raise NewsroomError("Malformed AI brief")
    if len(result["paragraphs"]) < 2 or len(result["paragraphs"]) > 3 or any(not isinstance(p, str) or len(p) > 1200 for p in result["paragraphs"]):
        raise NewsroomError("Insufficient or oversized AI brief")
    return result

def draft_candidate(candidate):
    """Draft first; publish automatically only when BOTH independent switches allow it."""
    if candidate.status != "queued":
        return candidate.article
    result = generate_ai_brief(candidate)
    warnings = result.get("warnings", [])
    if not isinstance(warnings, list):
        raise NewsroomError("Malformed AI warnings")
    title = str(result.get("headline", ""))[:240].strip()
    summary = str(result.get("summary", ""))[:600].strip()
    if len(title) < 12 or len(summary) < 50:
        raise NewsroomError("AI returned insufficient content")
    paragraphs = result["paragraphs"]
    body = "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
    with transaction.atomic():
        candidate = StoryCandidate.objects.select_for_update().select_related("source").get(pk=candidate.pk)
        if candidate.status != "queued":
            return candidate.article
        news_index = NewsIndexPage.objects.first()
        if not news_index:
            raise NewsroomError("Run bootstrap_site first")
        page = news_index.add_child(instance=ArticlePage(
            title=title, slug=article_slug(title, candidate.url), kind="editorial", live=False,
            category=candidate.source.category, summary=summary, body=body,
            source_name=candidate.source.name, source_url=candidate.url,
            byline=settings.SITE_NAME + " News Desk", ai_assisted=True,
        ))
        revision = page.save_revision()
        publish = settings.NEWSROOM_AUTO_PUBLISH and candidate.source.auto_publish and not warnings
        if publish:
            revision.publish()
        candidate.article = page
        candidate.status = "published" if publish else "draft"
        candidate.error = "; ".join(str(w)[:300] for w in warnings)[:1000]
        candidate.save(update_fields=["article", "status", "error"])
        return page

def run_newsroom():
    stats = {"new_candidates": 0, "drafted": 0, "errors": 0}
    for source in FeedSource.objects.filter(is_active=True):
        try:
            stats["new_candidates"] += collect_feed(source)
        except Exception as exc:
            logger.exception("Failed collecting feed id=%s", source.pk)
            source.last_error = str(exc)[:900]
            source.last_checked_at = timezone.now()
            source.save(update_fields=["last_error", "last_checked_at"])
            stats["errors"] += 1
    if settings.GROQ_API_KEY:
        candidates = StoryCandidate.objects.filter(status="queued").select_related("source").order_by("created_at")[:settings.NEWSROOM_ITEMS_PER_RUN]
        for candidate in candidates:
            try:
                draft_candidate(candidate)
                stats["drafted"] += 1
            except Exception as exc:
                logger.exception("Failed drafting candidate id=%s", candidate.pk)
                candidate.error = str(exc)[:900]
                candidate.save(update_fields=["error"])
                stats["errors"] += 1
    return stats
