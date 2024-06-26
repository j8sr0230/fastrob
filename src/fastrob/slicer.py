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
from utils import (slice_stl, parse_g_code, discretize_paths, shift_paths, axis_offset, clamp_paths,
                   make_wires)  # noqa


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


class Slicer:
    def __init__(self, feature_obj: Part.Feature, mesh: Mesh.Feature) -> None:
        feature_obj.addProperty("App::PropertyLink", "aMesh", "Slicer", "Target mesh")
        feature_obj.addProperty("App::PropertyLength", "bHeight", "Slicer", "Layer height of the slice")
        feature_obj.addProperty("App::PropertyLength", "cWidth", "Slicer", "Width of the seams")
        feature_obj.addProperty("App::PropertyInteger", "dPerimeters", "Slicer", "Number of perimeters")
        feature_obj.addProperty("App::PropertyEnumeration", "ePattern", "Slicer", "Pattern of the filling")
        feature_obj.addProperty("App::PropertyPercent", "fDensity", "Slicer", "Density of the filling")
        feature_obj.addProperty("App::PropertyAngle", "gAngle", "Slicer", "Angle of the filling")
        feature_obj.addProperty("App::PropertyLength", "hAnchor", "Slicer", "Anchor length of the filling")
        feature_obj.addProperty("App::PropertyVector", "iAxisOffset", "Slicer", "Additional offset before/after path")
        feature_obj.addProperty("App::PropertyInteger", "jDiscretize", "Slicer", "Distance between path points")
        feature_obj.addProperty("App::PropertyIntegerList", "kSeamShifts", "Slicer", "Shift of the perimeter seams")

        feature_obj.addProperty("App::PropertyEnumeration", "aMode", "Filter", "Mode of the path filter")
        feature_obj.addProperty("App::PropertyInteger", "bLayerIndex", "Filter", "Layer to be filtered")
        feature_obj.setPropertyStatus("bLayerIndex", "UserEdit")
        feature_obj.addProperty("App::PropertyInteger", "cPointIndex", "Filter", "Position to be filtered")
        feature_obj.setPropertyStatus("cPointIndex", "UserEdit")

        feature_obj.addProperty("App::PropertyVectorList", "aLocalPoints", "Result", "Points of the filtered layer(s)")
        feature_obj.addProperty("App::PropertyVector", "bLocalPoint", "Result", "Point of the filtered point index")
        feature_obj.addProperty(
            "App::PropertyVector", "cGlobalPoint", "Result", "Point of the filtered point index in global coordinates"
        )

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
        feature_obj.iAxisOffset = (0, 0, 10)
        feature_obj.jDiscretize = 0
        feature_obj.kSeamShifts = []

        feature_obj.aMode = ["None", "All", "Layer"]
        feature_obj.bLayerIndex = 0
        feature_obj.cPointIndex = 0

        feature_obj.aLocalPoints = [(0, 0, 0)]
        feature_obj.bLocalPoint = (0, 0, 0)
        feature_obj.cGlobalPoint = (0, 0, 0)

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

        self._slider: Optional[ValueSlider] = None
        self._paths: Optional[ak.Array] = None

    @property
    def paths(self) -> Optional[ak.Array]:
        return self._paths

    def reset_properties(self, feature_obj: Part.Feature) -> None:
        self._paths: Optional[ak.Array] = None

        if (hasattr(feature_obj, "bLayerIndex") and hasattr(feature_obj, "cPointIndex") and
                hasattr(feature_obj, "aLocalPoints") and hasattr(feature_obj, "bLocalPoint") and
                hasattr(feature_obj, "cGlobalPoint")):
            feature_obj.bLayerIndex = 0
            feature_obj.cPointIndex = 0
            feature_obj.aLocalPoints = [(0, 0, 0)]
            feature_obj.bLocalPoint = (0, 0, 0)
            feature_obj.cGlobalPoint = (0, 0, 0)

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
                        distance: int = feature_obj.getPropertyByName("jDiscretize")
                        temp_paths: Optional[ak.Array] = discretize_paths(self._paths, distance)

                        shifts: list[int] = feature_obj.getPropertyByName("kSeamShifts")
                        temp_paths: Optional[ak.Array] = shift_paths(temp_paths, shifts)

                        offset: App.Vector = feature_obj.getPropertyByName("iAxisOffset")
                        self._paths: Optional[ak.Array] = axis_offset(temp_paths, offset)

                        simplified: ak.Array = ak.flatten(self._paths)
                        flat: ak.Array = ak.flatten(simplified)

                        feature_obj.aLocalPoints = flat.to_list()
                        feature_obj.bLocalPoint = flat.to_list()[-1]
                        feature_obj.cGlobalPoint = (feature_obj.getGlobalPlacement().Base +
                                                    App.Vector(flat.to_list()[-1]))
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
            if self._feature_obj.getPropertyByName("aMode") == "Layer":
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
                clamped: ak.Array = clamp_paths(self._paths, clamped_point_idx)
                flat_clamped: ak.Array = ak.flatten(clamped)

                if hasattr(feature_obj, "aLocalPoints"):
                    feature_obj.aLocalPoints = flat_clamped.to_list()
                if hasattr(feature_obj, "bLocalPoint"):
                    feature_obj.bLocalPoint = flat_clamped.to_list()[-1]
                if hasattr(feature_obj, "cGlobalPoint"):
                    feature_obj.cGlobalPoint = (feature_obj.getGlobalPlacement().Base +
                                                App.Vector(flat_clamped.to_list()[-1]))

                feature_obj.Shape = make_wires(clamped)
                App.ActiveDocument.recompute()

            if hasattr(feature_obj, "aMode") and feature_obj.getPropertyByName("aMode") == "Layer":
                if hasattr(feature_obj, "bLayerIndex"):
                    layer_idx: int = feature_obj.getPropertyByName("bLayerIndex")
                    point_idx: int = feature_obj.getPropertyByName("cPointIndex")

                    clamped_layer_idx = max(0, min(layer_idx, len(self._paths) - 1))
                    layer: ak.Array = self._paths[clamped_layer_idx]
                    flat_layer: ak.Array = ak.flatten(layer)
                    clamped_point_idx = max(0, min(point_idx, len(flat_layer) - 1))
                    clamped: ak.Array = clamp_paths(ak.Array([layer]), clamped_point_idx)
                    flat_clamped: ak.Array = ak.flatten(clamped)

                    if hasattr(feature_obj, "aLocalPoints"):
                        feature_obj.aLocalPoints = flat_clamped.to_list()
                    if hasattr(feature_obj, "bLocalPoint"):
                        feature_obj.bLocalPoint = flat_clamped.to_list()[-1]
                    if hasattr(feature_obj, "cGlobalPoint"):
                        feature_obj.cGlobalPoint = (feature_obj.getGlobalPlacement().Base +
                                                    App.Vector(flat_clamped.to_list()[-1]))

                    feature_obj.Shape = make_wires(clamped)
                    App.ActiveDocument.recompute()

        if prop == "bLayerIndex" and self._paths is not None:
            if hasattr(feature_obj, "aMode") and feature_obj.getPropertyByName("aMode") == "Layer":
                layer_idx: int = feature_obj.getPropertyByName("bLayerIndex")

                clamped_idx = max(0, min(layer_idx, len(self._paths) - 1))
                layer: ak.Array = self._paths[clamped_idx]
                flat_layer: ak.Array = ak.flatten(layer)

                if hasattr(feature_obj, "aLocalPoints"):
                    feature_obj.aLocalPoints = flat_layer.to_list()
                if hasattr(feature_obj, "bLocalPoint"):
                    feature_obj.bLocalPoint = flat_layer.to_list()[-1]
                if hasattr(feature_obj, "cGlobalPoint"):
                    feature_obj.cGlobalPoint = (feature_obj.getGlobalPlacement().Base +
                                                App.Vector(flat_layer.to_list()[-1]))

                feature_obj.Shape = make_wires(layer)
                App.ActiveDocument.recompute()

        if prop in ("aMesh", "bHeight", "cWidth", "dPerimeters", "ePattern", "fDensity", "gAngle", "hAnchor",
                    "iAxisOffset", "jDiscretize", "kSeamShifts"):
            if hasattr(feature_obj, "aMode"):
                feature_obj.aMode = "None"

    def dumps(self) -> str:
        return ak.to_json(self._paths)

    def loads(self, state: str) -> None:
        paths_record: ak.Array = ak.from_json(state)
        self._paths: ak.Array = ak.zip([paths_record["0"], paths_record["1"], paths_record["2"]])
        return None


if __name__ == "__main__":
    import slicer  # noqa
    importlib.reload(slicer)
    from slicer import Slicer  # noqa

    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if type(selection) == Mesh.Feature:
                selection: Mesh.Feature = cast(Mesh.Feature, selection)

                slice_doc_obj: Part.Feature = cast(
                    Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Slicer")
                )
                Slicer(feature_obj=slice_doc_obj, mesh=selection)
                slice_doc_obj.ViewObject.Proxy = 0
            else:
                print("No mesh selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
