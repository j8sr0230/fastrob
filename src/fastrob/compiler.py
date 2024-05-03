from __future__ import annotations
from typing import cast, Optional

import importlib

import FreeCADGui as Gui
import FreeCAD as App
import Part


class Compiler:
    def __init__(self, feature_obj: Part.Feature, slicer: Part.Feature) -> None:
        feature_obj.addProperty("App::PropertyLink", "aSlicer", "Input", "Tool path to be compiled")
        feature_obj.addProperty("App::PropertyFile", "bFile", "Input", "Name and path of manufacturing code")
        feature_obj.addProperty("App::PropertyEnumeration", "cMachine", "Input", "Name of the target machine")

        feature_obj.aSlicer = slicer
        feature_obj.bFile = ""
        feature_obj.cMachine = ["KUKA", "ABB"]

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

    # noinspection PyMethodMayBeStatic
    def execute(self, feature_obj: Part.Feature) -> None:
        print(feature_obj.getPropertyByName("aSlicer").aLocalPoints)

    # noinspection PyMethodMayBeStatic
    def dumps(self) -> Optional[str]:
        return None

    def loads(self, state: dict) -> None:
        pass


if __name__ == "__main__":
    import compiler  # noqa
    importlib.reload(compiler)
    from compiler import Compiler  # noqa

    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]

            print(type(selection), hasattr(selection, "aLocalPoints"))

            if hasattr(selection, "aLocalPoints"):
                selection: Part.Feature = cast(Part.Feature, selection)

                compiler_doc_obj: Part.Feature = cast(
                    Part.Feature, App.ActiveDocument.addObject("Part::FeaturePython", "Compiler")
                )
                Compiler(feature_obj=compiler_doc_obj, slicer=selection)
                compiler_doc_obj.ViewObject.Proxy = 0
            else:
                print("No slicer selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
