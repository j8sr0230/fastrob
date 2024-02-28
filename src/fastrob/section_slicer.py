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

            wires: np.ndarray = np.array(selection.Shape.Wires, dtype=object)
            section_heights: np.ndarray = np.round([w.CenterOfGravity.z for w in wires], 2)
            unique, counts = np.unique(section_heights, return_counts=True)
            # height_occurrence: dict[float, int] = dict(zip(unique, counts))

            sorted_wires: np.ndarray = np.split(wires, np.add.accumulate(counts)[:-1])
            sliced_planes: list[Part.Face] = []
            for wires in sorted_wires:
                sliced_planes.append(Part.Face(wires, "Part::FaceMakerBullseye"))

            offset_paths: list[Part.Wire] = []
            for plane in sliced_planes:
                offset: float = -5
                while offset > -50:
                    Part.show(Part.makeCompound(plane.makeOffset(offset).Wires))
                    # offset_paths.extend(plane.makeOffset(offset).Wires)
                    offset += offset

            Part.show(Part.makeCompound(offset_paths))
            # Part.show(sliced_planes[-1])

        else:
            print("Selected object has no wires.")
    else:
        print("No FreeCAD instance found.")
