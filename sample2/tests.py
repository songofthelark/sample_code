from replay import run_search, log_to_events
from event_obj import Observation
from datetime import datetime

log = ['{"updateTime": "2016-01-01T00:43:00.001064", "update": {"ambientTemp": 80}}',
       '{"updateTime": "2016-01-01T01:38:00.001038", "update": {"ambientTemp": 81}}',
       '{"updateTime": "2016-01-01T03:18:30.001950", "update": {"schedule": true}}',
       '{"updateTime": "2016-01-02T01:32:00.002066", "update": {"schedule": false}}',
       '{"updateTime": "2016-01-02T02:35:00.001013", "update": {"ambientTemp": 82}}',
       '{"updateTime": "2016-01-02T04:35:00.001204", "update": {"ambientTemp": 83}}',
       '{"updateTime": "2016-01-03T00:32:30.001083", "update": {"heatTemp": 68}}',
       '{"updateTime": "2016-01-03T00:46:30.005581", "update": {"ambientTemp": 84}}',
       '{"updateTime": "2016-01-03T03:14:00.020107", "update": {"ambientTemp": 85}}',
       '{"updateTime": "2016-01-04T01:29:30.001738", "update": {"ambientTemp": 86}}',
       '{"updateTime": "2016-01-04T02:35:00.068493", "update": {"ambientTemp": 87}}',
       '{"updateTime": "2016-01-04T08:54:30.002086", "update": {"ambientTemp": 88}}',
       '{"updateTime": "2016-01-06T00:12:30.001252", "update": {"ambientTemp": 89}}',
       '{"updateTime": "2016-01-06T01:13:00.001923", "update": {"coolTemp": 69}}',
       '{"updateTime": "2016-01-06T04:09:00.001258", "update": {"ambientTemp": 90}}']


events = log_to_events(log)


# shorthand to turn date into isoformat
def iso(some_date: str) -> datetime:
    return datetime.fromisoformat(some_date)


def test_boundaries():
    # low end
    test_obs = run_search(events, iso("2016-01-01T00:43:00"), "ambientTemp")
    gold_obs = Observation(80, iso("2016-01-01T00:43:00.001064"))
    assert test_obs == gold_obs

    # high end
    test_obs = run_search(events, iso("2016-01-06T04:09:00"), "ambientTemp")
    gold_obs = Observation(90, iso("2016-01-06T04:09:00.001258"))
    assert test_obs == gold_obs

    # midpoint
    test_obs = run_search(events, iso("2016-01-03T00:46:30"), "ambientTemp")
    gold_obs = Observation(84, iso("2016-01-03T00:46:30.005581"))
    assert test_obs == gold_obs


def test_earlier_observed_values():
    test_obs = run_search(events, iso("2016-01-06T04:09:00"), "coolTemp")
    gold_obs = Observation(69, iso("2016-01-06T01:13:00.001923"))
    assert test_obs == gold_obs

    test_obs = run_search(events, iso("2016-01-06T04:09:00"), "heatTemp")
    gold_obs = Observation(68, iso("2016-01-03T00:32:30.001083"))
    assert test_obs == gold_obs
