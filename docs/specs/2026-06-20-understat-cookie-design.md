# Understat Live via Cloudflare Cookie (Phase 8)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the Understat provider.

---

## Why

Understat is behind Cloudflare; plain HTTP, cloudscraper, and headless Chromium all
get a dataless shell or a CAPTCHA (verified). The one path that can work for a
personal app: the user solves Cloudflare **once in their real browser**, then the
app reuses that session via the **`cf_clearance` cookie** + the matching
**User-Agent**. Cloudflare ties the clearance to the IP + UA that solved it, so
sending the same cookie/UA from the local app can pass.

## Honest caveats (documented in the UI + README)

- The cookie **expires** (~30 min – a few hours) → re-paste when live mode errors.
- It's **IP + User-Agent bound** → the UA must match the browser that got it, and
  the app must run on the same network.
- Cloudflare may still block on **TLS fingerprint** even with a valid cookie; if so,
  **Manual entry** remains the reliable fallback. This feature is best-effort.

## Design (small, mostly in the existing provider)

`data/understat.py`:
- `parse_cf_clearance(raw) -> str` — accept either a bare cf_clearance value or a
  full `document.cookie` string and extract the `cf_clearance` token.
- `build_request_kwargs(cf_clearance=None, user_agent=None) -> dict` — returns
  `{"headers": {...}, "cookies": {...}}`: a sensible default User-Agent (over_
  ridden by the caller's), and a `cf_clearance` cookie when supplied. **Pure and
  unit-tested.**
- `UnderstatProvider(__init__)` gains `cf_clearance=None, user_agent=None`; the
  fetch uses `requests.get(url, **build_request_kwargs(...), timeout=...)`.

`app.py` (Understat live branch):
- Two inputs — **Cloudflare cookie** (`cf_clearance`) and **User-Agent** — with a
  caption pointing at the README steps; passed into the provider.
- The existing "live blocked" error message stays as the fallback hint.

## Out of scope
- Automating the cookie capture (that's the headless-browser path, which fails).
- Persisting the cookie across app restarts.

## Acceptance anchors (tests)
- `parse_cf_clearance` extracts the token from a full cookie string and passes a
  bare value through; raises on a string with no cf_clearance.
- `build_request_kwargs` with no args → default UA, no cookies; with cf_clearance →
  cookie present; with user_agent → that UA used.
- `UnderstatProvider` stores the cookie/UA and (verified via the kwargs builder)
  would send them. The live network fetch itself is not unit-tested (no network).
