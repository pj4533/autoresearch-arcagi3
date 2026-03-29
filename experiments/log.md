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
| 006 | #27 | Disable Qwen thinking mode (enable_thinking=False) | 0.0000 | 120 | 0 | 0 | 0 | 4404s | improved | BREAKTHROUGH: JSON parse failures dropped from 100% to 9%. Duration 41% faster. vc33 3.5x faster. Model now produces valid JSON and varied actions. Foundational fix that unblocks everything. |
| 007 | #5 | Click target list in explore prompt (object detection) | 0.0000 | 120 | 0 | 0 | 0 | 3650s | reverted | 17% faster than exp_006. Click targets shown to LLM but still no score. Model can now output JSON but click actions still don't produce visible changes. |
| 008 | #6 | State graph with loop detection + status bar masking | 0.0000 | 120 | 0 | 0 | 0 | 2491s | reverted | Fastest yet (67% faster than baseline). State graph helps model decide faster but no score improvement. |
| 009 | #7 | Enhanced frame change description (colors, region) | 0.0000 | 120 | 0 | 0 | 0 | 1949s | reverted | New speed record (74% faster than baseline). Better frame descriptions help model decide faster but still no score. |
| 010 | #8 | StateAct-style structured prompting | 0.0000 | 120 | 0 | 0 | 0 | 3086s | reverted | Only 1 parse failure (best ever). Structured output works but no score improvement. |
| 011 | #9 | Stuck detection + random action fallback | 0.0000 | 120 | 0 | 0 | 0 | 1003s | reverted | 87% faster (random actions skip LLM after 15 stuck actions). But random actions don't score either. |
| 012 | #10 | Structured memory (facts/hypotheses/actions) | 0.0000 | 120 | 0 | 0 | 0 | 3268s | reverted | No improvement. Structured memory didn't help model choose better actions. |
| 013 | #32 | Brute-force click scan for VC33 (corrected coords) | 0.0000 | 120 | 0 | 0 | 0 | 3656s | reverted | col*2/row*2 mapping still shows "no visible change" for all clicks. Same coords as exp_004. Issue is NOT coordinate mapping. |
| 014 | #11 | Multi-action planning (plan 3 per LLM call) | 0.0000 | 120 | 0 | 0 | 0 | 1127s | reverted | 85% faster (plan execution skips LLM). But faster wrong actions still score 0. |
| 015 | #13 | ReflAct-style goal reflection prompt | 0.0000 | 120 | 0 | 0 | 0 | 2740s | reverted | No improvement. Goal reflection didn't help the model discover game mechanics. |
| 016 | #16 | Score change feedback in prompt | 0.0000 | 120 | 0 | 0 | 0 | 3257s | reverted | No score changes occurred so feedback never triggered. The agent never scores on any game. |
| 017 | #20 | Multi-turn conversation context | 0.0000 | 120 | 0 | 0 | 0 | 3886s | reverted | Slower (extra tokens with no KV cache). Multi-turn context didn't help discover game mechanics. |
| 018 | #1(new) | Hypothesis-driven exploration | 0.0000 | 120 | 0 | 0 | 0 | 3337s | reverted | Model forms hypotheses but test actions still don't produce score. 9 parse failures (higher than baseline). |
| 019 | #2(new) | Action-effect journal | 0.0000 | 120 | 0 | 0 | 0 | 3356s | reverted | Journal tracks actions but model still can't discover scoring mechanics. |
| 020 | #3(new) | State graph with untried action tracking | 0.0000 | 120 | 0 | 0 | 0 | 2390s | reverted | Fast (2390s) but no score. State graph guides exploration but games don't respond to any actions. |
| 021 | #6(new) | Systematic probe with click testing | 0.0000 | 120 | 0 | 0 | 0 | 1929s | reverted | DIAGNOSTIC: ALL probe actions (movement+clicks) show "no visible change" across ALL games. Found ROOT CAUSE: frame comparison timing bug — previous_grids and frame_grids are identical at step() time. |
| 022 | fix | Fix frame comparison timing bug | 0.0000 | 120 | 0 | 0 | 0 | 3525s | improved | BREAKTHROUGH: Frame changes now detected! ls20 probes show "52 cells changed" instead of "no visible change". Agent can finally see effects of its actions. Foundational fix like exp_006. |
| 023 | #5(new) | Enhanced frame change description (colors, region) | 0.0000 | 120 | 0 | 0 | 0 | 3418s | reverted | Rich descriptions (color transitions, regions) working but no score improvement yet. |
