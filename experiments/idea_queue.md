# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-28): The agent must DISCOVER game rules through exploration, REMEMBER what works, and APPLY learned rules efficiently. Prioritize ideas that make the agent smarter at learning — not ideas that encode answers or brute-force solutions.**

---

### 1. [Exploration Strategy] Hypothesis-driven exploration — "what to test?" not "what to do?"
- **Hypothesis**: The agent currently asks the LLM "what action should I take?" which leads to aimless movement. Humans explore by forming hypotheses ("clicking colored objects toggles something") and designing experiments to test them. Reframing to hypothesis-driven exploration produces more systematic, purposeful actions.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Restructure explore prompt:
  1. "What is your current HYPOTHESIS about how this game works?"
  2. "What EXPERIMENT would test this hypothesis?" (specific action + expected outcome)
  3. "What would you expect to see if your hypothesis is CORRECT vs WRONG?"
  Output: `{"hypothesis": "clicking colored blocks changes their color", "test_action": "ACTION6", "x": 50, "y": 25, "expected_if_true": "the block changes color", "expected_if_false": "nothing changes", "reasoning": "I haven't tried clicking yet"}`
  After executing, compare actual result to prediction. If prediction was wrong, prompt the model to revise hypothesis.
- **Expected impact**: More purposeful exploration. The agent learns by testing theories, not random wandering. Each action has a clear learning objective.

### 2. [Memory Management] Action-effect journal — track every action's observable effect
- **Hypothesis**: The agent takes actions but has poor memory of what happened. A structured journal recording every action and its observed effect ("ACTION1 → 12 cells shifted left", "ACTION6 at (30,20) → no change") gives the model a growing knowledge base to reason from. This is how humans build understanding — by accumulating observations.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: After each action, compute a detailed effect description (frame diff, score change, state change) and append to `context.datastore["action_journal"]` as a list of `{action, coords, effect, score_change}` entries. Include the last 15-20 entries in the explore prompt under "## What You've Tried". This gives the model a complete record of its exploration history.
- **Expected impact**: The model can see "I've tried 10 movements and none changed the grid — clicking is probably how this game works." Prevents repeating failed approaches.

### 3. [State Tracking] State graph with systematic exploration of untried actions
- **Hypothesis**: Competition winners built explicit state graphs (2nd and 3rd place). By hashing grid states and tracking which actions have been tried from each state, the agent can systematically explore rather than randomly wander. When all actions from a state are tried, navigate to a state with untried actions.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Hash masked grid (exclude status bar). Track `{state_hash: {actions_tried: {action: result_state}, visit_count}}`. In explore prompt: "From this state, you've tried: Move Up (→ same state), Move Down (→ new state). UNTRIED: Move Left, Move Right, Click." Agent always knows what's been tested and what hasn't.
- **Expected impact**: Eliminates wasted repeat actions. Ensures systematic coverage of all possibilities from each state.

### 4. [Memory Management] Cross-level knowledge transfer — carry learned rules forward
- **Hypothesis**: When the agent completes a level and starts a new one, it loses everything it learned. But game mechanics persist across levels (clicking toggles colors, movement shifts the grid). Carrying forward discovered rules lets the agent skip re-discovery and apply learned strategies immediately.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: On level transition (score increase + major grid change): save `action_effects`, confirmed hypotheses, and "mechanics summary" to `context.datastore["level_knowledge"]`. On new level, include "## What you learned from previous levels" in explore prompt. Also track which action TYPES were productive (clicks vs movement).
- **Expected impact**: Level 2+ should be much faster since the agent already knows the basic mechanics. Human players do this naturally — "oh, this level works like the last one."

### 5. [State Tracking] Enhanced frame change description — the agent needs to SEE effects
- **Hypothesis**: If the agent can't tell what changed after an action, it can't learn. The current description "12 cells changed (0.5%)" is almost useless. Detailed change descriptions (which colors, where, direction of shift) are the raw data the agent learns from.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Report: (a) color transitions ("5→3 x8, 4→3 x4"), (b) region ("bottom-left"), (c) movement direction if applicable ("shifted right by 1 cell"), (d) whether it looks like an object moved, appeared, or disappeared.
- **Expected impact**: The agent can actually understand what its actions DO. Foundation for all learning.

