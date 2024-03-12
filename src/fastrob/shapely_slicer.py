from typing import Union, cast
from math import sqrt
from itertools import accumulate, chain

import numpy as np

from shapely import distance, minimum_clearance
from shapely.geometry import Point, LineString, MultiLineString, Polygon, MultiPolygon
from shapely.affinity import rotate
from shapely.ops import linemerge
from shapely.plotting import plot_line, plot_polygon

from matplotlib.widgets import Slider
import matplotlib.pyplot as plt

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

DISCRETIZE_DISTANCE: float = 3


def print_poly_data(polygons: list[list[Union[Polygon, MultiPolygon]]], layer_idx: int) -> None:
    layer_m_polys: list[MultiPolygon] = [m_poly for m_poly in polygons[layer_idx]]
    for m_poly in layer_m_polys:
        for poly in m_poly.geoms:
            interiors: list[Polygon] = [Polygon(poly) for poly in MultiLineString(poly.interiors).geoms]

            print("Type:", type(poly))
            print("Polygons minimal clearance:", minimum_clearance(poly))
            print("Exterior type:", type(poly.exterior))
            print("Has interior:", not MultiLineString(poly.interiors).is_empty)
            print("Interior count:", len(interiors))
            print("Distance to interiors:", [distance(poly.exterior, interior) for interior in interiors])
            print()


def draw_slice(polygons: list[list[Union[Polygon, MultiPolygon]]], lines: list[MultiLineString]) -> Slider:
    fig: plt.Figure = plt.figure(1, figsize=SIZE, dpi=90)
    ax: plt.Axes = fig.add_subplot(111)
    ax.set_title("Slice Viewer")
    ax.set_xlabel("X in mm")
    ax.set_ylabel("Y in mm")
    ax.set_aspect("equal")

    layer_ax: plt.Axes = fig.add_axes((.94, 0.2, 0.02, 0.6))
    layer_slider: Slider = Slider(
        ax=layer_ax,
        label="Layer",
        valmin=0,
        valmax=len(polygons) - 1,
        valinit=len(polygons) - 1,
        orientation="vertical"
    )

    def update(val: float) -> None:
        ax.clear()

        for idx, polygon in enumerate(polygons[int(val)]):
            if idx == 0:
                plot_polygon(polygon, ax=ax, facecolor=GRAY, edgecolor=BLUE, alpha=0.5, add_points=False)
            elif idx == len(polygons[int(val)]) - 1:
                plot_polygon(polygon, ax=ax, facecolor=BLUE, edgecolor=BLUE, alpha=0.5, add_points=False)
            else:
                plot_polygon(polygon, ax=ax, facecolor="#fff", edgecolor=BLUE, alpha=0.5, add_points=False)

        plot_line(lines[int(val)], ax=ax, color=GREEN, add_points=False)  # type: ignore

        print_poly_data(polygons, int(val))

    layer_slider.on_changed(update)
    update(len(polygons) - 1)
    print_poly_data(polygons, len(polygons) - 1)

    return layer_slider


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
            buffer_polygon: MultiPolygon = section.segmentize(max_segment_length=5)
            buffer_polygon: Union[Polygon, MultiPolygon] = buffer_polygon.buffer(
                distance=-offset,
                quad_segs=16,
                cap_style="round",
                join_style="round",
                mitre_limit=5,
                single_sided=False
            )

            if not buffer_polygon.is_empty:
                if type(buffer_polygon) is Polygon:
                    layer_offsets.append(MultiPolygon([buffer_polygon]))
                else:
                    layer_offsets.append(buffer_polygon)
            else:
                break

        result.append(layer_offsets)
    return result


