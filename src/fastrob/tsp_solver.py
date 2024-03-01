from typing import cast

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

                point_map: dict[int, App.Vector] = {idx: pos[:-1] for idx, pos in enumerate(point_vectors)}

                G: nx.Graph = nx.Graph()
                G.add_nodes_from(point_map.keys())

                nx.draw(G, pos=point_map, node_size=10, with_labels=False)
                plt.show()

            else:
                print("Selection has no points.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
