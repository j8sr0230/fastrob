from __future__ import annotations
from typing import Optional, cast

import os
import sys
import subprocess
import importlib

import awkward as ak

import FreeCADGui as Gui
import FreeCAD as App
import Part
import Mesh

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

import utils
importlib.reload(utils)
from utils import slice_stl, parse_g_code, clamp_path, make_wires  # noqa


class SliceObject:
    def __init__(self, feature_obj: Part.Feature, mesh: Mesh.Feature) -> None:
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

        feature_obj.addProperty("App::PropertyInteger", "LayerIndex", "Inspection", "Layer to be evaluated")
        feature_obj.LayerIndex = -1
        feature_obj.addProperty("App::PropertyInteger", "PointIndex", "Inspection", "Position to be evaluated")
        feature_obj.PointIndex = -1

        feature_obj.addProperty("App::PropertyVectorList", "Points", "Result", "Points of the paths")
        feature_obj.Points = [(0, 0, 0)]
        feature_obj.addProperty("App::PropertyVector", "Point", "Result", "Current point").Point = (0, 0, 0)

        feature_obj.Proxy = self

        self._paths: Optional[ak.Array] = None

    def execute(self, feature_obj: Part.Feature) -> None:
        layer_idx: int = feature_obj.getPropertyByName("LayerIndex")
        point_idx: int = feature_obj.getPropertyByName("PointIndex")

        if layer_idx == -1 and point_idx == -1:
            mesh: Mesh.Feature = feature_obj.getPropertyByName("Mesh")
            if mesh is not None:
                temp_path: str = os.path.join(App.getUserAppDataDir(), "fastrob", mesh.Name.lower())
                Mesh.export([mesh], temp_path + ".stl")

                # noinspection PyUnresolvedReferences
                p: subprocess.CompletedProcess = slice_stl(
                    file=temp_path + ".stl",
                    layer_height=float(feature_obj.Height), seam_width=float(feature_obj.Width),
                    perimeters=int(feature_obj.Perimeters), fill_pattern=str(feature_obj.Pattern),
                    fill_density=int(feature_obj.Density), infill_angle=float(feature_obj.Angle),
                    infill_anchor_max=float(feature_obj.Anchor)
                )

                print(p.stdout)
                print(p.stderr)

                if not p.stderr:
                    self._paths: Optional[ak.Array] = ak.Array(parse_g_code(file=temp_path + ".gcode"))
                    simplified: ak.Array = ak.flatten(self._paths)
                    flat: ak.Array = ak.flatten(simplified)

                    feature_obj.PointIndex = len(flat)
                    feature_obj.Points = flat.to_list()
                    feature_obj.Point = flat.to_list()[-1]
                    feature_obj.Shape = make_wires(simplified)
                else:
                    self._paths: Optional[ak.Array] = None
                    feature_obj.Points = [(0, 0, 0)]
                    feature_obj.Point = (0, 0, 0)
                    feature_obj.Shape = Part.Shape()
            else:
                self._paths: Optional[ak.Array] = None
                feature_obj.Points = [(0, 0, 0)]
                feature_obj.Point = (0, 0, 0)
                feature_obj.Shape = Part.Shape()

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        if self._paths is not None:
            layer_idx: int = feature_obj.getPropertyByName("LayerIndex")
            point_idx: int = feature_obj.getPropertyByName("PointIndex")

            if prop == "LayerIndex":
                if layer_idx > -1:
                    clamped_idx = max(0, min(layer_idx, len(self._paths) - 1))
                    layer: ak.Array = self._paths[clamped_idx]
                    flat_layer: ak.Array = ak.flatten(layer)

                    feature_obj.PointIndex = len(flat_layer) - 1
                    feature_obj.Points = flat_layer.to_list()
                    feature_obj.Point = flat_layer.to_list()[-1]
                    feature_obj.Shape = make_wires(layer)
                else:
                    simplified: ak.Array = ak.flatten(self._paths)
                    flat: ak.Array = ak.flatten(simplified)

                    feature_obj.PointIndex = len(flat)
                    feature_obj.Points = flat.to_list()
                    feature_obj.Point = flat.to_list()[-1]
                    feature_obj.Shape = make_wires(simplified)

            elif prop == "PointIndex":
                if layer_idx > -1:
                    clamped_layer_idx = max(0, min(layer_idx, len(self._paths) - 1))
                    layer: ak.Array = self._paths[clamped_layer_idx]
                    flat_layer: ak.Array = ak.flatten(layer)

                    clamped_point_idx = max(0, min(point_idx, len(flat_layer) - 1))
                    clamped: ak.Array = clamp_path(ak.Array([layer]), clamped_point_idx)
                    flat_clamped: ak.Array = ak.flatten(clamped)

                    feature_obj.Points = flat_clamped.to_list()
                    feature_obj.Point = flat_clamped.to_list()[-1]
                    feature_obj.Shape = make_wires(clamped)
                else:
                    pass
                    # feature_obj.LayerIndex = -1
                    # simplified: ak.Array = ak.flatten(self._paths)
                    # flat: ak.Array = ak.flatten(simplified)
                    #
                    # feature_obj.PointIndex = len(flat)
                    # feature_obj.Points = flat.to_list()
                    # feature_obj.Point = flat.to_list()[-1]
                    # feature_obj.Shape = make_wires(simplified)
        else:
            feature_obj.LayerIndex = -1
            feature_obj.PointIndex = -1
            feature_obj.Points = [(0, 0, 0)]
            feature_obj.Points = (0, 0, 0)
            feature_obj.Shape = Part.Shape()

    def dumps(self) -> dict:
        return ak.to_json(self._paths)

    def loads(self, state: dict) -> None:
        paths_record: ak.Array = ak.from_json(state)
        self._paths: ak.Array = ak.zip([paths_record["0"], paths_record["1"], paths_record["2"]])
        return None


if __name__ == "__main__":
    import slice_object  # noqa
    importlib.reload(slice_object)
    from slice_object import SliceObject  # noqa

    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if type(selection) == Mesh.Feature:
                selection: Mesh.Feature = cast(Mesh.Feature, selection)

                slice_doc_obj: Part.Feature = cast(
                    Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Slice")
                )
                SliceObject(feature_obj=slice_doc_obj, mesh=selection)
                slice_doc_obj.ViewObject.Proxy = 0
                # ViewProviderSliceObject(view_obj=slice_doc_obj.ViewObject)
            else:
                print("No mesh selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
