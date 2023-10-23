# csv_plots

Set of utils to plot CSV data in convenient way.

`plot_csv <file>` will read all columns and trait as data series. First column will be considered as X-axis. By defualt script loads file and present all available columns as a chart lines. Both chart's axis use binary logarithm values.

- Legend is clickable; each item may hide related data series
- Right panel with available data is clickable
- Left mouse button toggles selection of one item
- Middle mouse button selects everything
- Right mouse button deselects everything
- `Update series` refreshes conent of chart with selected data
- `Generate table` generates HTML file with table from selected data in current directory and open it in default web browser

`analyse_experiments_csv.py <file>` is designed to load CSV file with output table from Celero library for C++ code benchmarking. It may handle output files from different benchmarking frameworks if they comply with data allignement and column names (currently columns are not configurable).

How to use?

1. Select your base experiment from available list
2. Select data which you would like to compare
3. Hit `Plot` button to receive subplots of data (hardcoded one for now)

## Installation

### Prerequisits

- Python 3.11 (tested)
- Poetry

### Steps

1. `python.exe -m poetry install`
2. `python.exe -m poetry shell`
3. `<main script>`

## Contribution

Open for proposal. Developed in free time manner. Bugs? Raise an issue.

## Release notes

### v0.0.1

- Initial version of scripts `plot_csv.py` and `analyse_experiments_csv.py`
