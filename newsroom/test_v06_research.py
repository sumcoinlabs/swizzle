"""DGB v0.6 integration: primary evidence, quota, staff-only draft privacy."""
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from newsroom.models import ArticlePage, FeedSource, ResearchAttempt, ResearchReview, StoryCandidate
from newsroom.research_v06 import (
    ResearchBlocked, auto_candidate_eligible, research_and_draft, _safe_html,
)

GOOD_NOTE = 'Official release notes describe a stable software release and compatibility guidance. ' * 10
BODY = ('## Overview\n\n' +
    ' '.join(['The official project release describes software improvements and their practical implications for users.'] * 12) +
    '\n\n## Details\n\n' +
    ' '.join(['The repository identifies the release and provides technical notes, but independent testing remains necessary.'] * 12))


def official_response(_):
    return {
        'tag_name': 'v1.2.3', 'name': 'Release v1.2.3',
        'published_at': '2026-11-06T01:00:00Z',
        'draft': False, 'prerelease': False, 'body': GOOD_NOTE,
    }


def ai_response(_):
    return {'choices': [{'message': {'content': json.dumps({
        'title': 'Official software project publishes a new release with updates',
        'summary': 'According to the project release notes, a new version is available with documented changes and cautions for users.',
        'body': BODY, 'verify': ['Confirm release version and its publication status', 'Check software notes against the official repository'],
    })}}], 'usage': {'prompt_tokens': 800, 'completion_tokens': 900}}


@override_settings(GROQ_API_KEY='gsk_' + 'X' * 34, GROQ_MODEL='openai/gpt-oss-120b',
                   NEWSROOM_AUTO_PUBLISH=False, NEWSROOM_AUTO_DRAFT=False)
class DGBResearchIntegrationTests(TestCase):
    def setUp(self):
        call_command('bootstrap_site', verbosity=0)
        self.source = FeedSource.objects.create(
            name='Official test releases',
            url='https://github.com/official-team/test-repository/releases.atom',
            category='crypto', is_active=True,
        )
        self.lead = StoryCandidate.objects.create(
            source=self.source, url='https://github.com/official-team/test-repository/releases/tag/v1.2.3',
            headline='Official project announces a stable software update',
            excerpt='The official project released a version and provided documentation for compatibility and maintenance checks.',
        )

    def test_primary_evidence_creates_unpublished_wagtail_article(self):
        page = research_and_draft(self.lead, evidence_fetcher=official_response, caller=ai_response)
        self.assertFalse(page.live)
        self.assertFalse(ArticlePage.objects.live().filter(pk=page.pk).exists())
        self.assertEqual(ResearchAttempt.objects.filter(status='complete').count(), 1)
        self.assertEqual(ResearchAttempt.objects.first().reserved_tokens, 10000)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'draft')
        self.assertIn('repository', ResearchReview.objects.get(candidate=self.lead).evidence['original_url'])
        self.assertNotIn('human checks still required', page.body.lower())
        self.assertEqual(len(ResearchReview.objects.get(candidate=self.lead).verification), 2)

    def test_unknown_primary_link_is_rejected_without_spending_tokens(self):
        self.lead.url = 'https://github.com/unrelated/project/releases/tag/v1.2.3'
        self.lead.save(update_fields=['url'])
        with self.assertRaises(ResearchBlocked):
            research_and_draft(self.lead, evidence_fetcher=official_response, caller=ai_response)
        self.assertEqual(ResearchAttempt.objects.count(), 0)

    def test_invalid_ai_response_still_reserves_tokens(self):
        with self.assertRaises(ResearchBlocked):
            research_and_draft(self.lead, evidence_fetcher=official_response, caller=lambda _: {'choices': []})
        self.assertEqual(ResearchAttempt.objects.filter(status='failed').count(), 1)
        self.assertEqual(ResearchAttempt.objects.first().reserved_tokens, 10000)
        self.assertFalse(ArticlePage.objects.exists())

    @override_settings(NEWSROOM_AI_DAILY_REQUEST_LIMIT=1)
    def test_budget_prevents_second_api_request(self):
        research_and_draft(self.lead, evidence_fetcher=official_response, caller=ai_response)
        second = StoryCandidate.objects.create(
            source=self.source, url='https://github.com/official-team/test-repository/releases/tag/v2.0.0',
            headline='Official project releases another verified version', excerpt='A different release',
        )
        with self.assertRaises(ResearchBlocked):
            research_and_draft(second, evidence_fetcher=official_response, caller=lambda _: self.fail('Extra AI call made'))
        self.assertEqual(ResearchAttempt.objects.count(), 1)

    def test_no_unattended_draft_without_original_timestamp(self):
        self.assertFalse(auto_candidate_eligible(self.lead))

    def test_source_timestamp_is_separate_from_swizzle_first_seen(self):
        from django.utils import timezone
        self.lead.source_published_at = timezone.now()
        self.lead.save(update_fields=['source_published_at'])
        from newsroom.research_v06 import _story
        story = _story(self.lead)
        self.assertTrue(story['published'])
        self.assertNotEqual(story['published'], story['first_seen'])

    def test_escaped_html_from_model(self):
        result = _safe_html('## Section\n\n<script>alert(1)</script> message\n\n## Original source\n\n[repo](https://github.com/)')
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('https://github.com/', result)

    def test_staff_status_page_cannot_be_viewed_by_customer(self):
        customer = get_user_model().objects.create_user(username='regular_research_test', password='example-password-12345')
        self.client.force_login(customer)
        self.assertEqual(self.client.get(reverse('control_ai')).status_code, 302)
        staff = get_user_model().objects.create_superuser(username='staff_research_test', email='', password='example-password-12345')
        self.client.force_login(staff)
        self.assertContains(self.client.get(reverse('control_ai')), 'AI research operations')

    @patch('website.ai_control.requests.get')
    def test_model_key_probe_makes_no_completions(self, fake_get):
        resp = fake_get.return_value
        resp.status_code = 200
        resp.json.return_value = {'data': [{'id': 'openai/gpt-oss-120b'}]}
        staff = get_user_model().objects.create_superuser(username='staff_research_probe', email='', password='example-password-12345')
        self.client.force_login(staff)
        response = self.client.post(reverse('control_ai_probe'))
        self.assertRedirects(response, reverse('control_ai'))
        self.assertEqual(fake_get.call_count, 1)
        self.assertIn('/models', fake_get.call_args.args[0])
