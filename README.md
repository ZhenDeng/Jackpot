# ⚽ Jackpot — Soccer Bet Prediction

Predict every item in a bet **Tab** — Match Result (1X2), Over/Under, BTTS,
Correct Score, Double Chance, Draw No Bet, and **Anytime Goalscorer** player props
— for a soccer match, from a single consistent goal model.

## How it works

One engine, one source of truth. Instead of modelling each market separately, it
estimates each team's **expected goals (λ)** for the specific match, builds a
**score-probability matrix** (bivariate Poisson + Dixon–Coles low-score
correction), and derives every market by summing the relevant cells. So the whole
Tab is mathematically consistent — Over 2.5 and Home Win can never contradict.

Key modelling choices:

- **xG-based strength** — team attack/defense from expected goals, which predict
  future goals better than past goals (falls back to goals when xG is missing).
- **Shrinkage** — small samples (early season, promoted teams) regress toward the
  league average so estimates stay sane.
- **Time decay** — recent matches weigh more.
- **Dixon–Coles correction** — fixes Poisson's under-count of 0-0 / 1-1 draws.
- **Market blending (optional)** — blend model with margin-stripped bookmaker
  odds; flag **value** where the model materially beats the market.
- **Honest confidence** — lower when data is thin.

## Data sources (free / personal stack)

| Need | Source | Cost |
| --- | --- | --- |
| Team & player xG (top-5 leagues) | Understat (scrape) | €0 |
| Weather → λ adjustment | OpenWeatherMap | €0 |
| Offline demo / tests | bundled `SampleDataProvider` | €0 |

> Scraping Understat is fine for personal use but is **not** licensed for
> commercial products. See `docs/specs/`.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# run the app (works offline with the bundled sample data)
PYTHONPATH=src .venv/bin/streamlit run src/jackpot/app.py
```

In the sidebar: pick the data source (start with **Sample (offline)**), a league
and two teams, optionally enter bookmaker odds to enable value flags, then
**Predict**.

## Tests

```bash
.venv/bin/pytest
```

The prediction engine is pure standard library (no NumPy/SciPy), so the test
suite is deterministic and fast.

## Layout

```
src/jackpot/
  poisson.py    matrix.py    markets.py    odds.py      # engine
  strength.py   lambdas.py   players.py   predict.py    # model + orchestration
  data/         base · sample · understat · weather     # swappable data layer
  app.py        # Streamlit UI (st.tabs per market)
tests/          # pytest
docs/specs/     # design spec + tasks
```

## Roadmap (not yet built)

- More player props (shots, cards, assists)
- Team props: corners / cards (needs referee + corner data)
- World Cup national-team variant (Elo + FBref national xG)
- Backtesting/calibration harness (RPS, log-loss, walk-forward)

Done: **Anytime Goalscorer** player props (xG-share allocation of team λ, penalty
boost, expected-minutes scaling) — see `docs/specs/2026-06-20-player-props-design.md`.

## Disclaimer

Predictions are probability estimates, not guarantees. Single-match football is
high variance. This is a personal analytics tool — bet responsibly.
