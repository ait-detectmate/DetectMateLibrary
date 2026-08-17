from detectmatelibrary.utils.persistency.component_interfaces import Stoppable
from detectmatelibrary.schemas import BaseSchema

from detectmatelibrary.common._config import BasicConfig

from typing import Any, Dict, List


class Component:
    """Empty methods."""
    def __init__(
        self,
        name: str,
        type_: str = "Core",
        config: BasicConfig = BasicConfig(),
    ) -> None:
        self.name, self.type_, self.config = name, type_, config
        self.saver: Stoppable | None = None

    def __repr__(self) -> str:
        return f"<{self.type_}> {self.name}: {self.config}"

    def run(
        self, input_: List[BaseSchema] | BaseSchema, output_: BaseSchema
    ) -> bool:
        return False

    def train(
        self, input_: List[BaseSchema] | BaseSchema,
    ) -> None:
        pass

    def configure(
        self, input_: List[BaseSchema] | BaseSchema,
    ) -> None:
        pass

    def set_configuration(self) -> None:
        pass

    def post_train(self) -> None:
        pass

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        self.config.update_config(new_config)

    def __enter__(self) -> "Component":
        return self

    def __exit__(self, *_: Any) -> None:
        if self.saver is not None:
            self.saver.stop()
