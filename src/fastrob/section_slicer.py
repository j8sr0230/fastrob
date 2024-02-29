from typing import cast
import itertools

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
                    rot_face: Part.Face = face.copy()
                    rot_face.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), -BB_ANGLE_DEG)
                    bb: App.BoundBox = rot_face.optimalBoundingBox()
                    bb: np.ndarray = np.array([[bb.XMin, bb.YMin, bb.ZMin], [bb.XLength, bb.YLength, bb.ZLength]])
                    bb_offset: np.ndarray = np.array([
                        bb[0] - np.array([BB_OFFSET, BB_OFFSET, 0]),
                        bb[1] + 2 * np.array([BB_OFFSET, BB_OFFSET, 0])
                    ])

                    bb_v0: App.Vector = App.Vector(bb_offset[0])
                    bb_v1: App.Vector = App.Vector(bb_offset[0] + np.array([bb_offset[1][0], 0, 0]))
                    bb_v2: App.Vector = App.Vector(bb_offset[0] + np.array([bb_offset[1][0], bb_offset[1][1], 0]))
                    bb_v3: App.Vector = App.Vector(bb_offset[0] + np.array([0, bb_offset[1][1], 0]))

                    bb_x_bottom: Part.Edge = Part.Edge(Part.LineSegment(bb_v0, bb_v1))
                    bb_x_top: Part.Edge = Part.Edge(Part.LineSegment(bb_v3, bb_v2))

                    hatch_count: int = int(round(bb_x_bottom.Length / SEAM_WIDTH, 0))
                    x_bottom_points: list[App.Vector] = bb_x_bottom.discretize(Number=hatch_count)
                    x_top_points: list[App.Vector] = bb_x_top.discretize(Number=hatch_count)

                    hatch_points: list[tuple] = list(zip(x_bottom_points, x_top_points))
                    hatch_lines: list[Part.Edge] = []
                    for point_set in hatch_points:
                        hatch_line: Part.Edge = Part.Edge(Part.LineSegment(point_set[0], point_set[1]))
                        hatch_lines.append(hatch_line)
                    hatch_lines: Part.Compound = Part.makeCompound(hatch_lines)
                    hatch_lines.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), BB_ANGLE_DEG)

                    hatch_line_map: dict[int, list[Part.Edge]] = {}
                    for idx, hatch_line in enumerate(hatch_lines.Edges):
                        inner_line_set: list[Part.Edge] = Part.Edge(hatch_line).common(face).Edges
                        hatch_line_map[idx] = inner_line_set

                    inner_hatch: Part.Compound = Part.makeCompound(
                        list(itertools.chain.from_iterable(hatch_line_map.values()))
                    )
                    Part.show(inner_hatch)
                    print(hatch_line_map)
                else:
                    print("Selection has no wires.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
