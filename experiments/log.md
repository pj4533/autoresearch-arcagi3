# Experiment Log

Score = max(0, 1 - (agent_actions / (3 * human_actions))). Higher = better.
Games: ls20, ft09, vc33. Agent: stategraph (programmatic state-graph explorer).
Previous explorer agent experiments (001-030) archived in log_archive_explorer.md.

| Exp | Idea | Description | Avg Score | Actions | ls20 | ft09 | vc33 | Duration | Status | Notes |
|-----|------|-------------|-----------|---------|------|------|------|----------|--------|-------|
| 001 | — | Stategraph baseline (no changes) | 0.0000 | 120 | 0 | 0 | 0 | 17s | baseline | 120 actions in 17s — mostly programmatic. LLM called every 15 steps. ls20: detects grid shifts. ft09: movement fails (click-only game). vc33: detects click effects but no score. |
| 002 | #2 | Click pipeline diagnostic | — | — | — | — | — | — | diagnostic | FINDINGS: vc33 clicks WORK (color 9 blocks → 265 cell changes). ft09 ALL actions only change status bar — game version 9ab2447a appears broken. ls20 has no click action. Agent object detection finds correct targets. Click coordinates correct (0-63 grid). vc33 is the scoring target. |
| 003 | #3 | Qwen3-32B dense model | 0.0000 | 120 | 0 | 0 | 0 | 35s | reverted | 2x slower than qwen3.5-35b (35s vs 17s) due to dense architecture. Hypothesis quality similar — generic observations about color manipulation. No improvement in scoring. |
| 004 | #5 | Remove LLM calls (LLM_INTERVAL=0) | 0.0000 | 120 | 0 | 0 | 0 | 1s | reverted | 12x faster (1.4s vs 17s). Pure programmatic exploration. Still no score — systematic coverage doesn't find winning sequences with 40 actions per game. |
| 005 | #6 | BFS shortest-path-to-frontier | 0.0000 | 120 | 0 | 0 | 0 | 24s | reverted | Replaced Priority 4-6 with BFS navigation to nearest untried-action state. Slightly slower (24s vs 17s). Better algorithmic navigation but no score improvement with 40 actions. |
| 006 | #1 | 5-tier click priority + max_actions=200 | 0.0000 | 600 | 0 | 0 | 0 | 122s | reverted | Color saliency priority (groups 0-3). 200 actions per game. vc33: GAME_OVER after 200 actions (ran out of lives from wrong clicks). Agent clicks objects but wrong sequence/logic. click_results cache prevents re-trying positions in new states. |
| 007 | — | Click cache clear + no LLM + 200 actions | 0.0000 | 600 | 0 | 0 | 0 | 7s | reverted | Clear click_queue on state change + LLM_INTERVAL=0. 600 actions in 6.6s. Still 0 — brute-force clicking can't solve vc33 puzzle logic. Lives are consumed by wrong clicks before finding the right sequence. |
