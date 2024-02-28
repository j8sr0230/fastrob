from typing import Optional, cast
import sys
import os

import numpy as np

import FreeCADGui as Gui
import FreeCAD as App
import Part

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from robot_controller import RobotController


class PlacementObserver:
    def __init__(self, robot_ctrl: RobotController, target_obj: App.GeoFeature):
        self._robot_ctrl: RobotController = robot_ctrl
        self._target_obj: App.GeoFeature = target_obj

    # noinspection PyPep8Naming
    def slotChangedObject(self, obj: Part.Feature, obj_property: str) -> None:
        if obj is self._target_obj and obj_property == "Placement":
            target_base: np.ndarray = np.array(obj.Placement.Base)
            target_rot: App.Rotation = obj.Placement.Rotation
            target_rot_matrix: App.Matrix = target_rot.toMatrix()
            target_rot_mat_3: np.ndarray = np.array([
                [target_rot_matrix.A11, target_rot_matrix.A12, target_rot_matrix.A13],
                [target_rot_matrix.A21, target_rot_matrix.A22, target_rot_matrix.A23],
                [target_rot_matrix.A31, target_rot_matrix.A32, target_rot_matrix.A33]
            ])

            self._robot_ctrl.move_to(target_pos=target_base, target_rot=target_rot_mat_3)

    # noinspection PyPep8Naming
    # noinspection PyUnusedLocal
    def slotDeletedObject(self, obj: Part.Feature) -> None:
        App.removeDocumentObserver(self)
        self._robot_ctrl.reset_axis()


if __name__ == "__main__":
    if App.ActiveDocument and len(App.ActiveDocument.getObjectsByLabel("robot")) > 0:
        robot: RobotController = RobotController(tool_label="TCP")
        print("Kinematic chain generated.")

        if len(Gui.Selection.getSelection()) > 0:
            selection: Optional[App.DocumentObject] = Gui.Selection.getSelection()[0]
        else:
            selection: Optional[App.DocumentObject] = None
        print("Selected object:", selection.Label if selection is not None else selection)

        if selection is not None and hasattr(selection, "Placement"):
            selection: App.GeoFeature = cast(App.GeoFeature, selection)
            observer: PlacementObserver = PlacementObserver(robot_ctrl=robot, target_obj=selection)
            App.addDocumentObserver(observer)
        else:
            print("Selected object has no placement.")
    else:
        print("No kinematic chain found.")
