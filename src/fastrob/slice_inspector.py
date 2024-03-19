from typing import cast

import numpy as np

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

import FreeCADGui as Gui
import FreeCAD as App
import Part


class SliceInspector(QtWidgets.QWidget):
    def __init__(self, paths: list[Part.Wire], parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._paths: list[Part.Wire] = paths

        self._path_heights: list[float] = [wire.Vertexes[0].Z for wire in self._paths]
        self._paths_by_layers: np.ndarray = np.split(
            ary=np.array(self._paths), indices_or_sections=np.where(np.diff(self._path_heights) != 0)[0] + 1
        )

        self._layer_index: int = 1
        self._current_layer: np.ndarray[Part.Wire] = self._paths_by_layers[self._layer_index - 1]
        self._remaining_layers: np.ndarray[Part.Wire] = np.array([])

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
        self._layer_slider.setMaximum(len(self._paths_by_layers))
        self._layer_layout.addWidget(self._layer_label)
        self._layer_layout.addWidget(self._layer_slider)
        self._layout.addLayout(self._layer_layout)

        self._pos_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._pos_label: QtWidgets.QLabel = QtWidgets.QLabel("Position")
        self._pos_slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._pos_slider.setMinimum(1)
        self._pos_slider.setMaximum(100)
        self._pos_layout.addWidget(self._pos_label)
        self._pos_layout.addWidget(self._pos_slider)
        self._layout.addLayout(self._pos_layout)

        self._info_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._info_label: QtWidgets.QLabel = QtWidgets.QLabel(
            "Layer: 1 " +
            ", Pos 1: " + str(np.round(self._current_layer[0].Vertexes[0].Point, 1))  # noqa
        )
        self._info_layout.addWidget(self._info_label)
        self._layout.addLayout(self._info_layout)

        self._current_layer_obj: App.DocumentObject = App.ActiveDocument.addObject("Part::Feature", "current_Layer")
        self._current_layer_obj.Label = "Current Layer"
        self._current_layer_obj.ViewObject.LineColor = (30, 30, 30)

        self._remaining_layers_obj: App.DocumentObject = App.ActiveDocument.addObject("Part::Feature",
                                                                                      "remaining_layers")
        self._remaining_layers_obj.Label = "Remaining Layers"
        self._remaining_layers_obj.ViewObject.LineColor = (150, 150, 150)

        cast(QtCore.SignalInstance, self._layer_slider.valueChanged).connect(self.on_layer_change)
        cast(QtCore.SignalInstance, self._pos_slider.valueChanged).connect(self.on_pos_change)

    def on_layer_change(self) -> None:
        self._layer_index: int = self._layer_slider.value()

        self._current_layer: np.ndarray = np.array(self._paths_by_layers[self._layer_index - 1])
        self._current_layer_obj.Shape = Part.Shape()

        if self._layer_index > 1:
            self._remaining_layers: np.ndarray = np.array(self._paths_by_layers[:self._layer_index - 1])
            self._remaining_layers_obj.Shape = Part.makeCompound(self._remaining_layers.flatten())
        else:
            self._remaining_layers: np.ndarray = np.array([])
            self._remaining_layers_obj.Shape = Part.Shape()

        self._info_label.setText(
            "Layer: " + str(self._layer_index) +
            ", Pos 1: " + str(np.round(self._current_layer[0].Vertexes[0].Point, 1))  # noqa
        )

    def on_pos_change(self) -> None:
        pos_index: int = self._pos_slider.value()

        path_lengths: list[int] = [len(path.Vertexes) for path in self._current_layer]
        accumulated_path_lengths: np.ndarray = np.add.accumulate(path_lengths)
        path_positions: list[list[App.Vector]] = [[v.Point for v in path.Vertexes] for path in self._current_layer]

        self._pos_slider.setMaximum(sum(path_lengths))

        completed_sections: np.ndarray = self._current_layer[accumulated_path_lengths < pos_index]
        started_section_id: int = np.where(accumulated_path_lengths >= pos_index)[0][0]

        if started_section_id > 0:
            pos_index_offset: int = sum(accumulated_path_lengths[:started_section_id])
        else:
            pos_index_offset: int = 0

        started_section: list[App.Vector] = path_positions[started_section_id][:(pos_index - pos_index_offset)]
        if len(started_section) > 1:
            completed_sections: np.ndarray = np.hstack([completed_sections, Part.makePolygon(started_section)])

        if completed_sections.size > 0:
            self._current_layer_obj.Shape = Part.makeCompound(completed_sections)
        else:
            self._current_layer_obj.Shape = Part.Shape()

        self._info_label.setText(
            "Layer: " + str(self._layer_index) +
            ", Pos " + str(pos_index) + ": " + str(np.round(started_section[-1], 1))  # noqa
        )


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Wires) > 0 and len(selection.Shape.Vertexes) > 0:
                    slice_inspector: QtWidgets.QWidget = SliceInspector(paths=selection.Shape.Wires)
                    slice_inspector.show()
                else:
                    print("Shape contains no wires.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
