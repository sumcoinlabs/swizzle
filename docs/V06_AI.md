# Swizzle v0.6 — audited DigiByte newsroom research integration

Source project: https://github.com/sumcoinlabs/dgb-newsroom-engine, pinned at `b9a6adf562add90672f556ae226926c9aa87db98`. The Mac installer copies the **unchanged** `ai_writer.py`, `editorial.py`, `newsroom_v06.py` and `artwork_v06.py` into `newsroom/dgb_v06/` as audited vendor modules. Those are user-owned source modules, not a running second DigiByte service. The full DGB `engine.py` HTTP/SQLite process is intentionally **not** installed or launched; Swizzle already has its own Django/Wagtail/PostgreSQL pipeline.

Integration features:
- DGB topic, priority and automatic eligibility scoring, including original feed publication times
- Primary GitHub release/commit/PR evidence retrieval from source-allowlisted repositories
- DGB article validation, cautious source-linked writing, private editor verification flags
- Conservative request/token reservations, failed-attempt accounting and bounded Groq usage
- Original artwork module vendored for subsequent Wagtail illustration integration (no art is produced by this phase)
- Staff-only research/usage dashboard with a no-generation API key connection check

Not integrated: DGB's private editor session UI, SQLite database, Google analytics connector, and its DigiByte-specific live publisher. No credentials, existing drafts, or DigiByte production services are copied or accessed.

## Activation

Use the in-place Mac upgrade first. Create an API key at https://console.groq.com/keys and enter it using the secure Mac command in the release package. It is stored only under `/home/electrumbtc1/.swizzle-stage/private/groq.key`, owned by `electrumbtc1`, mode `0600`. The `.env` contains only the key-file path and model name. **Never paste the key into chat or GitHub.**

Open `/control/ai/` and select **Verify API connection**. Open `/control/sources/` to monitor official sources and `/control/leads/` to select a specific primary-source lead and create an AI draft. The first live call requires model access and is counted against a daily conservative budget. AI drafts are always saved unpublished in Wagtail and must be manually verified.

The scheduled feed scans continue running; auto-drafting and auto-publication remain OFF, and real payments remain disabled. No external paid fallback. If the key is rejected or rate limited, the draft is not created and the usage reservation is retained.

## Security

No sudo, root processes, background copy of keys or migrations of the DigiByte database. All runtime files stay within the existing staging prefix. The original rootless uninstall remains responsible for removing staging. Existing simulated $29 paid releases remain unaffected.
