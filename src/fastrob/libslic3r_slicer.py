import subprocess


DEBUG: bool = True


def slice_stl(stl_file_path: str = "", layer_height: float = 2, seam_width: float = 6, perimeters_num: int = 1,
              fill_density: int = 100, infill_angle: float = 45, infill_anchor_max: int = 100
              ) -> subprocess.CompletedProcess:

    prusa_slicer_process: subprocess.CompletedProcess = subprocess.run(

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
        "--infill-anchor-max " + str(infill_anchor_max) + " " +

        # [ file.stl ... ]
        stl_file_path,

        shell=True, capture_output=True, text=True
    )

    return prusa_slicer_process


if __name__ == "__main__":
    target_path: str = "./resources/cuboid.stl"

    slicer_process: subprocess.CompletedProcess = slice_stl(
        stl_file_path=target_path, layer_height=2.2, seam_width=6,
        perimeters_num=2, fill_density=100, infill_angle=45
    )

    print(slicer_process.stdout)
