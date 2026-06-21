# Player "to score or assist" (goal involvement) — Design

**Date:** 2026-06-21
**Status:** implemented

## Goal

Change the player prop from **anytime goalscorer** to **anytime goalscorer or
assist** (goal involvement). Per the chosen option, involvement is the *primary*
number; the pure anytime-scorer % is kept as a secondary detail.

## Model

Each player gets two independent Poisson rates for the match:

- **Goal rate** `λ_goal` — their xG/90 share of the team's expected goals (existing).
- **Assist rate** `λ_assist` — their xA/90 share of the team's *assist pool*.

The team assist pool is `team_lambda × ASSIST_FRACTION`, where `ASSIST_FRACTION =
0.75` (the typical share of goals that are assisted). Assist rates are allocated
across players by xA/90 × minutes, with **no penalty pool** (penalties aren't
assisted).

**P(score or assist)** = `1 − e^(−(λ_goal + λ_assist))`.

This treats a player's goals and assists as independent Poisson processes. The
slight negative correlation within a single goal (the scorer and assister differ)
is ignored — a standard, well-behaved approximation. With `xA/90 = 0` it reduces
exactly to the previous anytime-scorer probability, so absence of assist data is a
clean fallback.

## Inputs

- `PlayerForm` gains `xa_per90: float = 0.0`.
- Manual + World Cup player table gains an **"xA/90"** column (blank → 0).
- Sample squads get illustrative xA/90 values.
- **Live (Understat) path unchanged:** it supplies no assists, so `xa_per90`
  defaults to 0 and the prop stays scorer-only there (no behaviour change).

## Output

Each player-prop entry becomes:

```
{player, p_involve, fair_odds_involve, p_score, p_2plus, fair_odds}
```

`fair_odds_involve = 1 / p_involve`; `fair_odds = 1 / p_score` (kept). Entries are
sorted by `p_involve` descending (the new primary metric).

## UI

Goalscorers tab → **"Goals & Assists"**. Per player:

```
{player} — {p_involve}% to score or assist  (odds X)  ·  scorer {p_score}%  ·  2+: {p_2plus}%
```

Caption updated to describe involvement and note that assists come from the xA/90
column.

## Components

- `jackpot.players` — add `p_involvement(goal_lambda, assist_lambda)`,
  `ASSIST_FRACTION`; reuse `allocate_lambdas(..., penalty_fraction=0.0)` for assists.
- `jackpot.data.base.PlayerForm` — add `xa_per90`.
- `jackpot.data.manual.rows_to_squad` — parse `xA/90`.
- `jackpot.predict._player_props` / `jackpot.national._player_props` — compute
  assist lambdas + involvement, reshape entries, sort by `p_involve`.
- `jackpot.app` — xA/90 input column; render involvement-primary rows.

## Tests

- `tests/test_players.py` — `p_involvement` formula, monotonicity, `=p_score`
  when assists are 0; assist allocation conservation.
- `tests/test_predict_player_props.py` / `test_predict_international.py` — new
  entry shape, sort by `p_involve`, involvement ≥ scorer.
- `tests/test_player_data.py` — `PlayerForm.xa_per90` default + field.
- `tests/test_manual.py` (or new) — `rows_to_squad` parses `xA/90`.
- `tests/test_app_smoke.py` — tab shows "score or assist".
