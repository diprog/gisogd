from nicegui import ui


class Column(ui.element):
    def __init__(self, column_class='col'):
        super().__init__('div')
        self.classes(column_class)


class Row(ui.element):
    def __init__(self, row_class='row'):
        super().__init__('div')
        self.classes(row_class)

# class Number(ui.number):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.
#

def col2():
    return Column('col-2')


def col7():
    return Column('col-7')


def col8():
    return Column('col-8')


def col():
    return Column()


row = Row
