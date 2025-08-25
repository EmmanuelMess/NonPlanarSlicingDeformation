import numpy as np
from pygcode import Line, GCodeLinearMove, GCodeRapidMove, GCodeFeedRate
from typing_extensions import override, Optional, List, cast, Tuple, Callable

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.configuration.CurrentDeformerState import CurrentDeformerState
from non_planar_slicing_deformation.state.ThreeAxisDeformerState import ThreeAxisDeformerState
from non_planar_slicing_deformation.undeformer.Undeformer import Undeformer


class ThreeAxisUndeformer(Undeformer):
    """
    Simple undefomer, modified to work with a common 3 axis 3d printer
    """

    def __init__(self) -> None:
        super().__init__(Defaults.threeAxisUndeformerDefaults)

        self.state: Optional[ThreeAxisDeformerState] = None

    @override
    def undeformImplementation(self, gcode: List[str]) -> Optional[List[str]]:  # noqa: C901
        if CurrentDeformerState().getState() is None:
            MAIN_LOGGER.error("Missing state, did you forget to call CurrentDeformerState.setState?")
            return None

        def undeformPoint(x: float, y: float, z: float) -> Tuple[float, float, float]:
            state = cast(ThreeAxisDeformerState, CurrentDeformerState().getState())

            radius = np.sqrt((x - state.translationX) ** 2 + (y - state.translationY) ** 2)
            z -= state.firstOrder * radius + state.secondOrder * radius ** 2
            return (x, y, z)

        gcodeList = [self.mapGcode(undeformPoint, Line(gcodeLine)).text for gcodeLine in gcode]

        return gcodeList

    @staticmethod
    def mapGcode(operation: Callable[[float, float, float], Tuple[float, float, float]], line: Line) \
            -> Line:  # noqa: C901
        """
        Transforms the gcode line by line with a transformation function
        :param operation: transformation function for points
        :param line: gcode line
        :return: the transformed line
        """
        if not line.block.gcodes:
            return line

        linearMoves = [gcode for gcode in line.block.gcodes if isinstance(gcode, GCodeLinearMove)]
        rapidLinearMoves = [gcode for gcode in line.block.gcodes if isinstance(gcode, GCodeRapidMove)]
        feedRates = [gcode for gcode in line.block.gcodes if isinstance(gcode, GCodeFeedRate)]

        if len(linearMoves) + len(rapidLinearMoves) > 1:
            MAIN_LOGGER.error(f"More than one linear move in line '{line}': {linearMoves}, {rapidLinearMoves}")
            return line

        if len(feedRates) > 1:
            MAIN_LOGGER.error(f"More than one feed rate in line '{line}': {feedRates}")
            return line

        MAIN_LOGGER.error("Not implemented")
        return line

        """
        position: Optional[List[float]] = None
        feed: Optional[float] = None
        extrusion: Optional[float] = None

        # extract position and feedrate
        if linearMoves:
            gcodeBlock: GCodeLinearMove = linearMoves[0]

            position = [0.0, 0.0, 0.0]

            if gcodeBlock.X is not None:
                position[0] = gcodeBlock.X
            if gcodeBlock.Y is not None:
                position[1] = gcodeBlock.Y
            if gcodeBlock.Z is not None:
                position[2] = gcodeBlock.Z

            gcodeBlock.X, gcodeBlock.Y, gcodeBlock.Z = operation(position[0], position[1], position[2])

            for param in line.block.modal_params:
                if param.letter == "E":
                    extrusion = float(param.value)

        if rapidLinearMoves:
            gcodeBlock: GCodeRapidMove = rapidLinearMoves[0]

            position = [0.0, 0.0, 0.0]

            if gcodeBlock.X is not None:
                position[0] = gcodeBlock.X
            if gcodeBlock.Y is not None:
                position[1] = gcodeBlock.Y
            if gcodeBlock.Z is not None:
                position[2] = gcodeBlock.Z

            gcodeBlock.X, gcodeBlock.Y, gcodeBlock.Z = operation(position[0], position[1], position[2])

        if feedRates:
            gcodeBlock: GCodeFeedRate = feedRates[0]

            feed = gcodeBlock.word.value

        return line
        """
