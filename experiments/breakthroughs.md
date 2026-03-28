# Breakthroughs

Experiments that improved the score. Each entry explains what changed and why it worked.

## Exp 006: Disable Qwen Thinking Mode

- **Category**: Prompt Engineering / Adapter Fix
- **Change**: Added `enable_thinking=False` to `apply_chat_template()` in `mlx_adapter.py`
- **Results**: avg=0.0000, ls20=0, ft09=0, vc33=0, actions=120, duration=4404s
- **Delta vs previous best**: Score unchanged but JSON parse rate improved from 0% to 91%. Duration reduced 41% (7480s→4404s).
- **Why it worked**: Qwen3.5's thinking mode generates `<think>` tokens that corrupt JSON output. Disabling it lets the model output clean JSON directly. This was the root cause of ALL previous experiment failures.
- **Code change**: One-line change in `src/arcagi3/adapters/mlx_adapter.py` — added `enable_thinking=False` parameter to `apply_chat_template()` call.
