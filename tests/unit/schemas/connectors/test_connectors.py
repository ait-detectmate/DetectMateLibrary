"""Tests for detectmatelibrary.schemas.connectors (select_connector)."""
import pytest

from detectmatelibrary.schemas.connectors import (
    DefaultConnector, MongoConnector, RedisConnector, VerificationConnector, select_connector,
)


@pytest.mark.parametrize("name, cls", [
    ("Default", DefaultConnector), ("Verification", VerificationConnector),
    ("Mongo", MongoConnector), ("Redis", RedisConnector),
])
def test_select_connector_finds_each_connector(name, cls):
    assert select_connector(name) is cls


def test_an_unknown_connector_lists_the_known_ones():
    with pytest.raises(ValueError, match="'Kafka' not found.*Verification"):
        select_connector("Kafka")
