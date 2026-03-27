# Research Notes

Accumulated knowledge from experiments. Never wiped, only appended.

## Key Insights

### Initial Agent Analysis (2026-03-27)

**Agent Architecture**: 3-phase Probe → Explore → Exploit (but exploit is never entered).

**Critical Weaknesses Identified:**

1. **Double LLM call per action**: Every explore step calls the LLM twice — once for reasoning (explore prompt) and once to convert "Move Up" → "ACTION1" (convert prompt). This halves throughput. Priority #1 to fix.

2. **No click probing**: Probe phase only tests ACTION1-5 (movement + perform). Games ft09 and vc33 rely on ACTION6 (clicking) which is never probed. The agent enters explore phase blind to clicking mechanics.

3. **Weak frame change description**: `_describe_frame_change` only returns "N cells changed (X% of grid)" — no information about WHAT changed (colors, positions, directions). The LLM can't reason well about game mechanics with so little information.

4. **Generic system prompt**: Same prompt for all 3 games despite radically different mechanics (ls20 = movement navigation, ft09 = click to toggle colors, vc33 = click-only reasoning).

5. **Flat unstructured memory**: Memory is an append-only string truncated to 15 lines. No distinction between confirmed facts and tentative hypotheses.

6. **Exploit phase never used**: Code defines PHASE_EXPLOIT constant but the step() dispatcher only has probe and "else" (explore). When the agent knows the answer, it still pays LLM cost per action.

7. **No loop detection**: No mechanism to detect when the agent is revisiting the same grid state.

8. **No cross-level transfer**: When moving to a new level, all accumulated knowledge is lost.

9. **No score tracking**: Agent doesn't explicitly track which actions caused score changes.

**Game-Specific Notes:**
- **ls20**: Uses ACTION1-5 (movement + perform). Navigation with hidden state. Probe phase is well-suited.
- **ft09**: Uses ACTION6 (click) + ACTION5 (perform). Click toggles colors (9→8). Multiple levels. Probe phase misses clicking entirely.
- **vc33**: ONLY uses ACTION6 (click). Movement actions are not available. Probe phase is completely useless since it only tests movement.

**Priority Analysis:**
- Ideas 1-4 are highest priority: they fix fundamental architectural weaknesses.
- Ideas 5-8 are medium priority: they improve strategy quality.
- Ideas 9-20 are lower priority: they add capabilities that build on the above.

### Category Coverage in Initial Queue
- Prompt Engineering: #1, #4, #15 (3 ideas)
- Exploration Strategy: #2, #8, #14 (3 ideas)
- State Tracking: #3, #9, #10 (3 ideas)
- Phase Transitions: #7, #11, #19 (3 ideas)
- Memory Management: #5, #13, #16 (3 ideas)
- Preprocessing: #12, #17, #20 (3 ideas)
- Action Sequencing: #6, #18 (2 ideas)

All 7 categories covered. Balanced distribution.

### Competition Research Findings (2026-03-27)

**ARC-AGI-3 Preview Competition Results (Aug 2025):**
- 1st: StochasticGoose (12.58%) — CNN + RL predicting frame-changing actions
- 2nd: Blind Squirrel (6.71%) — Directed state graphs with value-ranked action pairs
- 3rd: Graph-based exploration (training-free, solved 12 private levels)
- Best LLM approach: Tomas Engine (3.70%), crashed often
- Current frontier models (March 2026): All below 1%. Gemini 3.1 Pro tops at 0.37%.

**Key Takeaway**: Structured exploration and state tracking crushingly beat pure LLM reasoning.

**Most Actionable Strategies from Research:**

1. **State Graph Construction** (2nd/3rd place): Build directed graph where nodes = hashed grid states, edges = actions. Provides loop detection, shortest-path replay, frontier tracking. Single highest-impact change.

2. **Click Target Filtering** (1st place insight): Most cells are background/empty. Identifying interactive objects and only clicking those transforms the 4096-cell search into a ~10-50 target problem.

3. **StateAct Structured State Tracking** (academic research): Requiring explicit state tracking at each step reduced average steps from 31.49 to 19.11 (39% reduction). Outputs: current state summary, changes, mechanics discovered, goal hypothesis, untested approaches.

4. **ReflAct Goal Reflection** (academic research): "What is my current state relative to my goal?" prompting improved success rates by 21-28%.

5. **Cross-Level Budget Allocation**: Scoring formula weights later levels more. Optimal strategy: invest ~60% of action budget in exploration on levels 1-2, then exploit efficiently on levels 3+.

