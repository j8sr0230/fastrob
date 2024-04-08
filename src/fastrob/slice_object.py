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

from utils import slice_stl, parse_g_code_layers


class SliceObject:
    def __init__(self, feature_obj: Part.Feature, mesh: Mesh.Mesh) -> None:
        feature_obj.addProperty("App::PropertyLink", "Mesh", "Slicing", "Target mesh").Mesh = mesh
        feature_obj.addProperty("App::PropertyLength", "Height", "Slicing", "Layer height of the slice").Height = 2.
        feature_obj.addProperty("App::PropertyLength", "Width", "Slicing", "Width of the seams").Width = 6.
        feature_obj.addProperty("App::PropertyInteger", "Perimeters", "Slicing", "Number of perimeters").Perimeters = 1
        feature_obj.addProperty("App::PropertyEnumeration", "Pattern", "Slicing", "Pattern of the filling").Pattern = [
            "rectilinear", "alignedrectilinear", "grid", "triangles", "stars", "cubic", "line", "concentric",
            "honeycomb", "3dhoneycomb", "gyroid", "hilbertcurve", "archimedeanchords", "conspiratorial",
            "adaptivecubic", "supportcubic", "lightning"
        ]
        feature_obj.addProperty("App::PropertyPercent", "Density", "Slicing", "Density of the filling").Density = 100
        feature_obj.addProperty("App::PropertyAngle", "Angle", "Slicing", "Angle of the filling").Angle = 45.
        feature_obj.addProperty("App::PropertyLength", "Anchor", "Slicing", "Anchor length of the filling").Anchor = 10.
        feature_obj.Proxy = self

        self._temp_path: str = ""
        self._paths: Optional[ak.Array] = None

    @property
    def paths(self) -> Optional[ak.Array]:
        return self._paths

    # noinspection PyMethodMayBeStatic, PyUnusedLocal
    def execute(self, feat_obj: Part.Feature) -> None:
        mesh: Mesh.Feature = feat_obj.getPropertyByName("Mesh")
        if mesh is not None:
            self._temp_path: str = os.path.join(App.getUserAppDataDir(), "fastrob", mesh.Name.lower())
            Mesh.export([mesh], self._temp_path + ".stl")
        else:
            self._temp_path: str = ""

        if self._temp_path != "":
            # noinspection PyUnresolvedReferences
            p: subprocess.CompletedProcess = slice_stl(
                file=self._temp_path + ".stl",
                layer_height=float(feat_obj.Height), seam_width=float(feat_obj.Width),
                perimeters=int(feat_obj.Perimeters), fill_pattern=str(feat_obj.Pattern),
                fill_density=int(feat_obj.Density), infill_angle=float(feat_obj.Angle),
                infill_anchor_max=float(feat_obj.Anchor)
            )

            print(p.stdout)
            print(p.stderr)

            if not p.stderr:
                self._paths: ak.Array = ak.Array(parse_g_code_layers(file=self._temp_path + ".gcode"))
        else:
            self._paths: Optional[ak.Array] = None

        feat_obj.ViewObject.update()

    def dumps(self) -> tuple[str, dict]:
        return self._temp_path, ak.to_json(self._paths)

    def loads(self, state: tuple[str, dict]) -> None:
        self._temp_path: str = state[0]
        paths_record: ak.Array = ak.from_json(state[1])
        self._paths: ak.Array = ak.zip([paths_record["0"], paths_record["1"], paths_record["2"]])
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
    def dumps(self) -> None:
        return None

    # noinspection PyUnusedLocal
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
                SliceObject(feature_obj=slice_doc_obj, mesh=selection)
                ViewProviderSliceObject(view_obj=slice_doc_obj.ViewObject)
            else:
                print("No mesh selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
