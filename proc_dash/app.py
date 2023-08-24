"""
Constructs Dash app for viewing and filtering statuses of processing pipelines for a given dataset.
App accepts and parses a user-uploaded bagel.csv file (assumed to be generated by mr_proc) as input.
"""

import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Dash, ctx, dash_table, dcc, html, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import proc_dash.plotting as plot
import proc_dash.utility as util

EMPTY_FIGURE_PROPS = {"data": [], "layout": {}, "frames": []}
DEFAULT_NAME = "Dataset"

app = Dash(
    __name__, external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP]
)
server = app.server

# Navbar UI component
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    dbc.NavbarBrand(
                        "Neuroimaging Dataset Derivatives Status Dashboard"
                    )
                ),
                align="center",
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                children=[
                                    html.I(
                                        className="bi bi-box-arrow-up-right me-1"
                                    ),
                                    "Input schema",
                                ],
                                href="https://github.com/neurobagel/proc_dash/tree/main/schemas",
                                target="_blank",
                            ),
                            dbc.NavLink(
                                children=[
                                    html.I(className="bi bi-github me-1"),
                                    "GitHub",
                                ],
                                href="https://github.com/neurobagel/proc_dash",
                                target="_blank",
                            ),
                        ],
                    ),
                ),
                align="center",
            ),
        ],
        fluid=True,
    ),
    color="dark",
    dark=True,
)

UPLOAD_BUTTONS = [
    dcc.Upload(
        id={"type": "upload-data", "index": "imaging", "btn_idx": 0},
        children=dbc.Button(
            "Drag & Drop or Select an Imaging CSV File",
            color="secondary",
        ),
        multiple=False,
    ),
    dcc.Upload(
        id={"type": "upload-data", "index": "phenotypic", "btn_idx": 1},
        children=dbc.Button(
            "Drag & Drop or Select a Phenotypic CSV File",
            color="secondary",
        ),
        multiple=False,
    ),
]

upload_buttons_container = html.Div(
    id="upload-buttons",
    children=UPLOAD_BUTTONS,
    className="hstack gap-3",
)

sample_data = dbc.Button(
    "Example input files",
    color="light",
    href="https://github.com/neurobagel/proc_dash/blob/main/example_bagels",
    target="_blank",  # open external site in new tab
)

dataset_name_dialog = dbc.Modal(
    children=[
        dbc.ModalHeader(
            dbc.ModalTitle("Enter the dataset name:"), close_button=False
        ),
        dbc.ModalBody(
            dbc.Input(
                id="dataset-name-input", placeholder=DEFAULT_NAME, type="text"
            )
        ),
        dbc.ModalFooter(
            [
                dcc.Markdown("*Tip: To skip, press Submit or ESC*"),
                dbc.Button(
                    "Submit", id="submit-name", className="ms-auto", n_clicks=0
                ),
            ]
        ),
    ],
    id="dataset-name-modal",
    is_open=False,
    backdrop="static",  # do not close dialog when user clicks elsewhere on screen
)

dataset_summary_card = dbc.Card(
    dbc.CardBody(
        [
            html.H5(
                children=DEFAULT_NAME,
                id="summary-title",
                className="card-title",
            ),
            html.P(
                id="dataset-summary",
                style={"whiteSpace": "pre"},  # preserve newlines
                className="card-text",
            ),
        ],
    ),
    id="dataset-summary-card",
    style={"display": "none"},
)

status_legend_card = dbc.Card(
    dbc.CardBody(
        [
            html.H5(
                "Processing status legend",
                className="card-title",
            ),
            html.P(
                children=util.construct_legend_str(
                    util.PIPE_COMPLETE_STATUS_SHORT_DESC
                ),
                style={"whiteSpace": "pre"},  # preserve newlines
                className="card-text",
            ),
        ]
    ),
    id="processing-status-legend",
    style={"display": "none"},
)

