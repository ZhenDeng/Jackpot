# Player Props — Anytime Goalscorer (Phase 2)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** `2026-06-20-soccer-prediction-design.md` (engine + 1X2/OU/BTTS).

---

## Goal

Add a **Player Props** market to the Tab: for each match, predict each player's
probability of scoring — **Anytime Goalscorer** and **2+ Goals** — with fair odds.

## Core idea — tie player goals to the team λ (consistency)

We already compute each team's expected goals (λ) from the Dixon–Coles model.
Player props **distribute that same team λ across the squad**, so the player
predictions are consistent with the team prediction (the players' expected goals
sum back to the team's λ).

### Model

For each player expected to feature:

```
raw_i      = xg_per90_i * (expected_minutes_i / 90)      # player's base output
share_i    = raw_i / sum_j(raw_j)                          # share of team attack
lambda_i   = share_i * team_lambda * (1 - PENALTY_FRACTION)
           + (team_lambda * PENALTY_FRACTION   if penalty taker else 0)
```

- A small fixed `PENALTY_FRACTION` (~0.08) of team goals are modelled as penalties
  and assigned to the designated **penalty taker** — a real, cheap signal.
- Conservation holds: `sum_i(lambda_i) == team_lambda`, so the props never
  contradict the team's expected goals.

Then, treating each player's goals as Poisson(λ_i):

```
P(scores >= 1) = 1 - e^(-lambda_i)
P(scores >= 2) = 1 - e^(-lambda_i) * (1 + lambda_i)
```

- **Expected minutes** scale a player down (a rotation risk / likely sub scores
  less). A player with 0 expected minutes is excluded.

## Data model additions

- `PlayerForm(name, xg_per90, expected_minutes=90.0, penalty_taker=False)`
- `TeamForm.squad: Optional[List[PlayerForm]]` — None when squad data is absent.
- Player props are computed **only for sides that have squad data**; absence
  degrades gracefully (that side's props are simply omitted) — never an error.

## Data sources

- **Understat** already embeds `playersData` (per-player xG, shots, minutes) on the
  same league page we scrape for team xG — no new source needed.
- `SampleDataProvider` gains illustrative squads for the offline demo + tests.
- Penalty taker is not in Understat's basic feed → defaults to False (no boost)
  unless a provider supplies it. Documented limitation.

## Output

`markets.player_props` = `{"home": [...], "away": [...]}` where each entry is:

```
{ "player": str, "p_score": float, "p_2plus": float, "fair_odds": float }
```

sorted by `p_score` descending, top N per side.

## UI

New **Goalscorers** tab in `app.py`: two columns (home / away), each listing
players with Anytime % and fair odds; a caption when squad data is unavailable.

## Out of scope (still roadmap)

- Player shots / cards / assists props
- Team props (corners / cards) — corner data is the free-data gap
- World Cup national-team variant

## Acceptance anchors (tests)

- `P(score) == 1 - e^(-λ)`; 2+ formula correct.
- Player λ shares sum to the team λ (conservation).
- Higher xG/per-90 → higher score probability.
- Fewer expected minutes → lower probability.
- Penalty taker gets a boost over an identical non-taker.
- `predict()` includes `player_props` when squads present; omits a side cleanly
  when its squad is missing; never raises on absent squads.
- `SampleDataProvider` returns squads; `UnderstatProvider` parses `playersData`.
