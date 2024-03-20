from typing import cast
# import os
import subprocess

# import numpy as np
# from gcodeparser import GcodeParser, GcodeLine

import FreeCAD as App
import Part

# import Points

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
        obj.addProperty("App::PropertyLength", "Length", "Dimensions", "Length of the box").Length = 10.
        obj.addProperty("App::PropertyLength", "Width", "Dimensions", "Width of the box").Width = 10.
        obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Height of the box").Height = 10.
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

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnresolvedReferences
    def execute(self, fp: Part.Feature) -> None:
        fp.Shape = Part.makeBox(fp.Length, fp.Width, fp.Height)

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal, PyUnresolvedReferences
    def onChanged(self, fp: Part.Feature, prop: str) -> None:
        if prop == "Length" or prop == "Width" or prop == "Height":
            fp.Shape = Part.makeBox(fp.Length, fp.Width, fp.Height)


slice_doc_obj: Part.Feature = cast(Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Slice"))
SliceObject(slice_doc_obj)
slice_doc_obj.ViewObject.Proxy = 0