### 6. [Exploration Strategy] Systematic probe that discovers what action TYPES work
- **Hypothesis**: Before using the LLM, the probe phase should discover which categories of actions produce changes. Try each available action once and record: "movement actions cause grid shifts, clicking at center causes no change, clicking at (30,20) changes colors." This bootstraps the agent's understanding before expensive LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Probe each available action (including ACTION6 with a few click positions on visible objects). For each, record detailed frame change. Summarize findings: "Movement: 3/4 directions caused changes. Clicking: 0/3 positions caused changes." Pass summary to explore phase. The LLM then starts with actual knowledge of what works.
- **Expected impact**: Agent enters explore phase knowing what action types are productive. No more wasting 20 clicks when only movement works, or 20 movements when only clicks work.

### 7. [Prompt Engineering] Uncertainty-aware exploration — admit what you don't know
- **Hypothesis**: The model confidently asserts wrong hypotheses and commits to them. If we encourage explicit uncertainty ("I'm 30% confident clicking toggles colors"), the agent will: (a) test uncertain hypotheses before acting on them, (b) explore more when uncertain, (c) exploit only when confident.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add to JSON output: `"confidence": "LOW/MEDIUM/HIGH"` and `"what_i_dont_know": "..."`. When confidence is LOW, the agent should prioritize information-gathering actions. When HIGH, it can commit to a strategy. Track confidence over time in memory.
- **Expected impact**: Better explore/exploit balance. More targeted exploration.

### 8. [Prompt Engineering] Eliminate convert LLM call — output ACTION codes directly
- **Hypothesis**: Two LLM calls per action is wasteful. Having the model output ACTION codes directly (ACTION1, ACTION6 with x,y) skips the convert step, saving ~50% of LLM time and avoiding parse failures.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: List actions as "ACTION1 = Move Up", etc. Require ACTION codes in JSON. Skip convert when action starts with "ACTION".
- **Expected impact**: ~2x faster exploration iterations. More actions per time budget = more learning.

### 9. [Phase Transitions] Dynamic explore→exploit transition based on hypothesis confidence
- **Hypothesis**: The agent defines PHASE_EXPLOIT but never enters it. When the agent has tested a hypothesis multiple times and is confident about the rules, it should switch to efficient execution. This mirrors how humans play: explore briefly, then execute with purpose.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Track hypothesis confirmation count. When the same hypothesis has been confirmed by 3+ observations, transition to exploit: execute the hypothesis's implied strategy without LLM calls for each action. Fall back to explore if the strategy stops working.
- **Expected impact**: Once rules are discovered, the agent acts efficiently instead of re-analyzing every step.

### 10. [Exploration Strategy] Probe ACTION7 (undo) for safe exploration
- **Hypothesis**: Undo enables bolder exploration. If the agent knows it can reverse a bad action, it can try risky moves without fear of permanent damage. Especially important for LS20 which has a life mechanic.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In probe, test undo after another action. Record if it works. Tell the model: "Undo is available — explore boldly."
- **Expected impact**: More diverse exploration, especially of risky but potentially rewarding actions.

### 11. [Memory Management] Multi-turn conversation context
- **Hypothesis**: The model sees fresh prompts each step with no memory of its own previous reasoning. Including the previous step's analysis as conversation history gives continuity.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Store previous prompt/response. Include as user/assistant message pair.
- **Expected impact**: Model builds on its own prior analysis instead of starting fresh.

### 12. [Action Sequencing] Multi-action planning for exploration sequences
- **Hypothesis**: The model can plan exploration sequences ("try Move Right 3 times to reach that area") and execute them without LLM calls between. This is more efficient than deciding each step individually.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Ask for `"plan"` array. Execute plan steps without LLM. Clear plan if unexpected outcome (score change, major grid change).
- **Expected impact**: Faster systematic exploration.

