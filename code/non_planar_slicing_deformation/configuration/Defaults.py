from typing_extensions import Final

from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters

simpleDeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "radius": 0.0
    })
simpleUndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({

    })

threeAxisDeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({
    "first order": 0.0,
    "second order": 0.0,
    "x translation": 0.0,
    "y translation": 0.0,
    })
threeAxisUndeformerDefaults: Final[KeyValueParameters] = KeyValueParameters({

    })
