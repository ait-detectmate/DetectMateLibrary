from typing import Any, Dict, List

from detectmatelibrary.common.core import CoreComponent, CoreConfig
from detectmatelibrary.common._core_op._fed_component import FedOperations  # noqa: F401
from detectmatelibrary.common._core_op._fit_logic import StatesL
from detectmatelibrary.schemas._classes import BaseSchema


# --8<-- [start:read]
class ConfigComponent(CoreConfig):
    """Contains all the arguments of the component."""


class Component(CoreComponent):
    def run(
        self, input_: List[BaseSchema] | BaseSchema, output_: BaseSchema
    ) -> bool:
        """Run the component for a specific input."""
        pass

    def train(
        self, input_: List[BaseSchema] | BaseSchema,
    ) -> None:
        """Train the component with a specific input."""
        pass

    def update_state(self, state: StatesL) -> None:
        """Update the current state by request of the user.

        states:
        *   keep_training: force to keep training
        *   stop_training: force to stop training
        *   keep_configuring: force to keep configuring
        *   stop_configuring: force to stop configuring
        """
        pass

    def get_state(self) -> str:
        """Return the current state of the component.

        states:
        *   Configuring: the component is doing configurations
        *   Training: the component is training
        *   Default: the component is just processing data
        """
        pass

    def export_state(
        self, path: str | None = None, storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:
        """Export the current state if persistency class was implemented."""
        pass

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        """Import the current state if persistency class was implemented."""
        pass

    def process(self, data: BaseSchema | bytes) -> BaseSchema | bytes | None:
        """Process the data in a stream fashion (Defined in the
        CoreComponent)"""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Get the configuration of the component (Defined in the
        CoreComponent)"""
        pass

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update the configuration of the component (Defined in the
        CoreComponent)"""
        pass

    def get_window_size(self) -> int:
        """Get window size of the data buffer."""
        pass

    def stack(self, other: object | list[object | bytes] | bytes) -> None:
        """(Federation only) stack multiple components for federation tasks."""
        pass

    def aggregate(self, unstack: bool = False) -> None | bytes:
        """(Federation only) aggregate multiple components."""
        pass

    def to_binary(self) -> bytes | None:
        """(Federation only) fill it to be compatible with federation ops."""
        pass

    def from_binary(self, binary: bytes) -> object:
        """(Federation only) fill it to be compatible with federation ops."""
        pass

    def aggregate_strategy(self, components: set["FedOperations"]) -> None:
        """(Federation only) fill it to be compatible with federation ops."""
        pass
# --8<-- [end:read]
