# Remove the Understat data source — Design

**Date:** 2026-06-21
**Status:** implemented

## Goal

Remove the Understat live data source and all related code, tests, dependencies,
and docs. Understat is Cloudflare-gated (requires a hand-pasted `cf_clearance`
cookie), best-effort, and not licensed for non-personal use — the maintained live
path is **API-Football**, with **Manual entry** as the reliable fallback.

## Scope

Removed:

- `src/jackpot/data/understat.py` — the provider + parsing helpers
  (`parse_teams_data`, `understat_league_code`, `compute_league_avg`, cookie
  parsing). Imported only by `app.py`, so removal is self-contained.
- `app.py` — the `UnderstatProvider` import, the "Understat (live)" data-source
  option, the Cloudflare-cookie sidebar inputs, and the Understat-specific error
  branch. `get_provider` now always returns `SampleDataProvider`.
- Tests: `test_understat_cookie.py`, `test_understat_players.py`, and the
  Understat cases inside `test_runtime_providers.py` and `test_review_fixes.py`.
  The Understat cookie smoke test is replaced by one asserting Understat is no
  longer an offered data source.
- `requirements.txt` — `beautifulsoup4` and `lxml`, which were only present for
  the scraper (and were in fact unused — Understat parsed via regex/json).
- Docs: the Understat design + tasks specs, and all README references (data-source
  table, cookie how-to section, architecture map, spec list).

Kept (point-in-time history): other dated specs that merely *mention* Understat as
one of several sources are left unchanged.

## Result

Data sources are now: **Sample (offline)**, **Manual entry**, **API-Football
(live)**, **World Cup (national)**. The data-layer contract (`MatchDataProvider`)
is unchanged, so no engine code is affected.

## Tests

Full suite green after removal (259 tests). New: `test_app_smoke.py::
test_app_data_sources_exclude_understat` guards that the option is gone.
