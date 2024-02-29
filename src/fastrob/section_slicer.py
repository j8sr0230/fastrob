from typing import cast

import numpy as np

import FreeCADGui as Gui
import FreeCAD as App
import Part

BB_OFFSET: int = 5
BB_ANGLE_DEG: int = 20
SEAM_WIDTH: int = 5

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
                    face.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), -BB_ANGLE_DEG)
                    bb: App.BoundBox = face.optimalBoundingBox()
                    bb: np.ndarray = np.array([[bb.XMin, bb.YMin, bb.ZMin], [bb.XLength, bb.YLength, bb.ZLength]])
                    bb_offset: np.ndarray = np.array([
                        bb[0] - np.array([BB_OFFSET, BB_OFFSET, 0]),
                        bb[1] + 2 * np.array([BB_OFFSET, BB_OFFSET, 0])
                    ])

                    bb_v0: App.Vector = App.Vector(bb_offset[0])
                    bb_v1: App.Vector = App.Vector(bb_offset[0] + np.array([bb_offset[1][0], 0, 0]))
                    bb_v2: App.Vector = App.Vector(bb_offset[0] + np.array([bb_offset[1][0], bb_offset[1][1], 0]))
                    bb_v3: App.Vector = App.Vector(bb_offset[0] + np.array([0, bb_offset[1][1], 0]))
                    bb_l0 = Part.LineSegment(bb_v0, bb_v1)
                    bb_l2 = Part.LineSegment(bb_v3, bb_v2)

                    line_count: int = int(round(bb_l0.length() / SEAM_WIDTH, 0))
                    bottom_points: list[App.Vector] = bb_l0.discretize(Number=line_count)
                    top_points: list[App.Vector] = bb_l2.discretize(Number=line_count)

                    line_points: list[tuple] = list(zip(bottom_points, top_points))
                    lines: list[Part.LineSegment] = []
                    for line in line_points:
                        lines.append(Part.LineSegment(line[0], line[1]))

                    Part.show(Part.makeCompound(lines).rotate(face.CenterOfGravity, App.Vector(0, 0, 1), BB_ANGLE_DEG))
                else:
                    print("Selection has no wires.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
