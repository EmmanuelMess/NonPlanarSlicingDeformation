import time

import numpy as np
from pygcode import Line  # type: ignore
from typing_extensions import override, List, cast, Dict, Any, Optional, Tuple

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.CurrentDeformerState import CurrentDeformerState
from non_planar_slicing_deformation.deformer.s4_deformer import S4Functions
from non_planar_slicing_deformation.state.S4DeformerState import S4DeformerState
from non_planar_slicing_deformation.undeformer.worker.UndeformerWorker import UndeformerWorker


class S4UndeformerWorker(UndeformerWorker):
    """
    S4 undeformer, original implementation by Joshua Bird at https://github.com/jyjblrd/S4_Slicer.
    """

    def _readGcode(self, gcode: List[str], SEG_SIZE: float) -> List[Dict[str, Any]]:  # noqa: C901
        # read gcode
        pos = np.array([0., 0., 20.])
        feed = 5000
        gcode_points = []
        for line_text in gcode:
            line = Line(line_text)

            if not line.block.gcodes:
                continue

            for gcodeLine in sorted(line.block.gcodes):
                if gcodeLine.word == "G01" or gcodeLine.word == "G00":
                    prev_pos = pos.copy()

                    if gcodeLine.X is not None:
                        pos[0] = gcodeLine.X
                    if gcodeLine.Y is not None:
                        pos[1] = gcodeLine.Y
                    if gcodeLine.Z is not None:
                        pos[2] = gcodeLine.Z

                    inv_time_feed = None
                    # extract feed
                    for word in line.block.words:
                        if word.letter == "F":
                            feed = word.value

                    # extract extrusion
                    extrusion = None
                    for param in line.block.modal_params:
                        if param.letter == "E":
                            extrusion = param.value

                    # segment moves
                    # makes G1 (feed moves) less jittery
                    delta_pos: np.ndarray = pos - prev_pos
                    distance = np.linalg.norm(delta_pos)
                    if distance > 0:
                        num_segments = -(-distance // SEG_SIZE)  # hacky round up
                        seg_distance = distance / num_segments

                        # calculate inverse time feed
                        time_to_complete_move = (1 / feed) * seg_distance  # min/mm * mm = min
                        if time_to_complete_move == 0:
                            inv_time_feed = None
                        else:
                            inv_time_feed = 1 / time_to_complete_move  # 1/min

                        for i in range(int(num_segments)):
                            gcode_points.append({
                                "position": (prev_pos + delta_pos * (i + 1) / num_segments),
                                "command": gcodeLine.word,
                                "extrusion": extrusion / num_segments if extrusion is not None else None,
                                "inv_time_feed": inv_time_feed,
                                "move_length": seg_distance,
                                "start_position": prev_pos,
                                "end_position": pos,
                                "unsegmented_move_length": distance,
                                "after_retract": False,
                                "feed": feed
                                })
                    else:
                        # calculate inverse time feed
                        time_to_complete_move = (1 / feed) * distance  # min/mm * mm = min
                        if time_to_complete_move == 0:
                            inv_time_feed = None
                        else:
                            inv_time_feed = 1 / time_to_complete_move  # 1/min

                        gcode_points.append({
                            "position": pos.copy(),
                            "command": gcodeLine.word,
                            "extrusion": extrusion,
                            "inv_time_feed": inv_time_feed,
                            "move_length": distance,
                            "unsegmented_move_length": distance,
                            "after_retract": False,
                            "feed": feed
                            })

                    # # add G0 in same spot after retraction (so we can use it for zhop later)
                    # if gcodeLine.word == "G01" and extrusion is not None and extrusion < 0:
                    #     gcode_points.append({
                    #         "position": pos.copy(),
                    #         "command": "G00",
                    #         "extrusion": None,
                    #         "inv_time_feed": None,
                    #         "move_length": 0,
                    #         "after_retract": True
                    #     })

        return gcode_points

    @override
    def run(self) -> None:  # noqa: C901
        startTime = time.time()

        if self.gcode is None or self.parameters is None:
            self.result.emit(None)
            return

        if CurrentDeformerState().getState() is None:
            MAIN_LOGGER.error("Missing state, did you forget to call CurrentDeformerState.setState?")
            self.result.emit(None)
            return

        state: S4DeformerState = cast(S4DeformerState, CurrentDeformerState().getState())

        home_all = self.parameters["home all", bool]
        heat_up_extruder = self.parameters["heat extruder", bool]
        temperature = self.parameters["heat extruder temperature", int]
        nozzleOffset = cast(float, self.parameters["nozzle offset", float])

        SEG_SIZE = 0.6  # mm
        MAX_ROTATION = 30  # degrees
        MIN_ROTATION = -130  # degrees

        deformed_tet, _, _ = S4Functions.calculate_tet_attributes(state.deformed_tet, state.cell_neighbour_graph)

        # find how each vertex in tet has been transformed
        vertex_transformations = deformed_tet.points - state.input_tet.points

        # calculate tangential vectors (axis of rotation) for each cell
        tangential_vectors = np.cross(np.array([0, 0, 1]), state.input_tet.cell_data["cell_center"][:, :2])
        # normalize
        tangential_vectors /= np.linalg.norm(tangential_vectors, axis=1)[:, None]
        # replace nan with [1,0,0]
        tangential_vectors[np.isnan(tangential_vectors).any(axis=1)] = [1, 0, 0]

        # calculate rotation for each vertex and cell
        num_cells_per_vertex = np.zeros((state.input_tet.number_of_points))
        for cell_index, cell in enumerate(state.input_tet.field_data["cells"]):
            num_cells_per_vertex[cell] += 1
        vertex_rotations = np.zeros((deformed_tet.number_of_points))
        cell_rotations = np.zeros((deformed_tet.number_of_cells))
        for cell_index, cell in enumerate(deformed_tet.field_data["cells"]):
            new_vertices = deformed_tet.field_data["cell_vertices"][cell]
            new_cell_center = deformed_tet.cell_data["cell_center"][cell_index]
            old_vertices = state.input_tet.field_data["cell_vertices"][cell]
            old_cell_center = state.input_tet.cell_data["cell_center"][cell_index]

            # center points
            new_vertices -= new_cell_center
            old_vertices -= old_cell_center

            # project on to radial plane
            plane_x_vector = old_cell_center[:2] / np.linalg.norm(old_cell_center[:2])
            plane_x_vector = np.array([plane_x_vector[0], plane_x_vector[1], 0])
            plane_y_vector = np.array([0, 0, 1])

            new_vertices_projected = S4Functions.project_point_onto_plane(plane_x_vector, plane_y_vector, new_vertices)
            old_vertices_projected = S4Functions.project_point_onto_plane(plane_x_vector, plane_y_vector, old_vertices)

            # find rotation between the two sets of points using the kabsch algorithm
            covariance_matrix = np.dot(new_vertices_projected.T, old_vertices_projected)
            U, _, Vt = np.linalg.svd(covariance_matrix)
            rotation_matrix = np.dot(U, Vt)

            # get rotation angle from matrix 2x2
            rotation = -np.arccos(min(max(rotation_matrix[0, 0], -1), 1))
            if rotation_matrix[1, 0] < 0:
                rotation = -rotation

            rotation = max(min(rotation, np.deg2rad(MAX_ROTATION)), np.deg2rad(MIN_ROTATION))

            cell_rotations[cell_index] = rotation

            for vertex_index in cell:
                vertex_rotations[vertex_index] += rotation / num_cells_per_vertex[vertex_index]

        # calculate z squish scale for each cell (ratio of z length after rotation to z length before rotation)
        z_squish_scales = np.full((deformed_tet.number_of_cells), np.nan)
        for cell_index, cell in enumerate(deformed_tet.field_data["cells"]):
            warped_vertices = deformed_tet.field_data["cell_vertices"][cell]
            unwarped_vertices = state.input_tet.field_data["cell_vertices"][cell]

            # rotate new vertices to align with old vertices
            # unwarped_vertices_rotated = (
            #     (tet_rotation_matrices[cell_index].reshape(1, 3, 3) @ unwarped_vertices.reshape(4, 3, 1))
            #     .reshape(4, 3)
            # )

            # calculate z squish scale
            # z_squish_scales[cell_index] = (
            #   (unwarped_vertices_rotated[:, 2].max() - unwarped_vertices_rotated[:, 2].min())
            #   / (warped_vertices[:, 2].max() - warped_vertices[:, 2].min())
            # )
            z_squish_scales[cell_index] = S4Functions.tetrahedron_volume(
                *unwarped_vertices) / S4Functions.tetrahedron_volume(*warped_vertices)
            # z_squish_scales[cell_index] = min(z_squish_scales[cell_index], 5) # cap z squish scale

        gcode_points = self._readGcode(self.gcode, SEG_SIZE)

        # calculate containging cell for each gcode point
        gcode_points_containing_cells = cast(List[int], deformed_tet.find_containing_cell([
                                             point["position"] for point in gcode_points]))

        # for cells with no containing cell, find the closest cell
        gcode_points_closest_cells = cast(List[int], deformed_tet.find_closest_cell([
                                          point["position"] for point in gcode_points]))
        # gcode_points_containing_cells[gcode_points_containing_cells == -1] =
        #       gcode_points_closest_cells[gcode_points_containing_cells == -1]

        # transform gcode points to original mesh's shape
        new_gcode_points = []
        prev_new_position = None
        travelling_over_air = False
        travelling = False
        prev_rotation = 0
        prev_travelling = False
        prev_command = "G00"
        ROTATION_AVERAGING_ALPHA = 0.2  # exponential moving average alpha for rotation
        RETRACTION_LENGTH = 1.0
        ROTATION_MAX_DELTA = np.deg2rad(1)
        MAX_EXTRUSION_MULTIPLIER = 10
        lost_vertices = []
        highest_printed_point = 0
        for cell_index, (gcode_point, containing_cell_index) in enumerate(
                zip(gcode_points, gcode_points_containing_cells)):
            position: np.ndarray = gcode_point["position"]
            command: str = gcode_point["command"]
            inv_time_feed: Optional[float] = gcode_point["inv_time_feed"]
            extrusion: Optional[float] = gcode_point["extrusion"]

            def barycentric_interpolate_to_get_new_position_and_rotation(position: np.ndarray,
                                                                         containing_cell_index: int,
                                                                         command: str,
                                                                         cell_index: int) \
                    -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
                if command == "G00" and containing_cell_index == -1:  # Strict on travel moves being inside a tet
                    return None, None
                if command == "G01" and containing_cell_index == -1:  # Slightly more relaxed on printing moves
                    containing_cell_index = gcode_points_closest_cells[cell_index]

                # get barycentric coordinates of pos in containing cell
                vertiex_indices = deformed_tet.field_data["cells"][containing_cell_index]
                cell_vertices = deformed_tet.field_data["cell_vertices"][vertiex_indices]
                barycentric_coordinates = S4Functions.calc_barycentric_coordinates(
                    cell_vertices[0], cell_vertices[1], cell_vertices[2], cell_vertices[3], position)

                if np.sum(barycentric_coordinates) > 1.01:
                    return None, None

                # calculate the new position of the point using the barycentric coordinates
                # to weigh the vertex transformations
                # multiply barycentric coordinates row-wise with vertex transformations
                transformation = vertex_transformations[vertiex_indices] * barycentric_coordinates[:, None]

                # sum columns
                transformation = np.sum(transformation, axis=0)
                # apply to pos
                new_position = position - transformation

                # do the same for rotation
                rotation = np.sum(vertex_rotations[vertiex_indices] * barycentric_coordinates)

                return new_position, rotation

            dont_smooth_rotation = False
            new_position, rotation = barycentric_interpolate_to_get_new_position_and_rotation(position,
                                                                                              containing_cell_index,
                                                                                              command, cell_index)
            if new_position is None:
                if command == "G01":
                    lost_vertices.append(position)
                    continue
                elif command == "G00" and not travelling_over_air and prev_new_position is not None:
                    new_position = np.array(
                        [prev_new_position[0], prev_new_position[1], highest_printed_point])  # z hop over gap
                    # set rotation to a max of 45 because if rotation is very large, the
                    # extruder can "hang below" the nozzle and hit the part
                    rotation = max(min(prev_rotation, np.deg2rad(45)), np.deg2rad(-45))
                    dont_smooth_rotation = True  # force rotation immediately
                    travelling_over_air = True
                elif travelling_over_air:
                    continue
                else:
                    continue
            else:
                if travelling_over_air:
                    new_position[2] = highest_printed_point  # finish z hop over gap
                    # set rotation to 0 because if rotation is very large, the extruder can
                    # "hang below" the nozzle and hit the part
                    rotation = max(min(rotation, np.deg2rad(45)), np.deg2rad(-45))
                    dont_smooth_rotation = True  # force rotation immediately
                travelling_over_air = False

            extrusion_multiplier = 1
            if extrusion is not None and extrusion != RETRACTION_LENGTH and extrusion != -RETRACTION_LENGTH:

                # scale extrusion by z_squish_scale
                extrusion_multiplier = extrusion_multiplier * z_squish_scales[containing_cell_index]
                extrusion = extrusion * min(extrusion_multiplier, MAX_EXTRUSION_MULTIPLIER)
            elif extrusion == -RETRACTION_LENGTH:
                travelling = True
            elif extrusion == RETRACTION_LENGTH:
                travelling = False
            if prev_rotation is not None and not dont_smooth_rotation:
                rotation = ROTATION_AVERAGING_ALPHA * rotation + (1 - ROTATION_AVERAGING_ALPHA) * prev_rotation

            # if rotation delta between points is too high, add intermediate
            # interpolation points to prevent nozzle from hitting part as rotating
            if prev_rotation is not None and prev_new_position is not None and np.abs(
                    rotation - prev_rotation) > ROTATION_MAX_DELTA:
                delta_rotation = rotation - prev_rotation
                num_interpolations = int(np.abs(delta_rotation) / ROTATION_MAX_DELTA) + 1
                delta_pos = new_position - prev_new_position
                for i in range(num_interpolations):
                    new_gcode_points.append({
                        "position": prev_new_position + (delta_pos * ((i + 1) / num_interpolations)),
                        "original_position": position,
                        "rotation": prev_rotation + (delta_rotation * ((i + 1) / num_interpolations)),
                        "command": prev_command,
                        "extrusion": extrusion / num_interpolations if extrusion is not None else None,
                        "inv_time_feed": inv_time_feed * num_interpolations if inv_time_feed is not None else None,
                        "extrusion_multiplier": extrusion_multiplier,
                        "feed": gcode_point["feed"],
                        "travelling": prev_travelling
                        })
            else:
                new_gcode_points.append({
                    "position": new_position,
                    "original_position": position,
                    "rotation": rotation,
                    "command": command,
                    "extrusion": extrusion,
                    "inv_time_feed": inv_time_feed,
                    "extrusion_multiplier": extrusion_multiplier,
                    "feed": gcode_point["feed"],
                    "travelling": travelling
                    })

            prev_rotation = rotation
            prev_new_position = new_position.copy()
            prev_travelling = travelling
            prev_command = command

            if command == "G01" and extrusion is not None and extrusion > 0 and (
                    highest_printed_point != 0 or new_position[2] < 1):
                highest_printed_point = max(highest_printed_point, new_position[2])

        MAIN_LOGGER.warning(f"Lost {len(lost_vertices)} vertices")

        prev_r = 0
        prev_theta = 0
        prev_z = 20

        theta_accum = 0

        outputLines: List[str] = []

        # save transformed gcode
        # write header
        outputLines.append("G94 ; mm/min feed ")
        if home_all:
            outputLines.append("G28 ; home ")
        if heat_up_extruder:
            outputLines.append(f"M104 S{temperature} ; Heat extruder 0°C to {temperature}°C ")
            outputLines.append(f"M109 S{temperature} ; Heat extruder 0°C to {temperature}°C and wait")
        outputLines.append("M83 ; relative extrusion")
        outputLines.append("G1 E10 ; prime extruder")
        outputLines.append("G94 ; mm/min feed")
        outputLines.append("G90 ; absolute positioning")
        outputLines.append(f"G0 C{prev_theta} X{prev_r} Z{prev_z} B0 ; go to start")
        outputLines.append("G93 ; inverse time feed")

        for i, point in enumerate(new_gcode_points):
            position = point["position"]
            rotation = point["rotation"]

            if np.all(np.isnan(position)):
                continue

            if position[2] < 0:
                continue

            z_hop = 0
            if point["travelling"]:
                z_hop = 1

            # convert to polar coordinates
            r = np.linalg.norm(position[:2])
            theta = np.arctan2(position[1], position[0])
            z = position[2]

            # compensate for nozzle offset
            r += -np.sin(rotation) * (nozzleOffset + z_hop)
            z += (np.cos(rotation) - 1) * (nozzleOffset + z_hop) + z_hop

            delta_theta = theta - prev_theta
            if delta_theta > np.pi:
                delta_theta -= 2 * np.pi
            if delta_theta < -np.pi:
                delta_theta += 2 * np.pi

            theta_accum += delta_theta

            # polar printer
            string = f"{point['command']} C{np.rad2deg(theta_accum):.5f} X{r:.5f} Z{z:.5f} B{np.rad2deg(rotation):.5f}"
            # string = f"{point['command']} X{position[0]:.5f} Y{position[1]:.5f}
            # Z{position[2]} B{np.rad2deg(rotation):.5f}" # cartesian printer (3 axis)

            if point["extrusion"] is not None:
                string += f" E{point['extrusion']:.4f}"

            no_feed_value = False
            if point["inv_time_feed"] is not None:
                string += f" F{(point['inv_time_feed']):.4f}"
            else:
                string += " F20000"
                outputLines.append("G94")
                no_feed_value = True

            outputLines.append(string)

            if no_feed_value:
                outputLines.append("G93")  # back to inv feed

            # update previous values
            prev_r = r
            prev_theta = theta
            prev_z = z

        outputLines.append("G90 ; absolute positioning ")
        outputLines.append("G0 Z200 ; Move extruder up")
        outputLines.append("M400 ; wait for moves to finish")
        outputLines.append("G0 B0 ; rotate extruder to 0°")
        outputLines.append("M400 ; wait for moves to finish")

        if heat_up_extruder:
            outputLines.append("M104 S0 ; Heat extruder to 0°C")

        endTime = time.time()

        MAIN_LOGGER.debug(f"Undeform time {endTime - startTime}s")

        self.result.emit(outputLines)
