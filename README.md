# Swizzle — working repository name

**Brand-independent, self-hosted publishing platform.** One public news website combining independently sourced, AI-assisted editorial articles and competitively priced, clearly labeled paid press releases.

> **Status: development foundation, not production-approved.** No live domain, server, payment account, data import or DigiByte deployment has been configured. Do not accept real PR payments until security, refunds, legal notices, publisher verification, end-to-end checkout and compliance reviews are complete.

## Features implemented

- Django 5.2 LTS + Wagtail 7.4 LTS editorial CMS + PostgreSQL-backed persistent models
- Brand-neutral mobile-friendly website, category listings, full-text search, semantic article HTML
- Article/NewsArticle JSON-LD, canonical URLs, RSS feeds, XML and 48-hour Google News sitemap
- Independent newsroom pipeline: curated staff-controlled HTTPS RSS, dedupe, Groq JSON drafts, Wagtail revisions, explicit opt-in auto-publication
- Publisher portal: user registration/login with one-time offline recovery codes (no email dependency), company profiles, release submission, company authorization review, editorial review
- Stripe Checkout one-off release payment and idempotent signed webhooks; strict payment/identity/approval publication gate
- Stripe Checkout reader subscriptions and ad-free display logic; first-party dashboard notifications via Django messages
- AdSense hooks (disabled without your actual publisher IDs), optional Cloudflare Turnstile and responsive styling
- Celery/Redis background schedules, Gunicorn/systemd/Nginx templates, PostgreSQL+Redis GitHub Actions test workflow
- Private configuration through untracked `.env`; no hardcoded consumer-facing brand or domain

## Important limitations

- No live Stripe credentials, real transactions, domain, server or operational staff team yet; platform is **not** live.
- The **public** DigiByte v0.6 source lives at `sumcoinlabs/dgb-newsroom-engine`. Swizzle includes an optional, read-only import bridge for its vetted feed catalog and SQLite draft exports. It does not run the private DigiByte editorial service or change its production databases. See `docs/DGB_BRIDGE.md`.
- Wagtail News Starter Kit was evaluated as an architectural reference; this is an original Wagtail project rather than a verbatim copy of that template.
- No third-party distribution network, accepted OTC integrated newswire status, SEC filing, guaranteed Google News placement or automated verification of original financial disclosures.
- Public HTTP staging must **only** be accessed through an SSH tunnel; never enter credentials or activate Stripe on a publicly exposed plain-HTTP host.
- First setup generates migrations because no Python packages/PostgreSQL were available in the build environment. Commit reviewed migration files before a public deploy; CI exercises this bootstrap path.
- Regulatory text, automated fraud review, 2FA, comprehensive rate limiting, subscription self-service cancellation, refund workflows, company owner verification, policy pages and production monitoring must be finished before commercial launch.

## Local development (with local PostgreSQL)

```bash
bash scripts/setup_local.sh
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

The script creates untracked `.env` and installs Python dependencies; configure your own local PostgreSQL first. Visit `/` (public site), `/cms/` (Wagtail), `/staff/` (source feeds, company verification and paid publication), and `/publisher/` (customer portal). If you do not have Postgres running, you can still push the repository and let GitHub Actions run the integration tests.

## Running the editor automation

Add staff-vetted feed URLs at `/staff/newsroom/feedsource/` and explicitly enable them. Configure `GROQ_API_KEY`, then run `python manage.py poll_feeds`. The default is **draft only**. To permit automatic publication of narrowly sourced briefs, both `NEWSROOM_AUTO_PUBLISH=true` and the individual feed's `auto_publish` flag must be enabled. Always review accuracy and licensing considerations first.

## Changing the brand later

Edit `SITE_NAME`, `SITE_TAGLINE`, `SITE_DOMAIN`, `SITE_LANGUAGE` in `.env`, then update the Wagtail Site and eventual assets; source names, database schema, service names and internal repo do not need renaming. See `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md` and `docs/RELEASE_POLICY.md`.

## Licensing

Project-specific original code: MIT. Third-party dependencies retain their own licenses (including Wagtail under BSD-3-Clause). See `LICENSE`.


## User-facing routes

See [docs/NAVIGATION.md](docs/NAVIGATION.md). Staff work begins at `/control/`, editorial articles are authored in `/cms/`, and publishers use `/publisher/`. `/staff/` is advanced Django administration, not the normal dashboard.
