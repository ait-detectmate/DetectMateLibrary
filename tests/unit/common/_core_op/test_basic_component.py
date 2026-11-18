"""Tests for detectmatelibrary.common._core_op._basic_component."""
from detectmatelibrary.common._config import BasicConfig
from detectmatelibrary.common._core_op._basic_component import Component


def test_the_lifecycle_methods_do_nothing_by_default():
    component = Component(name="Bare")
    assert component.run(input_=None, output_=None) is False
    assert component.train(input_=None) is None
    assert component.configure(input_=None) is None
    assert component.set_configuration() is None
    assert component.post_train() is None


def test_repr_names_type_and_component():
    assert repr(Component(name="Bare", type_="Probe")).startswith("<Probe> Bare: ")


def test_config_access_goes_through_the_config():
    config = BasicConfig()
    component = Component(name="Bare", config=config)
    component.update_config({"auto_config": True})

    assert config.auto_config is True
    assert component.get_config() == config.get_config()


def test_context_manager_gives_the_component():
    component = Component(name="Bare")
    with component as entered:
        assert entered is component
