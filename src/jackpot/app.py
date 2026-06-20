"""Streamlit UI: pick a match, see a prediction Tab with one tab per bet market.

Run with:  streamlit run src/jackpot/app.py
"""
from __future__ import annotations

import streamlit as st

from jackpot.data.sample import SampleDataProvider
from jackpot.data.understat import UnderstatProvider
from jackpot.data.weather import weather_adjustment
from jackpot.odds import fair_odds
from jackpot.predict import predict

st.set_page_config(page_title="Jackpot — Soccer Predictions", page_icon="⚽", layout="centered")


def _pct(p: float) -> str:
    return f"{p * 100:.1f}%"


def _odds(o: float) -> str:
    return "∞" if o == float("inf") else f"{o:.2f}"


def _row(label: str, rec: dict) -> None:
    flag = "  🟢 **value**" if rec.get("value") else ""
    st.write(f"**{label}** — {_pct(rec['prob'])}  ·  fair odds {_odds(rec['fair_odds'])}{flag}")


@st.cache_resource
def get_provider(name: str):
    return SampleDataProvider() if name == "Sample (offline)" else UnderstatProvider()


st.title("⚽ Jackpot — Soccer Bet Predictions")
st.caption("Dixon–Coles goal model · xG-based · every market from one score matrix")

# ---- inputs ----
with st.sidebar:
    st.header("Match")
    source = st.radio("Data source", ["Sample (offline)", "Understat (live)"])
    provider = get_provider(source)

    if source.startswith("Sample"):
        leagues = provider.list_leagues()
    else:
        leagues = list(["EPL", "La Liga", "Serie A", "Bundesliga", "Ligue 1"])
    league = st.selectbox("League", leagues)

    try:
        teams = provider.list_teams(league)
    except Exception as e:  # pragma: no cover - UI guard
        st.error(f"Could not load teams: {e}")
        teams = []

    home = st.selectbox("Home team", teams, index=0 if teams else None)
    away = st.selectbox("Away team", teams, index=1 if len(teams) > 1 else None)

    st.subheader("Market odds (optional)")
    st.caption("Enter bookmaker decimal odds to enable value flags + blending.")
    use_odds = st.checkbox("Compare against market odds")
    market_odds = None
    blend_weight = 1.0
    if use_odds:
        oc1, oc2, oc3 = st.columns(3)
        oh = oc1.number_input("Home", min_value=1.01, value=2.10, step=0.05)
        od = oc2.number_input("Draw", min_value=1.01, value=3.40, step=0.05)
        oa = oc3.number_input("Away", min_value=1.01, value=3.60, step=0.05)
        market_odds = {"home": oh, "draw": od, "away": oa}
        blend_weight = st.slider("Model weight (vs market)", 0.0, 1.0, 0.7, 0.05)

    st.subheader("Weather (optional)")
    st.caption("Strong wind/rain modestly lowers expected goals (bounded).")
    use_weather = st.checkbox("Apply kickoff weather")
    weather_mult = 1.0
    if use_weather:
        wc1, wc2 = st.columns(2)
        wind_kph = wc1.number_input("Wind (kph)", min_value=0.0, value=10.0, step=5.0)
        rain_mm = wc2.number_input("Rain (mm/h)", min_value=0.0, value=0.0, step=1.0)
        weather_mult = weather_adjustment(wind_kph=wind_kph, rain_mm=rain_mm)
        st.caption(f"Goal multiplier applied to both sides: ×{weather_mult:.3f}")

    go = st.button("Predict", type="primary", use_container_width=True)


# ---- prediction ----
if go:
    if not home or not away or home == away:
        st.warning("Pick two different teams.")
        st.stop()
    try:
        match = provider.get_match(home, away, league)
    except Exception as e:
        st.error(f"Failed to load match data: {e}")
        st.stop()

    if market_odds is not None:
        match.context.market_odds = market_odds
    if weather_mult != 1.0:
        match.context.home_adjust = weather_mult
        match.context.away_adjust = weather_mult

    out = predict(match, blend_weight=blend_weight)

    c1, c2, c3 = st.columns(3)
    c1.metric("Expected goals — home", f"{out['lambda_home']:.2f}")
    c2.metric("Expected goals — away", f"{out['lambda_away']:.2f}")
    c3.metric("Confidence", out["confidence"])

    m = out["markets"]
    tabs = st.tabs(
        ["1X2", "Over/Under", "BTTS", "Correct Score", "Double Chance", "Draw No Bet", "Goalscorers"]
    )

    with tabs[0]:
        _row(f"{home} win", m["match_result"]["home"])
        _row("Draw", m["match_result"]["draw"])
        _row(f"{away} win", m["match_result"]["away"])

    with tabs[1]:
        for line, rec in m["over_under"].items():
            _row(f"Over {line}", rec["over"])
            _row(f"Under {line}", rec["under"])
            st.divider()

    with tabs[2]:
        _row("Both teams to score — Yes", m["btts"]["yes"])
        _row("Both teams to score — No", m["btts"]["no"])

    with tabs[3]:
        for h, a, p in m["correct_score"]:
            st.write(f"**{h}–{a}** — {_pct(p)}  ·  fair odds {_odds(fair_odds(p))}")

    with tabs[4]:
        _row(f"{home} or Draw (1X)", m["double_chance"]["1X"])
        _row(f"{home} or {away} (12)", m["double_chance"]["12"])
        _row(f"Draw or {away} (X2)", m["double_chance"]["X2"])

    with tabs[5]:
        _row(f"{home} (DNB)", m["draw_no_bet"]["home"])
        _row(f"{away} (DNB)", m["draw_no_bet"]["away"])

    with tabs[6]:
        st.caption("Anytime goalscorer — probability a player scores at least once.")
        pp = m["player_props"]
        gc1, gc2 = st.columns(2)
        for col, side, team_name in ((gc1, "home", home), (gc2, "away", away)):
            with col:
                st.markdown(f"**{team_name}**")
                entries = pp[side]
                if not entries:
                    st.caption("No squad data for this team.")
                    continue
                for e in entries:
                    two = f"  ·  2+: {_pct(e['p_2plus'])}" if e["p_2plus"] > 0.01 else ""
                    st.write(
                        f"{e['player']} — {_pct(e['p_score'])}  "
                        f"(odds {_odds(e['fair_odds'])}){two}"
                    )

    st.caption(
        "Predictions are probability estimates, not guarantees. Single matches are "
        "high variance — use this to find edges and quantify uncertainty."
    )
else:
    st.info("Set up a match in the sidebar and hit **Predict**.")
