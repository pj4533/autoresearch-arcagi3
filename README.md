# ARC-AGI-3 Autoresearch

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![ARC Prize](https://img.shields.io/badge/ARC--AGI--3-arcprize.org-orange.svg)](https://arcprize.org/)

Autonomous research system for [ARC-AGI-3](https://docs.arcprize.org/) game-playing agents. Runs experiments overnight on Apple Silicon using local Qwen models via MLX — zero API cost, fully automated.

**ARC-AGI-3** is a benchmark where AI agents interact with 64x64 grid environments, discovering rules through exploration and solving levels with minimal actions. No instructions are given — the agent must figure it out.

## How It Works

A two-agent autoresearch loop runs on local hardware:

1. **Researcher** — Analyzes past experiment results and proposes the next agent improvement to try
2. **Executor** — Implements the change, runs the benchmark, evaluates whether it helped

The system iterates on agent *strategy* (prompts, exploration heuristics, state tracking, memory management) rather than model weights. Results are tracked in SQLite and visualized via a web dashboard.

```
Researcher ──propose──> Executor ──run──> Results ──analyze──> Researcher ──> ...
```

## Quick Start

```bash
# Install
uv sync --extra mlx --extra dashboard

# Download primary model (~20GB, one-time)
python -c "from mlx_lm import load; load('mlx-community/Qwen3.5-35B-A3B-4bit')"

# Run baseline experiments
uv run python -m arcagi3.autoresearch.runner --baselines

# Start the dashboard
uv run python -m arcagi3.dashboard.app --port 8050 &

# Start autoresearch (let it crank overnight)
uv run python autoresearch.py --config qwen3.5-35b-local
```

## Target Hardware

Mac Studio M2 Ultra, 64GB unified memory. The primary model (Qwen3.5-35B-A3B MoE, 4-bit) runs at ~60-70 tok/s using ~20GB, leaving plenty of headroom. Each experiment takes ~10-30 minutes, giving **16-48 experiments per overnight run**.

## Local Models

| Model | Type | Speed | RAM | Use Case |
|-------|------|-------|-----|----------|
| Qwen3.5-35B-A3B | MoE | ~60-70 tok/s | ~20GB | Primary (fastest) |
| Qwen3-32B | Dense | ~20-30 tok/s | ~18GB | Higher quality |
| QwQ-32B | Reasoning | ~20-30 tok/s | ~18GB | Deep chain-of-thought |
| Qwen3.5-27B | Dense | ~30+ tok/s | ~14GB | Lightweight |

All models run via [mlx-lm](https://github.com/ml-explore/mlx-lm) on Apple Silicon. Cloud API models (Claude, GPT, Gemini, etc.) are also supported for validation.

## Project Structure

```
autoresearch.py              # Main autoresearch orchestrator
src/arcagi3/
  adapters/                  # LLM providers (MLX, Anthropic, OpenAI, Gemini, ...)
  explorer_agent/            # Probe -> Explore -> Exploit agent
  adcr_agent/                # Reference ADCR agent
  autoresearch/              # Experiment DB, batch runner, researcher, executor
  dashboard/                 # Web dashboard (Dash/Plotly)
  cli/                       # CLI for playing games directly
  agent.py                   # MultimodalAgent base class
  models.yml                 # Model configurations
```

## Links

- [ARC Prize](https://arcprize.org/) — The competition
- [ARC-AGI-3 Docs](https://docs.arcprize.org/) — Official documentation
- [ARC-AGI-3 Agents](https://github.com/arcprize/ARC-AGI-3-Agents) — Agent examples
- [mlx-lm](https://github.com/ml-explore/mlx-lm) — Local inference on Apple Silicon

## License

MIT
