from __future__ import annotations
from typing import cast, Optional, Iterator

import importlib
from math import radians

import numpy as np
import awkward as ak

from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink

import FreeCADGui as Gui
import FreeCAD as App
import Part


class RobotControllerObject:
    AXIS_LABELS: list[str] = ["aA1", "bA2", "cA3", "dA4", "eA5", "fA6"]

    def __init__(self, feature_obj: Part.Feature, robot_grp: App.DocumentObjectGroup) -> None:
        feature_obj.addProperty("App::PropertyLink", "aRobot", "Kinematic", "Robot kinematic")
        feature_obj.addProperty("App::PropertyEnumeration", "bMode", "Kinematic", "Mode of the robot controller")
        feature_obj.addProperty("App::PropertyAngle", "aA1", "Forward", "Target axis angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "bA2", "Forward", "Target axis angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "cA3", "Forward", "Target axis angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "dA4", "Forward", "Target axis angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "eA5", "Forward", "Target axis angle in degree")
        feature_obj.addProperty("App::PropertyAngle", "fA6", "Forward", "Target axis angle in degree")
        feature_obj.addProperty("App::PropertyVector", "aPoint", "Inverse", "Inverse kinematics target point")

        feature_obj.aRobot = robot_grp
        feature_obj.bMode = ["Forward", "Inverse"]
        feature_obj.aA1 = 0.
        feature_obj.bA2 = 0.
        feature_obj.cA3 = 0.
        feature_obj.dA4 = 0.
        feature_obj.eA5 = 0.
        feature_obj.fA6 = 0.
        feature_obj.aPoint = (1000, 0, 1000)

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

        # self._axis_parts: list[App.Part] = list(self.kinematic_part_iterator(cast(App.Part, robot_grp.Group[0])))
        # self._axis_offset_rad: np.ndarray = np.array([
        #     self._axis_parts[0].Placement.Rotation.Angle, self._axis_parts[1].Placement.Rotation.Angle,
        #     self._axis_parts[2].Placement.Rotation.Angle, self._axis_parts[3].Placement.Rotation.Angle,
        #     self._axis_parts[4].Placement.Rotation.Angle, self._axis_parts[5].Placement.Rotation.Angle
        # ])
        # self._chain: Optional[Chain] = self.build_ik_py_chain(self._axis_parts)

        self._axis_parts: Optional[list[App.Part]] = None
        self._axis_offset_rad: Optional[np.ndarray] = None
        self._chain: Optional[Chain] = None
        self.init_kinematics(cast(App.Part, robot_grp.Group[0]))

    @staticmethod
    def kinematic_chain(axis_parts: list[App.Part]) -> Chain:
        return Chain(name="robot", links=[
            OriginLink(),
            URDFLink(name="A1", origin_translation=np.array(axis_parts[0].Placement.Base),
                     origin_orientation=np.radians(axis_parts[0].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[0].Placement.Rotation.Axis)),
            URDFLink(name="A2", origin_translation=np.array(axis_parts[1].Placement.Base),
                     origin_orientation=np.radians(axis_parts[1].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[1].Placement.Rotation.Axis)),
            URDFLink(name="A3", origin_translation=np.array(axis_parts[2].Placement.Base),
                     origin_orientation=np.radians(axis_parts[2].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[2].Placement.Rotation.Axis)),
            URDFLink(name="A4", origin_translation=np.array(axis_parts[3].Placement.Base),
                     origin_orientation=np.radians(axis_parts[3].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[3].Placement.Rotation.Axis)),
            URDFLink(name="A5", origin_translation=np.array(axis_parts[4].Placement.Base),
                     origin_orientation=np.radians(axis_parts[4].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[4].Placement.Rotation.Axis)),
            URDFLink(name="A6", origin_translation=np.array(axis_parts[5].Placement.Base),
                     origin_orientation=np.radians(axis_parts[5].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(axis_parts[5].Placement.Rotation.Axis)),
            URDFLink(name="TCP", origin_translation=np.array(axis_parts[6].Placement.Base),
                     origin_orientation=np.radians(axis_parts[6].Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array([1, 0, 0]))
        ], active_links_mask=[False, True, True, True, True, True, True, False])

    def kinematic_part_iterator(self, kinematic_part: App.Part) -> Iterator:
        if kinematic_part.Label.startswith("A") or kinematic_part.Label.startswith("TCP"):
            yield kinematic_part

        if hasattr(kinematic_part, "Group") and len(kinematic_part.getPropertyByName("Group")) > 0:
            for next_item in self.kinematic_part_iterator(kinematic_part.Group[0]):
                yield next_item

    def init_kinematics(self, chain_item: App.Part) -> None:
        if hasattr(chain_item, "Group") and len(chain_item.getPropertyByName("Group")) > 0:
            self._axis_parts: list[App.Part] = list(
                self.kinematic_part_iterator(cast(App.Part, chain_item))
            )
            self._axis_offset_rad: np.ndarray = np.array([
                self._axis_parts[0].Placement.Rotation.Angle, self._axis_parts[1].Placement.Rotation.Angle,
                self._axis_parts[2].Placement.Rotation.Angle, self._axis_parts[3].Placement.Rotation.Angle,
                self._axis_parts[4].Placement.Rotation.Angle, self._axis_parts[5].Placement.Rotation.Angle
            ])
            self._chain: Optional[Chain] = self.kinematic_chain(self._axis_parts)

    def execute(self, feature_obj: Part.Feature) -> None:
        print("Exec:", self, feature_obj)

    # noinspection PyPep8Naming
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        if not hasattr(self, "_feature_obj"):
            self._feature_obj: Part.Feature = feature_obj
            self._axis_parts: Optional[list[App.Part]] = None
            self._chain: Optional[Chain] = None

        if hasattr(self, "_axis_parts") and hasattr(feature_obj, "aRobot") and self._axis_parts is None:
            robot_grp: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, feature_obj.getPropertyByName("aRobot"))
            self.init_kinematics(cast(App.Part, robot_grp.Group[0]))

        if prop == "aRobot":
            robot_grp: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, feature_obj.getPropertyByName("aRobot"))
            self.init_kinematics(cast(App.Part, robot_grp.Group[0]))

        if prop in self.AXIS_LABELS and self._axis_parts and len(self._axis_parts) == 7:
            if hasattr(feature_obj, "bMode") and feature_obj.getPropertyByName("bMode") == "Forward":
                idx: int = self.AXIS_LABELS.index(prop)
                angle_rad: float = radians(feature_obj.getPropertyByName(prop))
                self._axis_parts[idx].Placement.Rotation.Angle = angle_rad

        if prop == "aPoint" and hasattr(feature_obj, "bMode"):
            if feature_obj.getPropertyByName("bMode") == "Inverse":
                print(feature_obj.getPropertyByName("aPoint"))

    # noinspection PyMethodMayBeStatic
    def dumps(self) -> str:
        return ak.to_json(self._axis_offset_rad)

    def loads(self, state: dict) -> None:
        axis_offset_rad_ak: ak.Array = ak.from_json(state)
        self._axis_offset_rad: np.ndarray = axis_offset_rad_ak.to_numpy()


if __name__ == "__main__":
    import robot_controller_object  # noqa
    importlib.reload(robot_controller_object)
    from robot_controller_object import RobotControllerObject  # noqa

    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if type(selection) == App.DocumentObjectGroup and len(selection.getPropertyByName("Group")) > 0:
                selection: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, selection)

                robot_ctrl_doc_obj: Part.Feature = cast(
                    Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Controller")
                )
                RobotControllerObject(feature_obj=robot_ctrl_doc_obj, robot_grp=selection)
                robot_ctrl_doc_obj.ViewObject.Proxy = 0
            else:
                print("No or empty group selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
