from typing import cast
import itertools

import numpy as np

import FreeCADGui as Gui
import FreeCAD as App
import Part

BB_OFFSET: int = 5
BB_ANGLE_DEG: int = -45
SEAM_WIDTH: int = 5

if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                faces: list[Part.Face] = selection.Shape.Faces

                if len(faces) > 0:
                    face: Part.Face = faces[0]
                    rot_face: Part.Face = face.copy()
                    rot_face.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), -BB_ANGLE_DEG)
                    bb: App.BoundBox = rot_face.optimalBoundingBox()
                    bb.enlarge(BB_OFFSET)
                    bb.move(App.Vector(0, 0, BB_OFFSET))

                    bb_left_bottom: App.Vector = App.Vector(bb.XMin, bb.YMin, bb.ZMin)
                    bb_bottom: Part.Edge = Part.Edge(
                        Part.LineSegment(bb_left_bottom, bb_left_bottom + App.Vector(bb.XLength, 0, 0))
                    )

                    hatch_count: int = int(round(bb_bottom.Length / SEAM_WIDTH, 0))
                    hatch_starts: list[App.Vector] = bb_bottom.discretize(Number=hatch_count)
                    hatch: list[Part.Edge] = []
                    for start_point in hatch_starts:
                        hatch.append(
                            Part.Edge(Part.LineSegment(start_point, start_point + App.Vector(0, bb.YLength)))
                        )
                    hatch: Part.Compound = Part.makeCompound(hatch)
                    hatch.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), BB_ANGLE_DEG)

                    trimmed_hatch: list[list[Part.Edge]] = []
                    for hatch_line in hatch.Edges:
                        common: list[Part.Edge] = hatch_line.common(face).Edges
                        if len(common) > 0:
                            trimmed_hatch.append(common)

                    trimmed_hatch_comp: Part.Compound = Part.makeCompound(
                        list(itertools.chain.from_iterable(trimmed_hatch))
                    )

                    hatch_groups: list[list[list[Part.Edge]]] = []
                    hatch_group: list[list[Part.Edge]] = [trimmed_hatch.pop(0)]
                    hatch_group_length: int = len(hatch_group[0])
                    while trimmed_hatch:
                        next_hatch_grp: list[Part.Edge] = trimmed_hatch.pop(0)
                        next_hatch_grp_length: int = len(next_hatch_grp)

                        if hatch_group_length == next_hatch_grp_length:
                            hatch_group.append(next_hatch_grp)
                        else:
                            hatch_groups.append(hatch_group)
                            hatch_group: list[list[Part.Edge]] = [next_hatch_grp]
                            hatch_group_length: int = next_hatch_grp_length
                    else:
                        hatch_groups.append(hatch_group)

                    paths: list[list[Part.Edge]] = []
                    while hatch_groups:
                        hatch_group: list[list[Part.Edge]] = hatch_groups.pop(0)
                        if len(hatch_group[0]) == 1:
                            paths.append(list(itertools.chain.from_iterable(hatch_group)))
                        else:
                            zipped_paths: list[tuple[Part.Edge]] = list(zip(*hatch_group))
                            print(list(zipped_paths))

                            #paths.append(list(zip(*hatch_group)))

                    # print(paths)

                else:
                    print("Selection has no wires.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
