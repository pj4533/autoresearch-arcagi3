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
| 007 | bp35 | arc CLI play | 0 | 40 | — | attempted | IN_PROGRESS |
| 008 | dc22 | arc CLI play | 0 | 7 | — | attempted | IN_PROGRESS |
| 009 | ka59 | arc CLI play | 0 | 28 | — | attempted | IN_PROGRESS |
| 010 | su15 | arc CLI play | 1 | 36 | — | scored | IN_PROGRESS |
| 011 | sc25 | arc CLI play | 0 | 5 | — | attempted | IN_PROGRESS |
| 012 | sb26 | arc CLI play | 1 | 31 | — | scored | IN_PROGRESS |
| 013 | re86 | arc CLI play | 1 | 22 | — | scored | IN_PROGRESS |
| 014 | tn36 | arc CLI play | 0 | 11 | — | attempted | IN_PROGRESS |
| 015 | wa30 | arc CLI play | 0 | 34 | — | attempted | IN_PROGRESS |
| 016 | lp85 | arc CLI play | 0 | 0 | — | attempted | IN_PROGRESS |
| 017 | m0r0 | arc CLI play | 0 | 1 | — | attempted | IN_PROGRESS |
| 018 | tu93 | arc CLI play | 0 | 34 | — | attempted | IN_PROGRESS |
| 019 | g50t | arc CLI play | 0 | 5 | — | attempted | IN_PROGRESS |
| 020 | r11l | arc CLI play | 0 | 35 | — | attempted | IN_PROGRESS |
| 021 | sb26 | arc CLI play | 1 | 33 | — | scored | IN_PROGRESS |
| 022 | sk48 | arc CLI play | 0 | 0 | — | attempted | IN_PROGRESS |
| 023 | re86 | arc CLI play | 1 | 31 | — | scored | IN_PROGRESS |
| 024 | cd82 | arc CLI play | 0 | 6 | — | attempted | IN_PROGRESS |
| 025 | su15 | arc CLI play | 1 | 32 | — | scored | IN_PROGRESS |
| 026 | cn04 | arc CLI play | 0 | 16 | — | attempted | IN_PROGRESS |
| 027 | lf52 | arc CLI play | 0 | 5 | — | attempted | IN_PROGRESS |
| 028 | s5i5 | arc CLI play | 0 | 3 | — | attempted | IN_PROGRESS |
| 029 | re86 | arc CLI play | 1 | 40 | — | scored | IN_PROGRESS |
| 030 | bp35 | arc CLI play | 0 | 32 | — | attempted | IN_PROGRESS |
| 031 | sb26 | arc CLI play | 1 | 34 | — | scored | IN_PROGRESS |
| 032 | sb26 | arc CLI play | 1 | 30 | — | scored | IN_PROGRESS |
