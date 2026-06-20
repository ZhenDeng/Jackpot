# Tasks — Manual Input Mode (Phase 4)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [x] N1  `data/manual.py` — `build_manual_match(...)` builder + validation (TDD)
- [x] N2  `app.py` — "Manual entry" data source: number inputs + optional players table
- [x] N3  `app.py` — AppTest smoke for manual mode (renders + predicts)
- [x] N4  Docs: README "try a real match" section; friendlier live-source error; suite green

## Done criteria
- All boxes checked
- `pytest` green (existing 109 + new)
- No open CRITICAL/HIGH review findings
- App renders Manual entry mode and produces a prediction
