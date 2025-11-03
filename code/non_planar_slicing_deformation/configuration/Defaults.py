import numpy as np
from typing_extensions import Final

from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters

simpleDeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "zeroth order": np.float64(0.0),
    "first order": np.float64(0.0),
    "second order": np.float64(0.0),
    })
simpleUndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "home all": False,
    "heat extruder": True,
    "heat extruder temperature": 215,
    "nozzle offset": 42.5,
    })

threeAxisDeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "first order": np.float64(0.0),
    "second order": np.float64(0.0),
    "x translation": np.float64(0.0),
    "y translation": np.float64(0.0),
    })
threeAxisUndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({

    })

s4DeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "offset x": np.float64(0.0),
    "offset y": np.float64(0.0),
    "offset z": np.float64(0.0),
    "neighbour loss weight": np.int64(20),
    "max overhang": np.float64(30.0),
    "rotation multiplier": np.float64(2.0),
    "set initial rotation to zero": False,
    "initial rotation field smoothing": np.int64(30.0),
    "max rotation": np.float64(3600.0),
    "min rotation": np.float64(-3600.0),
    "optimize rotation iterations": np.int64(100),
    "steep overhang compensation": True,
    "calculate deformation iterations": np.int64(100),
    })
s4UndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "home all": False,
    "heat extruder": True,
    "heat extruder temperature": 215,
    "nozzle offset": 42.5,  # mm
    })
