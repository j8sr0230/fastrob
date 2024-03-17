from typing import cast

import numpy as np

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

import FreeCADGui as Gui
import FreeCAD as App
import Part


class SliceInspector(QtWidgets.QWidget):
    def __init__(self, slice_shape: Part.Shape, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._slice_shape: Part.Shape = slice_shape
        self._target_points: list[App.Vector] = self._slice_shape.Points if hasattr(self._slice_shape, "Points") else []

        self.setWindowTitle("Animation Slider")
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)

        self._slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(len(self._target_points) - 1)

        self._layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._slider)
        self.setLayout(self._layout)

        cast(QtCore.SignalInstance, self._slider.valueChanged).connect(self.on_value_change)

    def on_value_change(self) -> None:
        index: int = self._slider.value()
        self._robot_ctrl.move_to(np.array(self._target_points[index]))  # noqa


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Wires) > 0:
                    pass

                else:
                    print("Shape contains no wires.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
