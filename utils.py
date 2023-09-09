import math
import os.path
import pickle
from io import BytesIO

import aiofiles

def lon_lat_to_mercator(point: tuple[float, float]):
    lon, lat = point
    r_major = 6378137.0  # Большая полуось эллипсоида WGS84
    x = r_major * math.radians(lon)
    scale = x / lon
    y = 180.0 / math.pi * math.log(math.tan(math.pi / 4.0 + lat * (math.pi / 180.0) / 2.0)) * scale
    return x, y

def mercator_to_lon_lat(point: tuple[float, float]):
    x, y = point
    r_major = 6378137.0  # Большая  полуось  эллипсоида  WGS84
    lon = math.degrees(x / r_major)
    lat = math.degrees(math.atan(math.exp(y / r_major)) * 2 - math.pi / 2)
    return lon, lat

def correct_folder_name(name):
    forbidden = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    corrected = name
    for char in forbidden:
        corrected = corrected.replace(char, '_')
    return corrected


def convert_seconds_to_time(seconds):
    if seconds < 0:
        return 'неизвестно'

    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


async def get_from_cache(filename, not_found_return=None):
    try:
        async with aiofiles.open(os.path.join('.cache', filename), 'rb') as f:
            return pickle.loads(await f.read())
    except FileNotFoundError:
        return not_found_return


async def write_to_cache(obj, filename):
    async with aiofiles.open(os.path.join('.cache', filename), 'wb') as f:
        await f.write(pickle.dumps(obj))


def in_list(lst: list[object], item_to_find: object, compare_attr):
    item_to_find_attr = item_to_find.__getattribute__(compare_attr)
    for item in lst:
        if item.__getattribute__(compare_attr) == item_to_find_attr:
            return True
    return False


def makedirs(*names):
    path = os.path.join(*names)
    os.makedirs(path, exist_ok=True)
    return path


async def empty_func(*args, **kwargs):
    return


def combine_list_of_dicts(list_of_dicts: list[dict[str, list[BytesIO]]]) -> dict[str, list[BytesIO]]:
    combined_dict = {}
    for dictionary in list_of_dicts:
        for key, value in dictionary.items():
            try:
                combined_dict[key] += value
            except KeyError:
                combined_dict[key] = value
    return combined_dict
