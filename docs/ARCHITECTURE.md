# System architecture (working name: Swizzle)

## Purpose
This is a **single website with two separate editorial sources**:

1. Independent newsroom: staff-vetted RSS sources -> fact-constrained Groq drafts -> Wagtail editorial page/revision -> optional trusted-feed auto-publish when **both** switches enabled.
2. Third-party announcements: customer account -> organization -> release submission -> Stripe checkout -> verified webhook -> organization verification -> editorial approval -> labeled Wagtail publication.

They share presentation, search, RSS and sitemap infrastructure, but are distinguished by an immutable-in-practice `kind` field on published articles and conspicuous public disclosure.

## Runtime
Django 5.2 LTS + Wagtail 7.4 LTS, PostgreSQL, Celery + local Redis, Nginx + Gunicorn. No Docker, managed SQL, outbound SMTP, or custom frontend runtime required. At deploy time, all processes can run on a single adequately sized server; the source repo does not choose the server.

## Modules
- `home`: brand-neutral homepage
- `newsroom`: page models, RSS intake, Groq adapter and review queues
- `publishers`: accounts for organizations, plain-text releases, editorial verification and publication gate
- `billing`: Stripe Checkout and signed idempotent webhook fulfillment; reader subscriptions and hosted Stripe Billing Portal cancellation
- `accounts`: username/password login without SMTP
- `website`: public metadata, feeds, robots and Google News sitemap, ads and cache protection
- `config`: app settings, Celery schedule, routing

## Security boundaries
Readers never access Wagtail/Django staff dashboards without `is_staff`/permission checks. Company ownership is filtered by the logged-in user. Browser redirects never mark a press release paid. Only Stripe signed webhooks can update paid status. Staff approval, verified company, and settled payment are all required before publishing a customer release. Revenue data is never stored in cookies.

## Search and SEO
Rendered HTML includes visible article text without JavaScript, canonicals, JSON-LD, RSS, normal sitemap and 48h Google News sitemap for independent reporting. These features help crawlers understand content but do **not** guarantee ranking, news eligibility, traffic or distribution.

## Branding
`SITE_NAME`, `SITE_DOMAIN`, tagline and runtime assets are configurable. The Git repo and Django app labels intentionally do not encode a public product name. Rebranding does not require changing model names or URL routes; deploy domain changes with correct 301 redirects and Wagtail Site settings.

## DigiByte newsroom
The live DigiByteWallet.org website and user's private v0.6 engine **have not been read or modified by this project**. `newsroom.services` provides a compatible architectural seam for source polling and model generation. To reuse algorithms, extract and review individual modules from that engine locally after retrieving it from the Mac, subject to code ownership and licensing. Do not blindly copy production keys or deployment paths.
