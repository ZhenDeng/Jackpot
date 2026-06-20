import pytest

from jackpot.data.understat import (
    parse_cf_clearance,
    build_request_kwargs,
    UnderstatProvider,
    DEFAULT_USER_AGENT,
)


# ---- parse_cf_clearance ----

def test_parses_token_from_full_cookie_string():
    raw = "foo=1; cf_clearance=AbC123.xyz-_; bar=2"
    assert parse_cf_clearance(raw) == "AbC123.xyz-_"


def test_passes_bare_value_through():
    assert parse_cf_clearance("AbC123.xyz") == "AbC123.xyz"


def test_strips_whitespace():
    assert parse_cf_clearance("  cf_clearance = token123 ; x=1 ") == "token123"


def test_raises_when_no_clearance_in_named_cookie_string():
    with pytest.raises(ValueError):
        parse_cf_clearance("foo=1; bar=2")


def test_raises_on_empty():
    with pytest.raises(ValueError):
        parse_cf_clearance("")


# ---- build_request_kwargs ----

def test_defaults_have_user_agent_and_no_cookies():
    kw = build_request_kwargs()
    assert kw["headers"]["User-Agent"] == DEFAULT_USER_AGENT
    assert kw["cookies"] == {}


def test_cf_clearance_becomes_a_cookie():
    kw = build_request_kwargs(cf_clearance="tok")
    assert kw["cookies"]["cf_clearance"] == "tok"


def test_custom_user_agent_overrides_default():
    kw = build_request_kwargs(user_agent="MyUA/1.0")
    assert kw["headers"]["User-Agent"] == "MyUA/1.0"


def test_full_cookie_string_is_parsed_for_clearance():
    kw = build_request_kwargs(cf_clearance="a=1; cf_clearance=TOKEN; b=2")
    assert kw["cookies"]["cf_clearance"] == "TOKEN"


# ---- provider wiring ----

def test_provider_stores_cookie_and_user_agent():
    p = UnderstatProvider(cf_clearance="tok", user_agent="UA/9")
    assert p.cf_clearance == "tok"
    assert p.user_agent == "UA/9"
    # and exposes them through the request kwargs it will send
    kw = p._request_kwargs()
    assert kw["cookies"]["cf_clearance"] == "tok"
    assert kw["headers"]["User-Agent"] == "UA/9"


def test_provider_without_cookie_sends_no_cookie():
    p = UnderstatProvider()
    assert p._request_kwargs()["cookies"] == {}
