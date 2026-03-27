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

## Dead Ends

(patterns that don't work)
