import os
import subprocess

import numpy as np

from gcodeparser import GcodeParser, GcodeLine

import FreeCAD as Gui
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


def slice_stl(file: str = "", layer_height: float = 2, seam_width: float = 6, overlap: int = 50, perimeters: int = 1,
              fill_pattern: str = RECT, fill_density: int = 100, infill_angle: float = 45,
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


def slice_offset_zig_zag(file: str = "", layer_height: float = 2, seam_width: float = 6, infill_angle: float = 45
                         ) -> subprocess.CompletedProcess:

    return slice_stl(file=file, layer_height=layer_height, seam_width=seam_width, overlap=50, perimeters=1,
                     fill_pattern=RECT, fill_density=100, infill_angle=infill_angle, infill_anchor_max=100)


def slice_offset_line(file: str = "", layer_height: float = 2, seam_width: float = 6, infill_angle: float = 45
                      ) -> subprocess.CompletedProcess:

    return slice_stl(file=file, layer_height=layer_height, seam_width=seam_width, overlap=50, perimeters=1,
                     fill_pattern=RECT, fill_density=100, infill_angle=infill_angle, infill_anchor_max=0)


if __name__ == "__main__":
    dir_path: str = os.path.dirname(os.path.realpath(__file__))
    target_stl: str = str(os.path.join(dir_path, "resources", "pipe"))

    p: subprocess.CompletedProcess = slice_offset_zig_zag(
        file=target_stl + ".stl", layer_height=2, seam_width=6, infill_angle=45
    )

    # p: subprocess.CompletedProcess = slice_offset_line(
    #     file=target_stl + ".stl", layer_height=2, seam_width=6, infill_angle=0
    # )

    print(p.stdout)
    print(p.stderr)

    if not p.stderr:
        with open(target_stl + ".gcode", "r") as f:
            gcode_str: str = f.read()

            gcode: list[GcodeLine] = GcodeParser(gcode=gcode_str, include_comments=False).lines

            fc_paths: list[Part.Wire] = []
            paths: list[np.ndarray] = []
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
                            paths.append(rounded_path)

                            pts: Points.Points = Points.Points()
                            pts.addPoints(list(map(tuple, rounded_path)))
                            fc_paths.append(Part.makePolygon(pts.Points))

                            path: list[tuple[float]] = []

            if Gui.ActiveDocument:
                Part.show(Part.Compound(fc_paths))
            else:
                print(paths)
