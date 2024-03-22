from typing import cast

import FreeCADGui as Gui
import FreeCAD as App
import Part

from pivy import coin


class Molecule:
    def __init__(self, obj: Part.Feature) -> None:
        obj.addProperty("App::PropertyVector", "P1", "Line", "Start point").P1 = App.Vector(1, 1, 0)
        obj.addProperty("App::PropertyVector", "P2", "Line", "End point").P2 = App.Vector(5, 5, 0)
        obj.Proxy = self

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def onChanged(self, fp: Part.Feature, prop: str) -> None:
        if prop == "P1" or prop == "P2":
            fp.Shape = Part.makeLine(fp.getPropertyByName("P1"), fp.getPropertyByName("P2"))

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def execute(self, fp: Part.Feature) -> None:
        fp.Shape = Part.makeLine(fp.getPropertyByName("P1"), fp.getPropertyByName("P2"))


class ViewProviderMolecule:
    def __init__(self, obj: Gui.ViewProviderDocumentObject) -> None:
        obj.Proxy = self
        self.ViewObject = obj

        sep_1: coin.SoSeparator = coin.SoSeparator()
        sel_1: coin.SoSelection = coin.SoType.fromName("SoFCSelection").createInstance()
        # sel1.policy.setValue(coin.SoSelection.SHIFT)
        sel_1.ref()
        sep_1.addChild(sel_1)
        self._trl_1: coin.SoTranslation = coin.SoTranslation()
        sel_1.addChild(self._trl_1)
        sel_1.addChild(coin.SoSphere())

        sep_2: coin.SoSeparator = coin.SoSeparator()
        sel_2: coin.SoSelection = coin.SoType.fromName("SoFCSelection").createInstance()
        sel_2.ref()
        sep_2.addChild(sel_2)
        self._trl_2: coin.SoTranslation = coin.SoTranslation()
        sel_2.addChild(self._trl_2)
        sel_2.addChild(coin.SoSphere())

        obj.RootNode.addChild(sep_1)
        obj.RootNode.addChild(sep_2)

        self._sel_1 = sel_1
        self._sel_2 = sel_2

        # self.updateData(cast(Part.Feature, obj.Object), "P1")
        # self.updateData(cast(Part.Feature, obj.Object), "P2")

    # noinspection PyPep8Naming
    def getDetailPath(self, sub_name: str, path: coin.SoFullPath, append: bool) -> bool:
        vobj: Gui.ViewProviderDocumentObject = self.ViewObject
        if append:
            path.append(vobj.RootNode)
            path.append(vobj.SwitchNode)

            mode: int = vobj.SwitchNode.whichChild.getValue()
            if mode >= 0:
                mode: coin.SoSeparator = vobj.SwitchNode.getChild(mode)
                path.append(mode)
                sub: str = Part.splitSubname(sub_name)[-1]
                if sub == "Atom1":
                    path.append(self._sel_1)
                elif sub == "Atom2":
                    path.append(self._sel_2)
                else:
                    path.append(mode.getChild(0))
        return True

    # noinspection PyPep8Naming
    def getElementPicked(self, pp: coin.SoPickedPoint) -> str:
        path: coin.SoPath = pp.getPath()
        if path.findNode(self._sel_1) >= 0:
            return "Atom1"
        if path.findNode(self._sel_2) >= 0:
            return "Atom2"
        raise NotImplementedError

    # noinspection PyPep8Naming
    def updateData(self, fp: Part.Feature, prop: str):
        if prop == "P1":
            # print(hasattr(self, "_sel_1"))
            p: App.Vector = fp.getPropertyByName("P1")
            self._trl_1.translation = (p.x, p.y, p.z)
        elif prop == "P2":
            p: App.Vector = fp.getPropertyByName("P2")
            self._trl_2.translation = (p.x, p.y, p.z)

    # noinspection PyPep8Naming, PyMethodMayBeStatic
    def dumps(self):
        return None

    # noinspection PyPep8Naming, PyMethodMayBeStatic, PyUnusedLocal
    def loads(self, state):
        return None


if __name__ == "__main__":
    if App.ActiveDocument:
        a: Part.Feature = cast(Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Molecule"))
        Molecule(a)
        ViewProviderMolecule(a.ViewObject)
        App.ActiveDocument.recompute()

    else:
        print("No FreeCAD instance running.")
