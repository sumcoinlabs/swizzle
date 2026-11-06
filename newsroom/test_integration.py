"""Regression tests for draft visibility and the optional DGB v0.6 import bridge."""
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, SimpleTestCase, override_settings
from newsroom.management.commands.import_dgb_sources import parse_dgb_sources
from newsroom.management.commands.import_dgb_drafts import dgb_draft_rows
from newsroom.models import ArticlePage, FeedSource, StoryCandidate
from newsroom.services import draft_candidate


class BridgeParsingTests(SimpleTestCase):
    def test_dgb_public_source_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sources.json"
            path.write_text(json.dumps([{"name": "Releases", "url": "https://github.com/example/repo/releases.atom", "kind": "release"}]))
            self.assertEqual(len(parse_dgb_sources(path)), 1)
            path.write_text(json.dumps([{"name": "Bad", "url": "https://127.0.0.1/private", "kind": "news"}]))
            with self.assertRaises(ValueError):
                parse_dgb_sources(path)

    def test_sqlite_import_reads_only_expected_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stories.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE stories (id TEXT, title TEXT, url TEXT, kind TEXT, source TEXT, summary TEXT, status TEXT)")
                db.execute("CREATE TABLE drafts (story_id TEXT, content TEXT, generated_at TEXT)")
                db.execute("INSERT INTO stories VALUES (?,?,?,?,?,?,?)", ("story1", "New release", "https://example.com/release", "release", "Example", "Summary", "drafted"))
                db.execute("INSERT INTO drafts VALUES (?,?,?)", ("story1", json.dumps({"title": "A new example release", "body": "Evidence is pending human review."}), "2026-11-06"))
            self.assertEqual(len(list(dgb_draft_rows(path))), 1)
            self.assertEqual(list(dgb_draft_rows(path))[0][1]["title"], "A new example release")


class DraftVisibilityTests(TestCase):
    @override_settings(NEWSROOM_AUTO_PUBLISH=False)
    @patch("newsroom.services.generate_ai_brief")
    def test_ai_draft_is_not_publicly_visible(self, generate):
        call_command("bootstrap_site", verbosity=0)
        generate.return_value = {"headline": "Official project publishes an update", "summary": "A source-attributed update without independent verification in this example.",
                                 "paragraphs": ["According to the project, an update exists.", "Details should be checked against the linked source."], "warnings": []}
        feed = FeedSource.objects.create(name="Official", url="https://example.com/feed.xml", is_active=True)
        candidate = StoryCandidate.objects.create(source=feed, url="https://example.com/story1", headline="Some headline", excerpt="Source excerpt")
        page = draft_candidate(candidate)
        page.refresh_from_db()
        self.assertFalse(page.live, "An AI draft MUST NOT be published by Wagtail's default-live behavior")
        self.assertFalse(ArticlePage.objects.live().filter(pk=page.pk).exists())
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "draft")

    def test_rss_and_sitemap_do_not_crash(self):
        call_command("bootstrap_site", verbosity=0)
        response = self.client.get("/rss/editorial/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