overview_table = dash_table.DataTable(
    id="interactive-datatable",
    data=None,  # TODO: is this needed?
    sort_action="native",
    sort_mode="multi",
    filter_action="native",
    page_size=50,
    # fixed_rows={"headers": True},
    style_table={"height": "400px", "overflowY": "auto"},
    # TODO: When table is large, having both vertical + horizontal scrollbars doesn't look great.
    # Consider removing fixed height and using only page_size + setting overflowX to allow horizontal scroll.
    # Or, use relative css units here, e.g. vh for fractions of the viewport-height: https://www.w3schools.com/cssref/css_units.php
    # Also, should fix participant_id column, as long as it's first in the dataframe.
    style_cell={
        "fontSize": 13  # accounts for font size inflation by dbc theme
    },
    style_header={
        "position": "sticky",
        "top": 0,
    },  # Workaround to fixed_rows that does not impact column width. Could also specify widths in style_cell
    export_format="none",
)
# NOTE: Could cast columns to strings for the datatable to standardize filtering syntax,
# but this results in undesirable effects (e.g., if there is session 1 and session 11,
# a query for "1" would return both)

filter_form_title = html.Div(
    [
        html.H5(
            children="Advanced filtering options",
        ),
        html.I(
            className="bi bi-question-circle ms-1",
            id="tooltip-question-target",
        ),
        dbc.Tooltip(
            "Filter for multiple sessions simultaneously. "
            "Any filter specified directly in the data table will be applied on top of the advanced filtering.",
            target="tooltip-question-target",
        ),
    ],
    style={"display": "inline-flex"},
)

session_filter_form = dbc.Form(
    [
        # TODO: Put label and dropdown in same row
        html.Div(
            [
                dbc.Label(
                    "Filter by session(s):",
                    html_for="session-dropdown",
                    className="mb-0",
                ),
                dcc.Dropdown(
                    id="session-dropdown",
                    options=[],
                    multi=True,
                    placeholder="Select one or more available sessions to filter by",
                ),
            ],
            className="mb-2",  # Add margin to keep dropdowns spaced apart
        ),
        html.Div(
            [
                dbc.Label(
                    "Session selection operator:",
                    html_for="select-operator",
                    className="mb-0",
                ),
                dcc.RadioItems(
                    id="select-operator",
                    options=[
                        {
                            "label": html.Span("AND", id="and-selector"),
                            "value": "AND",
                        },
                        {
                            "label": html.Span("OR", id="or-selector"),
                            "value": "OR",
                        },
                    ],
                    value="AND",
                    inline=True,
                    inputClassName="me-1",
                    labelClassName="me-3",
                ),
                dbc.Tooltip(
                    "All selected sessions are present and match the pipeline-level filter.",
                    target="and-selector",
                ),
                dbc.Tooltip(
                    "Any selected session is present and matches the pipeline-level filter.",
                    target="or-selector",
                ),
            ],
            className="mb-2",
        ),
    ],
)

app.layout = html.Div(
    children=[
        navbar,
        dcc.Store(id="memory-filename"),
        dcc.Store(id="memory-sessions"),
        dcc.Store(id="memory-overview"),
        dcc.Store(id="memory-pipelines"),
        html.Div(
            children=[upload_buttons_container, sample_data],
            style={"margin-top": "10px", "margin-bottom": "10px"},
            className="hstack gap-3",
        ),
        dataset_name_dialog,
        html.Div(
            id="output-data-upload",
            children=[
                html.H4(id="input-filename"),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                children=[
                                    html.Div(
                                        id="upload-message",  # NOTE: Temporary placeholder, to be removed once error alert elements are implemented
                                    ),
                                    html.Div(
                                        id="column-count",
                                    ),
                                    html.Div(
                                        id="matching-participants",
                                        style={"margin-left": "15px"},
                                    ),
                                    html.Div(
                                        id="matching-records",
                                        style={"margin-left": "15px"},
                                    ),
                                ],
                                style={"display": "inline-flex"},
                            ),
                            align="end",
                        ),
                        dbc.Col(
                            dataset_summary_card,
                        ),
                    ]
                ),
                overview_table,
            ],
            style={"margin-top": "10px", "margin-bottom": "10px"},
        ),
        dbc.Row(
            [
                dbc.Row(filter_form_title),
                dbc.Row(
                    [
                        dbc.Col(
                            session_filter_form,
                            width=3,
                        ),
                        dbc.Col(
                            dbc.Row(
                                id="pipeline-dropdown-container",
                                children=[],
                            )
                        ),
                    ]
                ),
            ],
            id="advanced-filter-form",
            style={"display": "none"},
        ),
        status_legend_card,
        dbc.Row(
            [
                # NOTE: Legend displayed for both graphs so that user can toggle visibility of status data
                dbc.Col(
                    dcc.Graph(
                        id="fig-pipeline-status", style={"display": "none"}
                    )
                ),
                dbc.Col(
                    dcc.Graph(
                        id="fig-pipeline-status-all-ses",
                        style={"display": "none"},
                    )
                ),
            ],
        ),
    ],
    style={"padding": "10px 10px 10px 10px"},
)


