import numpy as np


def toFloat(value: np.float64) -> float:
    return value.item()


def forceToInt(value: np.float64) -> int:
    return np.int64(value).item()


def toInt(value: np.int64) -> int:
    return value.item()
