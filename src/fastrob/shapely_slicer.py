from typing import cast
from math import sqrt

import numpy as np
from shapely.geometry import Polygon
from shapely.plotting import plot_polygon
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


def plot_poly(polygon: Polygon) -> None:
    poly_z: float = round(polygon.exterior.coords[0][-1], 2)
    fig: plt.Figure = plt.figure(1, figsize=SIZE, dpi=90)
    ax: plt.Axes = fig.add_subplot(111)
    ax.set_title("Layer height: " + str(poly_z))
    ax.set_xlabel("X in mm")
    ax.set_ylabel("Y in mm")
    ax.set_aspect("equal")

    plot_polygon(polygon, ax=ax, add_points=True, color=BLUE)
    plt.show()


def layers(solid: Part.Solid, layer_height: float) -> list[Polygon]:
    bb: App.BoundBox = solid.optimalBoundingBox()
    layer_heights: np.ndarray = np.arange(bb.ZMin, bb.ZMax, layer_height)

    polygons: list[Polygon] = []
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
            polygons.append(Polygon(shell=ext_points, holes=int_points))

    return polygons


if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Solids) > 0:
                    target_solid: Part.Solid = selection.Shape.Solids[0]

                    polygon_layers: list[Polygon] = layers(solid=target_solid, layer_height=5)
                    plot_poly(polygon_layers[5])
                else:
                    print("No solid selected.")
            else:
                print("No shape selected.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
