import asyncio
import zipfile
from hashlib import md5
from io import BytesIO

import aiohttp
from aiohttp import ClientConnectorError

from constants import HEADERS
from errors import ServerError
from layers import Layer
from polygons import calculate_area, divide_quadrilateral, split_polygon
from utils import empty_func, combine_list_of_dicts


def prepare_layers_param(layers: str | list[str] | Layer | list[Layer]):
    if type(layers) is str:
        return [layers]
    elif type(layers) is Layer:
        return [layers.code]
    elif type(layers) is list[Layer]:
        return [layer.code for layer in layers]
    return layers


def unzip_layers_shp(layers_zip: bytes) -> dict[str, list[BytesIO]]:
    """
    Распаковывает архив, который мы получаем из get_shp_in_polygon.
    Не распаковывает архивы в архиве.
    Пример содержания исходного архива:
    | virtual1742.zip
    |     01 Функциональные зоны.cpg
    |     01 Функциональные зоны.dbf
    |     01 Функциональные зоны.prj
    |     01 Функциональные зоны.shp
    |     01 Функциональные зоны.shx
    | virtual1744.zip
    |     Территория объекта негативного воздействия, для которого указана санитарно-защитная зона.cpg
    |     Территория объекта негативного воздействия, для которого указана санитарно-защитная зона.dbf
    |     Территория объекта негативного воздействия, для которого указана санитарно-защитная зона.prj
    |     Территория объекта негативного воздействия, для которого указана санитарно-защитная зона.shp
    |     Территория объекта негативного воздействия, для которого указана санитарно-защитная зона.shx
    | virtual1746.zip
    |     Ориентировочная санитарно-защитная зона.cpg
    |     Ориентировочная санитарно-защитная зона.dbf
    |     Ориентировочная санитарно-защитная зона.prj
    |     Ориентировочная санитарно-защитная зона.shp
    |     Ориентировочная санитарно-защитная зона.shx
    """
    zip_files_per_layer_code = {}
    with zipfile.ZipFile(BytesIO(layers_zip), 'r') as zip_file:
        file_list = zip_file.namelist()
        for file in file_list:
            file_bytes = BytesIO(zip_file.read(file))
            layer_code = file.split('.')[0]
            try:
                zip_files_per_layer_code[layer_code].append(file_bytes)
            except KeyError:
                zip_files_per_layer_code[layer_code] = [file_bytes]
    return zip_files_per_layer_code


async def get_shp_in_polygon(layers: str | list[str] | Layer | list[Layer],
                             polygon: list,
                             error500_retries=5,
                             timeout=20,
                             semaphore=asyncio.Semaphore(1),
                             callback=empty_func,
                             timeout_retries=3) -> dict[str, list[BytesIO]]:
    async with semaphore:
        # В параметрах сервер принимает список из кодов слоев, то есть list[str].
        # Так что подгоняем аргумент под этот формат в зависимости от его типа.
        layers = prepare_layers_param(layers)

        # На всякий случай пропишем заголовки.
        headers = {
            'Accept': '*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7',
            'Origin': 'https://gisogd.mos.ru'
        }
        headers.update(HEADERS)
        headers['Sec-Fetch-Mode'] = 'cors'
        headers['Sec-Fetch-Dest'] = 'empty'
        headers['Sec-Fetch-Site'] = 'same-origin'
        headers['Referer'] = 'https://gisogd.mos.ru/gis/public_map/gisogd/isogd/'
        headers['Cache-Control'] = 'no-cache'

        # Параметры запроса.
        data = {
            "activeChapterCodes": [],
            "activeLayerCodes": layers,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    polygon
                ]
            }
        }


        # URL запроса.
        url = 'https://gisogd.mos.ru/isogd/front/api/orbisclient/export'

        error500_tries = 0
        timeout_tries = 0
        hash = str(md5(str(polygon).encode()).hexdigest())
        while True:
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                try:
                    async with session.post(url, json=data) as r:
                        if r.ok:
                            return unzip_layers_shp(await r.read())
                        elif r.status == 500:
                            if error500_tries == error500_retries:
                                raise ServerError
                            error500_tries += 1
                        else:
                            print(r.status, hash)
                            print(r.status)
                except asyncio.TimeoutError as e:
                    if timeout_tries == timeout_retries:
                        raise ServerError
                    timeout_tries += 1
                except ClientConnectorError as e:
                    print('ClientConnectorError')
                    await callback(e)
                await asyncio.sleep(1)


async def get_shp_in_polygon_divide_on_error(layers: str | list[str] | Layer | list[Layer],
                                             polygon: list,
                                             error500_retries=5,
                                             timeout=20,
                                             semaphore=asyncio.Semaphore(1),
                                             callback=empty_func) -> dict[str, list[BytesIO]]:
    area = calculate_area(polygon)

    if area < 0.1:
        print('Увы')
        return {}
    try:
        result = await get_shp_in_polygon(layers, polygon, error500_retries, timeout, semaphore, callback)
        return result
    except ServerError:  # Ошибка 500
        print('Делю полигон')
        coros = [get_shp_in_polygon_divide_on_error(layers, p, error500_retries, timeout, semaphore, callback) for p in
                 split_polygon(polygon)]
        results: list[dict] = await asyncio.wait_for(asyncio.gather(*coros), timeout=None)
        return combine_list_of_dicts(results)
