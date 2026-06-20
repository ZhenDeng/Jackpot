# Manual Input Mode (Phase 4)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the engine + player/team props phases.

---

## Why

Live Understat scraping is blocked (Cloudflare now requires a JS browser). Manual
input mode lets the user **type a real fixture's numbers** and get a full
prediction immediately — no scraping, always works, good for trying a specific
upcoming match.

## Goal

A third data source, **Manual entry**, where the user enters team-level form (and
optionally a few key players) and the app builds a `MatchData` directly, feeding
the exact same engine and every Tab market.

## Inputs

Per team:
- Name
- Goals/xG **scored** per game
- Goals/xG **conceded** per game
- Matches played (drives shrinkage + confidence)

Match:
- League average goals per game
- (Existing optional) market odds → value flags + blend
- (Existing optional) weather → λ adjustment

Optional per team (for player props):
- A short list of key players: name, xG/90, expected minutes, penalty taker.
- If omitted, the Goalscorers tab degrades gracefully (already supported).

## Design

A pure builder in the data layer keeps the logic testable and the UI thin:

```
data/manual.py
  build_manual_match(home_name, home_scored, home_conceded, home_matches,
                     away_name, away_scored, away_conceded, away_matches,
                     league_avg, home_squad=None, away_squad=None,
                     market_odds=None) -> MatchData
```

- Validates inputs (non-empty names, non-negative rates, matches >= 1,
  league_avg > 0); raises `ValueError` with a clear message otherwise.
- `*_squad` is an optional list of `PlayerForm` (or tuples coerced to one).
- Returns a standard `MatchData` — identical to what the providers produce, so the
  engine and all markets work unchanged.

## UI

`app.py`: add **"Manual entry"** to the data-source radio. When selected, the
sidebar swaps the team selectboxes for number inputs (two columns: home / away)
plus a league-average input, and an optional players table per team
(`st.data_editor`). Market-odds and weather sections stay shared. **Predict**
calls `build_manual_match(...)` then `predict(...)`.

## Out of scope

- Persisting entered matches
- Auto-filling numbers from any source (that's the live-scraping / Playwright phase)

## Acceptance anchors (tests)

- `build_manual_match` returns a `MatchData` whose `predict()` runs and yields all
  markets.
- Stronger home inputs → home favourite.
- Squads passed through → player props populated; omitted → empty (no error).
- Validation: empty name, negative rate, zero matches, non-positive league_avg all
  raise `ValueError`.
- Market odds passed through → value flags available.
- UI: Manual entry mode renders inputs and produces a prediction (AppTest).
