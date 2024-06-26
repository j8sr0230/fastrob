from __future__ import annotations
from typing import cast, Optional

import importlib

import awkward as ak

import FreeCADGui as Gui
import FreeCAD as App
import Part

from utils import linear_move, point_move


class Compiler:
    def __init__(self, feature_obj: Part.Feature, slicer: Part.Feature) -> None:
        feature_obj.addProperty("App::PropertyLink", "aSlicer", "Compiler", "Tool path to be compiled")
        feature_obj.addProperty("App::PropertyFile", "bFile", "Compiler", "Path to the machine code")
        feature_obj.addProperty("App::PropertyEnumeration", "cMachine", "Compiler", "Name of the target machine")
        feature_obj.addProperty("App::PropertyStringList", "dCustomStart", "Compiler", "Start commands (path wise)")
        feature_obj.addProperty("App::PropertyStringList", "eCustomEnd", "Compiler", "End commands (path wise)")
        feature_obj.addProperty("App::PropertyBool", "fSilent", "Compiler", "True prevents compiling on recompute")

        feature_obj.aSlicer = slicer
        feature_obj.bFile = ""
        feature_obj.cMachine = ["KUKA", "ABB"]
        feature_obj.dCustomStart = []
        feature_obj.eCustomEnd = []
        feature_obj.fSilent = False

        feature_obj.Proxy = self
        self._feature_obj: Part.Feature = feature_obj

    # noinspection PyMethodMayBeStatic
    def execute(self, feature_obj: Part.Feature) -> None:
        if not feature_obj.getPropertyByName("fSilent"):

            try:
                with open(feature_obj.getPropertyByName("bFile"), "w") as file:
                    has_axis_offset: bool = False
                    if feature_obj.getPropertyByName("aSlicer").iAxisOffset != App.Vector(0, 0, 0):
                        has_axis_offset = True

                    paths: Optional[ak.Array] = feature_obj.getPropertyByName("aSlicer").Proxy.paths
                    if paths is not None:
                        for layer in paths.to_list():
                            for path in layer:
                                for idx, pos in enumerate(path):

                                    if has_axis_offset:
                                        if idx < 2:
                                            cmd: str = point_move(feature_obj.getPropertyByName("cMachine"), pos)
                                            file.write(cmd + "\n")

                                            if idx == 1:
                                                for cmd in feature_obj.getPropertyByName("dCustomStart"):
                                                    file.write(cmd + "\n")

                                        elif idx < len(path) - 1:
                                            cmd: str = linear_move(feature_obj.getPropertyByName("cMachine"), pos)
                                            file.write(cmd + "\n")

                                        else:
                                            for cmd in feature_obj.getPropertyByName("eCustomEnd"):
                                                file.write(cmd + "\n")

                                            cmd: str = point_move(feature_obj.getPropertyByName("cMachine"), pos)
                                            file.write(cmd + "\n")

                                    else:
                                        if idx == 0:
                                            cmd: str = point_move(feature_obj.getPropertyByName("cMachine"), pos)
                                            file.write(cmd + "\n")

                                            for cmd in feature_obj.getPropertyByName("dCustomStart"):
                                                file.write(cmd + "\n")

                                        elif idx < len(path):
                                            cmd: str = linear_move(feature_obj.getPropertyByName("cMachine"), pos)
                                            file.write(cmd + "\n")

                                            if idx == len(path) - 1:
                                                for cmd in feature_obj.getPropertyByName("eCustomEnd"):
                                                    file.write(cmd + "\n")

                                file.write("\n")

                        print("Result written to", feature_obj.getPropertyByName("bFile"))
            except FileNotFoundError as e:
                print(e)

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
