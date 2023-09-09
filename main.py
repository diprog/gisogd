import asyncio
from nicegui import ui, events
import multiprocessing
import os
import pickle
from io import BytesIO
from typing import Optional

import aiofiles

from tqdm import tqdm

from constants import EXPORT_FOLDER
from gisogd import get_shp_in_polygon_divide_on_error
from gui import myui
from gui.elements import PolygonProgress, Progress
from layers import fetch_layers, get_layers_tree_for_ui, Layer
from ogr2ogr import shps_to_geopackages, reproject_gpkg_to_epsg32637
from polygons import polygons_from_file
from shp import combine_zip_files
from utils import makedirs, combine_list_of_dicts

geopackage_file = BytesIO()
polygons: list[list, list, list, list, list] = []
layers: list[Layer] = []
selected_layers: list[Layer] = []
export_folder = ''

# Пути для экспорта. Инициализируются в handle_upload.
polygons_path: Optional[str] = None
shp_path: Optional[str] = None
geopackage_path: Optional[str] = None
geopackage_epsg32637_path: Optional[str] = None


async def on_done(polygon_progress: PolygonProgress):
    filepath = os.path.join(polygons_path, f'{polygon_progress.id}.pickle')
    async with aiofiles.open(filepath, 'wb') as f:
        zip_files_per_layer_code = combine_list_of_dicts(polygon_progress.results)
        await f.write(pickle.dumps(zip_files_per_layer_code))


async def read_cached_polygon(polygon_id) -> dict[str, list[BytesIO]]:
    filepath = os.path.join(polygons_path, f'{polygon_id}.pickle')
    async with aiofiles.open(filepath, 'rb') as f:
        return pickle.loads(await f.read())


async def get_shp_in_polygon(layer_code, polygon, timeout, semaphore, polygon_progress: PolygonProgress):
    result = await get_shp_in_polygon_divide_on_error(layer_code, polygon, 3, timeout, semaphore)
    await polygon_progress.add(result)
    return result


async def stop():
    return


async def _start():
    return


async def start():
    print('Скрываю интерфейс')
    start_btn.disable()
    setup_view.classes('hidden')

    print('Раскрываю установленные настройки')
    with chosen_setup_view:
        ui.label(f'Предустановки').classes('text-h5')
        ui.label(f'Папка для экспорта: {export_folder}')
        ui.label(f'Timeout для запросов: {int(request_timeout_input.value)}')
        ui.label(f'Количество потоков: {int(threads_amount_input.value)}')
        ui.label(f'Количество полигонов: {len(polygons)}')
        ui.label(f'Выбрано слоев: {len(selected_layers)}/{len(layers)}')

    print('Раскрываю контейнер с прогрессом')
    main_div.classes(remove='hidden')
    semaphore = asyncio.Semaphore(int(threads_amount_input.value))
    print(int(threads_amount_input.value))

    # Для отображения общего прогресса в интерфейсе.
    with whole_progress_col:
        progress = Progress(len(polygons) * len(selected_layers))

    # Запуск потоков для каждого выбранного слоя.
    saved_polygon_ids = [int(fname.split('.')[0]) for fname in os.listdir(polygons_path)]
    print(saved_polygon_ids)
    zip_files_per_layer_code = {}
    coros = []
    for i, polygon in enumerate(polygons):
        if i in saved_polygon_ids:
            zip_files_per_layer_code = combine_list_of_dicts([await read_cached_polygon(i), zip_files_per_layer_code])
            progress.add_cached_polygon()
            progress.increment(len(selected_layers))
            continue

        with progress_column:
            polygon_progress = progress.add_polygon_progress(i, len(selected_layers), export_folder, on_done)

        for layer in selected_layers:
            coros.append(
                get_shp_in_polygon(layer.code, polygon, int(request_timeout_input.value), semaphore, polygon_progress))
    results = combine_list_of_dicts(await asyncio.wait_for(asyncio.gather(*coros), timeout=None))
    zip_files_per_layer_code = combine_list_of_dicts([zip_files_per_layer_code, results])
    print('Готово')

    # divided_polygon = divide_quadrilateral(polygon)
    # print(calculate_area(polygon), polygon)
    # print(len(divided_polygon), calculate_area(divided_polygon[0]), calculate_area(divided_polygon[1]))
    # return

    # semaphore = asyncio.Semaphore(50)
    # result = await get_shp_in_polygon_divide_on_error(['polygon_pp', 'virtual2386'], polygon, 3, semaphore)
    # combine_zip_files(result, layers, '.export/bruh')
    # print(result)
    # print('Конец')


