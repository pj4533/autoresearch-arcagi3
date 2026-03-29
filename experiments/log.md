# Experiment Log

Score = max(0, 1 - (agent_actions / (3 * human_actions))). Higher = better.
Games: ls20, ft09, vc33. Agent: stategraph (programmatic state-graph explorer).
Previous explorer agent experiments (001-030) archived in log_archive_explorer.md.

| Exp | Idea | Description | Avg Score | Actions | ls20 | ft09 | vc33 | Duration | Status | Notes |
|-----|------|-------------|-----------|---------|------|------|------|----------|--------|-------|
| 001 | — | Stategraph baseline (no changes) | 0.0000 | 120 | 0 | 0 | 0 | 17s | baseline | 120 actions in 17s — mostly programmatic. LLM called every 15 steps. ls20: detects grid shifts. ft09: movement fails (click-only game). vc33: detects click effects but no score. |
| 002 | #2 | Click pipeline diagnostic | — | — | — | — | — | — | diagnostic | FINDINGS: vc33 clicks WORK (color 9 blocks → 265 cell changes). ft09 ALL actions only change status bar — game version 9ab2447a appears broken. ls20 has no click action. Agent object detection finds correct targets. Click coordinates correct (0-63 grid). vc33 is the scoring target. |
