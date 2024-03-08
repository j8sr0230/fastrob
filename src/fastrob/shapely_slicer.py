from typing import Any, cast
from math import sqrt
from itertools import accumulate

import numpy as np

from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
from shapely.plotting import plot_polygon, plot_line
from shapely.affinity import rotate
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

DISCRETIZE_DISTANCE: float = 1


def plot_poly(polygons: list[Polygon], lines: list[LineString]) -> None:
    fig: plt.Figure = plt.figure(1, figsize=SIZE, dpi=90)
    ax: plt.Axes = fig.add_subplot(111)
    ax.set_xlabel("X in mm")
    ax.set_ylabel("Y in mm")
    ax.set_aspect("equal")

    for idx, polygon in enumerate(polygons):
        if idx == 0:
            plot_polygon(polygon, ax=ax, facecolor=GRAY, edgecolor=BLUE,  alpha=0.5, add_points=False)
        elif idx == len(polygons) - 1:
            plot_polygon(polygon, ax=ax, facecolor=BLUE, edgecolor=BLUE,  alpha=0.5, add_points=False)
        else:
            plot_polygon(polygon, ax=ax, facecolor="#fff", edgecolor=BLUE,  alpha=0.5, add_points=False)

    for line in lines:
        plot_line(line, ax=ax, color="#292929", alpha=0.5, add_points=False)

    plt.show()


def layer_polygons(solid: Part.Solid, layer_height: float) -> list[Polygon]:
    bb: App.BoundBox = solid.optimalBoundingBox()
    layer_heights: np.ndarray = np.arange(bb.ZMin, bb.ZMax, layer_height)

    result: list[Polygon] = []
    for layer_height in layer_heights:
        contours: list[Part.Wire] = solid.slice(App.Vector(0, 0, 1), layer_height)
        faces: Part.Shape = Part.makeFace(contours, "Part::FaceMakerBullseye")

        for face in faces.Faces:
            exterior: Part.Wire = cast(Part.Wire, face.OuterWire)
            interior: list[Part.Wire] = [wire for wire in face.Wires if not wire.isEqual(exterior)]

            ext_points: list[tuple] = [tuple(v) for v in exterior.discretize(Distance=DISCRETIZE_DISTANCE)]
            int_points: list[list[tuple]] = [
                [tuple(v) for v in wire.discretize(Distance=DISCRETIZE_DISTANCE)] for wire in interior
            ]
            result.append(Polygon(shell=ext_points, holes=int_points))

    return result


def offset_polygons(polygons: list[Polygon], offsets: tuple[float, ...]) -> list[list[Polygon]]:
    result: list[list[Polygon]] = []

    for polygon in polygons:
        poly_result: list[Polygon] = []
        for offset in accumulate(offsets):
            offset_poly: Polygon = polygon.buffer(-offset)
            if not offset_poly.is_empty:
                poly_result.append(polygon.buffer(
                    distance=-offset,
                    quad_segs=16,
                    cap_style=1,
                    join_style=1,
                    mitre_limit=5.0,
                    single_sided=False
                ))

        result.append(poly_result)
    return result


def zig_zag_lines(polygon: Polygon, angle_deg: float, seam_width: float, connected: bool) -> list[LineString]:
    rotated_poly: Polygon = rotate(polygon, angle=angle_deg, origin="centroid", use_radians=False)
    min_x, min_y, max_x, max_y = rotated_poly.bounds

    hatch_count: int = int(round((max_y-min_y) / seam_width, 0))
    hatch_y_pos: np.ndarray = np.linspace(min_y, max_y, hatch_count)

    hatch_y_coords: list[list[tuple[float, float]]] = []
    for idx, y_pos in enumerate(hatch_y_pos):
        if idx % 2 == 0:
            hatch_y_coords.append([(min_x, y_pos), (max_x, y_pos)])
        else:
            hatch_y_coords.append([(max_x, y_pos), (min_x, y_pos)])
    hatch: MultiLineString = rotate(
        MultiLineString(hatch_y_coords), angle=-angle_deg, origin=polygon.centroid, use_radians=False
    )

    trimmed_hatch: Any = hatch.intersection(polygon)

    flat_trimmed_hatch: list[LineString] = []
    if type(trimmed_hatch) is LineString:
        if trimmed_hatch.length > 0:
            flat_trimmed_hatch.append(trimmed_hatch)
    elif hasattr(trimmed_hatch, "geoms"):
        for item in trimmed_hatch.geoms:
            if type(item) is LineString and item.length > 0:
                flat_trimmed_hatch.append(item)

    connectors: list[LineString] = []
    for idx, hatch_l in enumerate(flat_trimmed_hatch):
        if idx < len(flat_trimmed_hatch) - 1:
            next_hatch_line: LineString = flat_trimmed_hatch[idx + 1]
            print(hatch_l.coords.xy[1], next_hatch_line.coords.xy[0])
            print()
            # connector: LineString = LineString(
            #     [hatch_line.coords.xy[1], next_hatch_line.coords.xy[0]]
            # )
            # connectors.append(connector)
            # flat_trimmed_hatch.append(connector)
    return flat_trimmed_hatch


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Solids) > 0:
                    target_solid: Part.Solid = selection.Shape.Solids[0]

                    layers_polys: list[Polygon] = layer_polygons(solid=target_solid, layer_height=5)

                    contour_polys: list[list[Polygon]] = offset_polygons(
                        polygons=layers_polys, offsets=(2., 1.,)
                    )

                    filling_lines: list[list[LineString]] = []
                    for contour_poly in contour_polys:
                        remainder_poly: Polygon = contour_poly[-1]

                        level_lines: list[LineString] = []
                        if type(remainder_poly) is MultiPolygon:
                            for poly in cast(MultiPolygon, remainder_poly).geoms:
                                level_lines.extend(
                                    zig_zag_lines(polygon=poly, angle_deg=-45, seam_width=2, connected=True)
                                )
                        else:
                            level_lines.extend(
                                zig_zag_lines(polygon=remainder_poly, angle_deg=-45, seam_width=2, connected=True)
                            )
                        filling_lines.append(level_lines)

                    plot_poly(contour_polys[2], filling_lines[2])

                else:
                    print("No solid selected.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