async def on_layers_tree_select(e: events.ValueChangeEventArguments):
    selected_layers.clear()
    for layer_code in e.value:
        for layer in layers:
            if layer.code == layer_code and layer.not_folder():
                selected_layers.append(layer)
                break
    selected_layers_label.set_text(f'Выбрано слоев: {len(selected_layers)}')
    print([layer.code for layer in selected_layers])
    update_start_btn()


async def load_layers(no_cache=False):
    """
    Загружаем слои с сайта или из кэша и помещаем данные в глобальную переменную для дальнейшего использования.
    """
    # Подгружаем слои.
    global layers
    global layers_tree
    layers = await fetch_layers(no_cache)

    # Рендерим дерево слоев.
    layers_tree_container.clear()
    if selected_layers:
        await on_layers_tree_select(events.ValueChangeEventArguments(value=[], sender=None, client=None))
    with layers_tree_container:
        with ui.card():
            ui.label('Дерево слоев')
            layers_tree = ui.tree(
                get_layers_tree_for_ui(layers),
                label_key='name',
                on_tick=on_layers_tree_select
            ).props('tick-strategy=leaf')

            layers_tree.add_slot('default-body', '''
                <span :props="props">{{ props.node.id }}</span>
            ''')
            layers_amount_label.set_text(f'Слоев загружено: {len([l for l in layers if l.not_folder()])}')

    update_start_btn()


async def load_layers_from_cache():
    await load_layers(no_cache=False)


async def load_layers_from_internet():
    await load_layers(no_cache=True)


def update_start_btn():
    if polygons and selected_layers:
        prepare_label.set_text('')
        start_btn.enable()
    else:
        error_text = []
        if not polygons:
            error_text.append('Не загружены полигоны')
        if not selected_layers:
            error_text.append('Не выбран ни один слой')
        prepare_label.set_text('\n'.join(error_text))
        start_btn.disable()


async def combine_into_shp():
    zip_files_per_layer_code = {}
    print(polygons_path)
    saved_polygon_ids = [int(fname.split('.')[0]) for fname in os.listdir(polygons_path)]
    for polygon_id in tqdm(saved_polygon_ids):
        zip_files_per_layer_code = combine_list_of_dicts(
            [await read_cached_polygon(polygon_id), zip_files_per_layer_code])
    print(zip_files_per_layer_code.keys())
    combine_zip_files(zip_files_per_layer_code, layers, shp_path)


async def shp_to_gpkg():
    process = multiprocessing.Process(target=shps_to_geopackages,
                                      args=(shp_path, geopackage_path))
    process.start()


async def gpkg_to_epsg32637():
    process = multiprocessing.Process(target=reproject_gpkg_to_epsg32637,
                                      args=(geopackage_path, geopackage_epsg32637_path))
    process.start()
    # reproject_gpkg_to_epsg32637(geopackage_path, geopackage_epsg32637_path)


def handle_upload(e: events.UploadEventArguments):
    """
    Завершение загрузки geopackage файла с полигонами.
    """
    global polygons
    global export_folder

    # Удаляем элемент интерфейса с загрузкой файла.
    polygons_gpkg_upload.delete()
    # Читаем полигоны из загруженного файла.
    polygons = polygons_from_file(BytesIO(e.content.read()))

    # Обрезаем количество полигонов, если указано в настройках.
    if polygons_amount := int(polygons_amount_input.value):
        polygons = polygons[:polygons_amount]

    # Заменяем текст "Загрузите файл с полигонами" на название папки, куда будут экспортироваться геоданные.
    export_folder = e.name.rsplit('.', 1)[0]
    polygons_name.set_text(export_folder)
    polygons_name.classes(remove='text-negative')

    # Отображаем количество прочитанных полигонов в интерфейсе.
    with polygons_col:
        ui.label(f'Количество полигонов: {len(polygons)}').classes('q-mb-sm')

    # Создаем отдельную папку для экспорта и нужные подпапки
    global polygons_path, shp_path, geopackage_path, geopackage_epsg32637_path
    base_path = os.path.join(EXPORT_FOLDER, export_folder)
    polygons_path = makedirs(base_path, 'polygons')
    shp_path = makedirs(base_path, 'shp')
    geopackage_path = makedirs(base_path, 'geopackage')
    geopackage_epsg32637_path = makedirs(base_path, 'geopackage_epsg32637')

    update_start_btn()


