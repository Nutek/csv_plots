import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.scale as scale
import matplotlib.widgets as wdg
from datetime import datetime
import numpy as np
import os
import sys
import webbrowser
from pathlib import Path

SEP = ","


def write_data_to_html(data, output_path):
    with open(output_path, "w") as f:
        f.write(
            data.style.format(precision=3, thousands=".", decimal=",")
            .highlight_max(axis=1, color="lightcoral")
            .highlight_min(axis=1, color="limegreen")
            .to_html()
        )


def generate_output_file_with_table(data, data_path, idx=""):
    output_path = data_path.parent.joinpath(f"out{idx}.html")
    write_data_to_html(data, output_path)
    return output_path


class Button:
    def __init__(self, name, action):
        self.name = name
        self.action = action

    def create(self, ax):
        self.btn = wdg.Button(ax, self.name, image=None)
        self.btn.on_clicked(self.action)


def toggle(val):
    return not val


def force_true(_):
    return True


def force_false(_):
    return False


class InteractivenesOfChart:
    def __init__(self, data: pd.DataFrame):
        plt.rcParams["grid.linestyle"] = "--"
        self.data = data
        self.data_series_names = list(data.columns)
        self.figure = plt.figure()
        self.main_plot = None

        self.figure.canvas.mpl_connect("pick_event", self.on_pick)
        self.figure.canvas.mpl_connect("button_press_event", self.on_clicked)

        self.buttons = [
            Button("Update series", lambda _: self.update_series()),
            Button("Generate table", lambda _: self.generate_table()),
        ]

        self._setup_actions()

        self.update_series()
        self.data

    def line_visibility(self, legline, action=toggle):
        origline = self.lined[legline]
        visible = action(origline.get_visible())
        origline.set_visible(visible)
        legline.set_alpha(1.0 if visible else 0.2)

    def on_pick(self, event):
        legline = event.artist
        self.line_visibility(legline)
        self.figure.canvas.draw()

    def on_clicked(self, event):
        clicked_ax = event.inaxes
        if clicked_ax == self.main_plot:
            action = None
            if event.button == 3:
                action = force_false
            elif event.button == 2:
                action = force_true
            else:
                return
            for legline in self.legend.get_lines():
                self.line_visibility(legline, action)

        if clicked_ax == self.check_ax:
            if event.button == 3:
                self._setup_check_list(False)
            elif event.button == 2:
                self._setup_check_list(True)
            else:
                return

        self.figure.canvas.draw()

    def get_filtered_data(self):
        return self.data.filter(
            items=[
                name
                for name, check in zip(
                    self.data_series_names, self.check_list.get_status()
                )
                if check
            ]
        )

    def generate_table(self):
        filtered_data = self.get_filtered_data()
        out_path = Path(f"out_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

        write_data_to_html(filtered_data, out_path)
        webbrowser.open(out_path)

    def update_series(self):
        if self.main_plot:
            self.main_plot.remove()

        self.main_plot = self.figure.add_axes((0.1, 0.1, 0.7, 0.8))
        self.main_plot.grid(True)

        filtered_data = self.get_filtered_data()
        for col in filtered_data:
            self.main_plot.loglog(
                filtered_data.index, filtered_data[col].values, label=col
            )

        not_empty = len(self.main_plot.lines)

        print("Empty?", not_empty, len(filtered_data.columns), filtered_data.empty)

        if not_empty:
            self.main_plot.set_yscale("log")
            self.main_plot.set_xscale("log", base=2)
            self.main_plot.set_ylabel("Time [ms]")

        self.legend = (
            self.main_plot.legend(
                loc="upper left",
                ncol=1,
                borderaxespad=0,
                fancybox=True,
                shadow=True,
            )
            if not_empty
            else None
        )

        if self.legend:
            for line in self.legend.get_lines():
                line.set_picker(5)

        self.lined = (
            dict(zip(self.legend.get_lines(), self.main_plot.get_lines()))
            if not_empty
            else None
        )
        self.figure.canvas.draw()

    def show(self):
        plt.show()

    def _setup_check_list(self, init_state):
        pos = self.check_ax.get_position()
        self.check_ax.remove()
        self.check_ax = self.figure.add_axes(pos)
        self.check_list = wdg.CheckButtons(
            self.check_ax,
            self.data_series_names,
            actives=[init_state] * len(self.data_series_names),
        )

    def _setup_actions(self):
        button_area = (0.8, 0.1, 0.2, 0.8)
        x, y, w, h = button_area

        actions_count = len(self.data_series_names) + len(self.buttons)

        button_height = h / actions_count

        buttons_area_height = button_height * len(self.buttons)
        top_of_buttons = y + buttons_area_height

        button_positions = list(
            np.linspace(
                start=y,
                stop=top_of_buttons,
                num=len(self.buttons),
                endpoint=False,
            )
        )[::-1]

        for btn, y_pos in zip(self.buttons, button_positions):
            btn.create(plt.axes((x, y_pos, w, button_height)))

        self.check_ax = plt.axes((x, top_of_buttons, w, h - buttons_area_height))
        self._setup_check_list(True)


def handle_file(data_path, idx):
    data_path = Path(data_path).absolute()

    if not data_path.exists():
        print(f"File '{data_path}' does not exist.")
        return

    if not data_path.is_file():
        print(f"File '{data_path}' is not a file.")
        return

    data = pd.read_csv(data_path, sep=SEP, index_col=0)

    if data.empty:
        print(f"File '{data_path}' is corrupted")
        return

    output_path = generate_output_file_with_table(data, data_path, idx)

    interaction = InteractivenesOfChart(data)

    interaction.show()


def main(args):
    app_path = Path(args[0]).absolute()
    app_name = os.path.basename(app_path)
    print(f"{app_name} is working")
    cwd = Path(os.getcwd()).absolute()

    args = args[1:]

    for idx, arg in enumerate(args):
        handle_file(arg, idx + 1)


if __name__ == "__main__":
    main(sys.argv)
