from typing import Optional, cast
import itertools

import FreeCADGui as Gui
import FreeCAD as App
import Part
import numpy as np

BB_OFFSET: int = 5


def layers(solid: Part.Solid, layer_height: float) -> list[Part.Face]:
    bb: App.BoundBox = solid.optimalBoundingBox()
    layer_heights: np.ndarray = np.arange(bb.ZMin, bb.ZMax, layer_height)

    faces: list[Part.Face] = []
    for z_level in layer_heights:
        wire_set: list[Part.Wire] = solid.slice(App.Vector(0, 0, 1), z_level)
        face: Part.Shape = Part.makeFace(wire_set, "Part::FaceMakerBullseye")
        faces.extend(face.Faces)
    return faces


def offset_faces(face: Part.Face, offsets: list[float]) -> list[list[Part.Face]]:
    result: list[list[Part.Face]] = []
    for offset in itertools.accumulate(offsets):
        try:
            result.append(face.makeOffset2D(-offset, 0, False, False, False).Faces)
        except (Part.OCCError, App.Base.CADKernelError):  # noqa
            pass

    return result


def zig_zag_wires(face: Part.Face, angle_deg: float, seam_width: float, connected: bool) -> list[Part.Wire]:
    rot_face: Part.Face = face.copy()
    rot_face.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), -angle_deg)
    bb: App.BoundBox = rot_face.optimalBoundingBox()
    bb.enlarge(BB_OFFSET)
    bb.move(App.Vector(0, 0, BB_OFFSET))

    bb_left_bottom: App.Vector = App.Vector(bb.XMin, bb.YMin, bb.ZMin)
    bb_left_edge: Part.Edge = Part.Edge(Part.LineSegment(
        bb_left_bottom, bb_left_bottom + App.Vector(0, bb.YLength, 0)
    ))

    hatch_count: int = int(round(bb_left_edge.Length / seam_width, 0))
    hatch_starts: list[App.Vector] = bb_left_edge.discretize(Number=hatch_count)
    hatch: list[Part.Edge] = [
        Part.Edge(Part.LineSegment(start, start + App.Vector(bb.XLength, 0))) for start in hatch_starts
    ]

    hatch_compound: Part.Compound = Part.makeCompound(hatch)
    hatch_compound.rotate(face.CenterOfGravity, App.Vector(0, 0, 1), angle_deg)

    trimmed_hatch: list[list[Part.Edge]] = [
        hatch_line.common(face).Edges for hatch_line in hatch_compound.Edges if len(hatch_line.common(face).Edges) > 0
    ]

    result: list[Part.Wire] = []
    if len(trimmed_hatch) > 0:
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

        while sorted_section_groups:
            sorted_section_grp: list[Part.Edge] = sorted_section_groups.pop(0)

            if connected:
                connectors: list[Part.Edge] = []

                for idx, edge in enumerate(sorted_section_grp):
                    if idx < len(sorted_section_grp) - 1:
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


def trim_wires(wires: list[Part.Wire], clean_distance: float) -> list[Part.Wire]:
    unique_combinations_array: np.ndarray = np.array(list(itertools.combinations(range(len(wires)), 2)))

    distances: np.ndarray = np.round(
        [wires[item[0]].distToShape(wires[item[1]])[0] for item in unique_combinations_array], 1
    )
    invalid_combinations: np.ndarray = unique_combinations_array[distances < clean_distance]
    invalid_wires: list[list[Part.Wire]] = [
        [wires[combination[0]], wires[combination[1]]] for combination in invalid_combinations
    ]

    invalid_wire_areas: list[list[float]] = []
    for wire_set in invalid_wires:
        area_0: float = 0 if not wire_set[0].isClosed() else Part.Face(wire_set[0]).Area
        area_1: float = 0 if not wire_set[1].isClosed() else Part.Face(wire_set[1]).Area
        invalid_wire_areas.append([area_0, area_1])

    for idx, invalid_area_set in enumerate(invalid_wire_areas):
        if invalid_area_set[0] > invalid_area_set[1]:
            cut_wire: Part.Wire = invalid_wires[idx][0]
            invalid_wire: Part.Wire = invalid_wires[idx][1]
        else:
            cut_wire: Part.Wire = invalid_wires[idx][1]
            invalid_wire: Part.Wire = invalid_wires[idx][0]

        trimmed_wire: Optional[Part.Shape] = None
        try:
            cutter: Part.Shape = cut_wire.makeOffset2D(-clean_distance, 0, True, False, False)
            trimmed_wire: Part.Shape = invalid_wire.cut(cutter)
        except (Part.OCCError, App.Base.CADKernelError):  # noqa
            pass

        if hasattr(trimmed_wire, "Wires") and len(trimmed_wire.Wires) > 0:
            if invalid_wire in wires:
                invalid_idx: int = wires.index(invalid_wire)
                wires.remove(invalid_wire)
                wires[invalid_idx:invalid_idx] = trimmed_wire.Wires

    return wires


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                target_solid: Part.Solid = selection.Shape.Solids[0]
                if target_solid is not None:
                    sliced_wires: list[Part.Wire] = []

                    target_faces: list[Part.Face] = layers(solid=target_solid, layer_height=2)

                    if len(target_faces) > 0:
                        is_even: bool = False
                        while target_faces:
                            target_face: Part.Face = target_faces.pop(0)
                            is_even: bool = not is_even

                            offset_face_list: list[list[Part.Face]] = offset_faces(face=target_face,
                                                                                   offsets=[2, 2, 1, 1])
                            if len(offset_face_list) > 1:
                                contour_faces: list[Part.Face] = list(
                                    itertools.chain.from_iterable(offset_face_list[:-1])
                                )
                            else:
                                contour_faces: list[Part.Face] = offset_face_list[0]

                            contour_compound: Part.Compound = Part.Compound(contour_faces)
                            contour_wires: list[Part.Wire] = contour_compound.Wires
                            # contour_wires: list[Part.Wire] = trim_wires(contour_wires, 2)

                            filling_angle_deg: float = -45 if is_even else 45
                            filling_face_list: list[Part.Face] = offset_face_list[-1]
                            filling_wires: list[list[Part.Wire]] = []
                            for target_face in filling_face_list:
                                filling: list[Part.Wire] = zig_zag_wires(
                                    face=target_face,  angle_deg=filling_angle_deg, seam_width=1, connected=True
                                )
                                filling_wires.append(filling)

                            if len(filling_wires) > 1:
                                filling_wires: list[Part.Wire] = list(itertools.chain.from_iterable(filling_wires))
                            else:
                                filling_wires: list[Part.Wire] = filling_wires[0]
                            # filling_wires: list[Part.Wire] = trim_wires(filling_wires, 1)

                            sliced_wires.extend(contour_wires + filling_wires)
                            # sliced_wires: list[Part.Wire] = trim_wires(sliced_wires, 1)

                        Part.show(Part.Compound(sliced_wires))
                else:
                    print("Selection has no solid.")
            else:
                print("Selection has no shape.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
