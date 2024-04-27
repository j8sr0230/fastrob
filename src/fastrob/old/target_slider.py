from typing import Optional, cast
import sys
import os

import numpy as np

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

import FreeCADGui as Gui
import FreeCAD as App

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from src.fastrob.old.robot_controller import RobotController


class AnimationSlider(QtWidgets.QWidget):
    def __init__(self, robot_ctrl: RobotController, point_obj: App.GeoFeature, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._robot_ctrl: RobotController = robot_ctrl
        self._point_obj: App.GeoFeature = point_obj
        self._target_points: list[App.Vector] = self._point_obj.Points if hasattr(self._point_obj, "Points") else []

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
    if App.ActiveDocument and len(App.ActiveDocument.getObjectsByLabel("robot")) > 0:
        robot: RobotController = RobotController(tool_label="TCP")
        print("Kinematic chain generated.")

        # robot.move_to(target_pos=np.array([1000, 500, 1000]))

        if len(Gui.Selection.getSelection()) > 0:
            selection: Optional[App.DocumentObject] = Gui.Selection.getSelection()[0]
        else:
            selection: Optional[App.DocumentObject] = None
        print("Selected object:", selection.Label if selection is not None else selection)

        if selection is not None and hasattr(selection, "Points"):
            selection: App.GeoFeature = cast(App.GeoFeature, selection)
            animation_slider: QtWidgets.QWidget = AnimationSlider(robot_ctrl=robot, point_obj=selection)
            animation_slider.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            animation_slider.show()
        else:
            print("Selected object has no target points.")
    else:
        print("No kinematic chain found.")
