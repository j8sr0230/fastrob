from __future__ import annotations
from typing import Optional, cast

import os
import sys
import subprocess
import importlib

import awkward as ak

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

import FreeCADGui as Gui
import FreeCAD as App
import Part
import Mesh

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

import utils
importlib.reload(utils)
from utils import slice_stl, parse_g_code, clamp_path, make_wires  # noqa


class ValueSlider(QtWidgets.QWidget):
    def __init__(self, label: str, feature_obj: Part.Feature, prop: str, min_max: tuple[int, int],
                 value: int, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Value Slider")
        self.setMinimumWidth(320)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._horizontal_layout: QtWidgets.QVBoxLayout = QtWidgets.QHBoxLayout()
        self.setLayout(self._horizontal_layout)

        self._label: QtWidgets.QLabel = QtWidgets.QLabel(label)
        self._horizontal_layout.addWidget(self._label)

        self._slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider.setMinimum(min_max[0])
        self._slider.setMaximum(min_max[1])
        self._slider.setValue(value)
        self._horizontal_layout.addWidget(self._slider)

        self._info_label: QtWidgets.QLabel = QtWidgets.QLabel()
        self._horizontal_layout.addWidget(self._info_label)

        self._feature_obj: Part.Feature = feature_obj
        self._prop: str = prop

        cast(QtCore.SignalInstance, self._slider.valueChanged).connect(self.on_value_change)

    def on_value_change(self) -> None:
        setattr(self._feature_obj, self._prop, int(self._slider.value()))
        self._info_label.setText(str(self._slider.value()))


class SliceObject:
    def __init__(self, feature_obj: Part.Feature, mesh: Mesh.Feature) -> None:
        feature_obj.addProperty("App::PropertyLink", "aMesh", "Slicing", "Target mesh")
        feature_obj.addProperty("App::PropertyLength", "bHeight", "Slicing", "Layer height of the slice")
        feature_obj.addProperty("App::PropertyLength", "cWidth", "Slicing", "Width of the seams")
        feature_obj.addProperty("App::PropertyInteger", "dPerimeters", "Slicing", "Number of perimeters")
        feature_obj.addProperty("App::PropertyEnumeration", "ePattern", "Slicing", "Pattern of the filling")
        feature_obj.addProperty("App::PropertyPercent", "fDensity", "Slicing", "Density of the filling")
        feature_obj.addProperty("App::PropertyAngle", "gAngle", "Slicing", "Angle of the filling")
        feature_obj.addProperty("App::PropertyLength", "hAnchor", "Slicing", "Anchor length of the filling")
        feature_obj.addProperty("App::PropertyEnumeration", "aMode", "Filter", "Mode of the path filter")
        # feature_obj.addProperty("App::PropertyInteger", "bLayerIndex", "Filter", "Layer to be filtered")
        feature_obj.addProperty("App::PropertyInteger", "bLayerIndex", "Filter", "Layer to be filtered")
        feature_obj.setPropertyStatus("bLayerIndex", "UserEdit")
        # feature_obj.addProperty("App::PropertyInteger", "cPointIndex", "Filter", "Position to be filtered")
        feature_obj.addProperty("App::PropertyInteger", "cPointIndex", "Filter", "Position to be filtered")
        feature_obj.setPropertyStatus("cPointIndex", "UserEdit")
        feature_obj.addProperty("App::PropertyVectorList", "aPoints", "Result", "Points of the filtered result")
        feature_obj.addProperty("App::PropertyVector", "bPoint", "Result", "Point belonging to the point index")

        feature_obj.aMesh = mesh
        feature_obj.bHeight = 2.
        feature_obj.cWidth = 6.
        feature_obj.dPerimeters = 1
        feature_obj.ePattern = [
            "rectilinear", "alignedrectilinear", "grid", "triangles", "stars", "cubic", "line", "concentric",
            "honeycomb", "3dhoneycomb", "gyroid", "hilbertcurve", "archimedeanchords", "conspiratorial",
            "adaptivecubic", "supportcubic", "lightning"
        ]
        feature_obj.fDensity = 100
        feature_obj.gAngle = 45.
        feature_obj.hAnchor = 10.
        feature_obj.aMode = ["None", "All", "Layer"]
        feature_obj.bLayerIndex = 0
        feature_obj.cPointIndex = 0
        feature_obj.aPoints = [(0, 0, 0)]
        feature_obj.bPoint = (0, 0, 0)

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

        self._slider: Optional[ValueSlider] = None
        self._paths: Optional[ak.Array] = None

    def reset_properties(self, feature_obj: Part.Feature) -> None:
        self._paths: Optional[ak.Array] = None

        if (hasattr(feature_obj, "bLayerIndex") and hasattr(feature_obj, "cPointIndex") and
                hasattr(feature_obj, "aPoints") and hasattr(feature_obj, "bPoint")):
            feature_obj.bLayerIndex = 0
            feature_obj.cPointIndex = 0
            feature_obj.aPoints = [(0, 0, 0)]
            feature_obj.bPoint = (0, 0, 0)

        feature_obj.Shape = Part.Shape()

    def execute(self, feature_obj: Part.Feature) -> None:
        if feature_obj.getPropertyByName("aMode") == "None":
            mesh: Mesh.Feature = feature_obj.getPropertyByName("aMesh")
            if mesh is not None:
                temp_path: str = os.path.join(App.getUserAppDataDir(), "fastrob", mesh.Name.lower())
                Mesh.export([mesh], temp_path + ".stl")

                # noinspection PyUnresolvedReferences
                p: subprocess.CompletedProcess = slice_stl(
                    file=temp_path + ".stl",
                    layer_height=float(feature_obj.bHeight), seam_width=float(feature_obj.cWidth),
                    perimeters=int(feature_obj.dPerimeters), fill_pattern=str(feature_obj.ePattern),
                    fill_density=int(feature_obj.fDensity), infill_angle=float(feature_obj.gAngle),
                    infill_anchor_max=float(feature_obj.hAnchor)
                )

                print(p.stdout)
                print(p.stderr)

                if not p.stderr:
                    self._paths: Optional[ak.Array] = ak.Array(parse_g_code(file=temp_path + ".gcode"))
                    if self._paths.layout.minmax_depth == (3, 3):
                        simplified: ak.Array = ak.flatten(self._paths)
                        flat: ak.Array = ak.flatten(simplified)

                        feature_obj.aPoints = flat.to_list()
                        feature_obj.bPoint = flat.to_list()[-1]
                        feature_obj.Shape = make_wires(simplified)
                    else:
                        self.reset_properties(feature_obj)
                else:
                    self.reset_properties(feature_obj)
            else:
                self.reset_properties(feature_obj)

    # noinspection PyPep8Naming
    def editProperty(self, prop: str) -> None:
        if prop == "bLayerIndex" and self._paths is not None:
            if self._feature_obj.getPropertyByName("aMode") in ("All", "Layer"):
                self._slider: ValueSlider = ValueSlider("Layer Index", self._feature_obj, prop,
                                                        (0, len(self._paths) - 1),
                                                        self._feature_obj.getPropertyByName("bLayerIndex"))
                self._slider.show()

        elif prop == "cPointIndex" and self._paths is not None:
            if self._feature_obj.getPropertyByName("aMode") == "All":
                simplified: ak.Array = ak.flatten(self._paths)
                flat: ak.Array = ak.flatten(simplified)

                self._slider: ValueSlider = ValueSlider("Point Index", self._feature_obj, prop, (0, len(flat) - 1),
                                                        self._feature_obj.getPropertyByName("cPointIndex"))
                self._slider.show()

            elif self._feature_obj.getPropertyByName("aMode") == "Layer":
                layer_idx: int = self._feature_obj.getPropertyByName("bLayerIndex")
                clamped_layer_idx = max(0, min(layer_idx, len(self._paths) - 1))
                layer: ak.Array = self._paths[clamped_layer_idx]
                flat_layer: ak.Array = ak.flatten(layer)

                self._slider: ValueSlider = ValueSlider("Point Index", self._feature_obj, prop,
                                                        (0, len(flat_layer) - 1),
                                                        self._feature_obj.getPropertyByName("cPointIndex"))
                self._slider.show()

    # noinspection PyPep8Naming
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        if not hasattr(self, "_feature_obj"):
            self._feature_obj: Part.Feature = feature_obj

        if prop == "cPointIndex" and self._paths is not None:
            if hasattr(feature_obj, "aMode") and feature_obj.getPropertyByName("aMode") == "All":
                point_idx: int = feature_obj.getPropertyByName("cPointIndex")

                simplified: ak.Array = ak.flatten(self._paths)
                flat: ak.Array = ak.flatten(simplified)

                clamped_point_idx = max(0, min(point_idx, len(flat) - 1))
                clamped: ak.Array = clamp_path(self._paths, clamped_point_idx)
                flat_clamped: ak.Array = ak.flatten(clamped)

                if hasattr(feature_obj, "aPoints") and hasattr(feature_obj, "bPoint"):
                    feature_obj.aPoints = flat_clamped.to_list()
                    feature_obj.bPoint = flat_clamped.to_list()[-1]

                feature_obj.Shape = make_wires(clamped)

            if hasattr(feature_obj, "aMode") and feature_obj.getPropertyByName("aMode") == "Layer":
                if hasattr(feature_obj, "bLayerIndex"):
                    layer_idx: int = feature_obj.getPropertyByName("bLayerIndex")
                    point_idx: int = feature_obj.getPropertyByName("cPointIndex")

                    clamped_layer_idx = max(0, min(layer_idx, len(self._paths) - 1))
                    layer: ak.Array = self._paths[clamped_layer_idx]
                    flat_layer: ak.Array = ak.flatten(layer)
                    clamped_point_idx = max(0, min(point_idx, len(flat_layer) - 1))
                    clamped: ak.Array = clamp_path(ak.Array([layer]), clamped_point_idx)
                    flat_clamped: ak.Array = ak.flatten(clamped)

                    if hasattr(feature_obj, "aPoints") and hasattr(feature_obj, "bPoint"):
                        feature_obj.aPoints = flat_clamped.to_list()
                        feature_obj.bPoint = flat_clamped.to_list()[-1]

                    feature_obj.Shape = make_wires(clamped)

        if prop == "bLayerIndex" and self._paths is not None:
            if hasattr(feature_obj, "aMode") and feature_obj.getPropertyByName("aMode") == "Layer":
                layer_idx: int = feature_obj.getPropertyByName("bLayerIndex")

                clamped_idx = max(0, min(layer_idx, len(self._paths) - 1))
                layer: ak.Array = self._paths[clamped_idx]
                flat_layer: ak.Array = ak.flatten(layer)

                if hasattr(feature_obj, "aPoints") and hasattr(feature_obj, "bPoint"):
                    feature_obj.aPoints = flat_layer.to_list()
                    feature_obj.bPoint = flat_layer.to_list()[-1]

                feature_obj.Shape = make_wires(layer)

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
