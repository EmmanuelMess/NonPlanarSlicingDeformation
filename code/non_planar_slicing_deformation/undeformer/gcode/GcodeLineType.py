from typing_extensions import Union

from non_planar_slicing_deformation.undeformer.gcode.FastMove import FastMove
from non_planar_slicing_deformation.undeformer.gcode.SlowMove import SlowMove

GcodeLineType = Union[SlowMove, FastMove]
