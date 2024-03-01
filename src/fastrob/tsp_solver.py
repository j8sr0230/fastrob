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

                point_ids: np.ndarray = np.arange(0, points_array.size)
                positions_map: dict[int, np.ndarray] = {node: pos for node, pos in zip(point_ids, points_array)}

                G: nx.Graph = nx.Graph()
                G.add_nodes_from(point_ids)

                fig, ax = plt.subplots(figsize=(10, 7))
                nx.draw_networkx(G, position=positions_map, ax=ax)
                plt.show()

                # start, *rest, end = points_array
                # paths: list[tuple] = [(start, *path, end) for path in permutations(rest)]

            else:
                print("Selection has no points.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
