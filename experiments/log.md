# Experiment Log

Score = max(0, 1 - (agent_actions / (3 * human_actions))). Higher = better.
Games: ls20, ft09, vc33. Max actions per experiment: 40.

| Exp | Idea | Description | Avg Score | Actions | ls20 | ft09 | vc33 | Duration | Status | Notes |
|-----|------|-------------|-----------|---------|------|------|------|----------|--------|-------|
| 001 | — | Baseline (no changes) | 0.0000 | 120 | 0 | 0 | 0 | 7480s | baseline | All explore responses failed JSON parse — model outputs prose instead of JSON. Every action falls back to ACTION1 (Move Up). |
| 002 | #1 | Game-type-aware prompts + ACTION fallback fix | 0.0000 | 120 | 0 | 0 | 0 | 9043s | reverted | Model behavior changed (tried ACTION6 for vc33) but JSON still malformed (literal "..." in values). Slower due to longer prompts. |
| 003 | #2 | Fix three hardcoded Move Up fallbacks | 0.0000 | 80 | 0 | 0 | 0 | 10990s | reverted | ls20 regressed to 0 actions. Much slower (2x LLM calls per action). JSON parse still 100% failure rate — root cause is model outputting prose, not fallback logic. |
| 004 | #3 | Programmatic click probe with object detection | 0.0000 | 120 | 0 | 0 | 0 | 3844s | reverted | 2x faster (ft09 in 9.5s!). Click probe works mechanically but all clicks show "no visible change" — coordinate mapping likely wrong. Need to verify grid-to-click coord conversion. |
| 005 | #4 | Eliminate convert LLM call, output ACTION codes | 0.0000 | 120 | 0 | 0 | 0 | 7511s | reverted | Same duration as baseline. Model sometimes produces JSON structure but truncated (unterminated strings). Still falls back to Move Up. |
