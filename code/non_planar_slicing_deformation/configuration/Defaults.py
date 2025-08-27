import numpy as np
from typing_extensions import Final

from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters

simpleDeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "zeroth order": np.float64(0.0),
    "first order": np.float64(0.0),
    "second order": np.float64(0.0),
    })
simpleUndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({

    })

threeAxisDeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "first order": np.float64(0.0),
    "second order": np.float64(0.0),
    "x translation": np.float64(0.0),
    "y translation": np.float64(0.0),
    })
threeAxisUndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({

    })
