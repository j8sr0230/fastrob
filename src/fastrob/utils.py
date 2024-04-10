import subprocess

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


def parse_g_code(file: str) -> list[list[list[tuple[float]]]]:
    paths: list[list[list[tuple[float]]]] = []

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
                            paths.append(layer.copy())
                            layer.clear()

        if len(layer) > 0:
            paths.append(layer.copy())

    return paths