@app.callback(
    [
        Output("dataset-name-modal", "is_open"),
        Output("summary-title", "children"),
        Output("dataset-name-input", "value"),
    ],
    [
        Input("memory-overview", "data"),
        Input("submit-name", "n_clicks"),
    ],
    [
        State("dataset-name-modal", "is_open"),
        State("dataset-name-input", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_dataset_name_dialog(
    parsed_data, submit_clicks, is_open, name_value
):
    """Toggles a popup window for user to enter a dataset name when the data store changes."""
    if parsed_data is not None:
        if name_value not in [None, ""]:
            return not is_open, name_value, None
        return not is_open, DEFAULT_NAME, None

    return is_open, None, None


@app.callback(
    [
        Output("memory-filename", "data"),
        Output("memory-sessions", "data"),
        Output("memory-overview", "data"),
        Output("memory-pipelines", "data"),
        Output("upload-message", "children"),
        Output("interactive-datatable", "export_format"),
    ],
    Input({"type": "upload-data", "index": ALL, "btn_idx": ALL}, "contents"),
    State({"type": "upload-data", "index": ALL, "btn_idx": ALL}, "filename"),
)
def process_bagel(contents, filename):
    """
    From the contents of a correctly-formatted uploaded .csv file, parse and store (1) the pipeline overview data as a dataframe,
    and (2) pipeline-specific metadata as individual dataframes within a dict.
    Returns any errors encountered during input file processing as a user-friendly message.
    """
    if all(c is None for c in contents):
        return (
            no_update,
            None,
            None,
            None,
            "Upload a CSV file to begin.",
            no_update,
        )

    filename = filename[ctx.triggered_id.btn_idx]
    try:
        bagel, upload_error = util.parse_csv_contents(
            contents=ctx.triggered[0]["value"],
            filename=filename,
            schema=ctx.triggered_id.index,
        )
        if upload_error is None:
            session_list = bagel["session"].unique().tolist()
            overview_df = util.get_pipelines_overview(
                bagel=bagel, schema=ctx.triggered_id.index
            )
            pipelines_dict = util.extract_pipelines(
                bagel=bagel, schema=ctx.triggered_id.index
            )
    except Exception as exc:
        print(exc)  # for debugging
        upload_error = "Something went wrong while processing this file."

    if upload_error is not None:
        return (
            filename,
            None,
            None,
            None,
            f"Error: {upload_error} Please try again.",
            "none",
        )

    # Change orientation of pipeline dataframe dictionary to enable storage as JSON data
    for key in pipelines_dict:
        pipelines_dict[key] = pipelines_dict[key].to_dict("records")

    return (
        filename,
        session_list,
        {
            "type": ctx.triggered_id.index,
            "data": overview_df.to_dict("records"),
        },
        pipelines_dict,
        None,
        "csv",
    )


@app.callback(
    Output("upload-buttons", "children"),
    Input("memory-filename", "data"),
    prevent_initial_call=True,
)
def reset_upload_buttons(memory_filename):
    """
    Resets upload buttons to their initial state when any new file is uploaded.

    Upload components need to be manually replaced to clear contents,
    otherwise previously uploaded imaging/pheno bagels cannot be re-uploaded
    (e.g. if a user uploads pheno_bagel.csv, then imaging_bagel.csv, then pheno_bagel.csv again)
    see https://github.com/plotly/dash-core-components/issues/816
    """
    return UPLOAD_BUTTONS


@app.callback(
    [
        Output("dataset-summary", "children"),
        Output("dataset-summary-card", "style"),
        Output("column-count", "children"),
    ],
    Input("memory-overview", "data"),
    # TODO: add prevent_initial_call=True to prevent callback from being triggered on page load
)
def display_dataset_metadata(parsed_data):
    """When successfully uploaded data changes, update summary info of dataset."""
    if parsed_data is None:
        return None, {"display": "none"}, None

    overview_df = pd.DataFrame.from_dict(parsed_data.get("data"))

    return (
        util.construct_summary_str(overview_df),
        {"display": "block"},
        f"Total number of columns: {len(overview_df.columns)}",
    )


@app.callback(
    [
        Output("session-dropdown", "options"),
        Output("advanced-filter-form", "style"),
    ],
    Input("memory-overview", "data"),
    State("memory-sessions", "data"),
    # TODO: add prevent_initial_call=True to prevent callback from being triggered on page load
)
def update_session_filter(parsed_data, session_list):
    """When uploaded data changes, update the unique session options and visibility of the session filter dropdown."""
    if parsed_data is None:
        return [], {"display": "none"}

    # TODO: Revisit
    # overview_df = pd.DataFrame.from_dict(parsed_data.get("data"))
    # sessions = (
    #     overview_df["session"].unique().tolist()
    # )
    session_opts = [{"label": ses, "value": ses} for ses in session_list]

    return session_opts, {"display": "block"}


@app.callback(
    [
        Output("pipeline-dropdown-container", "children"),
        Output("interactive-datatable", "style_filter_conditional"),
    ],
    Input("memory-pipelines", "data"),
    State("memory-overview", "data"),
    prevent_initial_call=True,
)
def create_pipeline_status_dropdowns(pipelines_dict, parsed_data):
    """
    Generates a dropdown filter with status options for each unique pipeline in the input csv,
    and disables the native datatable filter UI for the corresponding columns in the datatable.
    """
    pipeline_dropdowns = []

    if pipelines_dict is None or parsed_data.get("type") == "phenotypic":
        return pipeline_dropdowns, None

    for pipeline in pipelines_dict:
        new_pipeline_status_dropdown = dbc.Col(
            [
                dbc.Label(
                    pipeline,
                    className="mb-0",
                ),
                dcc.Dropdown(
                    id={
                        "type": "pipeline-status-dropdown",
                        "index": pipeline,
                    },
                    options=list(util.PIPE_COMPLETE_STATUS_SHORT_DESC.keys()),
                    placeholder="Select status to filter for",
                ),
            ]
        )
        pipeline_dropdowns.append(new_pipeline_status_dropdown)

    # "session" column filter is also disabled due to implemented dropdown filters for session
    style_disabled_filters = [
        {
            "if": {"column_id": c},
            "pointer-events": "None",
        }
        for c in list(pipelines_dict.keys()) + ["session"]
    ]

    return pipeline_dropdowns, style_disabled_filters


@app.callback(
    [
        Output("interactive-datatable", "columns"),
        Output("interactive-datatable", "data"),
    ],
    [
        Input("memory-overview", "data"),
        Input("session-dropdown", "value"),
        Input("select-operator", "value"),
        Input({"type": "pipeline-status-dropdown", "index": ALL}, "value"),
        State("memory-pipelines", "data"),
    ],
)
def update_outputs(
    parsed_data,
    session_values,
    session_operator,
    status_values,
    pipelines_dict,
):
    if parsed_data is None:
        return None, None

    data = pd.DataFrame.from_dict(parsed_data.get("data"))

    if session_values or any(v is not None for v in status_values):
        # NOTE: The order in which pipeline-specific dropdowns are added to the layout is determined by the
        # order of pipelines in the pipeline-specific data store (see callback that generates the dropdowns).
        # As a result, the dropdown values passed to a callback will also follow this same pipeline order.
        pipeline_selected_filters = dict(
            zip(pipelines_dict.keys(), status_values)
        )
        data = util.filter_records(
            data=data,
            session_values=session_values,
            operator_value=session_operator,
            status_values=pipeline_selected_filters,
        )
    tbl_columns = [
        {"name": i, "id": i, "hideable": True} for i in data.columns
    ]
    tbl_data = data.to_dict("records")

    return tbl_columns, tbl_data


@app.callback(
    [
        Output("matching-participants", "children"),
        Output("matching-records", "children"),
    ],
    [
        Input("interactive-datatable", "columns"),
        Input("interactive-datatable", "derived_virtual_data"),
    ],
)
def update_matching_rows(columns, virtual_data):
    """
    If the visible data in the datatable changes, update counts of
    unique participants and records shown.

    When no filter (built-in or dropdown-based) has been applied,
    this count will be the same as the total number of participants
    in the dataset.
    """
    # calculate participant count for active table as long as datatable columns exist
    if columns is not None and columns != []:
        active_df = pd.DataFrame.from_dict(virtual_data)
        return (
            f"Participants matching filter: {util.count_unique_subjects(active_df)}",
            f"Records matching filter: {util.count_unique_records(active_df)}",
        )

    return "", ""


@app.callback(
    [
        Output("input-filename", "children"),
        Output("interactive-datatable", "filter_query"),
        Output("session-dropdown", "value"),
    ],
    Input("memory-filename", "data"),
    prevent_initial_call=True,
)
def reset_selections(filename):
    """
    If file contents change (i.e., selected new CSV for upload), reset displayed file name and dropdown filter
    selection values. Reset will occur regardless of whether there is an issue processing the selected file.
    """
    if filename is not None:
        return f"Input file: {filename}", "", ""

    raise PreventUpdate


@app.callback(
    [
        Output("fig-pipeline-status-all-ses", "figure"),
        Output("fig-pipeline-status-all-ses", "style"),
        Output("processing-status-legend", "style"),
    ],
    Input("memory-overview", "data"),
    State("memory-sessions", "data"),
    prevent_initial_call=True,
)
def generate_overview_status_fig_for_participants(parsed_data, session_list):
    """
    If new dataset uploaded, generate stacked bar plot of pipeline_complete statuses per session,
    grouped by pipeline. Provides overview of the number of participants with each status in a given session,
    per processing pipeline.
    """
    if parsed_data is not None and parsed_data.get("type") != "phenotypic":
        return (
            plot.plot_pipeline_status_by_participants(
                pd.DataFrame.from_dict(parsed_data.get("data")), session_list
            ),
            {"display": "block"},
            {"display": "block"},
        )

    return EMPTY_FIGURE_PROPS, {"display": "none"}, {"display": "none"}


@app.callback(
    [
        Output("fig-pipeline-status", "figure"),
        Output("fig-pipeline-status", "style"),
    ],
    Input(
        "interactive-datatable", "data"
    ),  # Input not triggered by datatable frontend filtering
    State("memory-pipelines", "data"),
    State("memory-overview", "data"),
    prevent_initial_call=True,  # TODO: remove, not doing anything since input triggered by another on-load callback
)
def update_overview_status_fig_for_records(data, pipelines_dict, parsed_data):
    """
    When visible data in the overview datatable is updated (excluding built-in frontend datatable filtering
    but including custom component filtering), generate stacked bar plot of pipeline_complete statuses aggregated
    by pipeline. Counts of statuses in plot thus correspond to unique records (unique participant-session
    combinations).
    """
    if data is None or parsed_data.get("type") == "phenotypic":
        return EMPTY_FIGURE_PROPS, {"display": "none"}

    data_df = pd.DataFrame.from_dict(data)

    if not data_df.empty:
        status_counts = (
            plot.transform_active_data_to_long(data_df)
            .groupby(["pipeline_name", "pipeline_complete"])
            .size()
            .reset_index(name="records")
        )
    else:
        status_counts = plot.populate_empty_records_pipeline_status_plot(
            pipelines=pipelines_dict.keys(),
            statuses=util.PIPE_COMPLETE_STATUS_SHORT_DESC.keys(),
        )

    return plot.plot_pipeline_status_by_records(status_counts), {
        "display": "block"
    }


if __name__ == "__main__":
    app.run_server(debug=True)
