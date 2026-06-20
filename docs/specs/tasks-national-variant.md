# Tasks — World Cup / National-Team Variant (Phase 6)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [ ] W1  `national.py` — `elo_to_lambdas` + SAMPLE_ELO table (TDD)
- [ ] W2  `national.py` — `predict_international` assembling markets from Elo λ (TDD)
- [ ] W3  `national.py` — CLI (`python -m jackpot.national`) + README section
- [ ] W4  Full suite green; spec/tasks committed

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- `python -m jackpot.national "Brazil" "Croatia"` prints a prediction
