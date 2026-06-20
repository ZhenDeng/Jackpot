# Tasks — Understat Live via Cloudflare Cookie (Phase 8)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [ ] K1  `understat.py` — parse_cf_clearance + build_request_kwargs (TDD)
- [ ] K2  `understat.py` — UnderstatProvider accepts cf_clearance/user_agent, uses them (TDD)
- [ ] K3  `app.py` — Cloudflare cookie + User-Agent inputs in the live branch
- [ ] K4  README "make Understat live work" section (cookie steps + caveats); suite green

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- App shows cookie inputs in Understat (live) mode
