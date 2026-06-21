# Same Game Multi (SGM) — Design

**Date:** 2026-06-21
**Status:** implemented

## Goal

Add an **SGM** tab that combines the highest-confidence legs from a single match
into one multi (parlay), with a combined fair price. Works for both the club
(`predict`) and World Cup (`predict_international`) paths, which share the same
`markets` output shape.

## Leg selection

"Highest confidence" = highest probability. To keep legs distinct and avoid
nesting the same event twice (e.g. Over 1.5 *and* Over 2.5), we take the single
most probable selection from each distinct market **dimension**:

| Dimension          | Source market        | Selection picked          |
|--------------------|----------------------|---------------------------|
| Result             | `double_chance`      | best of 1X / 12 / X2      |
| Match goals        | `over_under`         | best over/under line+side |
| Both teams to score| `btts`               | Yes or No                 |
| Home team goals    | `team_total_goals`   | best home over/under      |
| Away team goals    | `team_total_goals`   | best away over/under      |

Candidates are ranked by probability; the top `n` (default 4) form the SGM. Five
dimensions are always available, so ≥4 legs are guaranteed.

## Combined price

`combined_prob = product(leg probabilities)`; `combined_fair_odds = 1 / combined_prob`.

**Correlation caveat:** legs in one game are not independent, so the product is an
*optimistic* combined probability and the fair odds are a **floor** — a real SGM
price will be shorter. Surfaced in the UI caption.

## Surfaces

- `jackpot.sgm.same_game_multi(markets, home, away, n=4)` — pure function.
- `app.py` — first tab ("SGM"): per-leg rows + combined probability / fair odds
  metrics + correlation caveat.

## Tests

- `tests/test_sgm.py` — unit (ordering, one-leg-per-dimension, product math,
  `n` capping, `n<1` rejection, real `predict()` output).
- `tests/test_app_smoke.py::test_app_renders_same_game_multi` — UI smoke.
