import math


def width_template(percent):
    percent = math.floor(percent)
    print(percent)
    return f'max-width: {percent}%; min-width: {percent}%'


col12 = col = width_template(100)
col8 = width_template(100 / 1.5)
col6 = width_template(100 / 2)
col2 = width_template(100 / 6)
