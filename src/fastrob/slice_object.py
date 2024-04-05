from typing import cast

import os
import sys
import subprocess

import FreeCADGui as Gui
import FreeCAD as App
import Part
import Mesh
import numpy as np
import awkward as ak

from gcodeparser import GcodeParser, GcodeLine

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
# from slice_inspector import SliceInspector
from utils import slice_stl


def parse_g_code(file: str) -> ak.Array:
    paths: list[list[tuple[float]]] = []

    with open(file, "r") as f:
        gcode: list[GcodeLine] = GcodeParser(gcode=f.read(), include_comments=False).lines
        App.Console.PrintLog(gcode)

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
                        paths.append(path.copy())
                        path.clear()

    if len(paths) > 1:
        heights: np.ndarray = np.array([p[0][-1] for p in paths])
        extended_heights: np.ndarray = np.hstack([0, heights, heights[-1] + 1])
        paths_per_layer = np.diff(np.where(np.diff(extended_heights) > 0)[0] + 1)
        return ak.unflatten(paths, counts=paths_per_layer, axis=0)

    else:
        return ak.Array(paths)


def parse_g_code_l(file: str) -> list[np.ndarray]:
    paths: list[list[list[tuple[float]]]] = []

    with open(file, "r") as f:
        gcode: list[GcodeLine] = GcodeParser(gcode=f.read(), include_comments=False).lines
        App.Console.PrintLog(gcode)

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
                    if not layer_change:
                        if len(path) > 1:
                            layer.append(path.copy())
                            path.clear()
                    else:
                        if len(layer) > 1:
                            paths.append(layer.copy())
                            layer.clear()
                            path.clear()

        if len(layer) > 0:
            paths.append(layer)

        return paths


class SliceObject:
    def __init__(self, obj: Part.Feature, mesh: Mesh.Mesh) -> None:
        obj.addProperty("App::PropertyLength", "Height", "Slicing", "Layer height of the slice").Height = 2.
        obj.addProperty("App::PropertyLength", "Width", "Slicing", "Width of the seams").Width = 6.
        obj.addProperty("App::PropertyInteger", "Perimeters", "Slicing", "Number of perimeters").Perimeters = 1
        obj.addProperty("App::PropertyEnumeration", "Pattern", "Slicing", "Pattern of the filling").Pattern = [
            "rectilinear", "alignedrectilinear", "grid", "triangles", "stars", "cubic", "line", "concentric",
            "honeycomb", "3dhoneycomb", "gyroid", "hilbertcurve", "archimedeanchords", "conspiratorial",
            "adaptivecubic", "supportcubic", "lightning"
        ]
        obj.addProperty("App::PropertyPercent", "Density", "Slicing", "Density of the filling").Density = 100
        obj.addProperty("App::PropertyAngle", "Angle", "Slicing", "Angle of the filling").Angle = 45.
        obj.addProperty("App::PropertyLength", "Anchor", "Slicing", "Maximal anchor of the filling").Anchor = 10.

        obj.addProperty("App::PropertyInteger", "Layer", "Inspection", "Layer to be inspected").Layer = 1
        obj.addProperty("App::PropertyInteger", "Position", "Inspection", "Position to be inspected").Position = 0
        # obj.addProperty("App::PropertyString", "Test")
        # obj.setPropertyStatus("Test", "UserEdit")
        obj.Proxy = self

        # noinspection PyUnresolvedReferences
        self._stl_path: str = os.path.join(App.getUserAppDataDir(), "fastrob", mesh.Name.lower())
        Mesh.export([mesh], self._stl_path + ".stl")

        self._paths: list[Part.Wire] = []
        # self._slice_inspector: Optional[SliceInspector] = None

    def execute(self, fp: Part.Feature) -> None:
        # noinspection PyUnresolvedReferences
        p: subprocess.CompletedProcess = slice_stl(
            file=self._stl_path + ".stl",
            layer_height=float(fp.Height), seam_width=float(fp.Width), perimeters=int(fp.Perimeters),
            fill_pattern=str(fp.Pattern), fill_density=int(fp.Density), infill_angle=float(fp.Angle),
            infill_anchor_max=float(fp.Anchor)
        )

        print(p.stdout)
        print(p.stderr)

        if not p.stderr:
            # self._paths: list[Part.Wire] = parse_g_code(file=self._stl_path + ".gcode", as_wires=True)

            layer_paths = parse_g_code_l(file=self._stl_path + ".gcode")
            print(layer_paths)

            # fp.Shape = Part.Compound(self._paths)
        else:
            fp.Shape = Part.Shape()

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def onChanged(self, fp: Part.Feature, prop: str) -> None:
        pass
        # if prop == "Length" or prop == "Width" or prop == "Height":
        #     fp.Shape = Part.makeBox(fp.Length, fp.Width, fp.Height)

    # noinspection PyPep8Naming
    # def editProperty(self, prop) -> None:
    #     if prop == "PropTest":
    #         self._slice_inspector = SliceInspector(self._paths)
    #         self._slice_inspector.show()

    # text, ok = QtWidgets.QInputDialog.getText(Gui.getMainWindow(), "Object", prop)
    # if ok:
    #     App.setActiveTransaction("Edit %s.%s" % (self.Object.Label, prop))
    #     self.Object.PropTest = text
    #     App.closeActiveTransaction()


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Mesh"):
                selection: Mesh.Mesh = cast(Mesh.Mesh, selection)

                slice_doc_obj: Part.Feature = cast(
                    Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Slice")
                )
                SliceObject(obj=slice_doc_obj, mesh=selection)
                slice_doc_obj.ViewObject.Proxy = 0
            else:
                print("No mesh selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
