import os.path

import aiohttp

from constants import HEADERS
from utils import correct_folder_name, get_from_cache, write_to_cache


class Layer:
    def __init__(self, kwargs):
        self.access = kwargs.get('access')
        self.code = kwargs.get('code')
        self.icon = kwargs.get('icon')
        self.id = kwargs.get('id')
        self.json = kwargs.get('json')
        self.map_layer_id = kwargs.get('map_layer_id')
        self.name = kwargs.get('name')
        self.parent_id = kwargs.get('parent_id')
        self.render_type = kwargs.get('render_type')
        self.selected = kwargs.get('selected')
        self.sort = kwargs.get('sort')
        self.style_mode = kwargs.get('style_mode')
        self.type = kwargs.get('type')
        self.path = None
        self.icon = 'layers' if self.type == 'folder' else 'trip_origin'

    def get_folder_path(self):
        return os.path.join(*[correct_folder_name(name) for name in self.path], correct_folder_name(self.name))

    def not_folder(self):
        return self.type in ('layer', 'virtual')


def get_path(selected_layer: Layer, layers: list[Layer], attr=None):
    def _get_path(selected_layer: Layer, layers: list[Layer], path: list[Layer]):
        for layer in layers:
            if selected_layer.parent_id == layer.id:
                path.append(layer)
                _get_path(layer, layers, path)

    path = []
    _get_path(selected_layer, layers, path)
    path = list(reversed(path))
    return [layer.__getattribute__(attr) for layer in path] if attr else path


async def fetch_layers(no_cache=False) -> list[Layer]:
    if not no_cache:
        if layers := await get_from_cache('layers.pickle'):
            return layers

    url = 'https://gisogd.mos.ru/gis/api/2.8/gisogd/isogd/layers/?type=publish&returnCss=0&with_access=1&returnBbox=0&bboxSR=3857&lng=ru'
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as r:
            layers = [Layer(kwargs) for kwargs in await r.json()]

            for layer in layers:
                layer.path = get_path(layer, layers, 'name')

            await write_to_cache(layers, 'layers.pickle')
            return layers


def get_layers_tree_for_ui(layers: list[Layer]):
    def _get_children(layer: Layer):
        children = []
        for l in layers:
            if l.parent_id == layer.id:
                children.append({'id': l.code, 'name': l.name, 'description': l.code, 'icon': l.icon, 'children': _get_children(l)})
        return children

    tree = []
    for layer in layers:
        if not layer.parent_id:
            tree.append({'id': layer.code, 'name': layer.name, 'description': layer.code, 'icon': layer.icon,  'children': _get_children(layer)})
    return tree
