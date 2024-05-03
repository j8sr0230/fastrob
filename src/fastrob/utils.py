from typing import Optional, Iterator
import subprocess

import numpy as np
import awkward as ak

from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink

import FreeCAD as App
import Part
import Points

from gcodeparser import GcodeParser, GcodeLine


def slice_stl(file: str, layer_height: float, seam_width: float, perimeters: int, fill_pattern: str, fill_density: int,
              infill_angle: float, infill_anchor_max: float) -> subprocess.CompletedProcess:
    cmd: str = (
            "prusa-slicer-console.exe "

            # [ ACTIONS ]
            "--export-gcode " +

            # [ TRANSFORM ]
            "--dont-arrange " +

            # [ OPTIONS ]
            "--nozzle-diameter " + str(seam_width) + " " +
            "--first-layer-height " + str(layer_height) + " " +
            "--layer-height " + str(layer_height) + " " +
            "--first-layer-extrusion-width " + str(seam_width) + " " +
            "--extrusion-width " + str(seam_width) + " " +
            "--solid-layers 0 " +
            "--perimeters " + str(perimeters) + " " +
            "--fill-pattern " + str(fill_pattern) + " " +
            "--infill-overlap 50% " +
            "--fill-density " + str(fill_density) + "% " +
            "--fill-angle " + str(infill_angle) + " " +
            "--infill-anchor-max " + str(infill_anchor_max) + " " +
            "--skirts 0 " +
            "--filament-retract-length 0 " +

            # [ file.stl ... ]
            file
    )

    return subprocess.run(args=cmd, shell=True, capture_output=True, text=True)


def parse_g_code(file: str) -> ak.Array:
    result: list[list[list[tuple[float]]]] = []

    with open(file, "r") as f:
        gcode: list[GcodeLine] = GcodeParser(gcode=f.read(), include_comments=False).lines

        layer: list[list[tuple[float]]] = []
        path: list[tuple[float]] = []
        pos: list[float] = [0., 0., 0.]

        for idx, line in enumerate(gcode):
            if line.command[0] == "G":
                layer_change: bool = False

                if "X" in line.params.keys():
                    pos[0] = line.params["X"]
                if "Y" in line.params.keys():
                    pos[1] = line.params["Y"]
                if "Z" in line.params.keys():
                    pos[2] = line.params["Z"]
                    layer_change: bool = True

                this_has_extrusion: bool = "E" in line.params.keys() and line.params["E"] > 0
                next_has_extrusion: bool = False

                if idx < len(gcode) - 1:
                    next_line: GcodeLine = gcode[idx + 1]
                    next_has_extrusion: bool = "E" in next_line.params.keys() and next_line.params["E"] > 0

                if this_has_extrusion or (not this_has_extrusion and next_has_extrusion):
                    path.append(tuple(pos))

                if not (this_has_extrusion and next_has_extrusion):
                    if len(path) > 1:
                        dist: float = np.linalg.norm(np.array(path[0]) - np.array(path[-1]))
                        if dist < 2:
                            path.append(path[0])

                        layer.append(path.copy())
                        path.clear()

                    if layer_change:
                        if len(layer) > 0:
                            result.append(layer.copy())
                            layer.clear()

        if len(layer) > 0:
            result.append(layer.copy())

    return ak.Array(result)


def discretize_paths(paths: ak.Array, distance: int = 2) -> ak.Array:
    if paths.layout.minmax_depth == (3, 3) and distance != 0:
        result: list[list[list[App.Vector]]] = []

        for layer in paths.to_list():
            new_layer: list[list[App.Vector]] = []
            for path in layer:
                if len(path) > 1:
                    points_kernel: Points.Points = Points.Points()
                    points_kernel.addPoints(path)
                    new_layer.append(Part.makePolygon(path).discretize(Distance=distance))
            result.append(new_layer)

        result: ak.Array = ak.Array(result)
        return ak.zip([result[..., 0], result[..., 1], result[..., 2]])

    else:
        return paths


def shift_paths(paths: ak.Array, shift: list[int]) -> ak.Array:
    if paths.layout.minmax_depth == (3, 3) and len(shift) != 0:
        shift.extend([shift[-1]] * len(paths))
        result: list[list[list[App.Vector]]] = []

        for idx, layer in enumerate(paths.to_list()):
            new_layer: list[list[App.Vector]] = []
            for path in layer:
                dist: float = np.linalg.norm(np.array(path[0]) - np.array(path[-1]))
                if len(path) > 1:
                    if dist < 1:
                        new_path: list[App.Vector] = path[:-1]
                        new_path: list[App.Vector] = new_path[-shift[idx]:] + path[:-shift[idx]]
                        new_path.append(new_path[0])
                        new_layer.append(new_path)
                    else:
                        new_layer.append(path)

            result.append(new_layer)
        return ak.Array(result)

    else:
        return paths


