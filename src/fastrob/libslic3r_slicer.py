import subprocess


DEBUG: bool = True


def slice_stl(stl_file_path: str = "", layer_height: float = 2, seam_width: float = 6, perimeters_num: int = 1,
              fill_density: int = 100, infill_angle: float = 45) -> int:
    p: subprocess.Popen = subprocess.Popen(
        (
                "prusa-slicer-console.exe "  
                
                # [ ACTIONS ]
                "--export-gcode " +

                # [ TRANSFORM ]
                "--dont-arrange " +

                # [ OPTIONS ]
                "--nozzle-diameter 10 " +
                "--layer-height " + str(layer_height) + " " +
                "--extrusion-width " + str(seam_width) + " " +
                "--solid-layers 0 " +
                "--perimeters " + str(perimeters_num) + " " +
                "--fill-pattern rectilinear " +
                "--fill-density " + str(fill_density) + "% " +
                "--fill-angle " + str(infill_angle) + " " +
                "--infill-anchor-max 0 " +

                # [ file.stl ... ]
                stl_file_path
        ),
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    if DEBUG:
        for line in p.stdout.readlines():
            print(str(line, "utf-8"))

    return p.wait()


if __name__ == "__main__":
    target_path: str = "./resources/cuboid.stl"
    slice_stl(
        stl_file_path=target_path, layer_height=3, seam_width=5,
        perimeters_num=1, fill_density=50, infill_angle=45
    )
