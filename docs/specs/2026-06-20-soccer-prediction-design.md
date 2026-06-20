# Soccer Bet Prediction — Design Spec

**Date:** 2026-06-20
**Status:** Approved for build (MVP vertical slice)
**Scope:** Personal-use app, top-5 European club leagues, free data stack.

---

## 1. Goal

Let a user input a soccer match (home team, away team, league, date) and get a
prediction for each item in a bet **Tab** — Match Result, Over/Under, BTTS,
Correct Score, and derived markets — each with probability, fair odds, a value
flag, and a confidence score.

## 2. Core idea (the algorithm)

Do **not** model each market separately. Model the single thing that drives them
all — each team's expected goals (λ) in this specific match — then derive every
market from one **score matrix**. This guarantees the whole Tab is internally
consistent (Over 2.5 and Home Win can never contradict each other).

Engine: **bivariate Poisson with the Dixon–Coles low-score correction.**

### Pipeline

```
input match
  -> estimate team attack/defense strength (from xG, with shrinkage + time decay)
  -> compute lambda_home, lambda_away (strength x home advantage x adjustments)
  -> build NxN score-matrix (Poisson x Dixon-Coles correction)
  -> derive each market by summing the relevant matrix cells
  -> convert to probability / fair odds / value flag / confidence
  -> (optional) blend with market odds when available
```

### Improvements baked in (from algorithm review)

1. **xG-based strength**, not raw goals — xG predicts future goals better.
   Fallback to goals when xG is missing.
2. **Shrinkage** — regress each team's strength toward the league mean, weighted
   by sample size. Fixes early-season / promoted-team cold start.
3. **Time decay** — recent matches weigh more (Dixon–Coles exponential decay).
4. **Dixon–Coles correction** — fixes Poisson under-counting of 0-0 / 1-1.
5. **Market blending (optional)** — `final_p = w*model_p + (1-w)*market_p`,
   after stripping the bookmaker overround. The value flag compares model vs.
   this blended baseline.
6. **Honest confidence** — lower when data is thin (few matches, missing xG).

## 3. Markets in scope (this MVP)

| Market | Derivation from score matrix |
| --- | --- |
| Match Result (1X2) | sum cells below / on / above the diagonal |
| Over/Under (1.5, 2.5, 3.5) | sum cells where home+away > line vs <= line |
| Both Teams To Score | sum cells where home>=1 AND away>=1 |
| Correct Score (top N) | individual cells, ranked |
| Double Chance | combine 1X2 sums (1X, 12, X2) |
| Draw No Bet | renormalise Home/Away excluding draw |

## 4. Architecture (modules, each independently testable)

```
src/jackpot/
  poisson.py      # poisson_pmf, dixon_coles tau correction
  strength.py     # TeamStrength estimation: xG-based, shrinkage, time decay
  lambdas.py      # compute lambda_home/away from strength + home adv + adjustments
  matrix.py       # build NxN score matrix from lambdas
  markets.py      # derive each market's outcome probabilities from the matrix
  odds.py         # fair odds, strip overround, market blend, value flag, confidence
  predict.py      # orchestrates: match + data -> full Tab prediction
  data/
    base.py       # MatchDataProvider interface, dataclasses (TeamForm, MatchInput)
    sample.py     # SampleDataProvider: bundled deterministic fixtures (offline)
    understat.py  # UnderstatProvider: real scraper for the 5 leagues (runtime)
    weather.py    # weather adjustment hook (OpenWeatherMap), stubbed for offline
  app.py          # Streamlit UI: input form + st.tabs() per market
tests/            # pytest, pure-stdlib engine -> deterministic
```

**Data layer is a swappable interface.** Engine and UI depend only on
`MatchDataProvider`, never on a concrete source. `SampleDataProvider` powers
tests and an offline demo; `UnderstatProvider` powers the live app. Swapping to a
paid API later (if the app ever goes commercial) means writing one new provider.

## 5. Data sources (free / personal stack)

| Need | Source | Notes |
| --- | --- | --- |
| Team & player xG, shots | Understat (scrape) | exactly the top-5 leagues |
| Fixtures, lineups, results | football-data.org free | scaffolding |
| Cards / misc (future props) | FBref (scrape) | roadmap |
| Weather | OpenWeatherMap free | λ adjustment hook |

Engine is pure-stdlib (`math` only) so the core is dependency-free and fully
testable. Heavy deps (Streamlit, scrapers) live only in the app/data layers.

## 6. Output per market item

- **Probability** (e.g. Home 47%)
- **Fair odds** = 1 / probability
- **Value flag** — set when model prob materially exceeds market implied prob
- **Confidence** — High/Medium/Low from data completeness + sample size

## 7. Out of scope (roadmap — future PRs)

- Player props (anytime scorer, shots, cards) — needs minutes + penalty modelling
- Team props: corners / cards — needs referee data + corner data (free-data gap)
- World Cup national-team variant — Elo (eloratings.net) + FBref national xG
- Backtesting/calibration harness (RPS, log-loss, walk-forward)
- Live in-match updating

These are explicitly **not** tasks for this job; they are the next phases.

## 8. Testing strategy

- TDD on the engine: every module gets failing tests first, written from the
  acceptance criteria below, then implemented.
- Engine tests are deterministic (fixed λ inputs -> known probabilities), using
  pure stdlib so they always run.
- Acceptance anchors:
  - Poisson pmf sums ~1 over k; matches known values.
  - Score matrix rows/cols sum to ~1.
  - All market probabilities for a market sum to ~1 (1X2, DC, etc.).
  - Higher λ_home shifts mass toward Home win and Over.
  - Dixon–Coles raises P(0-0)/P(1-1) vs plain Poisson.
  - Shrinkage pulls a tiny-sample team toward league mean.
  - Stripping overround makes implied probs sum to 1.
