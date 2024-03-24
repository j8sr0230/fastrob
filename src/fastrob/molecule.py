from typing import Any, cast

import FreeCAD as App
import Part

from pivy import coin


class Molecule:
    def __init__(self, feature_obj: Part.Feature) -> None:
        feature_obj.addProperty("App::PropertyVector", "P1", "Line", "Start point").P1 = App.Vector(1, 1, 0)
        feature_obj.addProperty("App::PropertyVector", "P2", "Line", "End point").P2 = App.Vector(5, 5, 0)
        feature_obj.Proxy = self

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def onChanged(self, feature_obj: Part.Feature, prop: str) -> None:
        if prop == "P1" or prop == "P2":
            feature_obj.Shape = Part.makeLine(feature_obj.getPropertyByName("P1"), feature_obj.getPropertyByName("P2"))

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def execute(self, feature_obj: Part.Feature) -> None:
        feature_obj.Shape = Part.makeLine(feature_obj.getPropertyByName("P1"), feature_obj.getPropertyByName("P2"))


class ViewProviderMolecule:
    def __init__(self, view_obj: Any) -> None:
        self._switch: coin.SoSwitch = coin.SoSwitch()
        self._switch.whichChild = coin.SO_SWITCH_ALL

        self._sep_1: coin.SoSeparator = coin.SoSeparator()
        self._sep_1.ref()
        self._sel_1: coin.SoSelection = coin.SoType.fromName("SoFCSelection").createInstance()
        self._trl_1: coin.SoTranslation = coin.SoTranslation()
        self._sel_1.addChild(self._trl_1)
        self._sel_1.addChild(coin.SoSphere())
        self._sep_1.addChild(self._sel_1)
        self._switch.addChild(self._sep_1)

        self._sep_2: coin.SoSeparator = coin.SoSeparator()
        self._sep_2.ref()
        self._sel_2: coin.SoSelection = coin.SoType.fromName("SoFCSelection").createInstance()
        self._trl_2: coin.SoTranslation = coin.SoTranslation()
        self._sel_2.addChild(self._trl_2)
        self._sel_2.addChild(coin.SoSphere())
        self._sep_2.addChild(self._sel_2)
        self._switch.addChild(self._sep_2)

        view_obj.RootNode.addChild(self._switch)

        view_obj.Proxy = self
        self.view_obj = view_obj

    # noinspection PyPep8Naming
    def getDetailPath(self, sub_name: str, path: coin.SoFullPath, append: bool) -> bool:
        if append:
            path.append(self.view_obj.RootNode)
            path.append(self.view_obj.SwitchNode)

            child_id: int = self.view_obj.SwitchNode.whichChild.getValue()
            if child_id >= 0:
                node: coin.SoSeparator = self.view_obj.SwitchNode.getChild(child_id)
                path.append(node)
                sub: str = Part.splitSubname(sub_name)[-1]
                if sub == "Atom1":
                    path.append(self._sel_1)
                elif sub == "Atom2":
                    path.append(self._sel_2)
                else:
                    path.append(node.getChild(0))
        return True

    # noinspection PyPep8Naming
    def getElementPicked(self, picked_point: coin.SoPickedPoint) -> str:
        path: coin.SoPath = picked_point.getPath()
        if path.findNode(self._sel_1) >= 0:
            return "Atom1"
        if path.findNode(self._sel_2) >= 0:
            return "Atom2"
        raise NotImplementedError

    # noinspection PyPep8Naming
    def updateData(self, feature_obj: Part.Feature, prop: str) -> None:
        if prop == "P1":
            p: App.Vector = feature_obj.getPropertyByName("P1")
            self._trl_1.translation = (p.x, p.y, p.z)
        elif prop == "P2":
            p: App.Vector = feature_obj.getPropertyByName("P2")
            self._trl_2.translation = (p.x, p.y, p.z)

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def onChanged(self, view_obj: Any, prop: str):
        if prop == "Visibility":
            if bool(view_obj.Object.getPropertyByName("Visibility")) is False:
                self._switch.whichChild = coin.SO_SWITCH_ALL
            else:
                self._switch.whichChild = coin.SO_SWITCH_NONE

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def dumps(self):
        return None

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def loads(self, state):
        return None


if __name__ == "__main__":
    if App.ActiveDocument:
        a: App.DocumentObject = App.ActiveDocument.addObject("Part::FeaturePython", "Molecule")
        Molecule(cast(Part.Feature, a))
        ViewProviderMolecule(a.ViewObject)
        App.ActiveDocument.recompute()

    else:
        print("No FreeCAD instance running.")
