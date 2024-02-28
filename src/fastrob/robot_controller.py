from typing import Optional, cast

import numpy as np

from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink
import matplotlib.pyplot
import matplotlib.axes
from mpl_toolkits.mplot3d import Axes3D  # noqa

import FreeCAD as App

DEBUG: bool = False


class RobotController:
    def __init__(self, tool_label: str = "TCP"):
        doc: App.Document = App.ActiveDocument

        self._a1_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel("A1")[0])
        self._a2_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel("A2")[0])
        self._a3_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel("A3")[0])
        self._a4_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel("A4")[0])
        self._a5_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel("A5")[0])
        self._a6_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel("A6")[0])
        self._tcp_obj: App.GeoFeature = cast(App.GeoFeature, doc.getObjectsByLabel(tool_label)[0])

        self._axis_offset_rad: np.ndarray = np.array([
            self._a1_obj.Placement.Rotation.Angle, self._a2_obj.Placement.Rotation.Angle,
            self._a3_obj.Placement.Rotation.Angle, self._a4_obj.Placement.Rotation.Angle,
            self._a5_obj.Placement.Rotation.Angle, self._a6_obj.Placement.Rotation.Angle
        ])

        self._chain: Chain = Chain(name="robot", links=[
            OriginLink(),
            URDFLink(name="A1", origin_translation=np.array(self._a1_obj.Placement.Base),
                     origin_orientation=np.radians(self._a1_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(self._a1_obj.Placement.Rotation.Axis)),
            URDFLink(name="A2", origin_translation=np.array(self._a2_obj.Placement.Base),
                     origin_orientation=np.radians(self._a2_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(self._a2_obj.Placement.Rotation.Axis)),
            URDFLink(name="A3", origin_translation=np.array(self._a3_obj.Placement.Base),
                     origin_orientation=np.radians(self._a3_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(self._a3_obj.Placement.Rotation.Axis)),
            URDFLink(name="A4", origin_translation=np.array(self._a4_obj.Placement.Base),
                     origin_orientation=np.radians(self._a4_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(self._a4_obj.Placement.Rotation.Axis)),
            URDFLink(name="A5", origin_translation=np.array(self._a5_obj.Placement.Base),
                     origin_orientation=np.radians(self._a5_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(self._a5_obj.Placement.Rotation.Axis)),
            URDFLink(name="A6", origin_translation=np.array(self._a6_obj.Placement.Base),
                     origin_orientation=np.radians(self._a6_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array(self._a6_obj.Placement.Rotation.Axis)),
            URDFLink(name="TCP", origin_translation=np.array(self._tcp_obj.Placement.Base),
                     origin_orientation=np.radians(self._tcp_obj.Placement.Rotation.toEulerAngles("XYZ")),
                     rotation=np.array([1, 0, 0]))
        ], active_links_mask=[False, True, True, True, True, True, True, False])

        self._default_tool_orientation: np.ndarray = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
        self.reset_axis()

        if DEBUG:
            ax: matplotlib.axes.Axes = matplotlib.pyplot.figure().add_subplot(111, projection="3d")
            self._chain.plot(
                self._chain.inverse_kinematics(np.array([1000, 0, 1000]), self._default_tool_orientation, "all"), ax
            )
            matplotlib.pyplot.show()

    def set_axis(self, axis_rad: np.ndarray = np.array([0, 0, 0, 0, 0, 0])) -> None:
        self._a1_obj.Placement.Rotation.Angle = axis_rad[0] + self._axis_offset_rad[0]
        self._a2_obj.Placement.Rotation.Angle = axis_rad[1] + self._axis_offset_rad[1]
        self._a3_obj.Placement.Rotation.Angle = axis_rad[2] + self._axis_offset_rad[2]
        self._a4_obj.Placement.Rotation.Angle = axis_rad[3] + self._axis_offset_rad[3]
        self._a5_obj.Placement.Rotation.Angle = axis_rad[4] + self._axis_offset_rad[4]
        self._a6_obj.Placement.Rotation.Angle = axis_rad[5] + self._axis_offset_rad[5]

    def reset_axis(self) -> None:
        self.set_axis(axis_rad=-self._axis_offset_rad)

    def move_to(self, target_pos: np.ndarray, target_rot: Optional[np.ndarray] = None) -> np.ndarray:
        target_axis_rad: np.ndarray = self._chain.inverse_kinematics(
            target_position=target_pos,
            target_orientation=self._default_tool_orientation if target_rot is None else target_rot,
            orientation_mode="all"
        )[1:-1]

        self.set_axis(axis_rad=target_axis_rad)
        return target_axis_rad