def axis_offset(paths: ak.Array, offset: App.Vector) -> ak.Array:
    if paths.layout.minmax_depth == (3, 3) and offset != App.Vector(0, 0, 0):
        first_items: ak.Array = ak.unflatten(ak.firsts(paths, axis=-1), counts=1, axis=-1)
        first_x = first_items["0"] + offset.x
        first_y = first_items["1"] + offset.y
        first_z = first_items["2"] + offset.z
        first_items: ak.Array = ak.zip([first_x, first_y, first_z])

        last_indexes: ak.Array = ak.unflatten(ak.num(paths, axis=-1) - 1, counts=1, axis=-1)
        last_items: ak.Array = paths[last_indexes]
        last_x = last_items["0"] + offset.x
        last_y = last_items["1"] + offset.y
        last_z = last_items["2"] + offset.z
        last_items: ak.Array = ak.zip([last_x, last_y, last_z])
        return ak.concatenate([first_items, paths, last_items], axis=-1)

    else:
        return paths


def clamp_paths(paths: ak.Array, idx: int) -> ak.Array:
    if paths.layout.minmax_depth == (3, 3):
        simplified: ak.Array = ak.flatten(paths)
        lengths: ak.Array = ak.num(simplified)
        accumulated_lengths: np.ndarray = np.add.accumulate(lengths.to_list())
        completed: ak.Array = simplified[idx + 1 > accumulated_lengths]

        started_ids: np.ndarray = np.where(idx + 1 <= accumulated_lengths)
        first_started_id: Optional[int] = started_ids[0][0] if len(started_ids[0]) > 0 else None

        result: ak.Array = completed
        if first_started_id is not None:
            idx_offset: int = sum(lengths[:first_started_id])
            result: ak.Array = ak.concatenate([result, [simplified[first_started_id][:(idx + 1 - idx_offset)]]])

        return result

    else:
        return paths


def make_wires(simple_path: ak.Array) -> Part.Shape:
    if simple_path.layout.minmax_depth == (2, 2):
        vectors: list[list[App.Vector]] = []
        for path in simple_path.to_list():
            points_kernel: Points.Points = Points.Points()
            points_kernel.addPoints(path)
            vectors.append(points_kernel.Points)

        shape: Part.Shape = Part.makeCompound([Part.makePolygon(path) for path in vectors if len(path) > 1])
        return shape if len(shape.Vertexes) > 1 else Part.Shape()

    else:
        return Part.Shape()


def kinematic_chain(axis_parts: list[App.Part]) -> Optional[Chain]:
    if len(axis_parts) >= 6:
        return Chain(name="robot", links=[
            OriginLink(),
            URDFLink(name="A1", origin_translation=np.array(axis_parts[0].Placement.Base),
                     origin_orientation=np.radians(axis_parts[0].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[0].Placement.Rotation.Axis)),
            URDFLink(name="A2", origin_translation=np.array(axis_parts[1].Placement.Base),
                     origin_orientation=np.radians(axis_parts[1].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[1].Placement.Rotation.Axis)),
            URDFLink(name="A3", origin_translation=np.array(axis_parts[2].Placement.Base),
                     origin_orientation=np.radians(axis_parts[2].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[2].Placement.Rotation.Axis)),
            URDFLink(name="A4", origin_translation=np.array(axis_parts[3].Placement.Base),
                     origin_orientation=np.radians(axis_parts[3].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[3].Placement.Rotation.Axis)),
            URDFLink(name="A5", origin_translation=np.array(axis_parts[4].Placement.Base),
                     origin_orientation=np.radians(axis_parts[4].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[4].Placement.Rotation.Axis)),
            URDFLink(name="A6", origin_translation=np.array(axis_parts[5].Placement.Base),
                     origin_orientation=np.radians(axis_parts[5].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[5].Placement.Rotation.Axis)),
            URDFLink(name="TCP", origin_translation=np.array(axis_parts[6].Placement.Base),
                     origin_orientation=np.radians(axis_parts[6].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array([1, 0, 0]))
        ], active_links_mask=[False, True, True, True, True, True, True, False])


def kinematic_part_iterator(kinematic_part: App.Part) -> Iterator:
    if kinematic_part.Label.startswith("A") or kinematic_part.Label.startswith("TCP"):
        yield kinematic_part

    if hasattr(kinematic_part, "Group") and len(kinematic_part.getPropertyByName("Group")) > 0:
        for next_item in kinematic_part_iterator(kinematic_part.Group[0]):
            yield next_item
