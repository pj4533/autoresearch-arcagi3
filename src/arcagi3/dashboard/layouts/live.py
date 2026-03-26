"""Live monitor page: current experiment status with auto-refresh."""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_running_status(db):
    """Show currently running experiment."""
    running = db.list_experiments(status="running", limit=1)
    if not running:
        return dbc.Alert(
            "No experiment currently running.",
            color="secondary",
            className="text-center",
        )

    exp = running[0]
    return dbc.Card(
        dbc.CardBody(
            [
                html.H4(f"Running: {exp['id']}", className="text-warning"),
                html.P(f"Agent: {exp['agent']} | Config: {exp['config']}"),
                html.P(f"Games: {exp['game_ids']}"),
                html.P(f"Hypothesis: {exp.get('hypothesis', '-')}"),
                html.P(f"Started: {exp['timestamp']}"),
                dbc.Spinner(color="warning", size="sm"),
                html.Span(" Running...", className="text-warning ms-2"),
            ]
        ),
        className="border-warning",
    )


def create_recent_completions(db):
    """Show recently completed experiments."""
    completed = db.list_experiments(status="completed", limit=5)
    if not completed:
        return html.P("No completed experiments yet.", className="text-muted")

    rows = []
    for exp in completed:
        verdict_color = {
            "accept": "success",
            "reject": "danger",
            "baseline": "info",
            "neutral": "secondary",
        }.get(exp.get("verdict"), "secondary")

        rows.append(
            dbc.ListGroupItem(
                [
                    html.Div(
                        [
                            html.Strong(exp["id"]),
                            dbc.Badge(
                                exp.get("verdict") or "?",
                                color=verdict_color,
                                className="ms-2",
                            ),
                        ]
                    ),
                    html.Small(
                        f"Score: {exp.get('avg_score', 0):.4f} | "
                        f"Actions: {exp.get('total_actions', 0)} | "
                        f"Duration: {exp.get('duration_seconds', 0):.0f}s",
                        className="text-muted",
                    ),
                    html.Br(),
                    html.Small(exp.get("hypothesis", "")[:80], className="text-muted"),
                ]
            )
        )

    return html.Div(
        [
            html.H4("Recent Completions"),
            dbc.ListGroup(rows),
        ]
    )


def create_queue_status(db):
    """Show queue depth."""
    pending = db.list_experiments(status="pending")
    return dbc.Alert(
        f"{len(pending)} experiment(s) pending in queue.",
        color="info" if pending else "secondary",
    )


def layout(db):
    """Build the live monitor page."""
    return html.Div(
        [
            html.H2("Live Monitor", className="mb-3"),
            dcc.Interval(id="live-interval", interval=10_000, n_intervals=0),
            create_running_status(db),
            html.Div(className="mt-4"),
            create_queue_status(db),
            html.Div(className="mt-4"),
            create_recent_completions(db),
        ]
    )
