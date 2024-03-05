from typing import cast
import itertools

import FreeCADGui as Gui
import FreeCAD as App
import Part
import numpy as np

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
    def __init__(self, face: Part.Face, offsets: tuple[float, ...] = (4, )) -> None:
        self._face: Part.Face = face
        self._offsets: tuple[float] = offsets

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

    def slice(self) -> list[list[Part.Face]]:
        result: list[list[Part.Face]] = []
        for offset in self._offsets:
            try:
                result.append(self.make_offset_2d(self._face, offset))
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

    def adaptive_clean(self, raw_wires: list[Part.Wire]) -> list[Part.Wire]:
        combinations: itertools.permutations = itertools.permutations(range(len(raw_wires)), 2)
        unique_combinations: set = set(map(lambda x: tuple(sorted(x)), list(combinations)))
        unique_combinations_array: np.ndarray = np.array(list(unique_combinations))

        distances: np.ndarray = np.round(
            [raw_wires[item[0]].distToShape(raw_wires[item[1]])[0] for item in unique_combinations_array],
            1)

        invalid_combinations: np.ndarray = unique_combinations_array[distances < self._offsets[0]]
        invalid_wires: list[list[Part.Wire]] = [
            [raw_wires[combination[0]], raw_wires[combination[1]]] for combination in invalid_combinations
        ]
        invalid_wire_areas: list[list[float]] = [
            [Part.Face(wire_set[0]).Area, Part.Face(wire_set[1]).Area] for wire_set in invalid_wires
        ]
        print(invalid_wires)
        print(invalid_wire_areas)

        return raw_wires


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
                        face=target_face, offsets=(2., 4., 5.)
                    )
                    offset_faces: list[list[Part.Face]] = offset_slicer.slice()
                    offset_contour_faces: list[Part.Face] = list(itertools.chain.from_iterable(offset_faces[:-1]))
                    offset_contour_comp: Part.Compound = Part.Compound(offset_contour_faces)
                    raw_offset_wires: list[Part.Wire] = offset_contour_comp.Wires
                    cleaned_wires: list[Part.Wire] = offset_slicer.adaptive_clean(raw_offset_wires)
                    Part.show(Part.Compound(cleaned_wires))

                    remainder_faces: list[Part.Face] = offset_faces[-1]
                    for inner_face in remainder_faces:
                        zig_zag_slicer: ZigZagFaceSlicer = ZigZagFaceSlicer(
                            face=inner_face, angle_deg=-45, seam_width=2, continuous=True
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
