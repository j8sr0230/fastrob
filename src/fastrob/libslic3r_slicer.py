import subprocess


DEBUG: bool = True


def slice_stl(stl_file: str, layer_height: float, seam_width: float, perimeters_num: int, fill_density: int, infill_angle: float) -> None:
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
                stl_file
        ),
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    if DEBUG:
        for line in p.stdout.readlines():
            print(str(line, "utf-8"))

        ret_val: int = p.wait()
        print(ret_val)


if __name__ == "__main__":
    slice_stl(
        stl_file="./resources/cuboid.stl",
        layer_height=3,
        seam_width=5,
        perimeters_num=1,
        fill_density=50,
        infill_angle=45
    )
