from typing import Any, cast
import sys
import os

import numpy as np

import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

from py_openshowvar import openshowvar

import FreeCAD as App

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from robot_controller import RobotController


class VarProxyClient(QtWidgets.QWidget):
    def __init__(self, robot_ctrl: RobotController, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._robot_ctrl: RobotController = robot_ctrl
        self._client: Any = None
        self._request_timer: QtCore.QTimer = QtCore.QTimer()

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
        cast(QtCore.SignalInstance, self._request_timer.timeout).connect(self.request_data)

    def on_start(self) -> None:
        print("Started listening ...")
        self._client: Any = openshowvar("192.168.1.50", 7000)

        self._request_timer: QtCore.QTimer = QtCore.QTimer()
        self._request_timer.timeout.connect(self.request_data)
        self._request_timer.start(50)

    def request_data(self) -> None:
        robot_data: Any = self._client.read("$AXIS_ACT", debug=False)
        robot_data_str: str = str(robot_data, "utf-8")

        axis_list_str: list[str] = robot_data_str.split(",")[:6]
        axis_list_deg: list[float] = [float(data_item.split(" ")[-1]) for data_item in axis_list_str]
        axis_array_rad: np.ndarray = np.round(np.radians(axis_list_deg), 2) + np.array([0, np.pi/2, -np.pi/2, 0, 0, 0])
        self._robot_ctrl.set_axis(axis_array_rad)
        # print(axis_array_rad)

    def on_stop(self) -> None:
        print("Stopped listening ...")
        self._request_timer.stop()
        self._client.close()
        self._robot_ctrl.reset_axis()


if __name__ == "__main__":
    if App.ActiveDocument and len(App.ActiveDocument.getObjectsByLabel("robot")) > 0:
        robot: RobotController = RobotController(tool_label="TCP")
        print("Kinematic chain generated.")

        var_proxy_client: QtWidgets.QWidget = VarProxyClient(robot_ctrl=robot)
        var_proxy_client.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        var_proxy_client.show()
    else:
        print("No kinematic chain found.")
