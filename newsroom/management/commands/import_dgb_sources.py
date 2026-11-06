"""Import public DGB v0.6 source catalog as inactive, staff-vetted Swizzle sources."""
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from newsroom.models import FeedSource


def parse_dgb_sources(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) > 100:
        raise ValueError("Expected a bounded list of source entries")
    sources = []
    seen = set()
    for row in data:
        if not isinstance(row, dict) or not {"name", "url", "kind"} <= set(row):
            raise ValueError("Unexpected source configuration")
        name, url, kind = row["name"], row["url"], row["kind"]
        if kind not in ("release", "development", "news") or not isinstance(name, str) or not 1 <= len(name) <= 180:
            raise ValueError("Invalid source name/type")
        if not isinstance(url, str) or len(url) > 2000:
            raise ValueError("Invalid source URL")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError("Expected an HTTPS feed URL with no credentials")
        try:
            ipaddress.ip_address(parsed.hostname)
        except ValueError:
            pass
        else:
            raise ValueError("IP literal feed hosts are not allowed")
        if parsed.hostname.lower() in ("localhost",) or parsed.hostname.lower().endswith((".local", ".internal")):
            raise ValueError("Local feed hosts are not allowed")
        if url in seen:
            raise ValueError("Duplicate feed URL")
        seen.add(url)
        sources.append({"name": name, "url": url, "category": "crypto"})
    return sources


class Command(BaseCommand):
    help = "Import public DigiByte newsroom v0.6 source catalog as INACTIVE sources"

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to public sources.json from dgb-newsroom-engine")

    def handle(self, *args, **opts):
        try:
            sources = parse_dgb_sources(opts["path"])
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(f"Invalid DGB source file: {exc}") from exc
        created = 0
        for src in sources:
            _, fresh = FeedSource.objects.get_or_create(url=src["url"], defaults={**src, "is_active": False})
            created += int(fresh)
        self.stdout.write(self.style.SUCCESS(f"Imported {created} inactive feed sources, {len(sources) - created} already present; enable only after review"))
