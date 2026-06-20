# Tasks — Player Props (Phase 2)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [x] P1  `players.py` — player goal model: shares, λ allocation (+penalty), P(score), P(2+) (TDD)
- [x] P2  Data model: `PlayerForm` + `TeamForm.squad` in `data/base.py` (TDD)
- [x] P3  `SampleDataProvider` squads for offline demo + tests (TDD)
- [x] P4  `predict.py` — add `player_props` to output, graceful when squads absent (TDD)
- [x] P5  `UnderstatProvider` — parse `playersData`, attach squads to teams (parser TDD)
- [x] P6  `app.py` — Goalscorers tab (home/away columns) + AppTest smoke (TDD)
- [x] P7  Docs: README player-props note + fix `PYTHONPATH` run command; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing 68 + new)
- No open CRITICAL/HIGH review findings
- App renders a Goalscorers tab from SampleDataProvider
