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
from utils import slice_stl, parse_g_code_layers


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

            layer_paths = parse_g_code_layers(file=self._stl_path + ".gcode")
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