with myui.col() as setup_view:
    with myui.col() as polygons_col:
        polygons_name = ui.label('Загрузите файл с полигонами').classes('text-negative text-h4')

    polygons_gpkg_upload = ui.upload(
        label='Нажмите на плюсик для загрузки файла',
        on_upload=handle_upload,
        max_file_size=1_000_000
    ).props('accept=.gpkg auto-upload flat')

    # Настройки.
    with myui.col():
        ui.label('Настройки').classes('text-h5 q-mb-sm')
        threads_amount_input = ui.number(label='Количество потоков', value=50, min=1).classes('q-mb-sm').props(
            'standout')
        polygons_amount_input = ui.number(label='Ограничить полигоны числом', value=0, min=0).props('standout')
        ui.label('Оставьте поле равным нулю, если нужно обработать все полигоны').classes(
            'q-mt-xs q-mb-sm text-caption')
        request_timeout_input = ui.number(label='Timeout для запросов (в секундах)', value=80, min=1).props('standout')

    # Слои.
    with myui.col() as layers_col:
        ui.label('Слои').classes('text-h5 q-mb-sm')
        layers_amount_label = ui.label(f'Количество слоев: 0')
        selected_layers_label = ui.label('Выбрано слоев: 0')
        with myui.col().classes('q-my-md') as layers_tree_container:
            layers_tree = None
        with myui.row().classes('q-mt-sm'):
            load_layers_from_cache_button = ui.button('Загрузить из кэша', on_click=load_layers_from_cache,
                                                      icon='cached').classes('q-mr-sm')
            load_layers_from_internet_button = ui.button('Загрузить с сайта gisogd', on_click=load_layers_from_internet,
                                                         icon='language')
        ui.label('Если кэша нет, то слои будут загружены с сайта').classes('q-mt-xs text-caption')

    # Управление.
    with myui.col():
        ui.label('Управление').classes('text-h5 q-mb-sm')
        prepare_label = ui.label().classes('text-negative q-mb-sm')
        with myui.row():
            start_btn = ui.button('Старт', icon='play_arrow', on_click=start).classes('q-mr-sm')
            stop_btn = ui.button('Стоп', icon='stop', on_click=stop)
            update_start_btn()
            stop_btn.disable()

        with myui.row():
            combine_into_shp_btn = ui.button('Объединить в shp', icon='play_arrow', on_click=combine_into_shp).classes(
                'q-mr-sm')
            shp_to_geopackage_btn = ui.button('shp в gpkg', icon='play_arrow', on_click=shp_to_gpkg).classes(
                'q-mr-sm')
            geopackage_to_epsg32637_btn = ui.button('gpkg в EPSG:32637', icon='play_arrow', on_click=gpkg_to_epsg32637)
    #

chosen_setup_view = myui.col()

# Отображение прогресса.
with myui.col().classes('hidden') as main_div:
    info_column = myui.col()
    with myui.col() as whole_progress_col:
        ui.label('Общий прогресс').classes('text-h6 q-mb-sm q-pb-none')

    ui.splitter().props('horizontal')
    progress_column = myui.col().style('min-width: 50vw')

    with progress_column:
        with myui.row().classes('full-width justify-between items-center'):
            with myui.col2():
                ui.label('Полигон').classes('text-bold text-uppercase')
            with myui.col7():
                ui.label('Прогресс').classes('text-bold text-uppercase')
            with myui.col2():
                ui.label('Слои').classes('text-bold text-uppercase')

os.makedirs('.cache', exist_ok=True)
os.makedirs('.export', exist_ok=True)

ui.run(title='ГИСОГД', language='ru', reload=False)
