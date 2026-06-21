"""Streamlit UI: pick a match, see a prediction Tab with one tab per bet market.

Run with:  streamlit run src/jackpot/app.py
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional

import streamlit as st

from jackpot.context import compute_adjustments
from jackpot.data.apifootball import ApiFootballProvider
from jackpot.data.manual import build_manual_match, rows_to_squad
from jackpot.data.sample import SampleDataProvider
from jackpot.data.understat import UnderstatProvider
from jackpot.data.weather import weather_adjustment, fetch_weather_for_city
from jackpot.national import predict_international, SAMPLE_ELO
from jackpot.odds import fair_odds
from jackpot.predict import predict
from jackpot.sgm import same_game_multi

DATA_SOURCES = [
    "Sample (offline)", "Manual entry", "Understat (live)",
    "API-Football (live)", "World Cup (national)",
]

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


@st.cache_data(ttl=1800, show_spinner=False)
def cached_weather(city: str, date: Optional[str] = None):
    """Geocode + weather for a city (cached 30 min, keyed by canonical city + date).

    ``date`` (ISO) fetches that day's forecast; None fetches current conditions.
    """
    return fetch_weather_for_city(city.strip().lower(), date=date)


def player_table_inputs():
    """Optional player table for goalscorer props → (home_squad, away_squad).

    Shared by Manual and World Cup modes. Returns (None, None) when unused.
    """
    home_squad = away_squad = None
    if st.checkbox("Add key players (optional, for score/assist props)"):
        st.caption(
            "Leave blank to skip. xG/90 ≈ chance quality per match; xA/90 ≈ chances "
            "created per match (drives 'to score or assist')."
        )
        defaults = {"Player": "", "xG/90": 0.0, "xA/90": 0.0, "Minutes": 90.0, "Penalty": False}
        blank = [dict(defaults) for _ in range(3)]
        st.markdown("Home players")
        home_rows = st.data_editor(blank, num_rows="dynamic", key="home_players")
        st.markdown("Away players")
        away_rows = st.data_editor([dict(b) for b in blank], num_rows="dynamic", key="away_players")
        home_squad = rows_to_squad(home_rows)
        away_squad = rows_to_squad(away_rows)
    return home_squad, away_squad


st.title("⚽ Jackpot — Soccer Bet Predictions")
st.caption("Dixon–Coles goal model · xG-based · every market from one score matrix")

# ---- inputs ----
with st.sidebar:
    st.header("Match")
    source = st.radio("Data source", DATA_SOURCES)
    match_date = st.date_input("Match date", value=_date.today())
    manual = source == "Manual entry"
    national = source == "World Cup (national)"

    # state carried into the prediction section
    provider = league = home = away = None
    man_inputs = {}
    nat_inputs = {}

    if national:
        st.caption(
            "National-team Elo model (World Cup = neutral venue). Get current Elo "
            "ratings from eloratings.net — e.g. Belgium ~1850, Iran ~1760."
        )
        home = st.text_input("Home nation", "Belgium")
        home_elo = st.number_input("Home Elo", 1000, 2400, int(SAMPLE_ELO.get("Belgium", 1800)))
        away = st.text_input("Away nation", "Iran")
        away_elo = st.number_input("Away Elo", 1000, 2400, 1760)
        neutral = st.checkbox("Neutral venue (World Cup)", value=True)
        nat_home_squad, nat_away_squad = player_table_inputs()
        nat_inputs = dict(
            home=home, away=away, elo_home=home_elo, elo_away=away_elo, neutral=neutral,
            home_squad=nat_home_squad, away_squad=nat_away_squad,
        )
    elif manual:
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

        home_squad, away_squad = player_table_inputs()

        home, away = hn, an
        man_inputs = dict(
            home_name=hn, home_scored=hs, home_conceded=hc, home_matches=hm,
            away_name=an, away_scored=as_, away_conceded=ac, away_matches=am,
            league_avg=league_avg, home_squad=home_squad, away_squad=away_squad,
        )
    else:
        provider = None
        live_ready = True          # Sample is always ready; live sources need a credential
        live_hint = ""
        if source.startswith("Sample"):
            provider = get_provider(source)
            leagues = provider.list_leagues()
        elif source.startswith("Understat"):
            # Cloudflare-gated: paste a cf_clearance cookie + matching User-Agent.
            st.caption(
                "Understat needs a Cloudflare cookie. Open understat.com → DevTools "
                "→ Application → Cookies → copy the `cf_clearance` value, and your "
                "User-Agent (Console: `navigator.userAgent`). See the README."
            )
            cf_cookie = st.text_input("Cloudflare cookie (cf_clearance)", type="password")
            cf_ua = st.text_input("User-Agent (must match the browser)")
            provider = UnderstatProvider(cf_clearance=cf_cookie or None, user_agent=cf_ua or None)
            leagues = ["EPL", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
            live_ready = bool(cf_cookie)
            live_hint = "Paste your Cloudflare cookie above to load live teams."
        else:  # API-Football (live)
            st.caption(
                "API-Football: get a free key (100 req/day) at dashboard.api-football.com, "
                "paste it below. Covers the top leagues. For the World Cup, use the "
                "**World Cup (national)** data source instead. See the README."
            )
            api_key = st.text_input("API-Football key", type="password")
            season = int(st.number_input("Season (start year)", 2015, 2030, 2024))
            provider = ApiFootballProvider(api_key=api_key, season=season) if api_key else None
            # World Cup is a knockout tournament with no league table, so the
            # standings-based provider can't represent it — it's handled by the
            # dedicated "World Cup (national)" Elo mode.
            leagues = ["EPL", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
            live_ready = bool(api_key)
            live_hint = "Enter your API-Football key above to load live teams."
        league = st.selectbox("League", leagues)

        # Don't hit the network for the team list until the credential is present.
        if not live_ready:
            st.info(live_hint)
            teams = []
        else:
            try:
                teams = provider.list_teams(league)
            except Exception as e:  # pragma: no cover - UI guard
                st.error(
                    f"Could not load teams: {e}. Live data can fail (expired credential, "
                    "quota, or Cloudflare) — use Manual entry as a reliable fallback."
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
        st.caption("Tip: `python -m jackpot.backtest <odds.csv>` finds the best weight for your data.")

    st.subheader("Weather (optional)")
    st.caption("Strong wind/rain modestly lowers expected goals (bounded).")
    weather_src = st.radio(
        "Weather source", ["Off", "Auto (Open-Meteo, free)", "Manual"], horizontal=True,
    )
    weather_mult = 1.0
    if weather_src == "Manual":
        wc1, wc2 = st.columns(2)
        wind_kph = wc1.number_input("Wind (kph)", min_value=0.0, value=10.0, step=5.0)
        rain_mm = wc2.number_input("Rain (mm/h)", min_value=0.0, value=0.0, step=1.0)
        weather_mult = weather_adjustment(wind_kph=wind_kph, rain_mm=rain_mm)
        st.caption(f"Goal multiplier applied to both sides: ×{weather_mult:.3f}")
    elif weather_src.startswith("Auto"):
        city = st.text_input("Match city (free, no API key)", placeholder="e.g. London")
        # today or a future Match date uses that day's forecast (Open-Meteo ~16-day
        # horizon — better than current for a same-day kickoff); past dates use current.
        fdate = match_date.isoformat() if match_date and match_date >= _date.today() else None
        # only fetch once a plausible name is typed (avoids a call per keystroke;
        # repeats are deduped by the cache)
        if len(city.strip()) >= 3:
            try:
                info = cached_weather(city, fdate)
                weather_mult = weather_adjustment(info["wind_kph"], info["rain_mm"])
                when = f"forecast {fdate}" if fdate else "current"
                st.caption(
                    f"{info['name']}, {info['country']} ({when}): wind {info['wind_kph']:.0f} "
                    f"km/h, rain {info['rain_mm']:.1f} mm → ×{weather_mult:.3f}"
                )
            except Exception as e:  # pragma: no cover - UI/network guard
                st.warning(f"Couldn't fetch weather for '{city}' ({e}). Using neutral.")

    st.subheader("Advanced factors (optional)")
    st.caption("Real context you supply — bounded, never invented. Off = no effect.")
    with st.expander("Rest & key absences"):
        rc1, rc2 = st.columns(2)
        home_rest = rc1.number_input("Home rest days", 0, 14, 7)
        away_rest = rc2.number_input("Away rest days", 0, 14, 7)
        home_att_out = rc1.checkbox("Home: key attacker out")
        away_att_out = rc2.checkbox("Away: key attacker out")
        home_def_out = rc1.checkbox("Home: key defender out")
        away_def_out = rc2.checkbox("Away: key defender out")
    home_adjust, away_adjust = compute_adjustments(
        weather_mult=weather_mult,
        home_rest=home_rest, away_rest=away_rest,
        home_attacker_out=home_att_out, away_attacker_out=away_att_out,
        home_defender_out=home_def_out, away_defender_out=away_def_out,
    )
    if (home_adjust, away_adjust) != (1.0, 1.0):
        st.caption(f"Goal multipliers — home ×{home_adjust:.3f}, away ×{away_adjust:.3f}")

    go = st.button("Predict", type="primary", use_container_width=True)


# ---- prediction ----
if go:
    if not home or not away or str(home).strip() == str(away).strip():
        st.warning("Enter two different teams.")
        st.stop()
    if not manual and not national and (provider is None or not live_ready):
        st.error("Enter your live-source credential first.")
        st.stop()

    if national:
        # Elo-driven national-team path (context factors applied to the Elo lambdas)
        out = predict_international(
            **nat_inputs,
            market_odds=market_odds,
            blend_weight=blend_weight,
            home_adjust=home_adjust,
            away_adjust=away_adjust,
        )
    else:
        try:
            match = build_manual_match(**man_inputs) if manual else provider.get_match(home, away, league)
        except ValueError as e:
            st.error(f"Invalid input: {e}")
            st.stop()
        except Exception as e:
            if manual:
                st.error(f"Failed to build match: {e}")
            elif source.startswith("Understat"):
                st.error(
                    f"Failed to load match data: {e}. Understat is Cloudflare-gated — "
                    "the cookie may have expired; use Manual entry as a fallback."
                )
            else:
                st.error(
                    f"Failed to load match data: {e}. Check your API key / quota, "
                    "or use Manual entry as a fallback."
                )
            st.stop()

        if market_odds is not None:
            match.context.market_odds = market_odds
        match.context.home_adjust = home_adjust
        match.context.away_adjust = away_adjust
        out = predict(match, blend_weight=blend_weight)

    c1, c2, c3 = st.columns(3)
    c1.metric("Expected goals — home", f"{out['lambda_home']:.2f}")
    c2.metric("Expected goals — away", f"{out['lambda_away']:.2f}")
    c3.metric("Confidence", out.get("confidence") or "—")

    m = out["markets"]
    tabs = st.tabs(
        ["SGM", "1X2", "Over/Under", "BTTS", "Correct Score", "Double Chance",
         "Draw No Bet", "Goals & Assists", "Team Props"]
    )

    with tabs[0]:
        st.caption(
            "Same Game Multi — the highest-confidence legs from this match combined "
            "into one bet (one pick per market so legs don't overlap)."
        )
        sgm = same_game_multi(m, home, away, n=4)
        for leg in sgm["legs"]:
            st.write(
                f"**{leg['market']}: {leg['selection']}** — {_pct(leg['prob'])}  "
                f"·  fair odds {_odds(leg['fair_odds'])}"
            )
        st.divider()
        sc1, sc2 = st.columns(2)
        sc1.metric("Combined probability", _pct(sgm["combined_prob"]))
        sc2.metric("Combined fair odds", _odds(sgm["combined_fair_odds"]))
        st.caption(
            "Legs in one game are correlated, so the combined probability "
            "(multiplied as if independent) is an optimistic estimate — treat the "
            "fair odds as a floor, and expect a real SGM price to be shorter."
        )

    with tabs[1]:
        _row(f"{home} win", m["match_result"]["home"])
        _row("Draw", m["match_result"]["draw"])
        _row(f"{away} win", m["match_result"]["away"])

    with tabs[2]:
        for line, rec in m["over_under"].items():
            _row(f"Over {line}", rec["over"])
            _row(f"Under {line}", rec["under"])
            st.divider()

    with tabs[3]:
        _row("Both teams to score — Yes", m["btts"]["yes"])
        _row("Both teams to score — No", m["btts"]["no"])

    with tabs[4]:
        for h, a, p in m["correct_score"]:
            st.write(f"**{h}–{a}** — {_pct(p)}  ·  fair odds {_odds(fair_odds(p))}")

    with tabs[5]:
        _row(f"{home} or Draw (1X)", m["double_chance"]["1X"])
        _row(f"{home} or {away} (12)", m["double_chance"]["12"])
        _row(f"Draw or {away} (X2)", m["double_chance"]["X2"])

    with tabs[6]:
        _row(f"{home} (DNB)", m["draw_no_bet"]["home"])
        _row(f"{away} (DNB)", m["draw_no_bet"]["away"])

    with tabs[7]:
        st.caption(
            "To score or assist — probability a player scores or assists at least "
            "once (assists from the xA/90 column). Anytime-scorer % shown alongside."
        )
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
                        f"{e['player']} — {_pct(e['p_involve'])} to score or assist  "
                        f"(odds {_odds(e['fair_odds_involve'])})  ·  "
                        f"scorer {_pct(e['p_score'])}{two}"
                    )

    with tabs[8]:
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
