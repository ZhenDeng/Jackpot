# Tasks — Player Props (Phase 2)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [ ] P1  `players.py` — player goal model: shares, λ allocation (+penalty), P(score), P(2+) (TDD)
- [ ] P2  Data model: `PlayerForm` + `TeamForm.squad` in `data/base.py` (TDD)
- [ ] P3  `SampleDataProvider` squads for offline demo + tests (TDD)
- [ ] P4  `predict.py` — add `player_props` to output, graceful when squads absent (TDD)
- [ ] P5  `UnderstatProvider` — parse `playersData`, attach squads to teams (parser TDD)
- [ ] P6  `app.py` — Goalscorers tab (home/away columns) + AppTest smoke (TDD)
- [ ] P7  Docs: README player-props note + fix `PYTHONPATH` run command; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing 68 + new)
- No open CRITICAL/HIGH review findings
- App renders a Goalscorers tab from SampleDataProvider
