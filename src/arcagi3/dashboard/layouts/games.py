"""Per-game analysis page: score distributions and action efficiency."""

import json

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go


def create_game_score_histogram(metrics, game_id):
    """Create score histogram for a specific game."""
    game_metrics = [m for m in metrics if m["game_id"] == game_id]
    if not game_metrics:
        return html.P(f"No data for {game_id}.", className="text-muted")

    scores = [m["score"] for m in game_metrics]
    fig = px.histogram(
        x=scores,
        nbins=20,
        labels={"x": "Score", "y": "Count"},
        title=f"Score Distribution: {game_id}",
        template="plotly_white",
    )
    fig.update_layout(height=300)
    return dcc.Graph(figure=fig)


def create_action_efficiency_chart(metrics, game_id):
    """Create action efficiency scatter plot."""
    game_metrics = [m for m in metrics if m["game_id"] == game_id]
    if not game_metrics:
        return html.Div()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[m["actions_taken"] for m in game_metrics],
            y=[m["score"] for m in game_metrics],
            mode="markers",
            marker=dict(size=10, opacity=0.7),
            text=[m["experiment_id"] for m in game_metrics],
            hovertemplate="<b>%{text}</b><br>Actions: %{x}<br>Score: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Action Efficiency: {game_id}",
        xaxis_title="Actions Taken",
        yaxis_title="Score",
        template="plotly_white",
        height=300,
    )
    return dcc.Graph(figure=fig)


def create_game_best_table(metrics, experiments_map, game_id):
    """Show best experiments for a specific game."""
    game_metrics = sorted(
        [m for m in metrics if m["game_id"] == game_id],
        key=lambda m: m["score"],
        reverse=True,
    )[:10]

    if not game_metrics:
        return html.Div()

    rows = []
    for m in game_metrics:
        exp = experiments_map.get(m["experiment_id"], {})
        rows.append(
            html.Tr(
                [
                    html.Td(m["experiment_id"]),
                    html.Td(f"{m['score']:.4f}"),
                    html.Td(m["actions_taken"]),
                    html.Td((exp.get("hypothesis") or "")[:50]),
                ]
            )
        )

    return html.Div(
        [
            html.H5(f"Top Experiments for {game_id}"),
            html.Table(
                [
                    html.Thead(
                        html.Tr([html.Th(c) for c in ["Experiment", "Score", "Actions", "Hypothesis"]])
                    ),
                    html.Tbody(rows),
                ],
                className="table table-sm",
            ),
        ],
        className="mt-3",
    )


def layout(db):
    """Build the per-game analysis page."""
    experiments = db.list_experiments(limit=500)
    experiments_map = {e["id"]: e for e in experiments}

    # Gather all metrics
    all_metrics = []
    for exp in experiments:
        metrics = db.get_metrics(exp["id"])
        all_metrics.extend(metrics)

    # Find all game IDs
    game_ids = sorted(set(m["game_id"] for m in all_metrics)) if all_metrics else ["ls20", "ft09", "vc33"]

    sections = []
    for game_id in game_ids:
        sections.append(
            html.Div(
                [
                    html.H3(f"Game: {game_id}", className="mt-4"),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(create_game_score_histogram(all_metrics, game_id), width=6),
                            dbc.Col(create_action_efficiency_chart(all_metrics, game_id), width=6),
                        ]
                    ),
                    create_game_best_table(all_metrics, experiments_map, game_id),
                ]
            )
        )

    return html.Div(
        [
            html.H2("Per-Game Analysis", className="mb-3"),
            *sections if sections else [html.P("No experiment data yet.", className="text-muted")],
        ]
    )
