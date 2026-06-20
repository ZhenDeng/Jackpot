# Team Props (Phase 3)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the engine spec + player-props phase.

---

## Goal

Add **team-level props** to the Tab — markets about a single team's outcome rather
than the match result.

## Scope decision (honest)

All props in this phase are **derived exactly from the existing score matrix**, so
they need **no new data**, can't contradict the other markets, and inherit the
engine's consistency guarantee:

- **Team Total Goals** — Over/Under per team (lines 0.5, 1.5, 2.5)
- **Clean Sheet** — each team keeps a clean sheet (opponent scores 0)
- **Win to Nil** — each team wins without conceding
- **Winning Margin** — home by 2+, by exactly 1, draw, away by 1, away by 2+

**Deferred (data gap):**
- **Corners** — Understat has no corner data; needs FBref scraping (separate phase).
- **Cards** — card rates are dominated by the **referee**, which the free feed
  lacks; shipping a cards model without it would be misleading.

## Math (from the score matrix `m[h][a]`)

- Home scores `k`: `Σ_a m[k][a]` (row sum). Away scores `k`: `Σ_h m[h][k]` (col sum).
- Team Total Goals Over `L` (home): `Σ_{k>L} rowsum(k)`.
- Home Clean Sheet = away scores 0 = `Σ_h m[h][0]`.
- Away Clean Sheet = home scores 0 = `Σ_a m[0][a]`.
- Home Win to Nil = `Σ_{h>=1} m[h][0]`.  Away Win to Nil = `Σ_{a>=1} m[0][a]`.
- Winning Margin: group cells by `h - a`.

## Output (`markets`)

- `team_total_goals`: `{ "home": {line: {over, under}}, "away": {...} }`
- `clean_sheet`: `{ "home": {prob,fair_odds}, "away": {...} }`
- `win_to_nil`: `{ "home": {...}, "away": {...} }`
- `winning_margin`: `{ "home_2plus", "home_1", "draw", "away_1", "away_2plus": {...} }`

(Each leaf is the standard `{prob, fair_odds, value}` record via `_outcome`.)

## UI

New **Team Props** tab in `app.py` with the four markets, home/away laid out
clearly. A caption notes corners/cards are out of scope for the free data stack.

## Acceptance anchors (tests)

- Team Total over/under complements to 1 per team; monotonic in the line.
- Home total Over 0.5 == 1 - P(home scores 0).
- Clean sheet (home) == P(away scores 0); equals matrix column-0... (away=0) sum.
- Win to Nil (home) <= min(Clean Sheet home, Home win); both <= 1.
- Winning-margin buckets sum to 1 and the draw bucket == 1X2 draw.
- `predict()` includes all four markets; values flagged only with market odds (none
  in scope here, so value defaults False).
