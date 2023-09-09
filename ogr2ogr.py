import os
import shutil
import subprocess
import tempfile

import tqdm

from constants import EXPORT_FOLDER

INPUT_PATH = 'grid_msu'


# функция для поиска файлов с расширением .shp
def find_shp_files(shp_folder_path):
    shp_files = []
    for root, dirs, files in os.walk(shp_folder_path):
        for file in files:
            if file.endswith(".shp"):
                shp_files.append(os.path.join(root, file))
    return shp_files


# функция для преобразования .shp в geopackage
def shp_to_geopackage(shp_filepath, shp_folder_path, gpkg_folder_path):
    gpkg_filepath = os.path.dirname(shp_filepath.replace(shp_folder_path, gpkg_folder_path)) + '.gpkg'
    os.makedirs(os.path.dirname(gpkg_filepath), exist_ok=True)

    temp_dir = tempfile.mkdtemp()

    temp_input_filepath = os.path.join(temp_dir, 'input.shp')
    temp_output_filepath = os.path.join(temp_dir, 'output.gpkg')

    shutil.copy(shp_filepath, temp_input_filepath)
    shutil.copy(os.path.splitext(shp_filepath)[0] + '.cpg', temp_input_filepath.replace('.shp', '.cpg'))
    shutil.copy(os.path.splitext(shp_filepath)[0] + '.dbf', temp_input_filepath.replace('.shp', '.dbf'))
    shutil.copy(os.path.splitext(shp_filepath)[0] + '.prj', temp_input_filepath.replace('.shp', '.prj'))
    shutil.copy(os.path.splitext(shp_filepath)[0] + '.shx', temp_input_filepath.replace('.shp', '.shx'))

    command = 'ogr2ogr'
    args = ['-progress', '-t_srs', 'EPSG:32637', '-s_srs',
            '+proj=tmerc +lat_0=55.66666666667 +lon_0=37.5 +k=1 +x_0=12 +y_0=14 +ellps=bessel +towgs84=316.151,78.924,589.65,-1.57273,2.69209,2.34693,8.4507 +units=m +no_defs',
            temp_output_filepath, temp_input_filepath]

    result = subprocess.run([command] + args)
    shutil.copy(temp_output_filepath, gpkg_filepath)
    shutil.rmtree(temp_dir)


def shps_to_geopackages(shp_folder_path, gpkg_folder_path):
    shp_files = find_shp_files(shp_folder_path)
    for shp_file in tqdm.tqdm(shp_files):
        shp_to_geopackage(shp_file, shp_folder_path, gpkg_folder_path)


# основная функция


def ogr2ogr_command():
    command = 'ogr2ogr'
    args = ['-t_srs', 'EPSG:32637', '01_.gpkg', '01.gpkg']
    cmd = [command] + args
    print(cmd)
    subprocess.run(cmd)


def reproject_geopackage(gpkg_folder_path, gpkg_output_folder_path, filepath):
    temp_dir = tempfile.mkdtemp()

    temp_input_filepath = os.path.join(temp_dir, 'input.gpkg')
    temp_output_filepath = os.path.join(temp_dir, 'output.gpkg')

    output_file = filepath.replace(gpkg_folder_path, gpkg_output_folder_path)

    shutil.copy(filepath, temp_input_filepath)

    # asdasd
    command = 'ogr2ogr'
    args = ['-progress', '-t_srs', 'EPSG:32637', temp_output_filepath, temp_input_filepath]
    subprocess.run([command] + args)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    shutil.copy(temp_output_filepath, output_file)
    shutil.rmtree(temp_dir)


def reproject_gpkg_to_epsg32637(gpkg_folder_path, gpkg_output_folder_path):
    filepaths = []
    for root, dirs, files in os.walk(gpkg_folder_path):
        for file in files:
            if file.endswith('.gpkg'):
                filepaths.append(os.path.join(root, file))

    for filepath in tqdm.tqdm(filepaths):
        reproject_geopackage(gpkg_folder_path, gpkg_output_folder_path, filepath)


def main():
    global INPUT_PATH
    export_folder = input('Название папки, в которой shp: ')
    INPUT_PATH = os.path.join(EXPORT_FOLDER, export_folder)
    while True:
        print('1. shp to gpkg')
        print('2. gpkg to EPSG:32637')
        print('3. Выход')
        num = int(input('Введите пункт меню: '))
        if num == 1:
            shps_to_geopackages()
        elif num == 2:
            reproject_gpkg_to_epsg32637()
        elif num == 3:
            break


# пример использования
if __name__ == '__main__':
    main()
