"""
Utility functions for formatting text and grids.
"""
import json
from collections import Counter, deque
from typing import Dict, List, Tuple


def get_human_inputs_text(available_actions: List[str], human_actions_map: Dict[str, str]) -> str:
    """
    Convert available actions to human-readable text.

    Args:
        available_actions: List of available action codes (e.g., ["ACTION1", "ACTION2"])
        human_actions_map: Dictionary mapping action codes to descriptions

    Returns:
        Formatted text listing available actions
    """
    text = "\n"
    for action in available_actions:
        if action in human_actions_map:
            text += f"{human_actions_map[action]}\n"
    return text


def grid_to_text_matrix(grid: List[List[int]]) -> str:
    """
    Convert a grid matrix to a readable text representation.

    Args:
        grid: 64x64 grid of integers (0-15) representing colors

    Returns:
        Formatted text representation of the grid (JSON format)
    """
    # Format as JSON for clarity and compactness
    return json.dumps(grid, separators=(",", ","))


def _bfs_components(grid: List[List[int]], exclude_colors: set, status_bar_rows: int = 2) -> List[dict]:
    """Find connected components of non-excluded colors via BFS."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    visited = set()
    components = []

    start_row = status_bar_rows
    end_row = rows - status_bar_rows

    for r in range(start_row, end_row):
        for c in range(cols):
            if (r, c) in visited or grid[r][c] in exclude_colors:
                continue
            color = grid[r][c]
            cells = []
            queue = deque([(r, c)])
            visited.add((r, c))
            while queue:
                cr, cc = queue.popleft()
                cells.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if start_row <= nr < end_row and 0 <= nc < cols and (nr, nc) not in visited and grid[nr][nc] == color:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            min_r = min(cr for cr, _ in cells)
            max_r = max(cr for cr, _ in cells)
            min_c = min(cc for _, cc in cells)
            max_c = max(cc for _, cc in cells)
            components.append({
                "color": color,
                "size": len(cells),
                "cells": cells,
                "min_row": min_r, "max_row": max_r,
                "min_col": min_c, "max_col": max_c,
                "center_row": (min_r + max_r) // 2,
                "center_col": (min_c + max_c) // 2,
            })
    return components


def detect_interactive_objects(grid: List[List[int]], status_bar_rows: int = 2) -> List[dict]:
    """
    Detect likely interactive objects in a game frame.

    Returns list of dicts with x, y (0-127 agent range), color, size.
    Small non-background objects are more likely interactive.
    """
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    if rows == 0 or cols == 0:
        return []

    # Find background color (most common in inner grid)
    flat = []
    for r in range(status_bar_rows, rows - status_bar_rows):
        flat.extend(grid[r])
    if not flat:
        return []
    color_counts = Counter(flat)
    background = color_counts.most_common(1)[0][0]

    components = _bfs_components(grid, {background}, status_bar_rows)

    # Filter: interactive = small (< 200 cells), not background
    # Large components are likely borders/structural
    interactive = [c for c in components if c["size"] < 200]
    interactive.sort(key=lambda c: c["size"])

    targets = []
    for comp in interactive:
        # Convert grid coords to 0-127 agent range
        x = min(comp["center_col"] * 2, 127)
        y = min(comp["center_row"] * 2, 127)
        targets.append({
            "x": x,
            "y": y,
            "color": comp["color"],
            "size": comp["size"],
            "row": comp["center_row"],
            "col": comp["center_col"],
        })
    return targets


def grid_to_structured_description(grid: List[List[int]], status_bar_rows: int = 2) -> str:
    """
    Convert a grid to a compact structured text description (~50 tokens).

    Identifies background, structural elements, and interactive objects.
    """
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    if rows == 0:
        return "Empty grid."

    # Find background
    flat = []
    for r in range(status_bar_rows, rows - status_bar_rows):
        flat.extend(grid[r])
    if not flat:
        return "Empty grid."
    color_counts = Counter(flat)
    background = color_counts.most_common(1)[0][0]

    components = _bfs_components(grid, {background}, status_bar_rows)

    structural = [c for c in components if c["size"] >= 200]
    interactive = [c for c in components if c["size"] < 200]
    interactive.sort(key=lambda c: c["size"])

    parts = [f"Grid: {cols}x{rows - 2 * status_bar_rows}. Background: color {background}."]

    if structural:
        struct_desc = ", ".join(f"color {c['color']} ({c['size']} cells)" for c in structural[:3])
        parts.append(f"Structural: {struct_desc}.")

    if interactive:
        obj_descs = []
        for c in interactive[:15]:  # cap at 15 objects
            w = c["max_col"] - c["min_col"] + 1
            h = c["max_row"] - c["min_row"] + 1
            obj_descs.append(f"color {c['color']} ({w}x{h}) at row={c['center_row']},col={c['center_col']}")
        parts.append(f"Objects: {'; '.join(obj_descs)}.")
    else:
        parts.append("No small objects detected.")

    return " ".join(parts)


def describe_frame_change_detailed(
    prev_grid: List[List[int]], curr_grid: List[List[int]], status_bar_rows: int = 2
) -> str:
    """
    Describe what changed between two frames in detail.

    Reports: cell count, color transitions, region of change.
    """
    rows = min(len(prev_grid), len(curr_grid))
    cols = min(len(prev_grid[0]), len(curr_grid[0])) if rows > 0 else 0

    start_row = status_bar_rows
    end_row = rows - status_bar_rows

    changes = []
    color_transitions: Counter = Counter()

    for r in range(start_row, end_row):
        for c in range(cols):
            if prev_grid[r][c] != curr_grid[r][c]:
                changes.append((r, c))
                color_transitions[(prev_grid[r][c], curr_grid[r][c])] += 1

    if not changes:
        return "No visible change."

    total = len(changes)
    grid_size = (end_row - start_row) * cols
    pct = (total / grid_size * 100) if grid_size > 0 else 0

    # Region of change
    min_r = min(r for r, _ in changes)
    max_r = max(r for r, _ in changes)
    min_c = min(c for _, c in changes)
    max_c = max(c for _, c in changes)
    mid_r = (end_row - start_row) // 2 + start_row
    mid_c = cols // 2

    region_v = "top" if max_r < mid_r else ("bottom" if min_r > mid_r else "middle")
    region_h = "left" if max_c < mid_c else ("right" if min_c > mid_c else "center")
    region = f"{region_v}-{region_h}"

    parts = [f"{total} cells changed ({pct:.1f}% of grid) in {region} region."]

    # Top color transitions
    top_transitions = color_transitions.most_common(3)
    trans_strs = [f"{old}->{new} x{count}" for (old, new), count in top_transitions]
    parts.append(f"Color changes: {', '.join(trans_strs)}.")

    return " ".join(parts)
