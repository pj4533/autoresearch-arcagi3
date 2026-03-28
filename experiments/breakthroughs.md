# Breakthroughs

Experiments that improved the score. Each entry explains what changed and why it worked.

## Exp 006: Disable Qwen Thinking Mode

- **Category**: Prompt Engineering / Adapter Fix
- **Change**: Added `enable_thinking=False` to `apply_chat_template()` in `mlx_adapter.py`
- **Results**: avg=0.0000, ls20=0, ft09=0, vc33=0, actions=120, duration=4404s
- **Delta vs previous best**: Score unchanged but JSON parse rate improved from 0% to 91%. Duration reduced 41% (7480s→4404s).
- **Why it worked**: Qwen3.5's thinking mode generates `<think>` tokens that corrupt JSON output. Disabling it lets the model output clean JSON directly. This was the root cause of ALL previous experiment failures.
- **Code change**: One-line change in `src/arcagi3/adapters/mlx_adapter.py` — added `enable_thinking=False` parameter to `apply_chat_template()` call.

## Exp 022: Fix Frame Comparison Timing Bug

- **Category**: Bug Fix / State Tracking
- **Change**: Save current frame to datastore before returning action; compare saved frame on next step instead of using `context.frames.previous_grids` (which is stale due to timing).
- **Results**: avg=0.0000, ls20=0, ft09=0, vc33=0, actions=120, duration=3525s
- **Delta vs previous best**: Score unchanged but frame change detection went from 0% to 100%. All 21 prior experiments were blind — the agent couldn't see what its actions did.
- **Why it worked**: `context.frames.previous_grids` and `frame_grids` are identical at `step()` time due to the order of operations in `_run_session_loop()`. The context is updated with the SAME frames before calling step(), making the comparison always return "no visible change". By saving the frame ourselves in the datastore before returning, we have a true "before" snapshot to compare against on the next step.
- **Code change**: Added `_save_current_frame()` method that copies the current grid to `context.datastore["saved_prev_grid"]`. Modified `_describe_frame_change()` to compare this saved grid against the current frame. Called at end of both `_probe_step()` and `_explore_step()`.
