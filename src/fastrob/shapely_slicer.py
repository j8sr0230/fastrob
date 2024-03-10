from typing import Any, Union, cast
from math import sqrt
from itertools import accumulate

import numpy as np
from shapely import segmentize
from shapely.geometry import Point, LineString, MultiLineString, Polygon, MultiPolygon
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
        plot_line(line, ax=ax, color=GRAY, alpha=0.5, add_points=True)  # type: ignore

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


def fill_zig_zag(sections: list[list[MultiPolygon]], angle_deg: float, width: float) -> list[MultiLineString]:
    result: list[MultiLineString] = []

    for layer_section in sections:
        filling_area: MultiPolygon = layer_section[-1]

        temp_result: MultiLineString = MultiLineString()
        for filling_sub_area in filling_area.geoms:
            filling_centroid: Point = filling_sub_area.centroid
            extended_filling_area: MultiPolygon = filling_sub_area.buffer(1)
            rotated_filling_area: MultiPolygon = rotate(extended_filling_area, angle_deg, filling_centroid)
            min_x, min_y, max_x, max_y = rotated_filling_area.bounds

            major_count: int = int(round((max_y - min_y) / width, 0))
            major_step: float = (max_y - min_y) / major_count
            minor_count: int = 5
            print("Major Step", major_step)
            print("Minor Step", major_step / minor_count)


            y_pos: np.ndarray = np.arange(min_y, max_y + major_step, major_step / minor_count)
            print("y_pos", y_pos)
            print("Y%", y_pos % major_step)
            print("Y% off", (y_pos - y_pos[0]))
            print("Y - %", (y_pos - y_pos[0] % major_step))
            print()

            major_coors: list[list[tuple[float, float]]] = []
            minor_coors: list[list[tuple[float, float]]] = []
            for y in y_pos:
                if round(y % major_step, 0) == 0:
                    major_coors.append([(min_x, y), (max_x, y)])
                else:
                    minor_coors.append([(min_x, y), (max_x, y)])

            major_hatch: MultiLineString = rotate(MultiLineString(major_coors), -angle_deg, filling_centroid)
            major_trimmed_hatch: Any = major_hatch.intersection(filling_sub_area)
            if type(major_trimmed_hatch) in (LineString, MultiLineString) and not major_trimmed_hatch.is_empty:
                major_trimmed_hatch: Union[LineString, MultiLineString] = segmentize(major_trimmed_hatch, 2)
                temp_result: MultiLineString = temp_result.union(major_trimmed_hatch)

            minor_hatch: MultiLineString = rotate(MultiLineString(minor_coors), -angle_deg, filling_centroid)
            minor_trimmed_hatch: Any = minor_hatch.intersection(filling_sub_area)
            if type(minor_trimmed_hatch) in (LineString, MultiLineString) and not minor_trimmed_hatch.is_empty:
                temp_result: MultiLineString = temp_result.union(minor_trimmed_hatch)
        print()
        result.append(temp_result)

    return result

# def zig_zag_lines(polygon: Polygon, angle_deg: float, seam_width: float, connected: bool) -> list[LineString]:
#     rotated_poly: Polygon = rotate(polygon, angle=angle_deg, origin="centroid", use_radians=False)
#     min_x, min_y, max_x, max_y = rotated_poly.bounds
#
#     hatch_count: int = int(round((max_y-min_y) / seam_width, 0))
#     hatch_y_pos: np.ndarray = np.linspace(min_y, max_y, hatch_count)
#
#     hatch_y_coords: list[list[tuple[float, float]]] = []
#     for idx, y_pos in enumerate(hatch_y_pos):
#         if idx % 2 == 0:
#             hatch_y_coords.append([(min_x, y_pos), (max_x, y_pos)])
#         else:
#             hatch_y_coords.append([(max_x, y_pos), (min_x, y_pos)])
#     hatch: MultiLineString = rotate(
#         MultiLineString(hatch_y_coords), angle=-angle_deg, origin=polygon.centroid, use_radians=False
#     )
#
#     trimmed_hatch: Any = hatch.intersection(polygon)
#
#     flat_trimmed_hatch: list[LineString] = []
#     if type(trimmed_hatch) is LineString:
#         if trimmed_hatch.length > 0:
#             flat_trimmed_hatch.append(trimmed_hatch)
#     elif hasattr(trimmed_hatch, "geoms"):
#         for item in trimmed_hatch.geoms:
#             if type(item) is LineString and item.length > 0:
#                 flat_trimmed_hatch.append(item)
#
#     connectors: list[LineString] = []
#     for idx, hatch_l in enumerate(flat_trimmed_hatch):
#         if idx < len(flat_trimmed_hatch) - 1:
#             next_hatch_line: LineString = flat_trimmed_hatch[idx + 1]
#             print(hatch_l.coords.xy[1], next_hatch_line.coords.xy[0])
#             print()
#             # connector: LineString = LineString(
#             #     [hatch_line.coords.xy[1], next_hatch_line.coords.xy[0]]
#             # )
#             # connectors.append(connector)
#             # flat_trimmed_hatch.append(connector)
#     return flat_trimmed_hatch


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
                        sections=planar_cuts, offsets=(0., 2., 2., 1.)
                    )
                    filling: list[MultiLineString] = fill_zig_zag(
                        sections=planar_offsets, angle_deg=0, width=2
                    )
                    # print([type(f) for f in filling])

                    layer_num: int = -1
                    draw_slice(planar_offsets[layer_num], [filling[layer_num]])
                    coords: Any = [geo.coords.xy for geo in filling[layer_num].geoms]
                    print(coords[0][0])

                    # G: nx.Graph = nx.Graph()
                    # G.add_nodes_from(point_attribute_list)
                    # G.add_edges_from(nx.geometric_edges(G, radius=2.7))
                    # nx.draw(G, pos=nx.get_node_attributes(G, "pos"), node_size=10, with_labels=False)
                    # plt.show()

                    # filling_lines: list[list[LineString]] = []
                    # for contour_poly in contour_polys:
                    #     remainder_poly: Polygon = contour_poly[-1]
                    #
                    #     level_lines: list[LineString] = []
                    #     if type(remainder_poly) is MultiPolygon:
                    #         for poly in cast(MultiPolygon, remainder_poly).geoms:
                    #             level_lines.extend(
                    #                 zig_zag_lines(polygon=poly, angle_deg=-45, seam_width=2, connected=True)
                    #             )
                    #     else:
                    #         level_lines.extend(
                    #             zig_zag_lines(polygon=remainder_poly, angle_deg=-45, seam_width=2, connected=True)
                    #         )
                    #     filling_lines.append(level_lines)

                else:
                    print("No solid selected.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
