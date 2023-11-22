import os, sys
import math
import wx
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from functools import reduce
from itertools import chain

class ChartData:
    def __init__(self, name):
        self._name = name
    def all_columns(self) -> list:
        return []
    def name(self) -> str:
        return self._name
    def prepare_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame()

class SimpleData(ChartData):
    def __init__(self, columnName, name=None) -> None:
        super().__init__(name or columnName)
        self.columnName = columnName
    def all_columns(self):
        return [self.columnName]
    def prepare_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        new_df = df.loc[:, self.columnName].to_frame()
        new_df.columns = [self.name()]
        return new_df

class RatioData(ChartData):
    def __init__(self, columnNumName, columnDenomName, name=None) -> None:
        super().__init__(name or f'Ratio {columnNumName} to {columnDenomName}')
        self.columnNumName = columnNumName
        self.columnDenomName = columnDenomName
    def all_columns(self):
        return [self.columnNumName, self.columnDenomName]
    def prepare_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        new_df = (df.loc[:, self.columnNumName] / df.loc[:, self.columnDenomName]).to_frame()
        new_df.columns = [self.name()]
        return new_df


edit_sep = ","
desc_columns = ["Group", "Experiment"]
index_column = ["Problem Space"]
data_columns = ["us/Iteration", "Task sum[us] Mean", "Task creation[us] Mean"]
# data_columns = ["us/Iteration"]#, "Task sum[us] Mean"] #, "Task creation[us] Mean"]
charts = [
    SimpleData("us/Iteration"),
    SimpleData("Task sum[us] Mean"),
    SimpleData("Task creation[us] Mean"),
    RatioData("Task sum[us] Mean", "us/Iteration", "Proc_time ratio"),
    RatioData("Task creation[us] Mean", "us/Iteration", "Creation to Proc time ratio"),
]
chart_columns = []

def display_help(app_path):
    app = os.path.basename(app_path)
    print(
        f""" {app} <CSV file path>

  '{app}' handles files which are outputs from Celero framework.
  For now there is now way to point which columns are definition
  of experiment series and which are important for analysis.
"""
    )


def load_file(input_file_path):
    return pd.read_csv(input_file_path, sep=edit_sep, index_col=False)

def all_in(sub_items, items) -> bool:
    return all(map(lambda item: item in items, sub_items))

def pd_and(arg1, arg2):
    return arg1 & arg2


def match_columns_with_values(column_names, required_values):
    return lambda df: reduce(
        pd_and,
        map(lambda pair: df[pair[0]] == pair[1], zip(column_names, required_values)),
    )


def match_to_experiment(experiment):
    return match_columns_with_values(desc_columns, experiment)


def preapre_index(df: pd.DataFrame, experiment):
    return df.loc[match_to_experiment(experiment), index_column].iloc[:, 0].to_numpy()


def preapre_data(df: pd.DataFrame, experiment):
    global chart_columns
    chart_columns = list(data_columns)
    df = df.loc[match_to_experiment(experiment), :]
    data = pd.DataFrame()
    new_dfs = [chart.prepare_frame(df) for chart in charts if all_in(chart.all_columns(), df.columns)]
    
    chart_columns = list(chain(*[new_df.columns.values.tolist() for new_df in new_dfs]))
    print(experiment, chart_columns)
    data = reduce(pd.DataFrame.join, new_dfs)        
    return data


def generate_charts_data(loaded_data: pd.DataFrame, selected_experiments: list):
    if len(selected_experiments) == 0:
        return {}

    index_data = preapre_index(loaded_data, selected_experiments[0])
    value_datas = [
        preapre_data(loaded_data, experiment) for experiment in selected_experiments
    ]
    for vals in value_datas:
        vals.index = index_data

    result = {}
    for chart_column in chart_columns:
        chart_data = None
        for idx, experiment in enumerate(selected_experiments):
            column_to_add = value_datas[idx].loc[:, [chart_column]]
            column_to_add.columns = [experiment]
            chart_data = (
                chart_data.join(column_to_add)
                if chart_data is not None
                else column_to_add
            )
        result[chart_column] = chart_data

    return result


class PlotManager:
    fig_no = 0

    @staticmethod
    def prepare_plots(count):
        PlotManager.fig_no += 1
        fig = plt.figure(PlotManager.fig_no)

        plots = fig.subplots(nrows=math.ceil((count + 0.5) / 2.0), ncols=2)
        if not isinstance(plots, np.ndarray):
            plots = np.ndarray([plots])

        return plots


def plot_datasets(chart_datas):
    plots = PlotManager.prepare_plots(len(chart_datas))

    for plot, (title, chart_data) in zip(plots.flatten(), chart_datas.items()):
        chart_data.plot(ax=plot, title=title)
        plot.grid(visible=True)

    plt.show()


def get_experiments_list(loaded_data: pd.DataFrame):
    return sorted(
        list({(g, e) for g, e in loaded_data.loc[:, desc_columns].to_numpy()})
    )


