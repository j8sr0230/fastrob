from typing import cast, Callable

# import numpy as np
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

                G: nx.Graph = nx.complete_graph(point_map.keys())
                for node in G:
                    edge_dict: dict[int, dict] = G[node]
                    for neighbour in edge_dict.keys():
                        dist: float = point_vectors[node].distanceToPoint(point_vectors[neighbour])
                        G[node][neighbour]["weight"] = dist

                # print(G[0])

                nx.draw(G, pos=point_map, node_size=10, with_labels=False)

                tsp: Callable = nx.approximation.traveling_salesman_problem
                solution: list[int] = tsp(G, nodes=point_map.keys())

                H: nx.Graph = nx.Graph()
                nx.add_path(H, solution)
                nx.draw(H, pos=point_map, node_size=10, with_labels=False)
                plt.show()
            else:
                print("Selection has no points.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
