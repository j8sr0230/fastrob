from typing import cast
import itertools

import FreeCADGui as Gui
import FreeCAD as App
import Part

BB_OFFSET: int = 5


class ZigZagFaceSlicer:
    def __init__(self, face: Part.Face, angle_deg: int = -45, seam_width: float = 2, continuous: bool = True) -> None:
        self._face: Part.Face = face
        self._angle_deg: int = angle_deg
        self._seam_width: float = seam_width
        self._continuous: bool = continuous

    def slice(self) -> list[Part.Wire]:
        rot_face: Part.Face = self._face.copy()
        rot_face.rotate(self._face.CenterOfGravity, App.Vector(0, 0, 1), -self._angle_deg)
        bb: App.BoundBox = rot_face.optimalBoundingBox()
        bb.enlarge(BB_OFFSET)
        bb.move(App.Vector(0, 0, BB_OFFSET))

        bb_left_bottom: App.Vector = App.Vector(bb.XMin, bb.YMin, bb.ZMin)
        bb_left: Part.Edge = Part.Edge(Part.LineSegment(
            bb_left_bottom,
            bb_left_bottom + App.Vector(0, bb.YLength, 0)
        ))

        hatch_count: int = int(round(bb_left.Length / self._seam_width, 0))
        hatch_starts: list[App.Vector] = bb_left.discretize(Number=hatch_count)
        hatch: list[Part.Edge] = []
        for start_point in hatch_starts:
            hatch.append(Part.Edge(Part.LineSegment(
                start_point,
                start_point + App.Vector(bb.XLength, 0)
            )))
        hatch: Part.Compound = Part.makeCompound(hatch)
        hatch.rotate(self._face.CenterOfGravity, App.Vector(0, 0, 1), self._angle_deg)

        trimmed_hatch: list[list[Part.Edge]] = []
        for hatch_line in hatch.Edges:
            common: list[Part.Edge] = hatch_line.common(self._face).Edges
            if len(common) > 0:
                trimmed_hatch.append(common)

        section_groups: list[list[list[Part.Edge]]] = []
        section_grp: list[list[Part.Edge]] = [trimmed_hatch.pop(0)]
        section_grp_count: int = len(section_grp[0])
        while trimmed_hatch:
            next_hatch_grp: list[Part.Edge] = trimmed_hatch.pop(0)
            next_hatch_grp_length: int = len(next_hatch_grp)

            if section_grp_count == next_hatch_grp_length:
                section_grp.append(next_hatch_grp)
            else:
                section_groups.append(section_grp)
                section_grp: list[list[Part.Edge]] = [next_hatch_grp]
                section_grp_count: int = next_hatch_grp_length
        else:
            section_groups.append(section_grp)

        sorted_section_groups: list[list[Part.Edge]] = []
        while section_groups:
            section_grp: list[list[Part.Edge]] = section_groups.pop(0)
            if len(section_grp[0]) == 1:
                sorted_section_groups.append(list(itertools.chain.from_iterable(section_grp)))
            else:
                zipped_sections: list[tuple[Part.Edge]] = list(zip(*section_grp))
                zipped_sections: list[list[Part.Edge]] = [list(tpl) for tpl in zipped_sections]
                sorted_section_groups.extend(zipped_sections)

        result: list[Part.Wire] = []
        while sorted_section_groups:
            sorted_section_grp: list[Part.Edge] = sorted_section_groups.pop(0)

            if self._continuous:
                connectors: list[Part.Edge] = []
                section_len: int = len(sorted_section_grp)

                for idx, edge in enumerate(sorted_section_grp):
                    if idx < section_len - 1:
                        next_edge: Part.Edge = sorted_section_grp[idx + 1]

                        if idx % 2 == 0:
                            start: App.Vector = App.Vector(edge.Vertexes[1].Point)
                            end: App.Vector = App.Vector(next_edge.Vertexes[1].Point)
                        else:
                            start: App.Vector = App.Vector(edge.Vertexes[0].Point)
                            end: App.Vector = App.Vector(next_edge.Vertexes[0].Point)

                        connectors.append(Part.Edge(Part.LineSegment(start, end)))
                result.append(Part.Wire(Part.__sortEdges__(sorted_section_grp + connectors)))

            else:
                for idx, edge in enumerate(sorted_section_grp):
                    if idx % 2 == 0:
                        edge_points: list[App.Vector] = [App.Vector(v.Point) for v in edge.Vertexes]
                        edge_points.reverse()
                        result.append(Part.Wire(
                            [Part.Edge(Part.LineSegment(edge_points[0], edge_points[1]))]
                        ))
                    else:
                        result.append(Part.Wire([edge]))
        return result


