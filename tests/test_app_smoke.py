"""Headless UI smoke tests using Streamlit's official AppTest harness.

These run the real app.py script in-process (no browser) and assert the UI
renders and produces a prediction — the QA layer for the Streamlit front end.
"""
import os

import pytest

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "jackpot", "app.py")


def _fresh():
    at = AppTest.from_file(APP, default_timeout=30)
    return at.run()


def test_app_renders_without_exception():
    at = _fresh()
    assert not at.exception
    # title is present
    assert any("Jackpot" in t.value for t in at.title)


def test_app_shows_prompt_before_predicting():
    at = _fresh()
    # default state: Predict not clicked -> info prompt
    assert any("Predict" in i.value for i in at.info)


def test_app_produces_prediction_for_two_teams():
    at = _fresh()
    # data source defaults to Sample (offline); pick two different teams
    # selectboxes order: [league, home, away]
    at.selectbox[1].set_value("Manchester City")
    at.selectbox[2].set_value("Burnley")
    at.run()
    at.button[0].click().run()

    assert not at.exception
    # confidence metric rendered
    assert any("Confidence" in m.label for m in at.metric)
    # at least one probability percentage rendered in the markdown body
    body = " ".join(m.value for m in at.markdown)
    assert "%" in body
    assert "fair odds" in body


def test_app_warns_on_same_team_both_sides():
    at = _fresh()
    # force both sides to the same team -> warning
    at.selectbox[1].set_value("Arsenal")
    at.selectbox[2].set_value("Arsenal")
    at.run()
    at.button[0].click().run()
    assert not at.exception
    assert any("different teams" in w.value for w in at.warning)
