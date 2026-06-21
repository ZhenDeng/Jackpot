# Context Factors + World Cup in the App (Phase 10)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the engine's `home_adjust`/`away_adjust` λ hooks and the national variant.

---

## Two features

1. **Context factors** — let real match context (weather, rest, key absences) nudge
   the prediction, as **transparent bounded levers** (not invented data).
2. **World Cup in the app** — add a national-team mode to the Streamlit dropdown so
   the Elo model is usable without the command line.

## Design principle (important)

Adding factors naively degrades a model. So every factor here is:
- **User-supplied** (you enter the real context — who's out, days rest), never guessed.
- **Bounded** — each multiplier is capped, and the combined adjustment is clamped to
  `[0.70, 1.30]` so no factor can dominate the goal model.
- **Optional & visible** — off by default; you see the resulting goal multiplier.
- **Tunable** — applies through the existing λ hooks, so the backtest harness can be
  extended to calibrate the magnitudes later.

Deep auto-lineup modelling (aggregating a full starting XI's xG) needs lineup data we
don't have free, so it stays a documented follow-up; the "key player out" toggles are
the honest, pragmatic version.

## Feature 1 — `context.py`

```
rest_factor(rest_days) -> float        # >=4 days: 1.0; fewer: down to ~0.92 at 1 day
compute_adjustments(
    weather_mult=1.0,
    home_rest=None, away_rest=None,
    home_attacker_out=False, away_attacker_out=False,
    home_defender_out=False, away_defender_out=False,
) -> (home_adjust, away_adjust)
```

- Weather multiplies **both** sides (shared pitch).
- Rest penalises the **fatigued** side's scoring.
- A key **attacker out** lowers that team's scoring (`×0.88`).
- A key **defender out** raises the **opponent's** scoring (`×1.10`) — modelled on the
  opponent's adjust, since defending maps to the other team's λ.
- Result clamped to `[0.70, 1.30]`.

These feed the engine's existing `MatchContext.home_adjust`/`away_adjust` (club modes)
and a new pair of params on `predict_international` (World Cup) — **no core engine
change**, just a new source for the multipliers.

## Feature 2 — `predict_international` gains adjustments

Add `home_adjust=1.0, away_adjust=1.0` params that scale the Elo-derived λ before the
matrix is built — parity with the club path so context factors work for nations too.

## UI (`app.py`)

- **New data source: "World Cup (national)"** — home/away nation text inputs, Elo
  number inputs (caption: get values from eloratings.net; a few samples shown), a
  **neutral venue** toggle (default on). Predict → `predict_international` → the same
  tabs. (Confidence metric shows "—" for nations; the renderer reads it defensively.)
- **"Advanced factors (optional)" expander** (all modes): rest days (home/away) and
  key attacker/defender-out checkboxes. Combined with the existing weather inputs via
  `compute_adjustments`, the resulting goal multipliers are shown and applied.

## Acceptance anchors (tests)
- `rest_factor`: full rest → 1.0; 1 day → ~0.92; monotonic; never below the floor.
- `compute_adjustments`: weather scales both; attacker-out lowers own side; defender-out
  raises the opponent; all-default → (1.0, 1.0); result clamped to [0.70, 1.30].
- `predict_international(home_adjust=…)`: raising home_adjust raises home win prob;
  defaults unchanged when omitted.
- App: "World Cup (national)" renders Elo inputs and produces a prediction (AppTest,
  no network); the Advanced-factors panel renders and a key-attacker-out lowers that
  team's expected goals end to end.
