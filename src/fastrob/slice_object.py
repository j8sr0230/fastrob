from typing import cast
import os
import subprocess

import numpy as np
from gcodeparser import GcodeParser, GcodeLine

import FreeCAD as App
import Part
import Points

# FILLING patterns
RECT: str = "rectilinear"
ALIGNED_RECT: str = "alignedrectilinear"
GRID: str = "grid"
TRI: str = "triangles"
STARS: str = "stars"
CUBIC: str = "cubic"
LINE: str = "line"
CONCENTRIC: str = "concentric"
HONEY: str = "honeycomb"
HONEY_3D: str = "3dhoneycomb"
GYROID: str = "gyroid"
HILBERT: str = "hilbertcurve"
ARCHIMEDEAN: str = "archimedeanchords"
CONSPIRATORIAL: str = "conspiratorial"
ADAPTIVE_CUBOID: str = "adaptivecubic"
SUPPORT_CUBICS: str = "supportcubic"
LIGHT: str = "lightning"

DEBUG: bool = True


class SliceObject:
    def __init__(self, obj: Part.Feature) -> None:
        obj.addProperty("App::PropertyLength", "Height", "Slicing", "Layer height of the slice").Height = 2.
        obj.addProperty("App::PropertyLength", "Width", "Slicing", "Width of the seam").Width = 6.
        obj.addProperty("App::PropertyAngle", "Angle", "Slicing", "Angle of the filling").Angle = 45.
        obj.Proxy = self

    @staticmethod
    def slice_stl(file: str = "", layer_height: float = 2, seam_width: float = 6, overlap: int = 50,
                  perimeters: int = 1, fill_pattern: str = RECT, fill_density: int = 100, infill_angle: float = 45,
                  infill_anchor_max: int = 100) -> subprocess.CompletedProcess:
        cmd: str = (
                "prusa-slicer-console.exe "  # "superslicer_console.exe "  

                # [ ACTIONS ]
                "--export-gcode " +

                # [ TRANSFORM ]
                "--dont-arrange " +

                # [ OPTIONS ]
                "--nozzle-diameter " + str((overlap / 100) * seam_width) + " " +
                "--first-layer-height " + str(layer_height) + " " +
                "--layer-height " + str(layer_height) + " " +
                "--first-layer-extrusion-width " + str((overlap / 100) * seam_width) + " " +
                "--extrusion-width " + str((overlap / 100) * seam_width) + " " +
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

    def slice_offset_zig_zag(self, file: str = "", layer_height: float = 2, seam_width: float = 6,
                             infill_angle: float = 45) -> subprocess.CompletedProcess:
        return self.slice_stl(file=file, layer_height=layer_height, seam_width=seam_width, overlap=50, perimeters=1,
                              fill_pattern=RECT, fill_density=100, infill_angle=infill_angle, infill_anchor_max=100)

    def slice_offset_line(self, file: str = "", layer_height: float = 2, seam_width: float = 6,
                          infill_angle: float = 45) -> subprocess.CompletedProcess:
        return self.slice_stl(file=file, layer_height=layer_height, seam_width=seam_width, overlap=50, perimeters=1,
                              fill_pattern=RECT, fill_density=100, infill_angle=infill_angle, infill_anchor_max=0)

    def execute(self, fp: Part.Feature) -> None:
        dir_path: str = os.path.dirname(os.path.realpath(__file__))
        target_stl: str = str(os.path.join(dir_path, "resources", "cuboid"))

        # noinspection PyUnresolvedReferences
        p: subprocess.CompletedProcess = self.slice_offset_zig_zag(
            file=target_stl + ".stl", layer_height=float(fp.Height), seam_width=float(fp.Width),
            infill_angle=float(fp.Angle)
        )

        # p: subprocess.CompletedProcess = self.slice_offset_line(
        #     file=target_stl + ".stl", layer_height=2, seam_width=6, infill_angle=0
        # )

        print(p.stdout)
        print(p.stderr)

        if not p.stderr:
            with open(target_stl + ".gcode", "r") as f:
                gcode_str: str = f.read()

                gcode: list[GcodeLine] = GcodeParser(gcode=gcode_str, include_comments=False).lines

                fc_paths: list[Part.Wire] = []
                # paths: list[np.ndarray] = []
                path: list[tuple[float]] = []
                pos: list[float] = [0., 0., 0.]

                for idx, line in enumerate(gcode):
                    is_g_cmd: bool = line.command[0] == "G"
                    current_has_extrusion: bool = "E" in line.params.keys() and line.params["E"] > 0

                    next_has_extrusion: bool = False
                    if idx < len(gcode) - 1:
                        next_line: GcodeLine = gcode[idx + 1]
                        next_has_extrusion: bool = "E" in next_line.params.keys() and next_line.params["E"] > 0

                    if is_g_cmd:
                        if "X" in line.params.keys():
                            pos[0] = line.params["X"]
                        if "Y" in line.params.keys():
                            pos[1] = line.params["Y"]
                        if "Z" in line.params.keys():
                            pos[2] = line.params["Z"]

                        if current_has_extrusion or (not current_has_extrusion and next_has_extrusion):
                            path.append(tuple(pos))

                        if not current_has_extrusion:
                            if len(path) > 1:
                                rounded_path: np.ndarray = np.round(path, 1)
                                # paths.append(rounded_path)

                                pts: Points.Points = Points.Points()
                                pts.addPoints(list(map(tuple, rounded_path)))
                                fc_paths.append(Part.makePolygon(pts.Points))

                                path: list[tuple[float]] = []

                fp.Shape = Part.Compound(fc_paths)
        else:
            fp.Shape = Part.Shape()

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal, PyUnresolvedReferences
    def onChanged(self, fp: Part.Feature, prop: str) -> None:
        pass
        # if prop == "Length" or prop == "Width" or prop == "Height":
        #     fp.Shape = Part.makeBox(fp.Length, fp.Width, fp.Height)


slice_doc_obj: Part.Feature = cast(Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Slice"))
SliceObject(slice_doc_obj)
slice_doc_obj.ViewObject.Proxy = 0
