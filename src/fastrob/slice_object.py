from typing import Any, Optional, cast

import os
import sys
import subprocess

import awkward as ak

from pivy import coin

import FreeCADGui as Gui
import FreeCAD as App
import Part
import Mesh

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
# from slice_inspector import SliceInspector
from utils import slice_stl, parse_g_code_layers


class SliceObject:
    def __init__(self, feat_obj: Part.Feature, mesh: Mesh.Mesh) -> None:
        feat_obj.addProperty("App::PropertyLink", "Mesh", "Slicing", "Target mesh").Mesh = mesh
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

        # obj.addProperty("App::PropertyString", "Test")
        # obj.setPropertyStatus("Test", "UserEdit")
        feat_obj.Proxy = self

        # noinspection PyUnresolvedReferences
        self._stl_path: str = ""
        # Mesh.export([mesh], self._stl_path + ".stl")

        self._paths: Optional[ak.Array] = None
        self.onChanged(feat_obj, "Mesh")

        # self._slice_inspector: Optional[SliceInspector] = None

    @property
    def paths(self) -> ak.Array:
        return self._paths

    # noinspection PyMethodMayBeStatic, PyUnusedLocal
    def execute(self, feat_obj: Part.Feature) -> None:
        print("Exec fo")

    # noinspection PyPep8Naming
    def onChanged(self, feat_obj: Part.Feature, prop: str) -> None:
        print("Change fo")
        if prop == "Mesh":
            # noinspection PyUnresolvedReferences
            if feat_obj.Mesh is not None:
                # noinspection PyUnresolvedReferences
                self._stl_path: str = os.path.join(App.getUserAppDataDir(), "fastrob", feat_obj.Mesh.Name.lower())
                # noinspection PyUnresolvedReferences
                Mesh.export([feat_obj.Mesh], self._stl_path + ".stl")
            else:
                self._stl_path: str = ""

        if prop in ("Mesh", "Height", "Width", "Perimeters", "Pattern", "Density", "Angle", "Anchor"):
            if self._stl_path != "":
                # noinspection PyUnresolvedReferences
                p: subprocess.CompletedProcess = slice_stl(
                    file=self._stl_path + ".stl",
                    layer_height=float(feat_obj.Height), seam_width=float(feat_obj.Width),
                    perimeters=int(feat_obj.Perimeters), fill_pattern=str(feat_obj.Pattern),
                    fill_density=int(feat_obj.Density), infill_angle=float(feat_obj.Angle),
                    infill_anchor_max=float(feat_obj.Anchor)
                )

                print(p.stdout)
                print(p.stderr)

                if not p.stderr:
                    self._paths: ak.Array = ak.Array(parse_g_code_layers(file=self._stl_path + ".gcode"))
            else:
                self._paths: Optional[ak.Array] = None

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

    def dumps(self) -> tuple[str, list]:
        return self._stl_path, self._paths.to_list()

    def loads(self, state: tuple[str, list]) -> None:
        self._stl_path: str = state[0]
        self._paths: ak.Array = ak.Array(state[1])
        return None


class ViewProviderSliceObject:
    def __init__(self, view_obj: Any) -> None:
        view_obj.addProperty("App::PropertyInteger", "Layer", "Inspection", "Layer to be inspected", 0).Layer = 1
        view_obj.addProperty("App::PropertyInteger", "Position", "Inspection", "Position to be inspected").Position = 0

        self._switch: coin.SoSwitch = coin.SoSwitch()
        self._switch.whichChild = coin.SO_SWITCH_ALL
        self._sep: coin.SoSeparator = coin.SoSeparator()
        self._sep.ref()
        self._coords: coin.SoCoordinate3 = coin.SoCoordinate3()
        self._lines: coin.SoLineSet = coin.SoLineSet()
        self._sep.addChild(self._coords)
        self._sep.addChild(self._lines)
        self._switch.addChild(self._sep)

        view_obj.Proxy = self

    # noinspection PyPep8Naming
    def updateData(self, feature_obj: Part.Feature, prop: str) -> None:
        print("Update vo")
        if self._switch not in feature_obj.ViewObject.RootNode.getChildren():
            feature_obj.ViewObject.RootNode.addChild(self._switch)

        if prop in ("Mesh", "Height", "Width", "Perimeters", "Pattern", "Density", "Angle", "Anchor"):
            paths: Optional[ak.Array] = cast(SliceObject, feature_obj.Proxy).paths
            if paths is not None and len(paths) > 1:
                feature_obj.ViewObject.Layer = len(paths)

                remaining_layers: ak.Array = paths[:len(paths) - 1]
                self._coords.point.values = ak.flatten(ak.flatten(remaining_layers)).to_list()
                self._lines.numVertices.values = ak.flatten(ak.num(remaining_layers, axis=-1), axis=None).to_list()

            else:
                feature_obj.ViewObject.Layer = 0
                self._coords.point.values = []
                self._lines.numVertices.values = []

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def onChanged(self, view_obj: Any, prop: str):
        print("Change vo")
        if prop == "Visibility":
            if bool(view_obj.Object.Visibility) is False:
                self._switch.whichChild = coin.SO_SWITCH_ALL
            else:
                self._switch.whichChild = coin.SO_SWITCH_NONE

        elif prop == "Layer":
            layer_idx: int = view_obj.getPropertyByName("Layer")
            paths: Optional[ak.Array] = cast(SliceObject, view_obj.Object.Proxy).paths
            if layer_idx > 1 and paths is not None:
                remaining_layers: ak.Array = paths[:layer_idx - 1]
                self._coords.point.values = ak.flatten(ak.flatten(remaining_layers)).to_list()
                self._lines.numVertices.values = ak.flatten(ak.num(remaining_layers, axis=-1), axis=None).to_list()
            else:
                self._coords.point.values = []
                self._lines.numVertices.values = []

        elif prop == "Position":
            pos_idx: int = view_obj.getPropertyByName("Position")
            print(pos_idx)

    # noinspection PyMethodMayBeStatic
    def dumps(self) -> Optional[tuple[Any]]:
        return None

    # noinspection PyUnusedLocal, PyMethodMayBeStatic
    def loads(self, state: Optional[tuple[Any]]) -> None:
        self._switch: coin.SoSwitch = coin.SoSwitch()
        self._sep: coin.SoSeparator = coin.SoSeparator()
        self._sep.ref()
        self._coords: coin.SoCoordinate3 = coin.SoCoordinate3()
        self._lines: coin.SoLineSet = coin.SoLineSet()
        self._sep.addChild(self._coords)
        self._sep.addChild(self._lines)
        self._switch.addChild(self._sep)
        return None


if __name__ == "__main__":
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    # noinspection PyUnresolvedReferences
    from slice_object import SliceObject, ViewProviderSliceObject

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
