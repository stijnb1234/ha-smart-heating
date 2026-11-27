from custom_components.smart_heating.report import (
    Digest,
    gas_change_pct,
    heating_degree_days,
    m3_per_hdd,
)


def test_degree_days_count_only_cold_days():
    assert heating_degree_days([8.0, 20.0, 15.0]) == 13.0
    assert m3_per_hdd(26.0, [8.0, 15.0], 18.0) == 2.0
    assert m3_per_hdd(None, [8.0], 18.0) is None
    assert m3_per_hdd(5.0, [20.0], 18.0) is None


def test_gas_change_is_weather_corrected():
    assert round(gas_change_pct(10.0, [8.0], 24.0, [-2.0])) == -17
    assert gas_change_pct(10.0, [8.0], None, []) is None


def test_digest_is_only_sent_when_there_is_something_to_say():
    assert not Digest().worth_sending
    assert not Digest(change_pct=4.0).worth_sending
    assert Digest(change_pct=-12.0).worth_sending
    assert Digest(actions=("Do this.",)).worth_sending
    assert Digest(effects=(("Study", 5.0, 3.0),)).worth_sending


def test_digest_reads_as_a_verdict_and_the_top_three_actions():
    digest = Digest(change_pct=-12.4, actions=("A.", "B.", "C.", "D."), effects=(("Study", 5.0, 3.5),))
    text = digest.format()
    assert text.startswith("You used 12% less gas")
    assert "3. C." in text and "D." not in text
    assert "Study" in text and "from 5 to 3.5" in text
    assert "3 things" in digest.short()
    nl = digest.format("nl")
    assert "12% minder gas" in nl and "van 5 naar 3,5" in nl