def fill_zig_zag(
        sections: list[list[MultiPolygon]], angles_deg: list[float], offset: float, connected: bool
) -> list[MultiLineString]:

    result: list[MultiLineString] = []

    for layer_idx, layer_section in enumerate(sections):
        layer_infill: Union[LineString, MultiLineString] = MultiLineString()

        filling_area: MultiPolygon = layer_section[-1] if len(layer_section) > 0 else MultiPolygon()

        if not filling_area.is_empty:
            for sub_area in filling_area.geoms:
                filling_center: Point = sub_area.centroid
                rotated_filling_area: MultiPolygon = rotate(
                    sub_area, angles_deg[layer_idx % len(angles_deg)], filling_center
                )
                shrunk_filling_area: MultiPolygon = rotated_filling_area.buffer(-0.1)

                if not shrunk_filling_area.is_empty:
                    min_x, min_y, max_x, max_y = shrunk_filling_area.bounds
                    height: float = max_y - min_y
                    hatch_count: int = int(round(height / offset, 0))
                    hatch_dist: float = height / hatch_count if hatch_count > 0 else height

                    if height > hatch_dist:
                        coords: list[list[tuple[float, float]]] = [
                            [(min_x - 2, y), (max_x + 2, y)] for y in np.arange(min_y, max_y + hatch_dist, hatch_dist)
                        ]
                    else:
                        coords: list[list[tuple[float, float]]] = [
                            [(min_x - 2, min_y + (height / 2)), (max_x + 2, min_y + (height / 2))]
                        ]

                    hatch: MultiLineString = rotate(
                        MultiLineString(coords), -angles_deg[layer_idx % len(angles_deg)], filling_center
                    )

                    trimmed_hatch: list[Union[LineString, MultiLineString]] = [
                        sub_area.intersection(line) for line in hatch.geoms if not line.is_empty
                    ]
                    nested_trimmed_hatch: list[list[LineString]] = [
                       [item] if type(item) is LineString else list(item.geoms) for item in trimmed_hatch
                    ]

                    hatch_groups: list[list[list[LineString]]] = []
                    hatch_group: list[list[LineString]] = []
                    grp_length: int = len(nested_trimmed_hatch[0])

                    for sub_list in nested_trimmed_hatch:
                        if grp_length == len(sub_list):
                            hatch_group.append(sub_list)
                        else:
                            hatch_groups.append(hatch_group)
                            hatch_group: list[list[LineString]] = [sub_list]
                            grp_length: int = len(sub_list)
                    else:
                        hatch_groups.append(hatch_group)

                    sorted_hatch_groups: list[list[LineString]] = []
                    for hatch_group in hatch_groups:
                        if len(hatch_group[0]) == 1:
                            sorted_hatch_groups.append(list(chain.from_iterable(hatch_group)))
                        else:
                            zipped_hatch_group: list[tuple[LineString]] = list(zip(*hatch_group))
                            zipped_hatch_group: list[list[LineString]] = [list(tpl) for tpl in zipped_hatch_group]
                            sorted_hatch_groups.extend(zipped_hatch_group)

                    for sorted_hatch_group in sorted_hatch_groups:
                        connectors: list[LineString] = []

                        if connected:
                            for idx, line in enumerate(sorted_hatch_group):
                                if idx < len(sorted_hatch_group) - 1:
                                    next_line: LineString = sorted_hatch_group[idx + 1]
                                    if not line.is_empty and not next_line.is_empty:
                                        if idx % 2 == 0:
                                            connectors.append(LineString([line.coords[1], next_line.coords[1]]))
                                        else:
                                            connectors.append(LineString([line.coords[0], next_line.coords[0]]))

                        connected_line: LineString = linemerge(
                            [line for line in sorted_hatch_group if not line.is_empty] + connectors
                        )
                        layer_infill: Union[LineString, MultiLineString] = layer_infill.union(connected_line)

            if type(layer_infill) is LineString:
                layer_infill: MultiLineString = MultiLineString([layer_infill])

        result.append(layer_infill)

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

                    planar_cuts: list[MultiPolygon] = slice_solid(solid=target_solid, layer_height=2)
                    planar_offsets: list[list[MultiPolygon]] = offset_sections(
                        sections=planar_cuts, offsets=(0., 2., 2., 1.,)
                    )

                    filling: list[MultiLineString] = fill_zig_zag(
                        sections=planar_offsets, angles_deg=[-45, 0, 45, 90], offset=1., connected=True
                    )

                    App.slider = draw_slice(planar_offsets, filling)
                    plt.show()

                else:
                    print("No solid selected.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
