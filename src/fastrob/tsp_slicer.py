from typing import cast

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

            if hasattr(selection, "Shape"):
                selection: Part.Feature = cast(Part.Feature, selection)
                if len(selection.Shape.Edges) > 0:
                    boundary_edges: list[Part.Edge] = selection.Shape.Edges
                    boundary_vertexes: list[Part.Vertex] = selection.Shape.Vertexes

                    G: nx.Graph = nx.Graph()
                    for edge in boundary_edges:
                        v_start: Part.Vertex = edge.firstVertex()
                        v_end: Part.Vertex = edge.lastVertex()

                        v_start_id: int = [idx for idx, v in enumerate(boundary_vertexes) if v.isSame(v_start)][0]
                        v_end_id: int = [idx for idx, v in enumerate(boundary_vertexes) if v.isSame(v_end)][0]

                        G.add_node(v_start_id, pos=(v_start.X, v_start.Y))
                        G.add_node(v_end_id, pos=(v_end.X, v_end.Y))
                        G.add_edge(v_start_id, v_end_id, weight=edge.Length)

                    nx.draw(G, pos=nx.get_node_attributes(G, "pos"), node_size=10, with_labels=False)
                    plt.show()

                    # tsp: Callable = nx.approximation.traveling_salesman_problem
                    # solution: list[int] = tsp(G, nodes=list(G.nodes), cycle=False)
                    # print(len(solution))
                    #
                    # H: nx.Graph = nx.Graph()
                    # nx.add_path(H, solution)
                    # nx.draw(H, pos=nx.get_node_attributes(G, "pos"), node_size=10, with_labels=False)
                    # plt.show()

                else:
                    print("Selection has no edges.")
            else:
                print("Selection has no shape.")
        else:
            print("Nothing selected.")
    else:
        print("No FreeCAD instance running.")
