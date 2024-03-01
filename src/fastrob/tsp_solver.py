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
                point_list: list[tuple[int, dict]] = [
                    (idx, {"pos": tuple(pos[:-1])}) for idx, pos in enumerate(point_vectors)
                ]

                # G: nx.Graph = nx.cycle_graph(point_map.keys())
                G: nx.Graph = nx.Graph()
                G.add_nodes_from(point_list)

                # print(nx.geometric_edges(G, radius=3))
                G.add_edges_from(nx.geometric_edges(G, radius=4))
                # nx.draw(G, pos=point_map, node_size=10, with_labels=False)
                # plt.show()

                connected_graphs: list[nx.Graph] = [G.subgraph(c).copy() for c in nx.connected_components(G)]
                # nx.draw(connected_graphs[0], pos=point_map, node_size=10, with_labels=False)
                # plt.show()

                for node in connected_graphs[0]:
                    edge_dict: dict[int, dict] = connected_graphs[0][node]
                    for neighbour in edge_dict.keys():
                        dist: float = point_vectors[node].distanceToPoint(point_vectors[neighbour])
                        connected_graphs[0][node][neighbour]["weight"] = dist

                tsp: Callable = nx.approximation.traveling_salesman_problem
                solution: list[int] = tsp(connected_graphs[0], nodes=connected_graphs[0].nodes)
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
