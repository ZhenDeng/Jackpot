# ⚽ Jackpot — Soccer Bet Prediction

Predict every item in a bet **Tab** — Match Result (1X2), Over/Under, BTTS,
Correct Score, Double Chance, Draw No Bet, **Score or Assist** player props, and
**team props** (team total goals, clean sheet, win to nil, winning margin) — for a
soccer match, from a single consistent goal model. A **Same Game Multi (SGM)** tab
combines the four highest-confidence legs (one pick per market) into one bet with a
combined fair price.

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
| Team data (top leagues) | API-Football (free tier, 100 req/day) | €0 |
| Weather → λ adjustment | Open-Meteo (free, no key) | €0 |
| Offline demo / tests | bundled `SampleDataProvider` | €0 |

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
- **API-Football (live)** — ✅ recommended live source. Official, ToS-clean API with
  a **free tier (100 req/day)**; covers the top leagues. (For the World Cup, use the
  **World Cup (national)** source — a knockout tournament has no league table.) Paste
  an API key (see below).
- **World Cup (national)** — predict an international match from **Elo ratings** (no
  command line needed). Enter the two nations and their Elo (from eloratings.net);
  World Cup = neutral venue by default.

Then optionally enter bookmaker odds (value flags + blending), kickoff weather, or
**Advanced factors** (see below), and hit **Predict**.

### Advanced factors (optional, all modes)

Real match context can nudge the prediction — entered by you, never invented, and
**bounded** so no single factor dominates (combined multiplier clamped to 0.70–1.30):

- **Weather** — wind/rain lowers both sides' expected goals. **Auto-fetch** from
  **Open-Meteo** (free, no API key) by typing the match city; set the **Match date**
  and a future kickoff uses that day's forecast (today/past use current conditions).
  Or enter wind/rain by hand.
- **Rest days** — a short-rested side scores slightly less.
- **Key attacker out** — that team scores less.
- **Key defender out** — the *opponent* scores more.

Off by default (no effect). The resulting goal multipliers are shown before you predict.

### Using API-Football (recommended live data)

1. Sign up free at **dashboard.api-football.com** and copy your **API key**
   (the free plan allows 100 requests/day — plenty for a personal app).
2. In the app: **Data source → API-Football (live)**, paste the key, pick the season
   start year (e.g. 2024 for the 2024/25 season).
3. Choose one of the top-5 leagues and two teams, then **Predict**. (The free tier
   only covers seasons ~2022–2024; current-season access needs a paid plan.)

Team form is goals-based in this version (the model's shrinkage handles it). Per-team
xG, player props, corners/cards, and odds from API-Football are planned follow-ups.

### Try a real match (Manual entry)

1. Run the app, set **Data source → Manual entry**.
2. Enter each team's recent **scored** and **conceded** per game — use xG/game if you
   have it (e.g. from fbref.com in your browser), goals/game otherwise.
3. Set the league average (~1.4–1.5 for top leagues).
4. (Optional) tick **Add key players** and enter a striker or two (xG/90 ~0.3–0.9).
5. **Predict** — every tab populates, including Goals & Assists if you added players.

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
(predicted vs actual home-win frequency). It grid-searches `home_adv` / `rho` /
`shrink_k` and prints the best-tuned weights. Download real CSVs from
football-data.co.uk.

**Tuning the model-vs-market blend weight:** if the CSV includes bookmaker odds
columns (`B365H/B365D/B365A`, `PSH/PSD/PSA`, or `AvgH/AvgD/AvgA`), the backtest also
grid-searches `blend_weight` and reports the value that minimises RPS for *your*
leagues — a data-backed answer to "what blend weight is best" rather than a guess.
Without odds columns the blend is inert and only the model weights are tuned.

## World Cup / national teams

National teams have no league table, so strength comes from **Elo ratings** instead
of club xG. Elo → expected goals → the same score matrix and markets:

```bash
PYTHONPATH=src .venv/bin/python -m jackpot.national "Brazil" "Croatia"
# explicit ratings / a home venue:
PYTHONPATH=src .venv/bin/python -m jackpot.national "TeamA" "TeamB" 2000 1700 --home
```

World Cup matches are treated as **neutral** venues by default. A small sample Elo
table is bundled; pass explicit ratings (from eloratings.net) for any nation.

This is also available in the **app** without the command line — pick
**Data source → World Cup (national)**. Confidence is derived from the Elo gap
(decisive mismatch → higher), and you can tick **Add key players** to enter each
side's key players (xG/90 + xA/90) for **score-or-assist props** (user-entered, as no free national squad
data exists — same as Manual mode).

## Corners & cards (count props)

Corners and cards are separate count markets (their own Poisson, not from the
goals matrix). Because the free feeds lack corner/referee data, these are fed by
**manually entered rates**:

```bash
PYTHONPATH=src .venv/bin/python -m jackpot.counts "Liverpool" "Everton" --ref 5.5
```

Corners use each team's corners-for/against; cards scale by a **referee** factor
(cards/game vs the league average) — the dominant driver of bookings. Reports
total + team Over/Under with fair odds.

## Layout

```
src/jackpot/
  poisson.py    matrix.py    markets.py    odds.py      # engine
  strength.py   lambdas.py   players.py   predict.py    # model + orchestration
  metrics.py    backtest.py   national.py   counts.py   # evaluation, tuning, variants
  data/         base · sample · apifootball · weather · results · manual
  app.py        # Streamlit UI (st.tabs per market)
tests/          # pytest
docs/specs/     # design spec + tasks
```

## Roadmap (not yet built)

- More player props (shots, assists)
- API-Football enrichments: per-team xG, player props, corners/cards, odds
  (v1 is goals-based team form)
- Auto-lineup modelling (aggregate a full starting XI's xG — needs lineup data;
  the "key player out" toggles are the current pragmatic version)
- Streamlit tab for count props (corners/cards)
- Calibrate the context-factor magnitudes via the backtest harness

Done:
- **Score or Assist** player props (anytime-scorer kept alongside) — `docs/specs/2026-06-20-player-props-design.md`, `docs/specs/2026-06-21-player-goal-or-assist-design.md`
- **Team props** (team total goals, clean sheet, win to nil, winning margin), all
  derived exactly from the score matrix — `docs/specs/2026-06-20-team-props-design.md`
- **Backtesting & calibration harness** (walk-forward, RPS/log-loss/Brier,
  calibration, weight tuning) — `docs/specs/2026-06-20-backtest-harness-design.md`
- **World Cup / national-team variant** (Elo → expected goals, neutral venues),
  reusing the full market engine — `docs/specs/2026-06-20-national-variant-design.md`
- **Corners & cards** count props (independent Poisson, referee factor, manual
  rates) — `docs/specs/2026-06-20-count-props-design.md`
- **Context factors** (weather, rest, key absences — bounded levers) + **World
  Cup in the app** (Elo model in the dropdown) — `docs/specs/2026-06-20-context-factors-design.md`
- **Backtest blend-weight tuning** (vs real bookmaker odds) + **match-date weather** (forecast for the kickoff day) — `docs/specs/2026-06-21-blend-tune-match-date-design.md`
- **Auto weather** via Open-Meteo (free, no API key — fetch wind/rain by city) — `docs/specs/2026-06-21-open-meteo-weather-design.md`
- **API-Football integration** (official API, free tier, top-5 leagues, goals-based
  team form) — `docs/specs/2026-06-20-apifootball-design.md`

## Disclaimer

Predictions are probability estimates, not guarantees. Single-match football is
high variance. This is a personal analytics tool — bet responsibly.