class ListEntry(str):
    def __new__(cls, label, idx):
        instance = super().__new__(cls, label)
        instance.idx = idx
        instance.is_selected = False
        return instance


class MainFrame(wx.Frame):
    def __init__(self, input_file_path, *args, **kw):
        self.input_data = load_file(input_file_path)

        kw.setdefault("parent", None)
        super().__init__(
            title=f"Analyse: {os.path.basename(input_file_path)}", *args, **kw
        )

        self.experiments = get_experiments_list(self.input_data)
        self.experiment_choice = [
            ListEntry(f"{group}: {exper}", idx)
            for idx, (group, exper) in enumerate(self.experiments)
        ]

        self._init_window()
        self.base_select.SetItems(self.experiment_choice)
        self.Bind(wx.EVT_COMBOBOX, self.refresh_entries, self.base_select)
        self.Bind(wx.EVT_LISTBOX, self.selection_changed, self.comparison_select)
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

        self.Bind(wx.EVT_BUTTON, self.plot_charts)

    def on_close(self, evt: wx.CloseEvent):
        plt.close("all")
        return self.Destroy()

    def refresh_entries(self, evt: wx.CommandEvent):
        filtered_entries = self.get_filtered_entries()

        self.comparison_select.SetItems(filtered_entries)

        for idx, entry in enumerate(filtered_entries):
            self.comparison_select.SetClientData(idx, entry)

        for idx, entry in enumerate(filtered_entries):
            if entry.is_selected:
                self.comparison_select.SetSelection(idx)

        self.update_button()

    def selection_changed(self, evt: wx.CommandEvent):
        def set_selected(value, collection):
            for entry in collection:
                entry.is_selected = value

        set_selected(False, self.get_filtered_entries())
        set_selected(True, self.get_comparison_selection())
        self.update_button()

    def get_comparison_selection(self):
        return map(
            self.comparison_select.GetClientData, self.comparison_select.GetSelections()
        )

    def get_plot_selection(self):
        base_selected = self.base_select.GetSelection()
        if not (0 <= base_selected < len(self.experiment_choice)):
            return []
        return [
            base_selected,
            *(entry.idx for entry in self.get_comparison_selection()),
        ]

    @staticmethod
    def is_valid_selection(selection):
        return len(selection) >= 2

    def update_button(self):
        self.plot_btn.Enable(MainFrame.is_valid_selection(self.get_plot_selection()))

    def plot_charts(self, evt: wx.CommandEvent):
        selection = self.get_plot_selection()
        if not MainFrame.is_valid_selection(selection):
            return

        chart_datas = generate_charts_data(
            self.input_data, [self.experiments[idx] for idx in selection]
        )
        plot_datasets(chart_datas)

    def get_filtered_entries(self):
        selected_base_idx = self.base_select.GetSelection()
        return [
            entry for entry in self.experiment_choice if entry.idx != selected_base_idx
        ]

    def _init_window(self):
        panel = wx.Panel(self)

        self.plot_btn = wx.Button(panel, label="Plot")
        self.plot_btn.Disable()
        self.base_select = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.comparison_select = wx.ListBox(panel, style=wx.LB_EXTENDED)

        panel.SetSizerAndFit(
            MainFrame._create_main_layout(
                MainFrame._create_grid(panel, self.base_select, self.comparison_select),
                MainFrame._create_button_row(self.plot_btn),
            )
        )

        self.status_bar = self.CreateStatusBar()
        self.SetMinSize(wx.Size(300, 150))
        self.Show()

    @staticmethod
    def _create_main_layout(grid, button_row):
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(grid, 1, wx.ALL | wx.EXPAND, 5)
        column.Add(button_row, 0, wx.ALL | wx.EXPAND, 0)
        return column

    @staticmethod
    def _create_button_row(plot_btn):
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.AddStretchSpacer(1)
        button_row.Add(plot_btn, 0, wx.ALL, 0)
        return button_row

    @staticmethod
    def _create_grid(
        panel: wx.Panel, base_combo: wx.ComboBox, comparison_list: wx.ListBox
    ):
        grid = wx.FlexGridSizer(cols=2, gap=wx.Size(5, 5))
        grid.AddGrowableCol(1, 1)
        grid.AddGrowableRow(1, 1)
        grid.Add(wx.StaticText(panel, label="Base experiment:"), 0)
        grid.Add(base_combo, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="Compare experiment:"), 0)
        grid.Add(comparison_list, 1, wx.EXPAND)
        return grid


def analyse_file(input_file_path: str):
    app_win = wx.App()
    frame = MainFrame(input_file_path)
    app_win.MainLoop()


if __name__ == "__main__":
    app = sys.argv[0]
    args = sys.argv[1:]

    if len(args) == 0:
        display_help(app)
    else:
        input_file = args[0]
        if not os.path.exists(input_file):
            print(f"Given file '{input_file} does not exist")
            exit(-1)
        analyse_file(input_file)
# end main
