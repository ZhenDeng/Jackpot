from jackpot.data.base import PlayerForm, TeamForm
from jackpot.data.sample import SampleDataProvider


def test_team_form_squad_defaults_none():
    t = TeamForm("X", 1.5, 1.2, matches=10, uses_xg=True)
    assert t.squad is None


def test_player_form_fields():
    p = PlayerForm("Haaland", xg_per90=0.9, xa_per90=0.2, expected_minutes=88.0, penalty_taker=True)
    assert p.name == "Haaland"
    assert p.xg_per90 == 0.9
    assert p.xa_per90 == 0.2
    assert p.expected_minutes == 88.0
    assert p.penalty_taker is True


def test_player_form_minutes_default():
    p = PlayerForm("Sub", xg_per90=0.3)
    assert p.expected_minutes == 90.0
    assert p.penalty_taker is False


def test_player_form_assist_default():
    p = PlayerForm("Sub", xg_per90=0.3)
    assert p.xa_per90 == 0.0


def test_sample_provider_attaches_squads():
    p = SampleDataProvider()
    md = p.get_match("Manchester City", "Burnley", "EPL")
    assert md.home.squad is not None
    assert len(md.home.squad) >= 3
    # squad members are PlayerForm with a designated penalty taker somewhere
    assert all(isinstance(pl, PlayerForm) for pl in md.home.squad)
    assert any(pl.penalty_taker for pl in md.home.squad)
