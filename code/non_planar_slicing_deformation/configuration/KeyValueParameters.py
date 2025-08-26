from typing_extensions import Any, Optional, Type, Dict, Tuple, TypeVar

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER

T = TypeVar("T")


class KeyValueParameters:
    """
    Meant to be a generic way to pass parameters from a configurable UI to a Deformer or Underformer
    """

    def __init__(self, defaults: Dict[str, Any]) -> None:
        self.map = defaults

    def __getitem__(self, item: Tuple[str, Type[T]]) -> Optional[T]:
        key, valueType = item
        if key not in self.map.keys():
            MAIN_LOGGER.warning(f"Key {key} is not in parameter map {self.map}")
            return None

        if not isinstance(self.map[key], valueType):
            MAIN_LOGGER.warning(f"Value for '{key}' is not of type '{valueType}'")
            return None

        return self.map[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self.map.keys():
            MAIN_LOGGER.warning(f"Key {key} is not in parameter map {self.map}, did you forget to set a default value?")

        self.map[key] = value
