# Which Swizzle interface is which?

**Public website** `/` — brand-neutral newspaper homepage. `/news/` lists independent stories and labeled press releases. `/search/` searches articles.

**Publisher dashboard** `/publisher/` — self-service customer experience. Register via `/account/register/`, create a company, submit a release, pay (only after payments are enabled), follow editorial review, share the published URL. A staff administrator may test this interface, but it is not the staff control center.

**Newsroom Control Center** `/control/` — the **staff-only** daily front door. Summarizes the editorial and press release review queues, pending company verification, and news feed status. It links to editing tools. No payment or publishing mutations happen on this page.

**Wagtail editorial CMS** `/cms/` — used by editors for creating, editing, reviewing, and publishing actual articles. Underlying publishing tool, not a second business dashboard.

**Django advanced database admin** `/staff/` — low-level administration of data records, permissions, sources, companies and payments. Not designed as a customer or editor experience. Access from the Control Center only when necessary.

## Current staging limitations

This preview has no automated publishing, no production AI credentials, no live payment collection, and no public domain. The 35 imported DigiByte sources remain inactive. The GitHub public v0.6 source code is not yet a running integrated background engine in this Swizzle staging installation.

## Removal

The original rootless v0.3 uninstall remains valid. From the Mac (with the v0.3 ZIP extracted), run:

`bash ~/Downloads/swizzle-rootless-v03/staging/remove-from-mac.sh`

It destroys ALL Swizzle staging state under `/home/electrumbtc1/.swizzle-stage/` after ownership/process checks, and does not alter the Bitcoin server's other services. Do not use for an upgrade.
