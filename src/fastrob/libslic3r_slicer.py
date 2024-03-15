import os
import subprocess

from gcodeparser import GcodeParser, GcodeLine


DEBUG: bool = True

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


def slice_stl(stl_file_path: str = "", layer_height: float = 2, seam_width: float = 6, perimeters_num: int = 1,
              fill_pattern: str = RECT, fill_density: int = 100, infill_angle: float = 45,
              infill_anchor_max: int = 100) -> subprocess.CompletedProcess:

    slice_cmd: str = (
            "superslicer_console.exe "  # "prusa-slicer-console.exe "  
        
            # [ ACTIONS ]
            "--export-gcode " +

            # [ TRANSFORM ]
            "--dont-arrange " +

            # [ OPTIONS ]
            "--nozzle-diameter 5 " +
            "--layer-height " + str(layer_height) + " " +
            # "--extrusion-width " + str(seam_width) + " " +
            "--extrusion-spacing " + str(3) + " " +
            # "--solid-layers 0 " +
            "--perimeters " + str(perimeters_num) + " " +
            "--fill-pattern " + str(fill_pattern) + " "
            # "infill-overlap 50% "
    )

    if fill_pattern == RECT:
        slice_cmd += (
            "--fill-density " + str(fill_density) + "% " +
            "--fill-angle " + str(infill_angle) + " " +
            "--infill-anchor-max " + str(infill_anchor_max) + " "
        )

    slice_cmd += stl_file_path

    prusa_slicer_process: subprocess.CompletedProcess = subprocess.run(
        args=slice_cmd, shell=True, capture_output=True, text=True
    )

    return prusa_slicer_process


if __name__ == "__main__":
    dir_path: str = os.path.dirname(os.path.realpath(__file__))
    target_stl: str = str(os.path.join(dir_path, "resources", "cuboid"))

    slicer_process: subprocess.CompletedProcess = slice_stl(
        stl_file_path=target_stl + ".stl", layer_height=2, seam_width=5, perimeters_num=0, fill_pattern=RECT,
        fill_density=100, infill_angle=0, infill_anchor_max=0
    )

    print(slicer_process.stdout)
    print(slicer_process.stderr)

    with open(target_stl + ".gcode", "r") as f:
        gcode_str: str = f.read()

    gcode: list[GcodeLine] = GcodeParser(gcode=gcode_str, include_comments=False).lines
    for line in gcode:
        print(line)
