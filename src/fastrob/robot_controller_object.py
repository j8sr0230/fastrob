from __future__ import annotations
from typing import cast, Optional

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

        # feature_obj.addProperty("App::PropertyLength", "bHeight", "Slicing", "Layer height of the slice")
        # feature_obj.addProperty("App::PropertyLength", "cWidth", "Slicing", "Width of the seams")
        # feature_obj.addProperty("App::PropertyInteger", "dPerimeters", "Slicing", "Number of perimeters")
        # feature_obj.addProperty("App::PropertyEnumeration", "ePattern", "Slicing", "Pattern of the filling")
        # feature_obj.addProperty("App::PropertyPercent", "fDensity", "Slicing", "Density of the filling")
        # feature_obj.addProperty("App::PropertyAngle", "gAngle", "Slicing", "Angle of the filling")
        # feature_obj.addProperty("App::PropertyLength", "hAnchor", "Slicing", "Anchor length of the filling")
        # feature_obj.addProperty("App::PropertyEnumeration", "aMode", "Filter", "Mode of the path filter")
        # # feature_obj.addProperty("App::PropertyInteger", "bLayerIndex", "Filter", "Layer to be filtered")
        # feature_obj.addProperty("App::PropertyInteger", "bLayerIndex", "Filter", "Layer to be filtered")
        # feature_obj.setPropertyStatus("bLayerIndex", "UserEdit")
        # # feature_obj.addProperty("App::PropertyInteger", "cPointIndex", "Filter", "Position to be filtered")
        # feature_obj.addProperty("App::PropertyInteger", "cPointIndex", "Filter", "Position to be filtered")
        # feature_obj.setPropertyStatus("cPointIndex", "UserEdit")
        # feature_obj.addProperty("App::PropertyVectorList", "aPoints", "Result", "Points of the filtered result")
        # feature_obj.addProperty("App::PropertyVector", "bPoint", "Result", "Point belonging to the point index")

        feature_obj.aRobot = robot_grp
        feature_obj.bMode = ["forward", "inverse"]

        feature_obj.aA1 = 0.
        feature_obj.bA2 = 0.
        feature_obj.cA3 = 0.
        feature_obj.dA4 = 0.
        feature_obj.eA5 = 0.
        feature_obj.fA6 = 0.

        # feature_obj.bHeight = 2.
        # feature_obj.cWidth = 6.
        # feature_obj.dPerimeters = 1

        # feature_obj.fDensity = 100
        # feature_obj.gAngle = 45.
        # feature_obj.hAnchor = 10.
        # feature_obj.aMode = ["None", "All", "Layer"]
        # feature_obj.bLayerIndex = 0
        # feature_obj.cPointIndex = 0
        # feature_obj.aPoints = [(0, 0, 0)]
        # feature_obj.bPoint = (0, 0, 0)

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

    @staticmethod
    def _travel_grp(group: App.DocumentObjectGroup, first_items: Optional[list[App.Part]] = None) -> list[App.Part]:
        if first_items is None:
            first_items: list[App.Part] = []

        if len(group.Group) > 0 and type(group.Group[0]) is App.Part:
            item: App.Part = cast(App.Part, group.Group[0])
            first_items.append(item)

    def execute(self, feature_obj: Part.Feature) -> None:
        pass

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        robot_grp: App.DocumentObjectGroup = cast(App.DocumentObjectGroup, feature_obj.getPropertyByName("aRobot"))

        if not hasattr(self, "_feature_obj"):
            self._feature_obj: Part.Feature = feature_obj

        if (feature_obj.getPropertyByName("bMode") == "forward" and
                prop in ("aA1", "bA2", "cA3", "dA4", "eA4", "fA5", "gA6")):
            angle_rad: float = radians(feature_obj.getPropertyByName(prop))
            cast(App.Part, robot_grp.Group[0]).Placement.Rotation.Angle = angle_rad

        if prop == "bA2" and feature_obj.getPropertyByName("bMode") == "forward":
            a1_rad: float = radians(feature_obj.getPropertyByName("bA2"))
            cast(App.Part, robot_grp.Group[0]).Placement.Rotation.Angle = a1_rad

        if prop == "aA1" and feature_obj.getPropertyByName("bMode") == "forward":
            a1_rad: float = radians(feature_obj.getPropertyByName("aA1"))
            cast(App.Part, robot_grp.Group[0]).Placement.Rotation.Angle = a1_rad

        if prop == "aA1" and feature_obj.getPropertyByName("bMode") == "forward":
            a1_rad: float = radians(feature_obj.getPropertyByName("aA1"))
            cast(App.Part, robot_grp.Group[0]).Placement.Rotation.Angle = a1_rad

        if prop == "aA1" and feature_obj.getPropertyByName("bMode") == "forward":
            a1_rad: float = radians(feature_obj.getPropertyByName("aA1"))
            cast(App.Part, robot_grp.Group[0]).Placement.Rotation.Angle = a1_rad

        if prop == "aA1" and feature_obj.getPropertyByName("bMode") == "forward":
            a1_rad: float = radians(feature_obj.getPropertyByName("aA1"))
            cast(App.Part, robot_grp.Group[0]).Placement.Rotation.Angle = a1_rad

    # def dumps(self) -> dict:
    #     return dict()
    #
    # def loads(self, state: dict) -> None:
    #     pass


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
