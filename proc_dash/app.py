"""
Constructs Dash app for viewing and filtering statuses of processing pipelines for a given dataset.
App accepts and parses a user-uploaded bagel.csv file (assumed to be generated by mr_proc) as input.
"""

import dash_bootstrap_components as dbc
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import proc_dash.utility as util
from dash import Dash, ctx, dash_table, dcc, html

app = Dash(
    __name__,
    external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"],
)


app.layout = html.Div(
    children=[
        html.H2(children="Neuroimaging Derivatives Status Dashboard"),
        dcc.Upload(
            id="upload-data",
            children=html.Button("Drag and Drop or Select .csv File"),
            style={"margin-top": "10px", "margin-bottom": "10px"},
            multiple=False,
        ),
        html.Div(
            id="output-data-upload",
            children=[
                html.H6(id="input-filename"),
                html.Div(
                    children=[
                        html.Div(id="total-participants"),
                        html.Div(
                            id="matching-participants",
                            style={"margin-left": "15px"},
                        ),
                    ],
                    style={"display": "inline-flex"},
                ),
                dash_table.DataTable(
                    id="interactive-datatable",
                    data=None,
                    sort_action="native",
                    sort_mode="multi",
                    filter_action="native",
                    page_size=50,
                    fixed_rows={"headers": True},
                    style_table={"height": "300px", "overflowY": "auto"},
                ),  # TODO: Treat all columns as strings to standardize filtering syntax?
            ],
            style={"margin-top": "10px", "margin-bottom": "10px"},
        ),
        dbc.Card(
            [
                # TODO: Put label and dropdown in same row
                html.Div(
                    [
                        dbc.Label("Filter by multiple sessions:"),
                        dcc.Dropdown(
                            id="session-dropdown",
                            options=[],
                            multi=True,
                            placeholder="Select one or more available sessions to filter by",
                            # TODO: Can set `disabled=True` here to prevent any user interaction before file is uploaded
                        ),
                    ]
                ),
                html.Div(
                    [
                        dbc.Label("Selection operator:"),
                        dcc.Dropdown(
                            id="select-operator",
                            options=[
                                {
                                    "label": "AND",
                                    "value": "AND",
                                    "title": "Show only participants with all selected sessions.",
                                },
                                {
                                    "label": "OR",
                                    "value": "OR",
                                    "title": "Show participants with any of the selected sessions.",
                                },
                            ],
                            value="AND",
                            clearable=False,
                            # TODO: Can set `disabled=True` here to prevent any user interaction before file is uploaded
                        ),
                    ]
                ),
            ]
        ),
    ]
)


@app.callback(
    [
        Output("interactive-datatable", "columns"),
        Output("interactive-datatable", "data"),
        Output("total-participants", "children"),
        Output("session-dropdown", "options"),
    ],
    [
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        Input("session-dropdown", "value"),
        Input("select-operator", "value"),
    ],
)
def update_outputs(contents, filename, session_values, operator_value):
    if contents is None:
        return None, None, "Upload a CSV file to begin.", []

    data, total_subjects, sessions, upload_error = util.parse_csv_contents(
        contents=contents, filename=filename
    )

    if upload_error is not None:
        return None, None, f"Error: {upload_error} Please try again.", []

    if session_values:
        data = util.filter_by_sessions(
            data=data,
            session_values=session_values,
            operator_value=operator_value,
        )

    tbl_columns = [{"name": i, "id": i} for i in data.columns]
    tbl_data = data.to_dict("records")
    tbl_total_subjects = f"Total number of participants: {total_subjects}"
    session_opts = [{"label": ses, "value": ses} for ses in sessions]

    return tbl_columns, tbl_data, tbl_total_subjects, session_opts


@app.callback(
    Output("matching-participants", "children"),
    [
        Input("interactive-datatable", "columns"),
        Input("interactive-datatable", "derived_virtual_data"),
    ],
)
def update_matching_participants(columns, virtual_data):
    """
    If the visible data in the datatable changes, update count of
    unique participants shown ("Participants matching query").

    When no filter (built-in or dropdown-based) has been applied,
    this count will be the same as the total number of participants
    in the dataset.
    """
    # calculate participant count for active table as long as datatable columns exist
    if columns is not None and columns != []:
        active_df = pd.DataFrame.from_dict(virtual_data)
        return f"Participants matching query: {util.count_unique_subjects(active_df)}"

    return ""


@app.callback(
    [
        Output("input-filename", "children"),
        Output("interactive-datatable", "filter_query"),
        Output("session-dropdown", "value"),
    ],
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def reset_table(contents, filename):
    """If file contents change (i.e., new CSV uploaded), reset file name and filter selection values."""
    if ctx.triggered_id == "upload-data":
        return f"Input file: {filename}", "", ""

    raise PreventUpdate


if __name__ == "__main__":
    app.run_server(debug=True)
