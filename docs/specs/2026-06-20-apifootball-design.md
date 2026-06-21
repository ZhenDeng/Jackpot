# API-Football Integration (Phase 9)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the swappable `MatchDataProvider` data layer.

---

## Why

Understat is Cloudflare-blocked. API-Football (api-sports.io) is an official,
ToS-clean API: one key covers all top leagues **and** the World Cup, with team
stats, and a **free tier (100 requests/day)** — enough for a personal app. It slots
into the existing `MatchDataProvider` interface with no engine changes.

## Design

A new provider that reads team form from the **`/standings`** endpoint — one call
per league returns every team's id, name, games played, and goals for/against, so a
single request powers both `list_teams` and `get_match` (kind to the free tier).

```
data/apifootball.py
  api_football_league_id(name) -> int        # EPL=39, La Liga=140, Serie A=135,
                                             # Bundesliga=78, Ligue 1=61, World Cup=1
  parse_standings(json) -> {team: {scored_per_game, conceded_per_game, matches}}
  compute_league_avg(parsed) -> float        # match-weighted
  class ApiFootballProvider(MatchDataProvider):
      __init__(api_key, season=2024)
      _request_headers() -> {"x-apisports-key": api_key}   # never logged
      _load_league(league) -> fetch /standings, parse, cache
      list_teams(league); get_match(home, away, league)
```

Endpoint: `GET https://v3.football.api-sports.io/standings?league={id}&season={year}`
with header `x-apisports-key: <key>`. Response shape (v3):
`response[0].league.standings[0]` is a list of entries, each with `team.id`,
`team.name`, `all.played`, `all.goals.for`, `all.goals.against`.

Per team: `scored_per_game = all.goals.for / all.played`,
`conceded_per_game = all.goals.against / all.played`, `matches = all.played`.
`uses_xg = False` (standings carries goals, not xG — the strength model's shrinkage
handles goal-based form). League average is the match-weighted mean.

## v1 scope vs follow-ups

**This phase (v1):** team form → the full goals-driven Tab (1X2, O/U, BTTS, correct
score, double chance, DNB, **team props**). No new engine code — markets already
derive from the matrix.

**Documented follow-ups (not this PR):**
- **xG** per team (aggregate `/fixtures/statistics` `expected_goals`) → set `uses_xg`.
- **Player props** from `/players` (per-player stats).
- **Corners/cards** from `/fixtures/statistics` → auto-fill the count-props.
- **Odds** from `/odds` → auto value flags.

## UI

`app.py`: add **"API-Football (live)"** to the data-source radio with an **API key**
(masked) + **season** input. Team-list fetch is **gated until a key is entered**
(no wasted calls), with a clear error + Manual-entry fallback hint on failure.

## Error handling

API-Football returns a 200 with a non-empty `errors` field on bad requests/quota.
`parse_standings` raises `ValueError` when `response` is empty; the provider surfaces
a readable message (caught by the UI).

## Acceptance anchors (tests)
- `api_football_league_id` maps the 5 leagues + World Cup; unknown raises KeyError.
- `parse_standings(sample)` computes correct per-game rates and matches; raises on an
  empty/error response.
- `compute_league_avg` is match-weighted (more-played teams weigh more).
- Provider builds correct `TeamForm`/`MatchData` from a pre-populated cache (no
  network); `_request_headers` carries the key; `__repr__` masks it.
- Unknown team in a league raises a clear KeyError.
