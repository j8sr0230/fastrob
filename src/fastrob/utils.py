from typing import Optional
import subprocess

import numpy as np
import awkward as ak

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
                        layer.append(path.copy())
                        path.clear()

                    if layer_change:
                        if len(layer) > 0:
                            result.append(layer.copy())
                            layer.clear()

        if len(layer) > 0:
            result.append(layer.copy())

    return ak.Array(result)


def clamp_path(path: ak.Array, idx: int) -> ak.Array:
    simplified: ak.Array = ak.flatten(path)
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


def make_wires(simple_path: ak.Array) -> Part.Shape:
    vectors: list[list[App.Vector]] = []
    for path in simple_path.to_list():
        points_kernel: Points.Points = Points.Points()
        points_kernel.addPoints(path)
        vectors.append(points_kernel.Points)

    shape: Part.Shape = Part.makeCompound([Part.makePolygon(path) for path in vectors if len(path) > 1])
    return shape if len(shape.Vertexes) > 1 else Part.Shape()
