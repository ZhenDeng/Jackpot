# World Cup mode: Confidence + Goalscorers (Phase 13)

**Date:** 2026-06-21
**Status:** Approved for build

---

## Problem

In **World Cup (national)** mode the prediction Tab shows two empty sections:
- **Confidence** renders "—" (because `predict_international` returns `confidence: None`).
- **Goalscorers** is empty (World Cup mode collects no squad data, so `player_props`
  is empty).

## Fix

### 1. Meaningful confidence for the Elo model
National predictions have no sample-size/xG basis like the club model, but the **Elo
gap** is a sound proxy for how decisive (predictable) the match is — a big mismatch is
a confident call, a near-even tie is genuinely a coin-flip. International football is
high variance, so the thresholds are deliberately conservative.

`national.py`: `elo_confidence(elo_home, elo_away) -> "High"|"Medium"|"Low"` from
`abs(elo_home - elo_away)` (e.g. ≥250 → High, ≥100 → Medium, else Low).
`predict_international` returns this instead of `None`.

### 2. Optional player entry in World Cup mode
The Elo model already accepts `home_squad`/`away_squad` and produces goalscorer props.
World Cup mode just doesn't offer the input. Reuse the **manual-mode player table**:

- Extract the existing "Add key players" data-editor into a shared helper
  `player_table_inputs()` returning `(home_squad, away_squad)`.
- Call it in both the **Manual** and **World Cup (national)** branches.
- Pass the squads into `predict_international` so the **Goalscorers** tab populates.

No free national squad data exists, so this stays **user-entered** (consistent with
manual mode); omitted → graceful empty (unchanged).

## Out of scope
- Auto-fetching national squads / player xG (no free source).
- Changing the club-mode confidence.

## Acceptance anchors (tests)
- `elo_confidence`: big gap → High, moderate → Medium, even → Low; symmetric.
- `predict_international` returns a non-None confidence reflecting the gap; bigger gap
  is at least as confident.
- App: World Cup mode renders a confidence value (not "—") after Predict; with players
  entered, the Goalscorers tab populates (the entered striker appears).
- Manual mode's player table still works (no regression from the extraction).
