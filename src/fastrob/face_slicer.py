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

                    hatch_points: list[tuple[App.Vector, App.Vector]] = list(zip(x_bottom_points, x_top_points))
                    hatch_lines: list[Part.Edge] = []
                    for point_set in hatch_points:
                        hatch_line: Part.Edge = Part.Edge(Part.LineSegment(point_set[0], point_set[1]))
                        hatch_lines.append(hatch_line)
                    hatch_lines: Part.Compound = Part.makeCompound(hatch_lines)
                    hatch_lines.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), BB_ANGLE_DEG)
                    # Part.show(hatch_lines)

                    hatch_sections: list[list[Part.Edge]] = []
                    for hatch_line in hatch_lines.Edges:
                        sections: list[Part.Edge] = Part.Edge(hatch_line).common(face).Edges
                        hatch_sections.append(sections)
                    # print(hatch_sections)

                    hatch_sections_compound: Part.Compound = Part.makeCompound(
                        list(itertools.chain.from_iterable(hatch_sections))
                    )
                    Part.show(hatch_sections_compound)

                    section_group: list[list[Part.Edge]] = [hatch_sections.pop(0)]
                    section_count: int = len(section_group)

                    sorted_sections: list[list[list[Part.Edge]]] = []
                    while hatch_sections:
                        next_section_grp: list[Part.Edge] = hatch_sections.pop(0)
                        next_section_count: int = len(next_section_grp)

                        if section_count == next_section_count:
                            section_group.append(next_section_grp)
                        else:
                            sorted_sections.append(section_group)
                            section_group: list[list[Part.Edge]] = [next_section_grp]

                    print(sorted_sections)

                    # section_count: int = 0
                    # path_sections: list[Part.Edge] = []
                    # for hatch_idx in hatch_sections_map.keys():
                    #     section_count: int = len(hatch_sections_map[hatch_idx])
                    #     for next_hatch_idx in
                    #     if hatch_idx + 1 < len(hatch_sections_map.keys()):

                    #     trimmed_hatch: list[Part.Edge] = []
                    #     section_count: int = len(hatch_sections_map[hatch_idx])
                    #     while hatch_idx < len(hatch_sections_map.keys()) - 1:
                    #         pass
                    #
                    #
                    #         next_hatch_count: int =
                    #         while hatch_count =
                    #
                    #         current_segment: Part.Edge = hatch_sections_map[hatch_idx].pop(0)
                    #
                    #
                    #         print(hatch_count)

                else:
                    print("Selection has no wires.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
