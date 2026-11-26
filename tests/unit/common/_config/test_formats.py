"""Tests for detectmatelibrary.common._config._formats."""
from detectmatelibrary.common._config._formats import EventsConfig, Header, Variable, _EventConfig


def test_to_dict_leaves_out_empty_names_and_params():
    assert Variable(pos=0).to_dict() == {"pos": 0}
    assert Variable(pos="pid", name="pid", params={"t": 1}).to_dict() == {
        "pos": "pid", "name": "pid", "params": {"t": 1}}
    assert Header(pos="Level").to_dict() == {"pos": "Level"}


def test_instances_key_their_variables_by_position():
    events = EventsConfig._init({1: {"inst": {
        "variables": [{"pos": 0, "name": "user"}], "header_variables": [{"pos": "Level"}]}}})
    instance = events[1].instances["inst"]

    assert list(instance.variables) == [0]
    assert list(instance.header_variables) == ["Level"]
    assert set(instance.get_all()) == {0, "Level"}


def test_event_shortcuts_read_the_first_instance():
    event = _EventConfig._init({
        "first": {"variables": [{"pos": 0}], "header_variables": [{"pos": "Level"}]},
        "second": {"variables": [{"pos": 1}]},
    })
    assert list(event.variables) == [0]
    assert list(event.header_variables) == ["Level"]
    assert set(event.get_all()) == {0, "Level"}


def test_event_shortcuts_of_an_event_without_instances_are_empty():
    event = _EventConfig(instances={})
    assert (event.variables, event.header_variables, event.get_all()) == ({}, {}, {})


def test_lookup_of_an_unknown_event_gives_none():
    events = EventsConfig._init({1: {"inst": {"variables": [{"pos": 0}]}}})
    assert 1 in events and 2 not in events
    assert events[2] is None


def test_to_dict_drops_empty_events_and_restores_integer_ids():
    events = EventsConfig(events={
        "1": _EventConfig._init({"inst": {"variables": [{"pos": 0}]}}),
        "login": _EventConfig._init({"inst": {"variables": [{"pos": "user"}]}}),
        "2": _EventConfig(instances={}),
    })
    assert events.to_dict() == {
        1: {"inst": {"params": {}, "variables": [{"pos": 0}]}},
        "login": {"inst": {"params": {}, "variables": [{"pos": "user"}]}},
    }
