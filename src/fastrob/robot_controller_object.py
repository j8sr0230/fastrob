from __future__ import annotations
from typing import cast, Optional, Iterator

import importlib
from math import radians, degrees

import numpy as np

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
        feature_obj.addProperty("App::PropertyVector", "aPoint", "Inverse", "Inverse kinematics target point")
        feature_obj.addProperty("App::PropertyRotation", "bRotation", "Inverse", "Inverse kinematics target rotation")
        for axis_label in self.AXIS_LABELS:
            feature_obj.addProperty("App::PropertyAngle", axis_label, "Forward", "Target axis angle in degree")

        feature_obj.aRobot = robot_grp
        feature_obj.bMode = ["Forward", "Inverse"]
        feature_obj.aPoint = (1000, 0, 1000)
        feature_obj.bRotation = App.Rotation(App.Vector(0, 1, 0), 90)
        for axis_label in self.AXIS_LABELS:
            setattr(feature_obj, axis_label, 0)

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

        self._kinematic_parts: Optional[list[App.Part]] = None
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

    def init_kinematics(self, kinematic_part: App.Part) -> None:
        self._kinematic_parts: list[App.Part] = list(self.kinematic_part_iterator(cast(App.Part, kinematic_part)))

        if len(self._kinematic_parts) == 7:
            self._axis_offset_rad: np.ndarray = np.array(
                [self._kinematic_parts[i].Placement.Rotation.Angle for i in range(6)]
            )

            self._chain: Optional[Chain] = self.kinematic_chain(self._kinematic_parts)

            for idx, axis_prop in enumerate(self.AXIS_LABELS):
                if hasattr(self._feature_obj, axis_prop):
                    setattr(self._feature_obj, axis_prop, degrees(self._kinematic_parts[idx].Placement.Rotation.Angle))

            if hasattr(self._feature_obj, "aPoint"):
                self._feature_obj.aPoint = self._kinematic_parts[-1].getGlobalPlacement().Base

    def set_axis(self, axis_rad: np.ndarray) -> None:
        if (hasattr(self, "_kinematic_parts") and type(self._kinematic_parts) is list
                and len(self._kinematic_parts) == 7 and hasattr(self, "_axis_offset_rad")
                and type(self._axis_offset_rad) is np.ndarray):

            for i in range(6):
                # noinspection PyPep8Naming
                self._kinematic_parts[i].Placement.Rotation.Angle = (axis_rad[i] + self._axis_offset_rad[i])

    def reset_axis(self) -> None:
        if hasattr(self, "_axis_offset_rad") and type(self._axis_offset_rad) is np.ndarray:
            self.set_axis(-self._axis_offset_rad)

    def move_to(self, target_pos: np.ndarray, target_rot: np.ndarray) -> np.ndarray:
        if self._chain:
            target_axis_rad: np.ndarray = self._chain.inverse_kinematics(
                target_position=target_pos,
                target_orientation=target_rot,
                orientation_mode="all"
            )[1:-1]
        else:
            target_axis_rad: np.ndarray = np.array([0, 0, 0, 0, 0, 0])

        self.set_axis(target_axis_rad)
        return target_axis_rad

    # def execute(self, feature_obj: Part.Feature) -> None:
    #     print("Exec:", self, feature_obj)

    # noinspection PyPep8Naming
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        if not hasattr(self, "_feature_obj"):
            self._feature_obj: Part.Feature = feature_obj
            self._kinematic_parts: Optional[list[App.Part]] = None
            self._axis_offset_rad: Optional[np.ndarray] = None
            self._chain: Optional[Chain] = None

        if hasattr(feature_obj, "aRobot") and self._kinematic_parts is None:
            robot_grp: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, feature_obj.getPropertyByName("aRobot"))
            if hasattr(robot_grp, "Group") and len(robot_grp.getPropertyByName("Group")) > 0:
                self.init_kinematics(cast(App.Part, robot_grp.Group[0]))

        if prop == "aRobot":
            robot_grp: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, feature_obj.getPropertyByName("aRobot"))
            if hasattr(robot_grp, "Group") and len(robot_grp.getPropertyByName("Group")) > 0:
                self.init_kinematics(cast(App.Part, robot_grp.Group[0]))

        if prop in self.AXIS_LABELS and type(self._kinematic_parts) is list and len(self._kinematic_parts) == 7:
            if hasattr(feature_obj, "bMode") and feature_obj.getPropertyByName("bMode") == "Forward":
                idx: int = self.AXIS_LABELS.index(prop)
                angle_rad: float = radians(feature_obj.getPropertyByName(prop))
                self._kinematic_parts[idx].Placement.Rotation.Angle = angle_rad

                if hasattr(feature_obj, "aPoint"):
                    feature_obj.aPoint = self._kinematic_parts[-1].getGlobalPlacement().Base

        if prop in ("aPoint", "bRotation") and hasattr(feature_obj, "aPoint") and hasattr(feature_obj, "bRotation"):
            if hasattr(feature_obj, "bMode") and feature_obj.getPropertyByName("bMode") == "Inverse":
                rot_matrix: App.Matrix = feature_obj.bRotation.toMatrix()
                rot_matrix_np: np.ndarray = np.array([
                    [rot_matrix.A11, rot_matrix.A12, rot_matrix.A13],
                    [rot_matrix.A21, rot_matrix.A22, rot_matrix.A23],
                    [rot_matrix.A31, rot_matrix.A32, rot_matrix.A33]
                ])
                angle_rad: np.ndarray = self.move_to(np.array(feature_obj.getPropertyByName("aPoint")), rot_matrix_np)

                for idx, axis_prop in enumerate(self.AXIS_LABELS):
                    if hasattr(feature_obj, axis_prop) and type(self._axis_offset_rad) is np.ndarray:
                        setattr(feature_obj, axis_prop, degrees(angle_rad[idx] + self._axis_offset_rad[idx]))

    # noinspection PyMethodMayBeStatic
    def dumps(self) -> Optional[str]:
        return None

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
