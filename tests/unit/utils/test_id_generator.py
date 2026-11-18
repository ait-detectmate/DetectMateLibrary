"""Tests for detectmatelibrary.utils.id_generator."""
from detectmatelibrary.utils.id_generator import SimpleIDGenerator


def test_counts_up_from_the_start_id():
    generate = SimpleIDGenerator(start_id=10)
    assert [generate() for _ in range(3)] == ["10", "11", "12"]


def test_prefix_is_joined_with_an_underscore():
    generate = SimpleIDGenerator(start_id=0, prefix="NewValueDetector")
    assert [generate(), generate()] == ["NewValueDetector_0", "NewValueDetector_1"]


def test_generators_count_independently():
    first, second = SimpleIDGenerator(start_id=1), SimpleIDGenerator(start_id=1)
    first()
    assert second() == "1"
