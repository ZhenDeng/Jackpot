# Tasks — Soccer Prediction MVP

Source of truth for "is this job done". Check a box only when implemented AND its
tests pass.

## Build

- [ ] T1  Project scaffold: package layout, requirements.txt, venv, README, pytest config
- [ ] T2  `poisson.py` — poisson_pmf + Dixon–Coles tau correction (TDD)
- [ ] T3  `strength.py` — xG-based team strength, shrinkage, time decay (TDD)
- [ ] T4  `lambdas.py` — compute λ_home/λ_away from strength + home adv + adjustments (TDD)
- [ ] T5  `matrix.py` — build NxN score matrix from λ with DC correction (TDD)
- [ ] T6  `markets.py` — derive 1X2, O/U(1.5/2.5/3.5), BTTS, correct score, DC, DNB (TDD)
- [ ] T7  `odds.py` — fair odds, strip overround, market blend, value flag, confidence (TDD)
- [ ] T8  `data/base.py` + `data/sample.py` — provider interface + offline fixtures (TDD)
- [ ] T9  `predict.py` — orchestrate match + provider -> full Tab prediction (TDD)
- [ ] T10 `data/understat.py` + `data/weather.py` — runtime providers (light/mock tests)
- [ ] T11 `app.py` — Streamlit UI: input form + st.tabs() per market
- [ ] T12 README run instructions + final full test-suite green

## Done criteria
- All boxes above checked
- `pytest` green
- No open CRITICAL/HIGH review findings
- Streamlit app launches and renders a prediction Tab from SampleDataProvider
