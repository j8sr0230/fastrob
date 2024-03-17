from typing import cast

import numpy as np

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

import FreeCADGui as Gui
import FreeCAD as App
import Part


class SliceInspector(QtWidgets.QWidget):
    def __init__(self, slice_wires: list[Part.Wire], parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._wires: list[Part.Wire] = slice_wires

        self._wire_heights: list[float] = [wire.Vertexes[0].Z for wire in self._wires]
        self._wires_by_layers: np.ndarray = np.split(
            ary=np.array(self._wires), indices_or_sections=np.where(np.diff(self._wire_heights) != 0)[0] + 1
        )

        self.setWindowTitle("Slice Inspector")
        self.setMinimumWidth(320)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self._layout)

        self._layer_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._layer_label: QtWidgets.QLabel = QtWidgets.QLabel("Layer   ")
        self._layer_slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._layer_slider.setMinimum(1)
        self._layer_slider.setMaximum(len(self._wires_by_layers))
        self._layer_layout.addWidget(self._layer_label)
        self._layer_layout.addWidget(self._layer_slider)
        self._layout.addLayout(self._layer_layout)

        self._pos_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._pos_label: QtWidgets.QLabel = QtWidgets.QLabel("Position")
        self._pos_slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._pos_slider.setMinimum(0)
        self._pos_slider.setMaximum(len(slice_wires[0].Vertexes))
        self._pos_layout.addWidget(self._pos_label)
        self._pos_layout.addWidget(self._pos_slider)
        self._layout.addLayout(self._pos_layout)

        self._info_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._info_label: QtWidgets.QLabel = QtWidgets.QLabel("Layer: 30, Pos: (100, 200, 3)")
        self._info_label.setAlignment(QtCore.Qt.AlignRight)
        self._info_layout.addWidget(self._info_label)
        self._layout.addLayout(self._info_layout)

        self._current_layer: App.DocumentObject = App.ActiveDocument.addObject("Part::Feature", "current_Layer")
        self._current_layer.Label = "Current Layer"
        # self._current_layer.Shape = Part.makeBox(100, 100, 100)
        self._remaining_layer: App.DocumentObject = App.ActiveDocument.addObject("Part::Feature", "remaining_layers")
        self._remaining_layer.Label = "Remaining Layers"
        # self._remaining_layer.Shape = Part.makeBox(100, 100, 100)

        cast(QtCore.SignalInstance, self._layer_slider.valueChanged).connect(self.on_layer_value_change)
        cast(QtCore.SignalInstance, self._pos_slider.valueChanged).connect(self.on_pos_value_change)

    def on_layer_value_change(self) -> None:
        index: int = self._layer_slider.value()

        remaining_wires: np.ndarray = np.array(self._wires_by_layers[:index], dtype=object)
        self._remaining_layer.Shape = Part.makeCompound(remaining_wires.flatten())
        self._info_label.setText("Layer: " + str(index) + ", Pos: (X, Y, Z)")

    def on_pos_value_change(self) -> None:
        index: int = self._pos_slider.value()
        print("Position:", index)


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Wires) > 0 and len(selection.Shape.Vertexes) > 0:
                    slice_inspector: QtWidgets.QWidget = SliceInspector(slice_wires=selection.Shape.Wires)
                    slice_inspector.show()
                else:
                    print("Shape contains no wires.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
