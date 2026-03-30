# Experiment Log

Score = max(0, 1 - (agent_actions / (3 * human_actions))). Higher = better.
25 games available. Agent: Claude Code playing directly via arc CLI with vision.

| Exp | Game | Description | Score | Actions | Duration | Status | Notes |
|-----|------|-------------|-------|---------|----------|--------|-------|
| 001 | ls20 | Sliding block puzzle, moved block through corridors | 0 | 16 | — | attempted | Block moves 1 cell per action. Couldn't figure out goal. |
| 002 | vc33 | Click-only game, gray/white split with staircase | 0 | 7 | — | attempted | Every click decrements header counter. No visible cell changes. |
| 003 | ft09 | Pattern grid game, 4 quadrants with colored cells | 0 | 5 | — | attempted | Analogy puzzle? XOR pattern? Clicks only decrease counter. |
| 004 | ar25 | L-shaped pieces, movement + perform + click | 0 | 16 | — | attempted | Piece moves but can't cross divider cleanly. Undo costs actions. |
| 005 | sp80 | Platformer with character, platform, castle structures | 0 | 22 | — | attempted | Character moves, world scrolls. Hit walls easily. No scoring. |
| 006 | tr87 | Symbol tile grid with reference patterns below | 0 | 3 | — | attempted | Tiles with symbols, cursor moves in reference area. Complex puzzle. |
