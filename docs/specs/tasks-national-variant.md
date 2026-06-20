# Tasks — World Cup / National-Team Variant (Phase 6)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [x] W1  `national.py` — `elo_to_lambdas` + SAMPLE_ELO table (TDD)
- [x] W2  `national.py` — `predict_international` assembling markets from Elo λ (TDD)
- [x] W3  `national.py` — CLI (`python -m jackpot.national`) + README section
- [x] W4  Full suite green; spec/tasks committed

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- `python -m jackpot.national "Brazil" "Croatia"` prints a prediction
