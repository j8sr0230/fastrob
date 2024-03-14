import subprocess


DEBUG: bool = True


def slice_stl(path: str) -> None:
    p: subprocess.Popen = subprocess.Popen(
        ("prusa-slicer-console.exe "
         "--fill-pattern concentric "
         "--export-gcode " +
         path),
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    if DEBUG:
        for line in p.stdout.readlines():
            print(str(line, "utf-8"))

        ret_val: int = p.wait()
        print(ret_val)


if __name__ == "__main__":
    slice_stl(path="./resources/cuboid.stl")
