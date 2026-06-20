# ⚽ Jackpot — Soccer Bet Prediction

Predict every item in a bet **Tab** — Match Result (1X2), Over/Under, BTTS,
Correct Score, Double Chance, Draw No Bet, **Anytime Goalscorer** player props, and
**team props** (team total goals, clean sheet, win to nil, winning margin) — for a
soccer match, from a single consistent goal model.

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

In the sidebar pick a **data source**:

- **Sample (offline)** — bundled teams, zero setup. Best for a first look.
- **Manual entry** — type a real upcoming fixture's recent form (xG per game) and
  optionally a few key players, then **Predict**. The way to try a real match today.
- **Understat (live)** — ⚠️ currently blocked: Understat moved behind Cloudflare and
  no longer serves data to simple scrapers. Needs a headless-browser phase to revive.

Then optionally enter bookmaker odds (value flags + blending) or kickoff weather,
and hit **Predict**.

### Try a real match (Manual entry)

1. Run the app, set **Data source → Manual entry**.
2. Enter each team's recent **scored** and **conceded** per game — use xG/game if you
   have it (e.g. from fbref.com or understat.com in your browser), goals/game otherwise.
3. Set the league average (~1.4–1.5 for top leagues).
4. (Optional) tick **Add key players** and enter a striker or two (xG/90 ~0.3–0.9).
5. **Predict** — every tab populates, including Goalscorers if you added players.

## Tests

```bash
.venv/bin/pytest
```

The prediction engine is pure standard library (no NumPy/SciPy), so the test
suite is deterministic and fast.

## Backtesting & calibration

Measure whether the model is actually any good — and tune its weights — by
replaying history with a strict **walk-forward** (each prediction sees only prior
matches, never its own or future results):

```bash
# runs the bundled sample season
PYTHONPATH=src .venv/bin/python -m jackpot.backtest

# or a real football-data.co.uk results CSV (Date,HomeTeam,AwayTeam,FTHG,FTAG)
PYTHONPATH=src .venv/bin/python -m jackpot.backtest path/to/E0.csv
```

Reports proper scoring rules — **RPS** (the right metric for ordered 1X2; ~0.222
is coin-flip), log-loss, Brier — plus top-pick accuracy and a calibration table
(predicted vs actual home-win frequency). It then grid-searches `home_adv` / `rho`
and prints the best-tuned weights. Download real CSVs from football-data.co.uk.

## Layout

```
src/jackpot/
  poisson.py    matrix.py    markets.py    odds.py      # engine
  strength.py   lambdas.py   players.py   predict.py    # model + orchestration
  metrics.py    backtest.py                             # evaluation + tuning
  data/         base · sample · understat · weather · results · manual
  app.py        # Streamlit UI (st.tabs per market)
tests/          # pytest
docs/specs/     # design spec + tasks
```

## Roadmap (not yet built)

- More player props (shots, cards, assists)
- Team props: **corners / cards** — needs FBref data (corner data absent from
  Understat; cards need referee data). Separate scraping phase.
- World Cup national-team variant (Elo + FBref national xG)
- Live data revival (headless browser, since Understat is now Cloudflare-gated)

Done:
- **Anytime Goalscorer** player props — `docs/specs/2026-06-20-player-props-design.md`
- **Team props** (team total goals, clean sheet, win to nil, winning margin), all
  derived exactly from the score matrix — `docs/specs/2026-06-20-team-props-design.md`
- **Backtesting & calibration harness** (walk-forward, RPS/log-loss/Brier,
  calibration, weight tuning) — `docs/specs/2026-06-20-backtest-harness-design.md`

## Disclaimer

Predictions are probability estimates, not guarantees. Single-match football is
high variance. This is a personal analytics tool — bet responsibly.
