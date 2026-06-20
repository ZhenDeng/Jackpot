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


def test_bare_token_with_base64_padding_passes_through():
    # cf_clearance values are base64url and often end with '=' padding
    assert parse_cf_clearance("AbC123.xyz-_9q8w==") == "AbC123.xyz-_9q8w=="


def test_full_cookie_with_padded_value():
    assert parse_cf_clearance("x=1; cf_clearance=TOK.en==; y=2") == "TOK.en=="


def test_raises_when_no_clearance_in_named_cookie_string():
    with pytest.raises(ValueError):
        parse_cf_clearance("foo=1; bar=2")


def test_raises_on_single_non_clearance_cookie():
    with pytest.raises(ValueError):
        parse_cf_clearance("session=abc123")


def test_repr_masks_the_cookie_credential():
    p = UnderstatProvider(cf_clearance="supersecrettoken")
    assert "supersecrettoken" not in repr(p)


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
