import time

from nicegui import ui

from gui import styles, myui
from utils import convert_seconds_to_time


class PolygonProgress:
    def __init__(self, id: int, total: int, export_folder: str, done_callback,  progress):
        self.id = id
        self.total = total
        self.export_folder = export_folder
        self.progress = progress
        self.done_callback = done_callback
        self.results: list[dict] = []
        with myui.row().classes('full-width justify-between items-center'):
            with myui.col2():
                ui.label(f'#{id}').classes('text-h6 text-body1')
            with myui.col7():
                self.progress_bar = ui.linear_progress(show_value=False, size='15px')
            with myui.col2():
                self.progress_text = ui.label()
        self.update_text()

    def update_text(self):
        self.progress_text.set_text(f'{len(self.results)} / {self.total}')

    async def add(self, result: dict):
        self.results.append(result)
        self.progress_bar.set_value(len(self.results) / self.total)
        self.update_text()
        self.progress.increment()
        if len(self.results) == self.total:
            await self.done_callback(self)

    def error(self, text):
        self.progress.add_error(text)


class Progress:
    def __init__(self, total):
        self.total = total
        self.done = 0
        self.polygon_progresses = {}
        self.label = ui.label()
        self.cached_polygons_amount_label = ui.label()
        with ui.element('p'):
            self.error_html = ui.html().classes('text-negative')
        self.errors: list[str] = []
        self.done_times: list[float] = []
        self.cached_polygons_amount = 0
        self.update_label()

    def update_label(self):
        try:
            time_left = (self.total - self.done) / self.calculate_iterations_per_second()
        except ZeroDivisionError:
            time_left = -1
        self.label.set_text(f'{self.done} / {self.total} ({convert_seconds_to_time(time_left)})')

    def add_polygon_progress(self, id: int, total: int, export_folder: str, done_callback):
        polygon_progress = PolygonProgress(id, total, export_folder, done_callback, self)
        self.polygon_progresses[id] = polygon_progress
        return polygon_progress

    def calculate_iterations_per_second(self):
        if len(self.done_times) < 2:
            return -1

        try:
            time_diffs = [self.done_times[i + 1] - self.done_times[i] for i in range(len(self.done_times) - 1)]
            average_time_diff = sum(time_diffs) / len(time_diffs)
            iterations_per_second = 1 / average_time_diff
            return iterations_per_second
        except ZeroDivisionError:
            return -1

    def calculate_iterations_last_second(self):
        if len(self.done_times) < 2:
            return -1

        try:
            current_time = self.done_times[-1]
            count = 0
            for _time in self.done_times:
                if current_time - _time <= 1:
                    count += 1
                else:
                    break

            iterations_last_second = count / 1  # 1  секунда
            return iterations_last_second
        except ZeroDivisionError:
            return -1

    def increment(self, amount=1):
        self.done_times.append(time.time())
        if len(self.done_times) > 20:
            for i in range(amount):
                self.done_times.pop(0)
        self.done += amount
        self.update_label()

    def add_error(self, text):
        self.errors.append(text)
        self.error_html.set_content('<br>'.join(self.errors))

    def add_cached_polygon(self):
        self.cached_polygons_amount += 1
        self.cached_polygons_amount_label.set_text(f'Прочитано готовых полигонов: {self.cached_polygons_amount}')
