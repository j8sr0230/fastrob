from typing import cast
from itertools import permutations

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

import FreeCADGui as Gui
import FreeCAD as App
import Part

if __name__ == "__main__":
    if App.ActiveDocument:
        if len(Gui.Selection.getSelection()) > 0:
            selection: App.DocumentObject = Gui.Selection.getSelection()[0]
            print("Selected object:", selection.Label)

            if hasattr(selection, "Points"):
                selection: Part.Feature = cast(Part.Feature, selection)
                point_vectors: list[App.Vector] = selection.Points.Points
                points_array: np.ndarray = np.array(point_vectors)
                print(points_array)

                G: nx.Graph = nx.Graph()
                G.add_node(points_array)

                fig, ax = plt.subplots(figsize=(10, 7))
                nx.draw_networkx(G, position=points_array)
                plt.show()

                # start, *rest, end = points_array
                # paths: list[tuple] = [(start, *path, end) for path in permutations(rest)]

            else:
                print("Selection has no points.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
