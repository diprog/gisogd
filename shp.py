import os
import tempfile
import zipfile
from io import BytesIO
from uuid import uuid4

import fiona
from aiofiles.os import makedirs
from tqdm import tqdm

from layers import Layer


def merge_shp_files(input_folder, output_path):
    file_list = [file for file in os.listdir(input_folder) if file.endswith('.shp')]

    with fiona.open(os.path.join(input_folder, file_list[0]), 'r', encoding='utf-8') as src:
        merged_schema = src.schema
        merged_crs = src.crs

    with fiona.open(output_path, 'w', driver='ESRI Shapefile', schema=merged_schema, crs=merged_crs,
                    encoding='utf-8') as dst:
        orbis_ids = set()
        for file in tqdm(file_list, desc='Объединение shp'):
            with fiona.open(os.path.join(input_folder, file), 'r', encoding='utf-8') as src:
                for feature in src:
                    orbis_id = feature['properties']['orbis_id']
                    if orbis_id not in orbis_ids:
                        dst.write(feature)
                        orbis_ids.add(orbis_id)


def combine_zip_files(zip_files_per_layer_code: dict[str, list[BytesIO]], layers: list[Layer], shp_folder):
    print(len(layers))
    for layer_code, zip_archives in zip_files_per_layer_code.items():
        temp_dir = tempfile.mkdtemp()
        for zip_archive in zip_archives:
            uuid = str(uuid4())
            with zipfile.ZipFile(zip_archive, 'r') as zip_file:
                for file in zip_file.infolist():
                    file.filename = f'{uuid}.' + file.filename.split(".")[-1]
                    zip_file.extract(file, temp_dir)
        for layer in [layer for layer in layers if layer.code == layer_code]:
            shp_filepath = os.path.join(shp_folder, layer.get_folder_path())
            os.makedirs(shp_filepath, exist_ok=True)
            merge_shp_files(temp_dir, shp_filepath)
            break
    print('Объединение завершено')
