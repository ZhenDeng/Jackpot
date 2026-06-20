# World Cup / National-Team Variant (Phase 6)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the engine + props phases.

---

## Why

National teams have **no league table** to derive attack/defense strength from, so
the club model's xG-based `estimate_strength` doesn't apply. International football
needs a different strength input: **Elo ratings** (free from eloratings.net,
academically more predictive than FIFA rankings). This phase adds an Elo-driven
path that produces λ, then reuses the **same score matrix and every market**.

## Core idea — Elo → λ, then the existing engine

```
dr        = elo_home - elo_away + (home_adv_elo if not neutral else 0)
supremacy = GOALS_PER_ELO * dr                 # expected goal difference
lam_home  = max(FLOOR, (total_goals + supremacy) / 2)
lam_away  = max(FLOOR, (total_goals - supremacy) / 2)
```

- World Cup matches are at **neutral** venues → `home_adv_elo = 0` by default.
- `total_goals` (~2.6 international baseline) and `GOALS_PER_ELO` are tunable
  constants (the backtest harness can later tune them on historical tournaments).
- λ then feeds `build_score_matrix` → all markets exactly as the club model does,
  so the Tab stays internally consistent.

## What this phase delivers (self-contained — no changes to predict.py/app.py)

`national.py`:
- `elo_to_lambdas(elo_home, elo_away, neutral=True, total_goals=2.6, ...) -> (λh, λa)`
- `predict_international(home, away, elo_home, elo_away, neutral=True,
   home_squad=None, away_squad=None, market_odds=None) -> dict` — builds the matrix
  from Elo-derived λ and assembles the markets (1X2, O/U, BTTS, correct score, team
  props, and player props when squads are supplied), reusing `markets.py`,
  `players.py`, and `odds.py`.
- A small bundled `SAMPLE_ELO` table of national teams so it runs offline / in tests.
- CLI: `python -m jackpot.national "Brazil" "Croatia"` prints a prediction (Elo
  looked up from the sample table, or pass `--elo` values).

## Player props for nations

Reuse the existing player model: aggregate club xG of the entered squad (the
manual `PlayerForm` list). Optional — omitted squads simply yield no goalscorer
props, exactly like the club path.

## Out of scope (later)
- Live Elo fetch (eloratings.net) and FBref national xG — manual/sample input now.
- Streamlit "World Cup" tab (kept out to stay independent of the open UI PRs).
- Group-stage simulation / tournament bracket.

## Acceptance anchors (tests)
- Equal Elo + neutral → λ_home == λ_away == total_goals / 2.
- Higher Elo team gets higher λ and is the 1X2 favourite; supremacy grows with the
  Elo gap.
- Non-neutral adds a home edge (λ_home up).
- λ never goes negative on huge Elo gaps (floor holds); λ sum ≈ total_goals when
  the floor isn't active.
- `predict_international` returns all core markets; probabilities are consistent
  (1X2 sums to 1, etc.); squads populate player props, omission is graceful.
- `SAMPLE_ELO` lookup works; unknown team raises a clear error.
