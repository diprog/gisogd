from io import BytesIO

import geopandas
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as matplotlibPolygon


def polygons_from_file(file: str | BytesIO) -> list[list[list, list, list, list, list]]:
    """
    Читает полигоны из geopackage файла.
    """
    data = geopandas.read_file(file)
    polygons = []
    for index, row in data.iterrows():
        left = row['left']
        top = row['top']
        right = row['right']
        bottom = row['bottom']

        polygon = [
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom],
            [left, top]
        ]
        polygons.append(polygon)
    return polygons


def calculate_area(polygon, hectares=True):
    #  Используем  формулу  Гаусса  для  вычисления  площади
    #  Принимаем,  что  полигон  представлен  в  виде  списка  точек  [x,  y]
    #  Последняя  точка  повторяется,  чтобы  закрыть  полигон
    area = 0
    n = len(polygon)

    for i in range(n - 1):
        current_point = polygon[i]
        next_point = polygon[i + 1]
        area += (current_point[0] * next_point[1]) - (next_point[0] * current_point[1])

    #  Площадь  будет  в  квадратных  метрах
    area = abs(area) / 2

    return area / 10000 if hectares else area


def calculate_area_m(polygon):
    return calculate_area(polygon, hectares=False)


def divide_quadrilateral(quadrilateral):
    left = quadrilateral[0][0]
    top = quadrilateral[0][1]
    right = quadrilateral[2][0]
    bottom = quadrilateral[2][1]

    midpoint_x = (left + right) / 2
    midpoint_y = (top + bottom) / 2

    half_quad_1 = [
        [left, top],
        [right, top],
        [right, midpoint_y],
        [left, midpoint_y],
        [left, top]
    ]

    half_quad_2 = [
        [left, midpoint_y],
        [right, midpoint_y],
        [right, bottom],
        [left, bottom],
        [left, midpoint_y]
    ]

    return half_quad_1, half_quad_2


def visualize_polygon(polygon):
    x = [point[0] for point in polygon]
    y = [point[1] for point in polygon]

    fig, ax = plt.subplots()
    ax.add_patch(matplotlibPolygon(polygon, closed=True, alpha=0.5))

    ax.plot(x, y, 'r')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title('Polygon  Visualization')

    plt.xlim(4181300, 4181500)
    plt.ylim(7502600, 7502750)
    plt.grid(True)
    plt.show()


from shapely.geometry import Polygon
from shapely.prepared import prep


def grid_bounds(geom, delta):
    minx, miny, maxx, maxy = geom.bounds
    nx = int((maxx - minx) / delta)
    ny = int((maxy - miny) / delta)
    gx, gy = np.linspace(minx, maxx, nx), np.linspace(miny, maxy, ny)
    grid = []
    for i in range(len(gx) - 1):
        for j in range(len(gy) - 1):
            poly_ij = Polygon([[gx[i], gy[j]], [gx[i], gy[j + 1]], [gx[i + 1], gy[j + 1]], [gx[i + 1], gy[j]]])
            grid.append(poly_ij)
    return grid


def partition(geom):
    minx, miny, maxx, maxy = geom.bounds
    width = (maxx - minx) / 3
    height = (maxy - miny) / 3
    delta = min(width, height)
    prepared_geom = prep(geom)
    grid = list(filter(prepared_geom.intersects, grid_bounds(geom, delta)))
    return grid


def split_polygon(polygon):
    polygons = [list(p.exterior.coords) for p in partition(Polygon(polygon))]
    print('Полигонов', len(polygons))
    return polygons
