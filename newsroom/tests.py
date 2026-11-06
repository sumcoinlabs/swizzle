from django.test import SimpleTestCase
from .models import article_slug

class SlugTests(SimpleTestCase):
    def test_stable_slugs_keep_sources_distinct(self):
        self.assertNotEqual(article_slug("Same story", "https://a.example/1"),
                            article_slug("Same story", "https://b.example/1"))
