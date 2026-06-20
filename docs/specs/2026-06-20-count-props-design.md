# Corners & Cards (Count Props) — Phase 7

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the engine; uses manual input (the free-data gap blocks live corner/card data).

---

## Why & scope

Corners and cards were the one part of the originally-requested Tab we deferred:
the data is the blocker (Understat has no corners; cards need referee data; FBref is
Cloudflare-gated). So this phase models them from **manually entered rates** — the
reliable path. The maths is straightforward independent-Poisson count modelling,
separate from the goals score-matrix (corners/cards are their own counts).

Delivered as a **library + CLI** (`python -m jackpot.counts`); no changes to
`predict.py` or `app.py`, so it merges independently. UI integration is a follow-up.

## Model

Each side's expected count is a Poisson rate; totals are the sum of two
independent Poissons (= Poisson of the summed rate).

**Corners** — driven by attacking dominance:
```
lam_home = (home_corners_for + away_corners_against) / 2
lam_away = (away_corners_for + home_corners_against) / 2
```

**Cards** — driven by team discipline and, dominantly, the **referee**:
```
ref_factor = referee_cards_per_game / league_referee_avg   (1.0 if no referee given)
lam_home   = home_card_rate * ref_factor
lam_away   = away_card_rate * ref_factor
```

**Over/Under for a count** at a `.5` line (no push):
```
under = P(X <= floor(line)) = sum_{k=0..floor(line)} Poisson(k; lam)
over  = 1 - under
```

## Output

`counts.py`:
- `poisson_over_under(lam, line) -> {over, under}`
- `corners_markets(home_for, home_against, away_for, away_against, ...)` and
  `cards_markets(home_rate, away_rate, referee_cpg=None, league_ref_avg=..., ...)`
  → `{lambda_home, lambda_away, lambda_total, total:{line:{over,under}},
     home:{line:..}, away:{line:..}}`
- `secondary_markets(...)` → wraps both into `{corners, cards}` with each leaf a
  `{prob, fair_odds}` record (reusing `odds.fair_odds`).
- CLI: `python -m jackpot.counts` prints a corners + cards report from supplied or
  default rates.

## Out of scope
- Live corner/card data (data gap — manual only).
- Player card props (booking points) and first-corner markets.
- Streamlit UI tab (kept out to stay independent of the merged UI).

## Acceptance anchors (tests)
- `poisson_over_under` complements to 1; over rises with lam; matches a hand value
  (lam=2, line=1.5 → under = 3e^-2).
- Corners: the more attacking team gets the higher corner lambda; total = sum.
- Cards: a stricter referee (higher cpg) raises expected cards proportionally;
  ref_factor = 1 when no referee supplied.
- `secondary_markets` returns corners+cards with fair_odds = 1/prob; lines present.
- Validation: negative rates / non-positive league_ref_avg raise ValueError.
