"""Explicit, read-only DGB v0.6 SQLite -> unpublished Wagtail draft importer."""
import json
import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import escape
from newsroom.models import ArticlePage, NewsIndexPage, article_slug


def dgb_draft_rows(path, limit=20):
    """Read a *user-provided export* as read-only; never open or mutate live upstream files."""
    path = Path(path).expanduser().resolve()
    if not path.is_file() or not 1 <= limit <= 200:
        raise ValueError("Provide a local SQLite export file and limit from 1 to 200")
    uri = path.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as db:
        db.row_factory = sqlite3.Row
        query = """SELECT s.id, s.title, s.url, s.kind, s.source,
                   s.summary, d.content FROM stories s
                   JOIN drafts d ON d.story_id = s.id
                   WHERE s.status != 'dismissed'
                   ORDER BY d.generated_at DESC LIMIT ?"""
        for r in db.execute(query, (limit,)):
            row = dict(r)
            try:
                draft = json.loads(row.pop("content"))
            except (TypeError, ValueError):
                continue
            if isinstance(draft, dict):
                yield row, draft


def plain_html(markdown_text):
    """Conservative plain paragraphs; no raw customer/AI HTML is trusted."""
    import re
    chunks = re.split(r"\n\s*\n", markdown_text)
    return "".join(f"<p>{escape(chunk.strip())}</p>" for chunk in chunks if chunk.strip())


class Command(BaseCommand):
    help = "Preview or explicitly import DGB v0.6 editorial drafts as UNPUBLISHED pages"

    def add_arguments(self, parser):
        parser.add_argument("path", help="Local, intentionally exported DGB stories.sqlite3")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--apply", action="store_true", help="Create unpublished Wagtail drafts (disabled by default)")

    def handle(self, *args, **opts):
        try:
            rows = list(dgb_draft_rows(opts["path"], opts["limit"]))
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise CommandError(f"Could not read source export: {exc}") from exc
        if not opts["apply"]:
            self.stdout.write(f"DRY RUN: {len(rows)} local DGB draft(s) found; pass --apply for unpublished imports")
            return
        index = NewsIndexPage.objects.first()
        if not index:
            raise CommandError("Run bootstrap_site before importing drafts")
        made = 0
        for story, draft in rows:
            title = str(draft.get("title") or story["title"] or "")[:240].strip()
            summary = str(draft.get("summary") or story["summary"] or "")[:600].strip()
            text = str(draft.get("body") or "")[:30000].strip()
            url = str(story.get("url") or "")[:1200]
            if len(title) < 12 or not text or not url.startswith("https://"):
                continue
            slug = article_slug(title, "dgb-export:" + str(story["id"]))
            if ArticlePage.objects.filter(slug=slug).exists():
                continue
            with transaction.atomic():
                page = index.add_child(instance=ArticlePage(
                    title=title, slug=slug, live=False,
                    kind="editorial", category="crypto", summary=summary or title,
                    body=plain_html(text), byline="Editorial desk — imported working draft",
                    source_url=url, source_name=str(story.get("source") or "Original source")[:180],
                    ai_assisted=bool(draft.get("ai_generated")),
                ))
                page.save_revision()
                made += 1
        self.stdout.write(self.style.SUCCESS(f"Created {made} UNPUBLISHED Wagtail drafts; editorial review required"))
