"""Experiments page: table of all experiments with detail view."""

import json

from dash import html, dash_table, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc


def create_experiment_table(experiments):
    """Create the experiments DataTable."""
    rows = []
    for exp in experiments:
        rows.append(
            {
                "ID": exp["id"],
                "Status": exp["status"],
                "Agent": exp["agent"],
                "Config": exp["config"],
                "Games": exp["game_ids"],
                "Score": f"{exp['avg_score']:.4f}" if exp.get("avg_score") is not None else "-",
                "Actions": exp.get("total_actions") or "-",
                "Verdict": exp.get("verdict") or "-",
                "Duration": f"{exp.get('duration_seconds', 0):.0f}s" if exp.get("duration_seconds") else "-",
                "Hypothesis": (exp.get("hypothesis") or "")[:80],
            }
        )

    return dash_table.DataTable(
        id="experiments-table",
        columns=[
            {"name": col, "id": col}
            for col in ["ID", "Status", "Agent", "Config", "Games", "Score", "Actions", "Verdict", "Duration", "Hypothesis"]
        ],
        data=rows,
        row_selectable="single",
        sort_action="native",
        filter_action="native",
        page_size=20,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"filter_query": "{Verdict} = accept"}, "backgroundColor": "#d4edda"},
            {"if": {"filter_query": "{Verdict} = reject"}, "backgroundColor": "#f8d7da"},
            {"if": {"filter_query": "{Status} = running"}, "backgroundColor": "#fff3cd"},
        ],
    )


def create_detail_panel(exp):
    """Create a detailed view for a selected experiment."""
    if not exp:
        return html.P("Select an experiment to see details.", className="text-muted")

    per_game = {}
    if exp.get("per_game_results"):
        try:
            per_game = json.loads(exp["per_game_results"])
        except json.JSONDecodeError:
            pass

    game_rows = []
    for game_id, r in per_game.items():
        game_rows.append(
            html.Tr(
                [
                    html.Td(game_id),
                    html.Td(r.get("score", 0)),
                    html.Td(r.get("actions", 0)),
                    html.Td(f"${r.get('cost', 0):.4f}"),
                    html.Td(r.get("state", "-")),
                    html.Td(r.get("error", "-")),
                ]
            )
        )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H4(f"Experiment {exp['id']}"),
                html.P(f"Hypothesis: {exp.get('hypothesis', '-')}"),
                html.P(f"Changes: {exp.get('changes', '-')}"),
                html.P(f"Git: {exp.get('git_commit', '-')[:12] if exp.get('git_commit') else '-'}"),
                html.P(f"Prompt hash: {exp.get('prompt_hash', '-')}"),
                html.P(f"Parent: {exp.get('parent_experiment_id', '-')}"),
                html.Hr(),
                html.H5("Per-Game Results"),
                html.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [html.Th(c) for c in ["Game", "Score", "Actions", "Cost", "State", "Error"]]
                            )
                        ),
                        html.Tbody(game_rows),
                    ],
                    className="table table-sm",
                )
                if game_rows
                else html.P("No per-game results available."),
            ]
        ),
        className="mt-3",
    )


def layout(db):
    """Build the experiments page layout."""
    experiments = db.list_experiments(limit=200)

    return html.Div(
        [
            html.H2("Experiments", className="mb-3"),
            create_experiment_table(experiments),
            html.Div(id="experiment-detail"),
        ]
    )
