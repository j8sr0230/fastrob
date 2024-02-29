from typing import cast

import numpy as np

import FreeCADGui as Gui
import FreeCAD as App
import Part

BB_OFFSET: int = 5

if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                faces: list[Part.Face] = selection.Shape.Faces
                wires: list[Part.Wire] = selection.Shape.Wires

                if 0 < len(faces) <= len(wires):
                    face: Part.Face = faces[0]
                    bb: App.BoundBox = face.optimalBoundingBox()
                    bb_np: np.ndarray = np.array([[bb.XMin, bb.YMin, bb.ZMin], [bb.XLength, bb.YLength, bb.ZLength]])
                    bb_offset: np.ndarray = np.array([
                        bb_np[0] - np.array([BB_OFFSET, BB_OFFSET, 0]),
                        bb_np[1] + 2 * np.array([BB_OFFSET, BB_OFFSET, 0])
                    ])

                    bb_v0: App.Vector = App.Vector(bb_offset[0])
                    bb_v1: App.Vector = App.Vector(bb_offset[0] + np.array([bb_offset[1][0], 0, 0]))
                    bb_v2: App.Vector = App.Vector(bb_offset[0] + np.array([bb_offset[1][0], bb_offset[1][1], 0]))
                    bb_v3: App.Vector = App.Vector(bb_offset[0] + np.array([0, bb_offset[1][1], 0]))

                    bb_l0 = Part.LineSegment(bb_v0, bb_v1)
                    bb_l1 = Part.LineSegment(bb_v1, bb_v2)
                    bb_l2 = Part.LineSegment(bb_v2, bb_v3)
                    bb_l3 = Part.LineSegment(bb_v3, bb_v0)

                    s_bb: Part.Shape = Part.Shape([bb_l0, bb_l1, bb_l2, bb_l3])
                    w_bb = Part.Wire(s_bb.Edges)

                    Part.show(w_bb)
                else:
                    print("Selection has no wires.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
