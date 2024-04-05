from typing import Any, cast

import os
import sys
import subprocess

from gcodeparser import GcodeParser, GcodeLine

from pivy import coin

import FreeCADGui as Gui
import FreeCAD as App
import Part
import Mesh

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
# from slice_inspector import SliceInspector
from utils import slice_stl  # , parse_g_code_layers


def parse_g_code_layers(file: str) -> list[list[list[tuple[float]]]]:
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
                    print(pos)

                this_has_extrusion: bool = "E" in line.params.keys() and line.params["E"] > 0
                next_has_extrusion: bool = False

                if idx < len(gcode) - 1:
                    next_line: GcodeLine = gcode[idx + 1]
                    next_has_extrusion: bool = "E" in next_line.params.keys() and next_line.params["E"] > 0

                if this_has_extrusion or (not this_has_extrusion and next_has_extrusion):
                    path.append(tuple(pos))

                if not this_has_extrusion:
                    if not layer_change:
                        if len(path) > 1:
                            layer.append(path.copy())
                            path.clear()
                    else:
                        if len(layer) > 0:
                            paths.append(layer.copy())
                            layer.clear()

        if len(layer) > 0:
            paths.append(layer.copy())

    return paths


class SliceObject:
    def __init__(self, feat_obj: Part.Feature, mesh: Mesh.Mesh) -> None:
        feat_obj.addProperty("App::PropertyLength", "Height", "Slicing", "Layer height of the slice").Height = 2.
        feat_obj.addProperty("App::PropertyLength", "Width", "Slicing", "Width of the seams").Width = 6.
        feat_obj.addProperty("App::PropertyInteger", "Perimeters", "Slicing", "Number of perimeters").Perimeters = 1
        feat_obj.addProperty("App::PropertyEnumeration", "Pattern", "Slicing", "Pattern of the filling").Pattern = [
            "rectilinear", "alignedrectilinear", "grid", "triangles", "stars", "cubic", "line", "concentric",
            "honeycomb", "3dhoneycomb", "gyroid", "hilbertcurve", "archimedeanchords", "conspiratorial",
            "adaptivecubic", "supportcubic", "lightning"
        ]
        feat_obj.addProperty("App::PropertyPercent", "Density", "Slicing", "Density of the filling").Density = 100
        feat_obj.addProperty("App::PropertyAngle", "Angle", "Slicing", "Angle of the filling").Angle = 45.
        feat_obj.addProperty("App::PropertyLength", "Anchor", "Slicing", "Maximal anchor of the filling").Anchor = 10.

        feat_obj.addProperty("App::PropertyInteger", "Layer", "Inspection", "Layer to be inspected").Layer = 1
        feat_obj.addProperty("App::PropertyInteger", "Position", "Inspection", "Position to be inspected").Position = 0
        # obj.addProperty("App::PropertyString", "Test")
        # obj.setPropertyStatus("Test", "UserEdit")
        feat_obj.Proxy = self

        # noinspection PyUnresolvedReferences
        self._stl_path: str = os.path.join(App.getUserAppDataDir(), "fastrob", mesh.Name.lower())
        Mesh.export([mesh], self._stl_path + ".stl")

        self._paths: list[list[list[tuple[float]]]] = []
        # self._slice_inspector: Optional[SliceInspector] = None

    @property
    def paths(self) -> list[list[list[tuple[float]]]]:
        return self._paths

    def execute(self, feat_obj: Part.Feature) -> None:
        # noinspection PyUnresolvedReferences
        p: subprocess.CompletedProcess = slice_stl(
            file=self._stl_path + ".stl",
            layer_height=float(feat_obj.Height), seam_width=float(feat_obj.Width), perimeters=int(feat_obj.Perimeters),
            fill_pattern=str(feat_obj.Pattern), fill_density=int(feat_obj.Density), infill_angle=float(feat_obj.Angle),
            infill_anchor_max=float(feat_obj.Anchor)
        )

        print(p.stdout)
        print(p.stderr)

        if not p.stderr:
            self._paths: list[list[list[tuple[float]]]] = parse_g_code_layers(file=self._stl_path + ".gcode")
            print(self._paths)

            # fp.Shape = Part.Compound(self._paths)
        else:
            feat_obj.Shape = Part.Shape()

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def onChanged(self, feat_obj: Part.Feature, prop: str) -> None:
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


class ViewProviderSliceObject:
    def __init__(self, view_obj: Any) -> None:
        self._view_obj = view_obj
        view_obj.Proxy = self

        self._switch: coin.SoSwitch = coin.SoSwitch()
        self._switch.whichChild = coin.SO_SWITCH_ALL

        self._sep: coin.SoSeparator = coin.SoSeparator()
        self._sep.ref()

        self._coords: coin.SoCoordinate3 = coin.SoCoordinate3()
        # self._coords.point.values = [(0, 0, 0), (50, 25, 0), (100, 0, 0), (100, 100, 40)]
        self._lines: coin.SoLineSet = coin.SoLineSet()
        # self._lines.numVertices.values = [2, 2]

        self._sep.addChild(self._coords)
        self._sep.addChild(self._lines)

        self._switch.addChild(self._sep)

        view_obj.RootNode.addChild(self._switch)

    # noinspection PyPep8Naming
    def updateData(self, feature_obj: Part.Feature, prop: str) -> None:
        if prop == "Layer":
            layer_idx: int = feature_obj.getPropertyByName("Layer")
            print(layer_idx)

            if layer_idx > 1:
                remaining_layers: list[list[list[tuple[float]]]] = cast(
                    SliceObject, feature_obj.Proxy
                ).paths[:layer_idx]
            else:
                remaining_layers: list[list[list[tuple[float]]]] = []

            print(remaining_layers)

            self._coords.point.values = [(0, 0, 0), (50, 25, 0), (100, 0, 0), (100, 100, 40)]
            self._lines.numVertices.values = [2, 2]

        elif prop == "Position":
            pos_idx: int = feature_obj.getPropertyByName("Position")
            print(pos_idx)

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def onChanged(self, view_obj: Any, prop: str):
        if prop == "Visibility":
            if bool(view_obj.Object.getPropertyByName("Visibility")) is False:
                self._switch.whichChild = coin.SO_SWITCH_ALL
            else:
                self._switch.whichChild = coin.SO_SWITCH_NONE


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
                SliceObject(feat_obj=slice_doc_obj, mesh=selection)
                ViewProviderSliceObject(view_obj=slice_doc_obj.ViewObject)
            else:
                print("No mesh selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
