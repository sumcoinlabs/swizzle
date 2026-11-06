# Deployment checklist (server and domain not selected)

Do NOT deploy to DigiByte production just because it is available. First select the host and measure resources. Recommend at least 4 GiB RAM for PostgreSQL, Redis, Django, Gunicorn and one Celery worker; review actual load before co-hosting.

1. Provision Ubuntu and non-root `swizzle` user; install PostgreSQL 16+, Redis 7+, Nginx, Python 3.12/3.13 with venv, compiler packages as needed. Restrict PostgreSQL and Redis to localhost.
2. Copy the tested source into `/srv/swizzle/current`, install pinned-version-range requirements in `/srv/swizzle/venv` and create a database/limited database user.
3. Create private `/etc/swizzle.env` with a random `DJANGO_SECRET_KEY`, `DATABASE_URL`, allowed hosts, CSRF origins and production hostname. Never commit it.
4. Generate and **commit reviewed app migrations** to source control (`manage.py makemigrations`), then run `manage.py migrate`, `manage.py bootstrap_site` and `manage.py collectstatic --noinput`; create `createsuperuser`.
5. Enable `swizzle-web.service`, `swizzle-worker.service`, `swizzle-beat.service`. Confirm running and journal logs. Configure Nginx and TLS using the final domain, then update Wagtail Site hostname + canonical links.
6. Configure Cloudflare Turnstile for public sign-up and company submission. Production registration fails closed until a Turnstile secret is provided.
7. Create a Stripe account approved for the intended press-release/financial-media business; connect the webhook endpoint `/billing/stripe/webhook/` for `checkout.session.completed`, `customer.subscription.updated`, and `customer.subscription.deleted`. Add key, webhook signing secret, subscription Price ID.
8. Configure a real `ads.txt` seller line and AdSense client/slot IDs only after approval. Keep shared page caching off for authenticated users.
9. Set `NEWSROOM_AUTO_PUBLISH=false` until trusted sources, quality checks and staff workflow have been tested. Add sources in `/staff/newsroom/feedsource/` and activate individually. Start polling with `python manage.py poll_feeds` or Celery beat.
10. Test failed webhooks, retries, canceled checkouts, staff rejection, copyright complaints, robots/news sitemap and indexing. Set up Postgres backups off-host, log rotation, monitoring and security patching before production traffic.

**No domain / server now:** This repository can be pushed and CI-tested without configuring either. Stripe payment and subscription flows are deliberately disabled until keys are configured.
