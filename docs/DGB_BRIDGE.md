# DigiByte v0.6 source bridge (opt-in, no production modifications)

Upstream: https://github.com/sumcoinlabs/dgb-newsroom-engine (public, maintained separately). Its v0.6 design has bounded-source research, draft-only publication, private verification notes and explicit human review.

Swizzle shares that *workflow principle*, not the original production database or private credentials. To import the upstream **public feed configuration**, clone the upstream repository into a separate directory (for example `~/Documents/dgb-newsroom-engine` on a Mac). Then in the Swizzle Django environment run:

```sh
python manage.py import_dgb_sources /path/to/dgb-newsroom-engine/sources.json
```

This imports configured sources as **inactive**, ready for staff to review. It does not make any network request or automatically collect them. The importer accepts only HTTPS public hostname URLs of the three known upstream kinds.

Optional **local, read-only** legacy draft import (only when you intentionally provide an exported copy of the private SQLite database):

```sh
python manage.py import_dgb_drafts /path/to/exported/stories.sqlite3
python manage.py import_dgb_drafts /path/to/exported/stories.sqlite3 --apply --limit 20
```

Without `--apply` this reports counts only. With `--apply` it creates **unpublished** Swizzle editorial drafts, never live pages, preserving their source URL and metadata as separate fields. It never copies or modifies the upstream SQLite file, and never auto-approves a draft. Imported content is **not verified**; staff must review each story. Only use a database export for which you have rights and understand the sensitivity. Do not commit SQLite, private drafts, or API keys to GitHub.

This is a controlled migration/adapter, not yet a runtime replacement for all features of the DigiByte engine (e.g. its editorial dashboard, source health metrics or artwork). Those remain separate until tested.
