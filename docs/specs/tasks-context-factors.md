# Tasks — Context Factors + World Cup in the App (Phase 10)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [x] F1  `context.py` — rest_factor + compute_adjustments (bounded, clamped) (TDD)
- [x] F2  `national.py` — predict_international accepts home_adjust/away_adjust (TDD)
- [x] F3  `app.py` — "World Cup (national)" data source: nation + Elo inputs, neutral toggle, renders tabs (AppTest)
- [x] F4  `app.py` — "Advanced factors" panel (rest, key player out) → compute_adjustments applied in all modes (AppTest)
- [x] F5  README factors + World Cup-in-app section; roadmap update; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- App offers "World Cup (national)" mode and an Advanced-factors panel