class OffsetFaceSlicer:
    def __init__(self, face: Part.Face, seam_width: float = 4, contours: int = 2) -> None:
        self._face: Part.Face = face
        self._seam_width: float = seam_width
        self._contours: int = contours

    @staticmethod
    def make_offset_2d(face: Part.Face, offset: float) -> list[Part.Face]:
        outer_wire: Part.Wire = cast(Part.Wire, face.OuterWire)
        outer_face: Part.Face = Part.Face(outer_wire)
        outer_offset: Part.Face = outer_face.makeOffset2D(-offset, 0, False, False, False)

        inner_wires: list[Part.Wire] = [inner for inner in face.Wires if not inner.isEqual(outer_wire)]
        inner_faces: list[Part.Face] = [Part.Face(w) for w in inner_wires]
        inner_comp: Part.Compound = Part.Compound(inner_faces)
        inner_offset: Part.Compound = inner_comp.makeOffset2D(offset, 0, False, False, False)

        result: list[Part.Face] = outer_offset.cut(inner_offset).Faces
        if len(result) == 0:
            raise ValueError
        return result

    def slice(self) -> list[Part.Face]:
        result: list[Part.Face] = []
        for i in range(self._contours):
            try:
                offset_faces: list[Part.Face] = self.make_offset_2d(self._face, (i + 1) * (self._seam_width / 2))
                result.extend(offset_faces)
            except ValueError:
                print("To many contours.")
                result: list[Part.Face] = [self._face]
                break
            except Part.OCCError:
                print("Maximal offset reached.")
                break
            except App.Base.CADKernelError:  # noqa
                print("Maximal offset reached.")
                break

        return result

    def post_process(self) -> None:
        # outer_result_wire: Part.Wire = cast(Part.Wire, result.Faces[0].OuterWire)
        # inner_result_wires: list[Part.Wire] = [w for w in result.Wires if not w.isEqual(outer_result_wire)]
        # distance_map: list = [inner_w.distToShape(outer_result_wire)[0] for inner_w in inner_result_wires]
        # if any([d <= abs(offset) for d in distance_map]):
        #     print("Trim")
        #     inner_result_comp: Part.Compound = Part.Compound(inner_result_wires)
        #     cutter: Part.Face = Part.Face(outer_result_wire).makeOffset2D(offset, 0, True, False, False)
        #     trimmed_inner_wires: Part.Shape = inner_result_comp.cut(cutter)
        #     Part.show(trimmed_inner_wires)
        # result: Part.Shape = Part.Face(Part.Compound([outer_result_wire]))
        pass


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                faces: list[Part.Face] = selection.Shape.Faces

                if len(faces) > 0:
                    target_face: Part.Face = faces[0]

                    offset_slicer: OffsetFaceSlicer = OffsetFaceSlicer(
                        face=target_face, seam_width=4, contours=3
                    )
                    contour_faces: list[Part.Face] = offset_slicer.slice()
                    contour_comp: Part.Compound = Part.Compound(contour_faces[:-1])
                    Part.show(contour_comp)

                    for inner_face in contour_faces[-1].Faces:
                        zig_zag_slicer: ZigZagFaceSlicer = ZigZagFaceSlicer(
                            face=inner_face, angle_deg=-45, seam_width=1, continuous=True
                        )
                        filling_path: list[Part.Wire] = zig_zag_slicer.slice()
                        Part.show(Part.Compound(filling_path))
                else:
                    print("Selection has no face.")
            else:
                print("Selection has no shape.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
