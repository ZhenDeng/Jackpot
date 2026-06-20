"""Streamlit UI: pick a match, see a prediction Tab with one tab per bet market.

Run with:  streamlit run src/jackpot/app.py
"""
from __future__ import annotations

import streamlit as st

from jackpot.data.manual import build_manual_match, rows_to_squad
from jackpot.data.sample import SampleDataProvider
from jackpot.data.understat import UnderstatProvider
from jackpot.data.weather import weather_adjustment
from jackpot.odds import fair_odds
from jackpot.predict import predict

DATA_SOURCES = ["Sample (offline)", "Manual entry", "Understat (live)"]

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
    source = st.radio("Data source", DATA_SOURCES)
    manual = source == "Manual entry"

    # state carried into the prediction section
    provider = league = home = away = None
    man_inputs = {}

    if manual:
        st.caption("Type a real fixture's recent form (xG per game preferred).")
        league_avg = st.number_input("League avg goals / team / game", 0.1, 5.0, 1.45, 0.05)
        hcol, acol = st.columns(2)
        with hcol:
            st.markdown("**Home**")
            hn = st.text_input("Home name", "Home FC")
            hs = st.number_input("Home scored/game", 0.0, 6.0, 1.8, 0.1)
            hc = st.number_input("Home conceded/game", 0.0, 6.0, 1.1, 0.1)
            hm = st.number_input("Home matches", 1, 60, 20)
        with acol:
            st.markdown("**Away**")
            an = st.text_input("Away name", "Away FC")
            as_ = st.number_input("Away scored/game", 0.0, 6.0, 1.2, 0.1)
            ac = st.number_input("Away conceded/game", 0.0, 6.0, 1.6, 0.1)
            am = st.number_input("Away matches", 1, 60, 20)

        home_squad = away_squad = None
        if st.checkbox("Add key players (optional, for goalscorer props)"):
            st.caption("Leave blank to skip. xG/90 ≈ a striker's chance quality per match.")
            cols = ["Player", "xG/90", "Minutes", "Penalty"]
            blank = [{c: ("" if c == "Player" else (90.0 if c == "Minutes" else (0.0 if c == "xG/90" else False))) for c in cols} for _ in range(3)]
            st.markdown("Home players")
            home_rows = st.data_editor(blank, num_rows="dynamic", key="home_players")
            st.markdown("Away players")
            away_rows = st.data_editor([dict(b) for b in blank], num_rows="dynamic", key="away_players")
            home_squad = rows_to_squad(home_rows)
            away_squad = rows_to_squad(away_rows)

        home, away = hn, an
        man_inputs = dict(
            home_name=hn, home_scored=hs, home_conceded=hc, home_matches=hm,
            away_name=an, away_scored=as_, away_conceded=ac, away_matches=am,
            league_avg=league_avg, home_squad=home_squad, away_squad=away_squad,
        )
    else:
        if source.startswith("Sample"):
            provider = get_provider(source)
            leagues = provider.list_leagues()
        else:
            # Understat is Cloudflare-gated: let the user paste a cf_clearance
            # cookie + matching User-Agent from their browser (see README).
            st.caption(
                "Understat needs a Cloudflare cookie. Open understat.com in your "
                "browser → DevTools → Cookies → copy `cf_clearance`, and your "
                "User-Agent (`navigator.userAgent`). See the README."
            )
            cf_cookie = st.text_input("Cloudflare cookie (cf_clearance)", type="password")
            cf_ua = st.text_input("User-Agent (must match the browser)")
            provider = UnderstatProvider(
                cf_clearance=cf_cookie or None,
                user_agent=cf_ua or None,
            )
            leagues = ["EPL", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
        league = st.selectbox("League", leagues)

        # Don't hit the network for the team list in live mode until a cookie is
        # supplied — without it the fetch is guaranteed to fail (Cloudflare).
        live_no_cookie = not source.startswith("Sample") and not cf_cookie
        if live_no_cookie:
            st.info("Paste your Cloudflare cookie above to load live teams.")
            teams = []
        else:
            try:
                teams = provider.list_teams(league)
            except Exception as e:  # pragma: no cover - UI guard
                st.error(
                    f"Could not load teams: {e}. Live Understat is Cloudflare-gated — "
                    "the cookie may have expired; use Manual entry as a fallback."
                )
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
    if not home or not away or str(home).strip() == str(away).strip():
        st.warning("Enter two different teams." if manual else "Pick two different teams.")
        st.stop()
    try:
        if manual:
            match = build_manual_match(**man_inputs)
        else:
            match = provider.get_match(home, away, league)
    except ValueError as e:
        st.error(f"Invalid input: {e}")
        st.stop()
    except Exception as e:
        if manual:
            st.error(f"Failed to build match: {e}")
        else:
            st.error(
                f"Failed to load match data: {e}. Live Understat is currently blocked "
                "by Cloudflare — use Sample or Manual entry."
            )
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
        ["1X2", "Over/Under", "BTTS", "Correct Score", "Double Chance", "Draw No Bet",
         "Goalscorers", "Team Props"]
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

    with tabs[7]:
        st.markdown("**Team Total Goals**")
        for line, sides in m["team_total_goals"].items():
            _row(f"{home} Over {line}", sides["home"]["over"])
            _row(f"{home} Under {line}", sides["home"]["under"])
            _row(f"{away} Over {line}", sides["away"]["over"])
            _row(f"{away} Under {line}", sides["away"]["under"])
            st.divider()
        st.markdown("**Clean Sheet**")
        _row(f"{home}", m["clean_sheet"]["home"])
        _row(f"{away}", m["clean_sheet"]["away"])
        st.markdown("**Win to Nil**")
        _row(f"{home}", m["win_to_nil"]["home"])
        _row(f"{away}", m["win_to_nil"]["away"])
        st.markdown("**Winning Margin**")
        labels = {
            "home_2plus": f"{home} by 2+", "home_1": f"{home} by 1", "draw": "Draw",
            "away_1": f"{away} by 1", "away_2plus": f"{away} by 2+",
        }
        for key, label in labels.items():
            _row(label, m["winning_margin"][key])
        st.caption("Corners & cards are out of scope on the free data stack (no corner data; cards need referee data).")

    st.caption(
        "Predictions are probability estimates, not guarantees. Single matches are "
        "high variance — use this to find edges and quantify uncertainty."
    )
else:
    st.info("Set up a match in the sidebar and hit **Predict**.")
