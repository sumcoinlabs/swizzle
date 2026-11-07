# Swizzle v0.5 — working staging workflows

## Roles

`stageadmin` is a **staff** account. Log in at `/account/login/` and go to `/control/`. Staff sessions do not enter customer submission routes. Wagtail `/cms/` remains the rich article editor; Django `/staff/` is advanced maintenance only.

To simulate a **customer**, open a separate incognito/private browser window at `http://localhost:8988/account/register/`, register a different username, and use `/publisher/`. The staff session remains in the ordinary browser.

## Research newsroom

1. `/control/sources/` — three DGB official release feeds are enabled for private staging. Enable additional reviewed sources explicitly if desired.
2. "Scan now" fetches only the selected source, stores bounded headline/excerpt candidates; it cannot publish anything. The private Celery worker and beat optionally schedule subsequent scans every 15 minutes.
3. `/control/leads/` — convert a candidate into an **unpublished** source-based research outline, or an AI brief *only if a private Groq key is configured.*
4. `/cms/` — edit and verify source evidence, write original reporting, choose the news page and publish intentionally.

This is **not** the full DigiByte v0.6 research engine; the public v0.6 feed catalog and its cautious workflow principles are used, while deeper official-source evidence integration remains future work. No API key is copied from DigiByte. Initial staging `.env` has `GROQ_API_KEY=` and `NEWSROOM_ITEMS_PER_RUN=0`, therefore automatic AI drafting is disabled. Automatic public publishing is OFF.

## Paid PR staging demo — NO REAL MONEY

1. Customer registers in an incognito browser, creates a company, writes a release, and submits it.
2. Staff reviews company identity/authority at `/control/companies/` and records independent review notes.
3. Staff opens `/control/releases/`, clicks **Simulate $29 payment** — only enabled with `DJANGO_DEBUG=true` and `STAGING_DEMO_PAYMENTS=true`. It records an explicit `is_test_payment` flag; it does NOT generate a Stripe transaction or count as real revenue.
4. Staff reads the entire release and confirms editorial approval.
5. Staff deliberately clicks **Publish labeled release**. It appears on the public preview with the paid-PR disclosure.

Simulation cannot satisfy the release publication gate if staging test settings are switched off. **Never migrate this staging database or simulated paid releases into production.** Real Stripe remains disabled. Never enable the public site, accept actual customers, or treat mock payments as revenue.

## Server boundaries

All files under `/home/electrumbtc1/.swizzle-stage/`, all processes UID 1000, private service ports 8788/15488/16388, no root/sudo/Docker/PM2/Bitcoin changes. The original uninstall script remains `~/Downloads/swizzle-rootless-v03/staging/remove-from-mac.sh` on the Mac. It deletes all staging data: run only if you intend to remove the test application.