### 13. [Phase Transitions] Auto re-probe on level transition
- **Hypothesis**: New levels may have different mechanics. Re-running the probe on level transitions ensures the agent re-maps what works.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Detect score jumps or >50% grid change. Reset to probe.
- **Expected impact**: Don't assume old rules apply on new levels.

### 14. [Preprocessing] Grid differencing — show the agent exactly what changed
- **Hypothesis**: A text diff showing changed cells (old→new values with positions) gives the model precise data to reason about game mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: After each action, include compact diff: "Changed: (5,3) 4→3, (5,4) 4→3, (6,3) 5→3 [3 cells shifted in bottom-left]"
- **Expected impact**: Raw data for rule discovery.

### 15. [Architecture] Combine ALL best changes into one experiment
- **Hypothesis**: 27 experiments tested ideas individually. Each showed partial improvement (better JSON, faster, better frame visibility, better action selection) but none scored. The compound effect of ALL improvements together may cross the threshold. Individual gains don't compound when reverted between experiments.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/*.prompt`
- **Changes**: Apply simultaneously on the accepted #27+#22 baseline: (1) eliminate convert call, (2) state graph with untried action tracking, (3) action-effect journal in prompt, (4) enhanced frame descriptions, (5) hypothesis-driven prompting, (6) prompt compression. Test all together — the whole is greater than the sum of parts.
- **Expected impact**: Compound effect of speed + visibility + exploration diversity + memory. If 40 actions at 6s/act = 240s total, the agent gets fast iterations with full feedback.

### 16. [Architecture] Increase max_actions to 100 for exploration budget
- **Hypothesis**: 40 actions may simply not be enough to both discover rules AND complete a level. LS20 level 1 needs 29 baseline actions — a human who already knows the rules. An agent discovering from scratch likely needs 50-80 exploration actions before it even understands the objective. At 6-9s/action with prompt compression, 100 actions = ~10-15 minutes per game — still fast.
- **Files to modify**: `run_benchmark.py` or CLI args
- **Changes**: Run with `--max-actions 100` instead of 40. This gives 2.5x more exploration budget. The agent can afford to spend 60 actions exploring and still have 40 left to execute.
- **Expected impact**: More exploration budget may be the simplest path to first score on LS20. The agent sees effects, makes diverse actions, but runs out of actions before finding the goal.

### 17. [Architecture] Try Qwen3-32B dense model (has KV cache, potentially better reasoning)
- **Hypothesis**: Qwen3.5-35B-A3B is a MoE model activating only 3B parameters per forward pass. Qwen3-32B is dense (all 32B params active) with standard attention (KV cache works!). It may have better per-token reasoning quality. With KV cache, repeated prompts are faster. Trade: slower generation (20-30 tok/s vs 60-70) but better thinking per token.
- **Files to modify**: `run_benchmark.py` or CLI args
- **Changes**: Run with `--config qwen3-32b-local`. Compare reasoning quality and score to qwen3.5-35b-local.
- **Expected impact**: If the bottleneck is model reasoning (not prompt engineering), a better model solves it directly. The dense architecture also supports KV cache reuse.

### 18. [Architecture] Programmatic state-graph exploration for LS20 (LLM only for interpretation)
- **Hypothesis**: Competition winners used programmatic graph exploration, not LLM-per-step. For LS20, implement a BFS/DFS that systematically tries each untried action from each state. The LLM is only called every 10 actions to interpret the accumulated observations and suggest a direction. This is closer to how the 2nd/3rd place winners approached it.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In explore phase for LS20: (1) hash state, (2) if untried actions exist from this state, pick one (no LLM), (3) record transition, (4) every 10 steps, call LLM with state graph summary to get high-level direction, (5) navigate to frontier states with untried actions. This reduces LLM calls from 40 to ~4 while systematically covering the state space.
- **Expected impact**: Systematic coverage + reduced LLM dependency. Competition data shows this approach beats pure LLM by 3-4x.

---

## Completed

