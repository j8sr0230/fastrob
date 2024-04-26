from __future__ import annotations
from typing import cast, Optional, Iterator

import importlib
from math import radians

import FreeCADGui as Gui
import FreeCAD as App
import Part


class RobotControllerObject:
    def __init__(self, feature_obj: Part.Feature, robot_grp: App.DocumentObjectGroup) -> None:
        feature_obj.addProperty("App::PropertyLink", "aRobot", "Kinematic", "Robot kinematic")
        feature_obj.addProperty("App::PropertyEnumeration", "bMode", "Kinematic", "Mode of the robot controller")

        feature_obj.addProperty("App::PropertyAngle", "aA1", "Forward", "Angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "bA2", "Forward", "Angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "cA3", "Forward", "Angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "dA4", "Forward", "Angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "eA5", "Forward", "Angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "fA6", "Forward", "Angle in degree")

        feature_obj.aRobot = robot_grp
        feature_obj.bMode = ["forward", "inverse"]
        feature_obj.aA1 = 0.
        feature_obj.bA2 = 0.
        feature_obj.cA3 = 0.
        feature_obj.dA4 = 0.
        feature_obj.eA5 = 0.
        feature_obj.fA6 = 0.

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

        self._axis_parts: list[App.Part] = list(self.kinematic_chain_iterator(cast(App.Part, robot_grp.Group[0])))

    def kinematic_chain_iterator(self, chain_item: App.Part) -> Iterator:
        if chain_item.Label.startswith("A"):
            yield chain_item

        if hasattr(chain_item, "Group") and len(chain_item.getPropertyByName("Group")) > 0:
            for next_item in self.kinematic_chain_iterator(chain_item.Group[0]):
                yield next_item

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        if not hasattr(self, "_feature_obj"):
            self._feature_obj: Part.Feature = feature_obj

        if not hasattr(self, "_axis_parts") and hasattr(self, "aRobot"):
            robot_grp: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, feature_obj.getPropertyByName("aRobot"))
            self._axis_parts: list[App.Part] = list(self.kinematic_chain_iterator(cast(App.Part, robot_grp.Group[0])))

        if prop in ("aA1", "bA2", "cA3", "dA4", "eA5", "fA6"):
            idx: int = ["aA1", "bA2", "cA3", "dA4", "eA5", "fA6"].index(prop)
            angle_rad: float = radians(feature_obj.getPropertyByName(prop))
            self._axis_parts[idx].Placement.Rotation.Angle = angle_rad

    def dumps(self) -> dict:
        return dict()

    def loads(self, state: dict) -> None:
        pass


if __name__ == "__main__":
    import robot_controller_object  # noqa
    importlib.reload(robot_controller_object)
    from robot_controller_object import RobotControllerObject  # noqa

    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if type(selection) == App.DocumentObjectGroup:
                selection: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, selection)

                robot_ctrl_doc_obj: Part.Feature = cast(
                    Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Controller")
                )
                RobotControllerObject(feature_obj=robot_ctrl_doc_obj, robot_grp=selection)
                robot_ctrl_doc_obj.ViewObject.Proxy = 0
            else:
                print("No group selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
