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
            " --first-layer-height " + str(layer_height) + " " +
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


if __name__ == "__main__":
    dir_path: str = os.path.dirname(os.path.realpath(__file__))
    target_stl: str = str(os.path.join(dir_path, "resources", "cuboid"))

    p: subprocess.CompletedProcess = slice_offset_zig_zag(
        file=target_stl + ".stl", layer_height=2, seam_width=6, infill_angle=45
    )

    print(p.stdout)
    print(p.stderr)

    if not p.stderr:
        with open(target_stl + ".gcode", "r") as f:
            gcode_str: str = f.read()

        gcode: list[GcodeLine] = GcodeParser(gcode=gcode_str, include_comments=False).lines
        for line in gcode:
            # TODO: Extract paths
            print(line)
