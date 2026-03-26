"""
ARC-AGI-3 Autoresearch Dashboard.

Multi-page Dash application for visualizing experiment results.

Usage:
    uv run python -m arcagi3.dashboard.app
    uv run python -m arcagi3.dashboard.app --host 0.0.0.0 --port 8050
"""

import argparse
import json
import logging

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State

from arcagi3.autoresearch.experiment_db import ExperimentDB

logger = logging.getLogger(__name__)

# Global DB reference (set at startup)
_db: ExperimentDB = None


def create_app(db_path: str = "experiments/experiments.db") -> dash.Dash:
    """Create and configure the Dash application."""
    global _db
    _db = ExperimentDB(db_path)

    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        suppress_callback_exceptions=True,
    )

    app.title = "ARC-AGI-3 Autoresearch"

    # Navigation bar
    navbar = dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Overview", href="/", active="exact")),
            dbc.NavItem(dbc.NavLink("Experiments", href="/experiments", active="exact")),
            dbc.NavItem(dbc.NavLink("Games", href="/games", active="exact")),
            dbc.NavItem(dbc.NavLink("Live", href="/live", active="exact")),
        ],
        brand="ARC-AGI-3 Autoresearch",
        brand_href="/",
        color="primary",
        dark=True,
    )

    app.layout = html.Div(
        [
            dcc.Location(id="url", refresh=False),
            navbar,
            dbc.Container(
                id="page-content",
                className="mt-4",
                fluid=True,
            ),
            # Auto-refresh interval (10 seconds)
            dcc.Interval(id="refresh-interval", interval=10_000, n_intervals=0),
        ]
    )

    # Page routing callback
    @app.callback(
        Output("page-content", "children"),
        [Input("url", "pathname"), Input("refresh-interval", "n_intervals")],
    )
    def display_page(pathname, _n):
        from arcagi3.dashboard.layouts import overview, experiments, games, live

        if pathname == "/experiments":
            return experiments.layout(_db)
        elif pathname == "/games":
            return games.layout(_db)
        elif pathname == "/live":
            return live.layout(_db)
        else:
            return overview.layout(_db)

    # Experiment detail callback
    @app.callback(
        Output("experiment-detail", "children"),
        Input("experiments-table", "selected_rows"),
        State("experiments-table", "data"),
        prevent_initial_call=True,
    )
    def show_experiment_detail(selected_rows, data):
        from arcagi3.dashboard.layouts.experiments import create_detail_panel

        if not selected_rows:
            return html.Div()
        row = data[selected_rows[0]]
        exp = _db.get_experiment(row["ID"])
        return create_detail_panel(exp)

    return app


def main():
    parser = argparse.ArgumentParser(description="ARC-AGI-3 Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8050, help="Port to bind to")
    parser.add_argument("--db", default="experiments/experiments.db", help="DB path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    app = create_app(args.db)
    logger.info(f"Dashboard starting at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
