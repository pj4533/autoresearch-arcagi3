"""Frame rendering for CLI output — text grids, PNG export, and diff summaries."""
import os
from typing import List, Optional

from arcagi3.cli.backends.base import GameFrame


def render_frame_text(
    frame: GameFrame,
    previous_frame: Optional[List[List[int]]] = None,
    game_id: str = "",
    action_count: int = 0,
    max_actions: int = 0,
) -> str:
    """Render a frame as formatted text for CLI output."""
    lines = []

    # Header
    display_id = game_id
    if frame.guid:
        display_id = f"{game_id}"
    lines.append(f"=== ARC-AGI-3: {display_id} ===")

    # State info
    lines.append(f"State: {frame.state}")
    lines.append(f"Score: {frame.levels_completed} levels completed")

    if max_actions > 0:
        lines.append(f"Actions: {action_count} / {max_actions}")
    else:
        lines.append(f"Actions: {action_count}")

    if frame.available_actions:
        lines.append(f"Available: {', '.join(frame.available_actions)}")

    # Frame grid (last grid is the visible state)
    if frame.grids:
        grid = frame.grids[-1]
        lines.append("")
        lines.append(f"Frame ({len(grid)}x{len(grid[0]) if grid else 0}):")
        # Render as space-separated values (compact)
        for row in grid:
            lines.append(" ".join(f"{v:2d}" for v in row))

    # Diff summary
    if previous_frame and frame.grids:
        diff = compute_frame_diff(previous_frame, frame.grids[-1])
        if diff:
            lines.append("")
            lines.append(f"Changes: {diff}")

    return "\n".join(lines)


def compute_frame_diff(
    prev_grid: List[List[int]], curr_grid: List[List[int]]
) -> Optional[str]:
    """Compute a text summary of what changed between two grids."""
    if not prev_grid or not curr_grid:
        return None

    rows_prev = len(prev_grid)
    rows_curr = len(curr_grid)
    if rows_prev != rows_curr:
        return f"Grid size changed: {rows_prev} rows -> {rows_curr} rows"

    changed_cells = 0
    min_row, max_row = rows_curr, 0
    min_col, max_col = len(curr_grid[0]) if curr_grid else 0, 0
    total_cells = 0

    for r in range(rows_curr):
        cols = min(len(prev_grid[r]), len(curr_grid[r]))
        total_cells += cols
        for c in range(cols):
            if prev_grid[r][c] != curr_grid[r][c]:
                changed_cells += 1
                min_row = min(min_row, r)
                max_row = max(max_row, r)
                min_col = min(min_col, c)
                max_col = max(max_col, c)

    if changed_cells == 0:
        return "No changes"

    pct = (changed_cells / total_cells * 100) if total_cells > 0 else 0
    return (
        f"{changed_cells} cells changed ({pct:.1f}%) "
        f"in rows {min_row}-{max_row}, cols {min_col}-{max_col}"
    )


def save_frame_image(frame: GameFrame, path: str):
    """Save frame as PNG image."""
    from arcagi3.utils.image import grid_to_image

    if not frame.grids:
        return

    grid = frame.grids[-1]
    img = grid_to_image(grid)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, format="PNG")
