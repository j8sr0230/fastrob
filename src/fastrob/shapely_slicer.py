from typing import Any, Union, Callable, cast
from math import sqrt
from itertools import accumulate

import numpy as np
from shapely import intersection_all
from shapely.geometry import Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon
from shapely.affinity import rotate
from shapely.plotting import plot_line, plot_polygon
import matplotlib.pyplot as plt
import networkx as nx

import FreeCADGui as Gui
import FreeCAD as App
import Part


GM = (sqrt(5)-1.0)/2.0
W = 8.0
H = W*GM
SIZE = (W, H)

BLUE = '#6699cc'
GRAY = '#999999'
DARK_GRAY = '#333333'
YELLOW = '#ffcc33'
GREEN = '#339933'
RED = '#ff3333'
BLACK = '#000000'

DISCRETIZE_DISTANCE: float = 2


def draw_slice(polygons: list[Union[Polygon, MultiPolygon]], lines: list[MultiLineString]) -> None:
    fig: plt.Figure = plt.figure(1, figsize=SIZE, dpi=90)
    ax: plt.Axes = fig.add_subplot(111)
    ax.set_title("Slice Viewer")
    ax.set_xlabel("X in mm")
    ax.set_ylabel("Y in mm")
    ax.set_aspect("equal")

    for idx, polygon in enumerate(polygons):
        if idx == 0:
            plot_polygon(polygon, ax=ax, facecolor=GRAY, edgecolor=BLUE, alpha=0.5, add_points=False)
        elif idx == len(polygons) - 1:
            plot_polygon(polygon, ax=ax, facecolor=BLUE, edgecolor=BLUE, alpha=0.5, add_points=False)
        else:
            plot_polygon(polygon, ax=ax, facecolor="#fff", edgecolor=BLUE, alpha=0.5, add_points=False)

    for line in lines:
        plot_line(line, ax=ax, color=GRAY, alpha=0.5, add_points=False)  # type: ignore

    plt.show()


def slice_solid(solid: Part.Solid, layer_height: float) -> list[MultiPolygon]:
    bb: App.BoundBox = solid.BoundBox
    layer_heights: np.ndarray = np.arange(bb.ZMin + layer_height, bb.ZMax + layer_height, layer_height)

    result: list[MultiPolygon] = []
    for layer_height in layer_heights:
        section_wires: list[Part.Wire] = solid.slice(App.Vector(0, 0, 1), layer_height)
        section_shapes: Part.Shape = Part.makeFace(section_wires, "Part::FaceMakerBullseye")

        section_faces: list[Polygon] = []
        for section_face in section_shapes.Faces:
            if section_face.isValid() and section_face.Area > 0:
                exterior_wire: Part.Wire = cast(Part.Wire, section_face.OuterWire)
                interior_wires: list[Part.Wire] = [
                    wire for wire in section_face.Wires if not wire.isEqual(exterior_wire)
                ]

                ext_points: list[tuple] = [tuple(v) for v in exterior_wire.discretize(Distance=DISCRETIZE_DISTANCE)]
                int_points: list[list[tuple]] = [
                    [tuple(v) for v in wire.discretize(Distance=DISCRETIZE_DISTANCE)] for wire in interior_wires
                ]
                section_faces.append(Polygon(shell=ext_points, holes=int_points))
        result.append(MultiPolygon(section_faces))

    return result


def offset_sections(sections: list[MultiPolygon], offsets: tuple[float, ...]) -> list[list[MultiPolygon]]:
    result: list[list[MultiPolygon]] = []

    for section in sections:
        layer_offsets: list[MultiPolygon] = []
        for offset in accumulate(offsets):
            buffer_polygon: Union[Polygon, MultiPolygon] = section.buffer(-offset)

            if not buffer_polygon.is_empty:
                if type(buffer_polygon) is Polygon:
                    layer_offsets.append(MultiPolygon([buffer_polygon]))
                else:
                    layer_offsets.append(buffer_polygon)
            else:
                break

        result.append(layer_offsets)
    return result


def fill_zig_zag(sections: list[list[MultiPolygon]], angle_deg: float, offset: float) -> list[MultiLineString]:
    result: list[MultiLineString] = []

    for layer_section in sections:
        filling_area: MultiPolygon = layer_section[-1]

        temp_result: MultiLineString = MultiLineString()
        for filling_sub_area in filling_area.geoms:
            filling_centroid: Point = filling_sub_area.centroid
            rotated_filling_area: MultiPolygon = rotate(filling_sub_area, angle_deg, filling_centroid)
            shrunk_filling_area: MultiPolygon = rotated_filling_area.buffer(-0.1)
            min_x, min_y, max_x, max_y = shrunk_filling_area.bounds

            fill_height: float = max_y - min_y
            hatch_line_count: int = int(np.round(fill_height / offset, 0))
            hatch_line_distance: float = fill_height / hatch_line_count

            hatch_line_coords: list[list[tuple[float, float]]] = []
            if fill_height > hatch_line_distance:
                hatch_y_pos: np.ndarray = np.arange(
                    start=min_y,
                    stop=max_y + hatch_line_distance,
                    step=hatch_line_distance
                )
                for y in hatch_y_pos:
                    hatch_line_coords.append([(min_x - 2, y), (max_x + 2, y)])
            else:
                hatch_line_coords: list[list[tuple[float, float]]] = [
                    [(min_x - 2, min_y + (fill_height / 2)), (max_x + 2, min_y + (fill_height / 2))]
                ]

            hatch: MultiLineString = rotate(MultiLineString(hatch_line_coords), -angle_deg, filling_centroid)
            hatch_intersections: list[int] = [
                len(item.geoms) for item in filling_sub_area.boundary.intersection(hatch.geoms) if not item.is_empty
            ]
            print(len(result), ":", hatch_intersections)

            sorted_intersection_ids: list[list[int]] = []
            group: list[int] = []
            intersect_count: int = 0
            for idx, num in enumerate(hatch_intersections):
                if num == intersect_count:
                    group.append(idx)
                else:
                    sorted_intersection_ids.append(group)
                    group: list[int] = [num]
                    intersect_count = num
            else:
                sorted_intersection_ids.append(group)
            print(sorted_intersection_ids)




            temp_result: MultiLineString = temp_result.union(hatch)

            # intersection_count: list[int] = []
            # for line in hatch.geoms:
            #     if type(filling_sub_area.boundary.intersection(line)) is MultiPoint:
            #         intersection_count.append(len(filling_sub_area.boundary.intersection(line).geoms))
            #
            # print(intersection_count)
            # trimmed_hatch: Any = hatch.intersection(filling_sub_area)
            # if type(trimmed_hatch) in (LineString, MultiLineString) and not trimmed_hatch.is_empty:
                # trimmed_hatch: Union[LineString, MultiLineString] = segmentize(trimmed_hatch, 1)
                # temp_result: MultiLineString = temp_result.union(hatch)

        result.append(temp_result)

    return result


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Solids) > 0:
                    target_solid: Part.Solid = selection.Shape.Solids[0]

                    planar_cuts: list[MultiPolygon] = slice_solid(solid=target_solid, layer_height=5)
                    planar_offsets: list[list[MultiPolygon]] = offset_sections(
                        sections=planar_cuts, offsets=(0., 2., 1.)
                    )
                    filling: list[MultiLineString] = fill_zig_zag(
                        sections=planar_offsets, angle_deg=-0, offset=2.
                    )

                    layer_num: int = -1
                    draw_slice(planar_offsets[layer_num], [filling[layer_num]])

                else:
                    print("No solid selected.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
