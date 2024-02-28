import matplotlib.pyplot as plt
import numpy as np


def create_zigzag_fill_pattern(polygon_points, num_layers=5, zigzag_spacing=0.1):
    """
    Erstellt ein Zigzag-Füllmuster für ein gegebenes Polygon.

    Args:
        polygon_points (list of tuples): Die Eckpunkte des Polygons als (x, y)-Tupel.
        num_layers (int): Anzahl der Füllschichten (Standard: 5).
        zigzag_spacing (float): Abstand zwischen den Zigzag-Linien (Standard: 0.1).

    Returns:
        None (Zeigt das Füllmuster mit Matplotlib an).
    """
    # Polygonpunkte in ein NumPy-Array umwandeln
    polygon = np.array(polygon_points)

    # Berechne die Begrenzungsbox des Polygons
    min_x, min_y = np.min(polygon, axis=0)
    max_x, max_y = np.max(polygon, axis=0)

    # Erstelle Zigzag-Linien
    for layer in range(num_layers):
        y = min_y + layer * zigzag_spacing
        zigzag_line = [(min_x, y), (max_x, y)]
        plt.plot(*zip(*zigzag_line), color='b')

    # Zeige das Polygon und das Füllmuster
    plt.plot(*zip(*polygon), color='r', marker='o')
    plt.title("Zigzag-Füllmuster für ein Polygon")
    plt.xlabel("X-Koordinate")
    plt.ylabel("Y-Koordinate")
    plt.grid(True)
    plt.show()


# Beispielaufruf
polygon_points = [(0, 0), (2, 0), (2, 1), (1, 1.5), (0, 1)]
create_zigzag_fill_pattern(polygon_points)
