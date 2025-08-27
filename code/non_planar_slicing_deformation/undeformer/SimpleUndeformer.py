from typing_extensions import override, Optional, List, cast

import numpy as np

import pygcode as pg  # type: ignore

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.configuration.CurrentDeformerState import CurrentDeformerState
from non_planar_slicing_deformation.state.SimpleDeformerState import SimpleDeformerState
from non_planar_slicing_deformation.undeformer.Undeformer import Undeformer
from non_planar_slicing_deformation.undeformer.gcode.FastMove import FastMove
from non_planar_slicing_deformation.undeformer.gcode.GcodeLineType import GcodeLineType, Move
from non_planar_slicing_deformation.undeformer.gcode.SlowMove import SlowMove
from non_planar_slicing_deformation.undeformer.gcode.Comment import Comment


class SimpleUndeformer(Undeformer):
    """
    Simple undefomer, original implementation by Joshua Bird at https://github.com/jyjblrd/Radial_Non_Planar_Slicer.
    """

    def __init__(self) -> None:
        super().__init__(Defaults.simpleUndeformerDefaults)

        self.state: Optional[SimpleDeformerState] = None

    def _readGcode(self, state: SimpleDeformerState, gcode: List[str]) -> List[GcodeLineType]:  # noqa: C901
        pos = np.array([0., 0., 20.])
        feed = 0.0
        gcodePoints: List[GcodeLineType] = []

        for gcodeLine in map(pg.Line, gcode):
            if not gcodeLine.block.gcodes:
                if gcodeLine.comment:
                    gcodePoints.append(Comment(text=gcodeLine.text.rstrip()))
                continue

            nextGcodeBlock = None
            prev_pos = np.array([0, 0, 0], dtype=np.float64)

            # extract position and feedrate
            for gcodeBlock in sorted(gcodeLine.block.gcodes):
                if gcodeBlock.word in ["G01", "G00"]:
                    nextGcodeBlock = gcodeBlock
                    prev_pos = pos.copy()

                    if gcodeBlock.X is not None:
                        pos[0] = gcodeBlock.X
                    if gcodeBlock.Y is not None:
                        pos[1] = gcodeBlock.Y
                    if gcodeBlock.Z is not None:
                        pos[2] = gcodeBlock.Z

                if gcodeBlock.word.letter == "F":
                    feed = float(gcodeBlock.word.value)

            if nextGcodeBlock is None:
                continue

            extrusion = None
            # extract extrusion
            for param in gcodeLine.block.modal_params:
                if param.letter == "E":
                    extrusion = param.value

            # segment moves
            # prevents G0 (rapid moves) from hitting the part
            # makes G1 (feed moves) less jittery
            delta_pos = pos - prev_pos
            distance: float = cast(float, np.linalg.norm(delta_pos))
            if distance > 0 and nextGcodeBlock.word == "G01":
                seg_size = 1  # mm
                num_segments = -(-distance // seg_size)  # hacky round up
                seg_distance = distance / num_segments

                # calculate inverse time feed
                time_to_complete_move = (1 / feed) * seg_distance  # min/mm * mm = min
                if time_to_complete_move == 0:
                    inv_time_feed = None
                else:
                    inv_time_feed = 1 / time_to_complete_move  # 1/min

                for i in range(int(num_segments)):
                    gcodePoints.append(SlowMove(
                        position=(prev_pos + delta_pos * (i + 1) / num_segments) + state.offsetsApplied,
                        command=nextGcodeBlock.word,
                        extrusion=extrusion / num_segments if extrusion is not None else None,
                        inverseTimeFeed=inv_time_feed,
                        moveLength=seg_distance,
                        startPosition=prev_pos,
                        endPosition=pos,
                        unsegmentedMoveLength=distance
                        ))
            else:
                gcodePoints.append(FastMove(
                    position=pos.copy() + state.offsetsApplied,
                    command=nextGcodeBlock.word,
                    extrusion=extrusion,
                    inverseTimeFeed=None,
                    moveLength=0
                    ))

        return gcodePoints

    @override
    def undeformImplementation(self, gcode: List[str]) -> Optional[List[str]]:  # noqa: C901
        if CurrentDeformerState().getState() is None:
            MAIN_LOGGER.error("Missing state, did you forget to call CurrentDeformerState.setState?")
            return None

        state = cast(SimpleDeformerState, CurrentDeformerState().getState())

        # TODO split this into functions

        # read gcode
        gocdeCommands = self._readGcode(state, gcode)
        gcodeMoves = [point for point in gocdeCommands if isinstance(point, Move)]

        # untransform gcode
        positions = np.array([point.position for point in gcodeMoves], dtype=np.float64)
        distances_to_center = np.linalg.norm(positions[:, :2], axis=1)
        translate_upwards = np.hstack([
            np.zeros((len(positions), 2)),
            np.tan(state.rotation(distances_to_center).reshape(-1, 1)) * distances_to_center.reshape(-1, 1)
            ], dtype=np.float64)

        new_positions = positions - translate_upwards

        # cap travel move height to be just above the part and to not travel over the origin
        max_z = 0
        for i, command in enumerate(gcodeMoves):
            if command.command == "G01":
                max_z = np.max(np.array([max_z, new_positions[i, 2]]))
        for i, command in enumerate(gcodeMoves):
            if command.command == "G00":
                if new_positions[i, 2] > max_z:
                    new_positions[i] = None

        # rescale extrusion by change in move_length
        prev_pos = np.array([0., 0., 0.])
        for i, command in enumerate(gcodeMoves):
            if command.extrusion is not None and command.moveLength != 0:
                extrusion_scale = cast(float, np.linalg.norm(new_positions[i] - prev_pos) / command.moveLength)
                command.extrusion *= min(extrusion_scale, 10.0)
            prev_pos = new_positions[i]

        # rescale extrusion to compensate for rotation deformation
        distances_to_center = np.linalg.norm(new_positions[:, :2], axis=1)
        extrusion_scales = np.cos(state.rotation(distances_to_center))
        for i, command in enumerate(gcodeMoves):
            if command.extrusion is not None:
                command.extrusion *= extrusion_scales[i]

        NOZZLE_OFFSET = np.float64(42.5)  # mm

        prev_r = np.float64(0)
        prev_theta = np.float64(0)
        prev_z = np.float64(20)

        theta_accum = 0
        positionIndex = 0

        # save transformed gcode
        outputLines: List[str] = []
        # write header
        outputLines.append("G94 ; mm/min feed  ")
        outputLines.append("G28 ; home ")
        outputLines.append("M83 ; relative extrusion ")
        outputLines.append("G1 E10 ; prime extruder ")
        outputLines.append("G94 ; mm/min feed ")
        outputLines.append("G90 ; absolute positioning ")
        outputLines.append(f"G0 C{prev_theta} X{prev_r} Z{prev_z} B{-np.rad2deg(state.rotation(np.float64(0)))}")
        outputLines.append("G93 ; inverse time feed ")

        for command in gocdeCommands:
            if isinstance(command, Comment):
                outputLines.append(f"{command.text}")
                continue
            if isinstance(command, Move):
                position = new_positions[positionIndex, :]

                if position is None:
                    continue

                if np.all(np.isnan(position)):
                    continue

                if position[2] < 0:
                    continue

                # If you want to print on another type of 4 axis printer, you will need to change next code
                # convert to polar coordinates
                r = np.float64(np.linalg.norm(position[:2]))  # mypy needs the cast for some reason
                theta = np.arctan2(position[1], position[0])
                z = position[2]

                rotation = state.rotation(r)

                # compensate for nozzle offset
                r += np.sin(rotation) * NOZZLE_OFFSET
                z += (np.cos(rotation) - 1) * NOZZLE_OFFSET

                delta_theta = theta - prev_theta
                if delta_theta > np.pi:
                    delta_theta -= 2 * np.pi
                if delta_theta < -np.pi:
                    delta_theta += 2 * np.pi

                theta_accum += delta_theta

                string = f"{
                    command.command} C{
                    np.rad2deg(theta_accum):.5f} X{
                    r:.5f} Z{
                    z:.5f} B{
                    -np.rad2deg(rotation):.5f}"
                # If you want to print on another type of 4 axis printer, you will need to change previous code

                if command.extrusion is not None:
                    string += f" E{command.extrusion:.4f}"

                no_feed_value = False
                if command.inverseTimeFeed is not None:
                    string += f" F{command.inverseTimeFeed:.4f}"
                else:
                    string += " F50000"
                    outputLines.append("G94")
                    no_feed_value = True

                outputLines.append(string)

                if no_feed_value:
                    outputLines.append("G93")  # back to inv feed

                # update previous values
                prev_r = r
                prev_theta = theta
                prev_z = z

                positionIndex += 1

        return outputLines
