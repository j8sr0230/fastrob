import subprocess


DEBUG: bool = False


p: subprocess.Popen = subprocess.Popen(
    "prusa-slicer-console.exe --export-gcode ./resources/cuboid.stl",
    shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)

if DEBUG:
    for line in p.stdout.readlines():
        print(str(line, "utf-8"))

ret_val: int = p.wait()
