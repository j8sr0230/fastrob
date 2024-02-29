from typing import cast
import sys
import os

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

import FreeCAD as App

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from robot_controller import RobotController


class VarProxyClient(QtWidgets.QWidget):
    def __init__(self, robot_ctrl: RobotController, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._robot_ctrl: RobotController = robot_ctrl

        self.setWindowTitle("VarProxy Client")
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)

        self._start_button: QtWidgets.QPushButton = QtWidgets.QPushButton("Start")
        self._stop_button: QtWidgets.QPushButton = QtWidgets.QPushButton("Stop")

        self._layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self._start_button)
        self._layout.addWidget(self._stop_button)
        self.setLayout(self._layout)

        cast(QtCore.SignalInstance, self._start_button.clicked).connect(self.on_start)
        cast(QtCore.SignalInstance, self._stop_button.clicked).connect(self.on_stop)

    @staticmethod
    def on_start() -> None:
        print("Started")

    @staticmethod
    def on_stop() -> None:
        print("Stopped")


if __name__ == "__main__":
    if App.ActiveDocument and len(App.ActiveDocument.getObjectsByLabel("robot")) > 0:
        robot: RobotController = RobotController(tool_label="TCP")
        print("Kinematic chain generated.")

        var_proxy_client: QtWidgets.QWidget = VarProxyClient(robot_ctrl=robot)
        var_proxy_client.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        var_proxy_client.show()
    else:
        print("No kinematic chain found.")