6. **Visual Object Prioritization for Clicks** (graph-based approach): Segment frame into connected components. Prioritize larger, more colorful, more morphologically distinct objects. Five priority tiers.

7. **Curiosity-Driven Exploration**: Prioritize actions whose outcomes are least predictable (highest information gain). Build forward model: "if I do X in state S, I expect S'". When result differs, that's the most valuable learning.

**Sources Reviewed:**
- ARC Prize 2025 Results and Analysis (arcprize.org)
- ARC-AGI-3 Technical Report (arxiv 2603.24621)
- 1st Place Write-up StochasticGoose (medium.com)
- Graph-Based Exploration for ARC-AGI-3 (arxiv 2512.24156)
- StateAct: Self-prompting and State-tracking (arxiv 2410.02810)
- ReflAct: World-Grounded Decision Making (arxiv 2505.15182)
- LPLH: Learning to Play Like Humans (arxiv 2505.12439)
- ICM: Curiosity-driven Exploration (Pathak et al.)

**Updated Queue Priorities (after research):**
- Inserted State Graph Construction at #2 (highest-impact new idea)
- Inserted StateAct prompting at #5
- Inserted Click Target Filtering at #7
- Inserted ReflAct Goal Reflection at #11
- Queue now has 22 ideas across all 7 categories

### Updated Category Coverage
- Prompt Engineering: #1, #5, #6, #11 (4 ideas)
- Exploration Strategy: #3, #12, #20 (3 ideas)
- State Tracking: #2, #4, #13 (3 ideas)
- Phase Transitions: #10, #14, #17 (3 ideas)
- Memory Management: #8, #15, #18 (3 ideas)
- Preprocessing: #7, #16, #19, #22 (4 ideas)
- Action Sequencing: #9, #21 (2 ideas)

### ADCR Agent Analysis (2026-03-27)

Studied the reference ADCR agent to identify proven patterns the Explorer agent should adopt.

**Patterns ADCR Uses That Explorer Lacks:**

1. **`---` Divider Pattern**: ADCR gets analysis AND memory update in ONE LLM call by using a `---` separator. The model writes analysis above the divider and memory scratchpad below it. Explorer currently doesn't combine outputs — this is a free efficiency win.

2. **Multi-Turn Message History**: ADCR includes the previous prompt and the model's previous response as conversation history. This gives the model continuity between steps. Explorer sends fresh single-message prompts each time with no conversation context.

3. **"NEW LEVEL!!!!" Positive Reinforcement**: ADCR detects score increases and tells the model "Whatever you did must have been good!" Explorer provides no feedback when score changes. This is important for the model to learn what works.

4. **image_diff() Visual Highlighting**: ADCR sends a diff-highlighted image showing what changed between frames. Explorer only counts changed cells as text. The `image_diff()` utility already exists in the codebase.

5. **JSON Retry Mechanism**: ADCR retries JSON parsing twice before falling back. Explorer immediately falls back to ACTION1 on first failure, wasting the action.

6. **Dynamic Action Examples in Prompts**: ADCR builds example actions from available_actions list. Explorer's prompts are more static.

7. **Movement-First Guidance**: ADCR explicitly instructs "favor moves before clicking." Explorer has no such guidance.

8. **Word-Limited Memory**: ADCR enforces memory_word_limit properly. Explorer truncates by line count (15 lines) which is crude.

**Utility Code Findings:**

- **FrameGrid**: `List[List[int]]`, values 0-15, typically 64x64
- **Click coordinates**: 0-127 range (divided by 2 internally → maps to 64x64 grid)
- **grid_to_text_matrix**: Just `json.dumps(grid)` — very compact but no spatial structure
- **extract_json_from_response**: Robust — tries fenced blocks, brace matching, control char cleanup
- **image_diff(img_a, img_b)**: Highlights changed pixels — available but Explorer doesn't use it
- **16-color palette**: 0=white, 5=black, 8=red, 9=blue, 11=yellow, etc.
- **get_human_inputs_text()**: Utility function for formatting action descriptions — exists but unused by Explorer

**New Ideas Generated from ADCR Analysis:**
- Added #23: Adopt `---` divider for combined analysis+memory
- Added #24: Score change feedback ("NEW LEVEL" reinforcement)
- Added #25: Multi-turn conversation context
- Added #26: Use image_diff() for visual change highlighting

## Dead Ends

(patterns that don't work)
