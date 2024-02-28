from typing import Optional, cast

import numpy as np

import FreeCADGui as Gui
import FreeCAD as App
import Part


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: Optional[App.DocumentObject] = Gui.Selection.getSelection()[0]
        else:
            selection: Optional[App.DocumentObject] = None
        print("Selected object:", selection.Label if selection is not None else selection)

        if selection is not None and hasattr(selection, "Shape") and hasattr(selection.Shape, "Wires"):
            selection: App.GeoFeature = cast(App.GeoFeature, selection)
            print(selection.Shape.Wires)

        else:
            print("Selected object has no wires.")
    else:
        print("No FreeCAD instance found.")