- **#1 [Prompt Engineering] Game-type-aware system prompt** — Exp 002: reverted (score=0.0000). Model tried correct actions but JSON output still malformed.
- **#2 [Exploration Strategy] Fix three hardcoded Move Up fallbacks** — Exp 003: reverted (score=0.0000). ls20 regressed to 0 actions. Root cause is JSON parse failure, not fallback logic.
- **#3 [Exploration Strategy] Programmatic click probe** — Exp 004: reverted (score=0.0000). 2x faster but all clicks "no visible change" — coordinate mapping wrong.
- **#4 [Prompt Engineering] Eliminate convert LLM call** — Exp 005: reverted (score=0.0000). Model sometimes produces JSON but truncated by max_tokens.
- **#27 [Prompt Engineering] Disable Qwen thinking mode** — Exp 006: ACCEPTED (foundational fix). JSON parse 0%→91%, duration 41% faster. Unblocks all other ideas.
- **#5 [Preprocessing] Click target list in explore prompt** — Exp 007: reverted (score=0.0000). Click targets shown but clicks still don't register visible changes.
- **#6 [State Tracking] State graph with loop detection** — Exp 008: reverted (score=0.0000). Fastest run (2491s) but no score improvement.
- **#7 [State Tracking] Enhanced frame change description** — Exp 009: reverted (score=0.0000). New speed record (1949s) but still no score.
- **#8 [Prompt Engineering] StateAct-style structured prompting** — Exp 010: reverted (score=0.0000). Best JSON parse rate (1 failure) but no score.
- **#9 [Phase Transitions] Stuck detection + random fallback** — Exp 011: reverted (score=0.0000). Very fast (1003s) but random actions don't score.
- **#10 [Memory Management] Structured memory** — Exp 012: reverted (score=0.0000). No improvement.
- **#32 [Exploration Strategy] Brute-force click for VC33** — Exp 013: reverted (score=0.0000). Corrected coords still no visible change. Click issue is NOT coordinate mapping.
- **#11 [Action Sequencing] Multi-action planning** — Exp 014: reverted (score=0.0000). 85% faster but no score.
- **#13 [Prompt Engineering] ReflAct-style reflection** — Exp 015: reverted (score=0.0000). No improvement.
- **#16 [Prompt Engineering] Score change feedback** — Exp 016: reverted (score=0.0000). No score changes ever occur so feedback never triggers.
- **#20 [Memory Management] Multi-turn conversation context** — Exp 017: reverted (score=0.0000). Slower due to extra tokens.
- **#1(new) [Exploration Strategy] Hypothesis-driven exploration** — Exp 018: reverted (score=0.0000). Hypotheses formed but no score.
- **#2(new) [Memory Management] Action-effect journal** — Exp 019: reverted (score=0.0000). Journal tracks but model can't discover scoring mechanics.
- **#3(new) [State Tracking] State graph with untried actions** — Exp 020: reverted (score=0.0000). Fast but no score.
- **#6(new) [Exploration Strategy] Systematic probe with clicks** — Exp 021: reverted (score=0.0000). DIAGNOSTIC: found frame comparison timing bug.
- **fix [Bug Fix] Frame comparison timing** — Exp 022: ACCEPTED. Agent can now see action effects.
- **#5(new) [State Tracking] Enhanced frame descriptions** — Exp 023: reverted (score=0.0000). Rich descriptions working but no score.
- **#8(new) [Prompt Engineering] Eliminate convert LLM call** — Exp 024: reverted (score=0.0000). Faster but no score.
- **#10(new) [Exploration Strategy] Probe undo** — Exp 025: reverted (score=0.0000). Undo not available in these games.
- **#14(new) [Preprocessing] Grid differencing** — Exp 026: reverted (score=0.0000). Detailed diffs working but no score.
- **#15(new) [Prompt Engineering] Prompt compression** — Exp 027: reverted (score=0.0000). Fastest ls20 (373s) but no score.
- **#12(new) [Action Sequencing] Multi-action planning** — Exp 028: reverted (score=0.0000). Fastest benchmark (1390s) but no score.
