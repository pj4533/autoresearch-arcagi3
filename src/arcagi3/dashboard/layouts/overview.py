"""Overview page: score timeline and summary cards."""

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go


def create_summary_cards(summary):
    """Create summary statistic cards."""
    best = summary.get("best_experiment")
    best_text = f"{best['id']} ({best['avg_score']:.4f})" if best else "N/A"

    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4(str(summary["total"]), className="card-title"),
                            html.P("Total Experiments", className="card-text text-muted"),
                        ]
                    ),
                    className="text-center",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4(str(summary["completed"]), className="card-title"),
                            html.P("Completed", className="card-text text-muted"),
                        ]
                    ),
                    className="text-center",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4(str(summary["accepted"]), className="card-title"),
                            html.P("Accepted", className="card-text text-muted"),
                        ]
                    ),
                    className="text-center",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4(best_text, className="card-title"),
                            html.P("Best Experiment", className="card-text text-muted"),
                        ]
                    ),
                    className="text-center",
                ),
                width=3,
            ),
        ],
        className="mb-4",
    )


def create_score_timeline(experiments):
    """Create score timeline chart."""
    completed = [e for e in experiments if e.get("avg_score") is not None]
    if not completed:
        return html.P("No completed experiments yet.", className="text-muted text-center mt-4")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[e["id"] for e in completed],
            y=[e["avg_score"] for e in completed],
            mode="lines+markers",
            name="Avg Score",
            marker=dict(
                color=[
                    "#28a745" if e.get("verdict") == "accept"
                    else "#dc3545" if e.get("verdict") == "reject"
                    else "#6c757d"
                    for e in completed
                ],
                size=10,
            ),
            text=[e.get("hypothesis", "")[:60] for e in completed],
            hovertemplate="<b>%{x}</b><br>Score: %{y:.4f}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Average Score Over Experiments",
        xaxis_title="Experiment",
        yaxis_title="Average Score",
        template="plotly_white",
        height=400,
    )
    return dcc.Graph(figure=fig)


def create_actions_chart(experiments):
    """Create total actions chart."""
    completed = [e for e in experiments if e.get("total_actions") is not None]
    if not completed:
        return html.Div()

    fig = px.bar(
        x=[e["id"] for e in completed],
        y=[e["total_actions"] for e in completed],
        labels={"x": "Experiment", "y": "Total Actions"},
        title="Actions Per Experiment",
        template="plotly_white",
    )
    fig.update_layout(height=300)
    return dcc.Graph(figure=fig)


def layout(db):
    """Build the overview page layout."""
    summary = db.get_summary()
    experiments = db.list_experiments(order_by="id ASC", limit=200)

    return html.Div(
        [
            html.H2("Overview", className="mb-3"),
            create_summary_cards(summary),
            create_score_timeline(experiments),
            create_actions_chart(experiments),
        ]
    )
