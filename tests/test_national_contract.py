"""predict_international should match predict()'s output contract (review fixes)."""
from jackpot.national import predict_international


def _out():
    return predict_international("Belgium", "Iran", 1850, 1760)


def test_team_total_goals_uses_same_lines_as_club_path():
    # club path uses (0.5, 1.5, 2.5); the 0.5 line is the key single-team market
    ttg = _out()["markets"]["team_total_goals"]
    assert set(ttg.keys()) == {"0.5", "1.5", "2.5"}


def test_output_has_shared_contract_keys():
    out = _out()
    # the app and any shared renderer can rely on these regardless of model path
    assert out["home_team"] == "Belgium"
    assert out["away_team"] == "Iran"
    assert "confidence" in out  # present (None for national), so out["confidence"] is safe
