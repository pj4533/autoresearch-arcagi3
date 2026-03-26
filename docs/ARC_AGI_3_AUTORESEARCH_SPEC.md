# ARC-AGI-3 Local Autoresearch: Implementation Spec

> **Purpose:** Transform the `autoresearch-arcagi3` repo from an API-dependent benchmarking scaffold into a fully local, overnight-cranking autoresearch system running on Mac Studio with Qwen models via MLX.
>
> **Target hardware:** Mac Studio M2 Ultra, 64GB unified memory, ~800 GB/s bandwidth
>
> **Give this document to Claude Code in the `autoresearch-arcagi3` repo.**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State of the Repo](#2-current-state-of-the-repo)
3. [What Needs to Change](#3-what-needs-to-change)
4. [Phase 1: MLX Local Model Adapter](#4-phase-1-mlx-local-model-adapter)
5. [Phase 2: Experiment Runner (Overnight Batch)](#5-phase-2-experiment-runner-overnight-batch)
6. [Phase 3: Dashboard](#6-phase-3-dashboard)
7. [Phase 4: Two-Agent Autoresearch Architecture](#7-phase-4-two-agent-autoresearch-architecture)
8. [Model Selection & Configuration](#8-model-selection--configuration)
9. [ARC-AGI-3 Autoresearch Strategy](#9-arc-agi-3-autoresearch-strategy)
10. [File Structure After Implementation](#10-file-structure-after-implementation)
11. [Implementation Order & Dependencies](#11-implementation-order--dependencies)
12. [Appendix: Research References](#12-appendix-research-references)

---

## 1. Executive Summary

### The Goal

Run ARC-AGI-3 agents overnight on Mac Studio using local Qwen models (zero API cost), with:
- A **batch experiment runner** that systematically tests agent variations
- A **web dashboard** showing results, graphs, and live progress
- A **two-agent autoresearch loop** (researcher proposes ideas, executor runs experiments)
- Everything local — no cloud APIs, no external dependencies during runs

### Why This Works

ARC-AGI-3 is interactive game environments (not static puzzles). Agents take actions in a 64x64 grid world, trying to solve levels efficiently. The metric is **action efficiency** vs human baseline.

With local Qwen models on MLX:
- **Qwen3.5-35B-A3B** at 4-bit: ~60-70 tok/s, ~20GB RAM → leaves ~34GB headroom
- **Qwen3-32B** at 4-bit: ~20-30 tok/s, ~18GB RAM → leaves ~36GB headroom
- Each LLM call: ~3-10 seconds (MoE models are fastest)
- Each game run (40 actions): ~3-10 minutes
- Each experiment (3 games): ~10-30 minutes
- **Overnight (8 hours): ~16-48 full experiments**

The 64GB constraint actually pushes us toward faster MoE models, meaning *more* experiments per night even though individual model capability is lower. For ARC-AGI-3, where strategy matters more than raw model intelligence, this is a favorable tradeoff.

### Key Insight: What to Iterate On

Unlike Parameter Golf (iterate on model weights) or ModelWar (iterate on warrior code), ARC-AGI-3 autoresearch iterates on **agent strategy**:

| Dimension | What Changes | Example |
|-----------|-------------|---------|
| **Prompts** | System prompt, explore prompt, analysis templates | "Add explicit hypothesis-testing instructions" |
| **Exploration heuristics** | How the agent decides what to try | "Systematic grid scanning instead of random actions" |
| **State representation** | How the agent tracks what it's learned | "Build an action→effect transition table" |
| **Phase transitions** | When to shift from exploring to exploiting | "Switch to exploit after 3 consistent hypotheses" |
| **Memory management** | What the agent remembers across actions | "Track position history to detect loops" |
| **Multi-level transfer** | Using knowledge from level N to solve level N+1 | "Preserve action-effect map across levels" |

The experiment log tracks: which variation was tried, on which games, resulting score, actions used. The autoresearch loop reads the log, proposes the next variation, implements it, and runs it.

---

## 2. Current State of the Repo

### What Exists (and is solid)

- **Full benchmarking framework** — `MultimodalAgent` base class, `ARC3Tester` orchestrator, checkpointing, scoring
- **Two agent implementations** — ADCR (reference) and Explorer (probe→explore→exploit)
- **13+ LLM provider adapters** — Anthropic, OpenAI, Gemini, DeepSeek, etc.
- **CLI tool** (`arc`) — Direct game playing with local backend at 2000+ FPS
- **Offline mode** — Games run via local `arcengine` library, no ARC server needed
- **3 committed game environments** — ls20, ft09, vc33 with metadata
- **Autoresearch protocol doc** — Experiment log spec, strategy evolution phases
- **Prompt system** — Jinja2 templates with `PromptManager`
- **Cost tracking** — Per-action token usage and cost calculation

### What's Missing

1. **No local model support** — All adapters call external APIs. No MLX/local inference.
2. **No batch experiment runner** — Can run one game at a time, but no automated sweep.
3. **No dashboard** — Results are JSON files in `results/`. No visualization.
4. **No autoresearch loop** — The protocol doc describes the loop, but there's no code that drives it autonomously.
5. **No researcher agent** — No system to propose new experiment ideas based on past results.

---

## 3. What Needs to Change

### Architecture Change: API → Local Inference

```
CURRENT:
  Agent.step() → ProviderAdapter.call_provider() → External API → response

AFTER:
  Agent.step() → MLXAdapter.call_provider() → Local mlx-lm → response
                                                    ↑
                                          Qwen model loaded in memory
                                          Running on Mac Studio GPU
```

### New Components

```
autoresearch-arcagi3/
├── src/arcagi3/
│   ├── adapters/
│   │   └── mlx_adapter.py          ← NEW: Local MLX inference
│   ├── autoresearch/
│   │   ├── runner.py               ← NEW: Batch experiment runner
│   │   ├── researcher.py           ← NEW: Idea generation agent
│   │   ├── executor.py             ← NEW: Experiment execution agent
│   │   ├── experiment_db.py        ← NEW: SQLite experiment tracker
│   │   └── mutations.py            ← NEW: Agent code mutation strategies
│   └── dashboard/
│       ├── server.py               ← NEW: Flask/FastAPI dashboard
│       └── templates/              ← NEW: Dashboard HTML/JS
├── autoresearch.py                 ← NEW: Main entry point
└── experiments/
    ├── experiment_log.jsonl         (exists, enhanced)
    └── experiments.db               ← NEW: SQLite for fast queries
```

---

## 4. Phase 1: MLX Local Model Adapter

### Overview

Create `src/arcagi3/adapters/mlx_adapter.py` that implements the `ProviderAdapter` interface using `mlx-lm` for local inference.

### Requirements

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
mlx = [
    "mlx-lm>=0.24.0",
]
```

Install: `uv sync --extra mlx`

### Implementation: `mlx_adapter.py`

```python
"""
MLX Local Model Adapter for ARC-AGI-3.

Runs Qwen models locally on Apple Silicon via mlx-lm.
Zero API cost. Requires macOS 15+ and Apple Silicon.

Usage:
    # In models.yml, add a config like:
    - name: "qwen3.5-122b-local"
      model_name: "mlx-community/Qwen3.5-122B-A10B-4bit"
      provider: "mlx"
      is_multimodal: false
      max_completion_tokens: 4096
      temperature: 0.7
      pricing:
        input: 0.0
        output: 0.0
"""
```

Key design decisions:

1. **Model loading:** Load the model ONCE at adapter initialization, keep it in memory across all calls. The model stays resident in unified memory. Do NOT reload per-call.

2. **Chat template:** Use `tokenizer.apply_chat_template()` to format messages properly. Qwen models have specific chat templates that must be honored.

3. **Message format conversion:** The existing framework sends messages in OpenAI format (`{"role": "system", "content": "..."}`, `{"role": "user", "content": [...]}` with text/image blocks). The adapter must:
   - Extract text content from structured message blocks
   - Flatten image blocks to text descriptions (since we'll use text grid mode, not vision)
   - Apply the Qwen chat template

4. **Token counting:** Use `len(tokenizer.encode(text))` for accurate local token counts. Report these through the standard `extract_usage()` interface.

5. **Generation parameters:** Support `temperature`, `top_p`, `max_tokens`, `repetition_penalty` from the model config.

6. **Thinking mode:** Qwen3/3.5 models support a "thinking" mode via `/think` tags. For reasoning-heavy tasks, enable thinking mode. The adapter should support a `thinking` config option.

### Implementation Details

```python
class MLXAdapter(ProviderAdapter):
    """Local MLX inference adapter."""

    def init_client(self):
        """Load model and tokenizer into memory."""
        from mlx_lm import load
        model, tokenizer = load(self.model_config.model_name)
        self._model = model
        self._tokenizer = tokenizer
        return None  # No external client needed

    def call_provider(self, messages):
        """Run local inference."""
        from mlx_lm import generate

        # Convert messages to chat template format
        chat_messages = self._convert_messages(messages)
        prompt = self._tokenizer.apply_chat_template(
            chat_messages, tokenize=False, add_generation_prompt=True
        )

        # Get generation params from config
        max_tokens = getattr(self.model_config, 'max_completion_tokens', 4096)
        temperature = getattr(self.model_config, 'temperature', 0.7)
        top_p = getattr(self.model_config, 'top_p', 0.9)

        # Generate
        response_text = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            temp=temperature,
            top_p=top_p,
        )

        # Track token counts
        prompt_tokens = len(self._tokenizer.encode(prompt))
        completion_tokens = len(self._tokenizer.encode(response_text))

        # Return a simple response object
        return MLXResponse(
            text=response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def _convert_messages(self, messages):
        """Convert framework message format to simple chat messages."""
        converted = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            if isinstance(content, str):
                converted.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Extract text parts, skip image blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block["text"])
                        elif block.get("type") in ("image_url", "image"):
                            text_parts.append("[Image frame provided as text grid above]")
                    elif isinstance(block, str):
                        text_parts.append(block)
                converted.append({"role": role, "content": "\n".join(text_parts)})

        return converted

    def extract_content(self, response):
        return response.text

    def extract_usage(self, response):
        return (response.prompt_tokens, response.completion_tokens, 0)

    # ... implement remaining abstract methods
```

### MLXResponse Dataclass

```python
from dataclasses import dataclass

@dataclass
class MLXResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
```

### Register the Adapter

In `src/arcagi3/adapters/__init__.py`, add the MLX adapter to the registry. The adapter selection happens in the provider factory based on `model_config.provider`.

In `runner.py` or wherever the adapter factory lives, add:
```python
if provider == "mlx":
    from arcagi3.adapters.mlx_adapter import MLXAdapter
    return MLXAdapter(config)
```

### Model Configs for `models.yml`

Add these configs:

```yaml
################
#### MLX Local ####
################

  # Primary: Fast MoE model (~60-70 tok/s, ~20GB on 64GB M2 Ultra)
  - name: "qwen3.5-35b-local"
    model_name: "mlx-community/Qwen3.5-35B-A3B-4bit"
    provider: "mlx"
    is_multimodal: false
    max_completion_tokens: 4096
    temperature: 0.7
    top_p: 0.9
    pricing:
      date: "2026-03-25"
      input: 0.0
      output: 0.0

  # Dense alternative: Higher quality per-token (~20-30 tok/s, ~18GB)
  - name: "qwen3-32b-local"
    model_name: "mlx-community/Qwen3-32B-4bit"
    provider: "mlx"
    is_multimodal: false
    max_completion_tokens: 4096
    temperature: 0.7
    pricing:
      date: "2026-03-25"
      input: 0.0
      output: 0.0

  # Reasoning: Deep chain-of-thought (~20-30 tok/s, ~18GB)
  - name: "qwq-32b-local"
    model_name: "mlx-community/QwQ-32B-4bit"
    provider: "mlx"
    is_multimodal: false
    max_completion_tokens: 8192
    temperature: 0.7
    top_p: 0.9
    pricing:
      date: "2026-03-25"
      input: 0.0
      output: 0.0

  # Lightweight: Maximum headroom (~30+ tok/s, ~14GB)
  - name: "qwen3.5-27b-local"
    model_name: "mlx-community/Qwen3.5-27B-4bit"
    provider: "mlx"
    is_multimodal: false
    max_completion_tokens: 4096
    temperature: 0.7
    pricing:
      date: "2026-03-25"
      input: 0.0
      output: 0.0
```

### Testing Phase 1

After implementation, verify with:
```bash
# Quick smoke test — single game, 10 actions
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config qwen3.5-35b-local \
  --max_actions 10 --offline --no-vision

# Should complete in ~1-2 minutes, zero API cost
```

**Critical:** The first run will download the model from HuggingFace (~20GB for 35B-A3B 4-bit). Subsequent runs load from cache instantly.

---

## 5. Phase 2: Experiment Runner (Overnight Batch)

### Overview

Create `src/arcagi3/autoresearch/runner.py` — a batch experiment runner that:
1. Reads an experiment queue (JSONL file or SQLite)
2. Runs each experiment (agent + config + game set)
3. Logs results with full provenance
4. Supports resume after interruption

### Experiment Database

Use SQLite for fast querying and dashboard integration.

**File:** `src/arcagi3/autoresearch/experiment_db.py`

```sql
CREATE TABLE experiments (
    id TEXT PRIMARY KEY,           -- exp_001, exp_002, ...
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    agent TEXT NOT NULL,           -- agent name
    config TEXT NOT NULL,          -- model config name
    game_ids TEXT NOT NULL,        -- comma-separated game IDs
    hypothesis TEXT,               -- what we're testing
    changes TEXT,                  -- what was modified (diff or description)
    -- Results (filled after completion)
    total_score REAL,
    avg_score REAL,
    total_actions INTEGER,
    total_cost REAL,
    per_game_results TEXT,         -- JSON blob
    verdict TEXT,                  -- accept, reject, baseline, partial
    notes TEXT,
    duration_seconds REAL,
    -- Provenance
    parent_experiment_id TEXT,     -- which experiment this builds on
    git_commit TEXT,               -- commit hash of agent code
    prompt_hash TEXT               -- hash of prompt templates for quick comparison
);

CREATE TABLE experiment_metrics (
    experiment_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    score REAL,
    actions_taken INTEGER,
    levels_completed INTEGER,
    cost REAL,
    duration_seconds REAL,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
```

### Batch Runner

**File:** `src/arcagi3/autoresearch/runner.py`

```python
"""
Batch experiment runner for ARC-AGI-3 autoresearch.

Usage:
    # Run all pending experiments
    python -m arcagi3.autoresearch.runner

    # Run a specific experiment
    python -m arcagi3.autoresearch.runner --experiment exp_005

    # Run overnight (will process queue until empty or interrupted)
    python -m arcagi3.autoresearch.runner --continuous

    # Resume after interruption
    python -m arcagi3.autoresearch.runner --resume
"""
```

Core logic:
1. Load experiment queue from SQLite
2. For each pending experiment:
   a. Set status to "running"
   b. Apply any code/prompt changes (git stash/apply pattern)
   c. Run the agent on all specified games (sequential, not parallel — one model in memory)
   d. Collect results
   e. Update SQLite with scores
   f. Set verdict (compare to parent experiment or baseline)
   g. Git commit if accepted
3. Continue to next experiment

### Experiment Queue Format

Experiments can be queued by:
1. **Manually** — Write to SQLite or append to JSONL
2. **Researcher agent** — Proposes and queues experiments automatically
3. **CLI** — `python -m arcagi3.autoresearch.queue add --hypothesis "..." --changes "..."`

### Queue CLI

```bash
# Add experiment to queue
uv run python -m arcagi3.autoresearch.queue add \
  --hypothesis "Adding loop detection reduces wasted actions" \
  --changes "Modified explore phase to track position history" \
  --games ls20,ft09,vc33 \
  --config qwen3.5-122b-local

# List queue
uv run python -m arcagi3.autoresearch.queue list

# Show experiment details
uv run python -m arcagi3.autoresearch.queue show exp_005

# Show best experiments
uv run python -m arcagi3.autoresearch.queue best --top 10
```

### Overnight Run Pattern

```bash
# Start overnight batch (runs until queue empty)
# Use nohup so it survives terminal close
nohup uv run python -m arcagi3.autoresearch.runner --continuous \
  > autoresearch.log 2>&1 &

# Monitor progress
tail -f autoresearch.log

# Or check dashboard (Phase 3)
open http://localhost:8050
```

---

## 6. Phase 3: Dashboard

### Overview

Web dashboard showing experiment results, graphs, and live progress. Starts as local-only, designed to be publishable later.

### Technology Choice

**Use Dash (Plotly)** — Python-native, reactive, no separate frontend build step. One file, instant graphing, auto-refresh.

Alternative: **FastAPI + HTMX** if you prefer a lighter dependency. But Dash is better for the graphing-heavy requirements.

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dashboard = [
    "dash>=2.14.0",
    "dash-bootstrap-components>=1.5.0",
    "plotly>=5.18.0",
]
```

### Dashboard Pages

**File:** `src/arcagi3/dashboard/app.py`

#### Page 1: Overview
- **Score timeline** — Line chart of avg_score over experiments (x=experiment_id, y=score)
- **Best score badge** — Current best experiment highlighted
- **Experiment count** — Total run, accepted, rejected
- **Running experiment status** — If one is active, show game/action progress

#### Page 2: Experiment Details
- **Table** of all experiments with columns: ID, hypothesis, score, actions, verdict, timestamp
- **Click to expand** — Shows per-game breakdown, full hypothesis, changes description, diff
- **Compare mode** — Select two experiments, show side-by-side results

#### Page 3: Per-Game Analysis
- **Game selector** (ls20, ft09, vc33, + any new games)
- **Score distribution** — Histogram of scores for that game across all experiments
- **Action efficiency curve** — Actions taken vs human baseline
- **Best strategies** — Which experiments scored highest on this game

#### Page 4: Live Monitor
- **Current experiment** — Which one is running
- **Action-by-action log** — Live feed of actions and frame changes
- **ETA** — Estimated time to experiment completion
- Auto-refreshes every 10 seconds

### Dashboard Implementation Notes

1. **Data source:** Read from SQLite `experiments.db` — Dash callbacks query on refresh
2. **Auto-refresh:** Use `dcc.Interval` component for periodic updates
3. **Public mode:** Add `--public` flag that binds to `0.0.0.0` instead of `localhost`
4. **Static export:** Add a "Download Report" button that generates a static HTML snapshot

### Running the Dashboard

```bash
# Start dashboard (local only)
uv run python -m arcagi3.dashboard.app

# Start dashboard (accessible on network)
uv run python -m arcagi3.dashboard.app --host 0.0.0.0 --port 8050

# Start dashboard alongside experiment runner
uv run python -m arcagi3.dashboard.app --port 8050 &
uv run python -m arcagi3.autoresearch.runner --continuous
```

---

## 7. Phase 4: Two-Agent Autoresearch Architecture

### Overview

The autoresearch loop uses two conceptual roles. These are NOT separate running processes — they're phases within a single orchestration script that uses LLM calls to drive decisions.

```
┌─────────────────────────────────────────────────┐
│                 Orchestrator                     │
│                                                  │
│  ┌──────────────┐      ┌──────────────────────┐ │
│  │  RESEARCHER   │      │      EXECUTOR        │ │
│  │               │      │                      │ │
│  │ • Read logs   │      │ • Apply changes      │ │
│  │ • Analyze     │─────→│ • Run experiment     │ │
│  │   failures    │      │ • Log results        │ │
│  │ • Propose     │←─────│ • Report outcome     │ │
│  │   next idea   │      │                      │ │
│  └──────────────┘      └──────────────────────┘ │
│                                                  │
│  Loop: researcher → executor → researcher → ...  │
└─────────────────────────────────────────────────┘
```

### The Researcher

**File:** `src/arcagi3/autoresearch/researcher.py`

The researcher is an LLM call (using a model config, can be the same local model or a different one) that:

1. **Reads experiment history** from SQLite
2. **Reads current agent code** (prompts, exploration logic)
3. **Analyzes patterns:**
   - Which games are hardest?
   - What types of changes improved scores?
   - What hasn't been tried?
   - Where are the biggest failure modes?
4. **Proposes the next experiment:**
   - A hypothesis (what we expect to improve)
   - Specific changes (prompt modifications, code changes, parameter tweaks)
   - Which games to test on
   - Expected impact

The researcher maintains a **prioritized idea list** in `experiments/ideas.md`:

```markdown
# Research Ideas (Auto-maintained)

## Priority 1 (Next to try)
- [ ] Add position tracking to detect navigation loops
  - Rationale: ls20 shows repeated actions with no grid changes
  - Expected: -30% wasted actions on ls20
  - Difficulty: Low (modify datastore tracking)

## Priority 2
- [ ] Implement grid region analysis (group cells by color/value)
  - Rationale: Agent sees raw grid but doesn't identify objects
  - Expected: Better hypothesis formation
  - Difficulty: Medium (add preprocessing step)

## Completed
- [x] Initial probe phase (baseline) → score: 0, actions: 45
- [x] Extended probe to 7 actions → score: 0, actions: 42
```

### The Executor

**File:** `src/arcagi3/autoresearch/executor.py`

The executor takes a proposed experiment and:

1. **Creates a git branch** for the experiment: `exp/exp_023_loop_detection`
2. **Applies changes** — either:
   - Prompt template modifications (edit `.prompt` files)
   - Python code modifications (edit agent `.py` files)
   - Configuration changes (edit `models.yml` or experiment params)
3. **Runs the benchmark** using the batch runner
4. **Evaluates results** against the parent experiment
5. **Decides verdict:**
   - **Accept** — Score improved. Merge branch to main. Update baseline.
   - **Reject** — Score regressed or no change. Delete branch.
   - **Partial** — Improved on some games, regressed on others. Keep branch for reference.
6. **Updates the experiment database**
7. **Reports back** to the researcher

### Mutation Strategies

**File:** `src/arcagi3/autoresearch/mutations.py`

Define categories of changes the system can make:

```python
MUTATION_CATEGORIES = {
    "prompt_engineering": {
        "description": "Modify prompt templates",
        "targets": ["prompts/system.prompt", "prompts/explore.prompt", "prompts/convert.prompt"],
        "examples": [
            "Add explicit step-by-step reasoning instructions",
            "Include grid analysis heuristics in system prompt",
            "Change JSON output format to include confidence scores",
        ],
    },
    "exploration_strategy": {
        "description": "Change how the agent explores",
        "targets": ["explorer_agent/agent.py"],
        "examples": [
            "Extend probe phase to test action combinations",
            "Add grid scanning (try actions at different positions)",
            "Implement random exploration fallback",
        ],
    },
    "state_tracking": {
        "description": "Improve how the agent tracks state",
        "targets": ["explorer_agent/agent.py"],
        "examples": [
            "Track position history to detect loops",
            "Build transition table: state + action → new state",
            "Count frame changes to measure progress",
        ],
    },
    "phase_transitions": {
        "description": "Change when phases switch",
        "targets": ["explorer_agent/agent.py"],
        "examples": [
            "Dynamic probe length based on grid complexity",
            "Add exploit phase when hypothesis confidence > threshold",
            "Re-enter probe when score stalls",
        ],
    },
    "memory_management": {
        "description": "Change what the agent remembers",
        "targets": ["explorer_agent/agent.py", "prompts/explore.prompt"],
        "examples": [
            "Structured memory: separate observations from hypotheses",
            "Sliding window with importance scoring",
            "Cross-level memory transfer",
        ],
    },
}
```

### Orchestration Script

**File:** `autoresearch.py` (repo root)

```python
"""
ARC-AGI-3 Autoresearch Orchestrator.

Two-phase loop:
1. RESEARCH: Analyze past experiments, propose next idea
2. EXECUTE: Implement changes, run benchmark, evaluate

Usage:
    # Start autoresearch loop (runs until interrupted)
    uv run python autoresearch.py --config qwen3.5-122b-local

    # Start with a specific idea (skip researcher)
    uv run python autoresearch.py --config qwen3.5-122b-local \
      --hypothesis "Add loop detection" \
      --changes "Track position history in datastore"

    # Research only (propose ideas, don't execute)
    uv run python autoresearch.py --research-only

    # Execute only (run queued experiments)
    uv run python autoresearch.py --execute-only
"""
```

Core loop:
```python
def autoresearch_loop(config, max_experiments=None):
    db = ExperimentDB("experiments/experiments.db")
    runner = ExperimentRunner(db)

    experiment_count = 0
    while max_experiments is None or experiment_count < max_experiments:
        # Phase 1: Research
        researcher = Researcher(config, db)
        proposal = researcher.propose_next_experiment()

        if proposal is None:
            logger.info("Researcher has no more ideas. Stopping.")
            break

        # Phase 2: Execute
        executor = Executor(config, db, runner)
        result = executor.run_experiment(proposal)

        # Update researcher's knowledge
        researcher.update_from_result(result)

        experiment_count += 1
        logger.info(f"Completed experiment {experiment_count}: {result.verdict}")
```

### Important: Researcher Should Never Stop

When one category of ideas is exhausted (e.g., all prompt engineering ideas tested), the researcher should **pivot to the next category**, not declare completion. The idea list is a starting point — the researcher should generate novel ideas based on experiment results, not just exhaust a fixed list.

If ALL categories seem exhausted, the researcher should:
1. Look for **combinations** of successful changes
2. Try **reversing** accepted changes to test if they're actually helping
3. Propose **architectural** changes (new agent design, different phase structure)
4. Search for **inspiration** from the research literature (SOAR, NVARC, Poetiq approaches)

---

## 8. Model Selection & Configuration

### Hardware: Mac Studio M2 Ultra 64GB

M2 Ultra with 64GB unified memory and ~800 GB/s bandwidth. After macOS overhead (~10GB), roughly **50-54GB available** for model weights + KV cache.

This rules out the large MoE models (122B, 235B) but opens up a fast-iteration strategy with smaller models.

### Recommended Model Stack

| Role | Model | Quant | Memory | Speed | When to Use |
|------|-------|-------|--------|-------|-------------|
| **Primary** | Qwen3.5-35B-A3B | 4-bit | ~20GB | ~60-70 tok/s | Default for all experiments (fastest) |
| **Dense alternative** | Qwen3-32B | 4-bit | ~18GB | ~20-30 tok/s | When MoE quality isn't enough |
| **Reasoning** | QwQ-32B | 4-bit | ~18GB | ~20-30 tok/s | Hard puzzles needing deep chain-of-thought |
| **Lightweight** | Qwen3.5-27B | 4-bit | ~14GB | ~30+ tok/s | Maximum headroom, fast experiments |

### Model Selection Strategy

Start with **Qwen3.5-35B-A3B** for all experiments. It's the sweet spot for 64GB:
- Extremely fast (~60-70 tok/s) because only 3B params are active per token
- 35B total params gives broader knowledge than a dense 3B model
- Only ~20GB means plenty of headroom for KV cache + OS
- MoE architecture designed for efficiency

The key insight: for ARC-AGI-3, the bottleneck isn't model intelligence — it's **agent strategy**. Preview competition results showed frontier models scored 0% while a CNN + simple RL scored 12.58%. A fast 35B MoE that lets you run 40+ experiments overnight will find better strategies than a slow 122B that runs 10.

If a strategy works with the 35B MoE, you can validate on **Qwen3-32B** (dense, higher quality per-token) or **QwQ-32B** (dedicated reasoning) to see if stronger models amplify the gains.

For cloud scaling: strategies discovered locally with 35B models can be tested with frontier API models (the repo already has adapters for Claude, GPT-5, Gemini) to see how far they scale.

### MLX Setup

```bash
# Install mlx-lm (in the project venv)
uv add mlx-lm

# Pre-download the primary model (do this before overnight run!)
python -c "from mlx_lm import load; load('mlx-community/Qwen3.5-35B-A3B-4bit')"

# Verify it works
mlx_lm.generate --model mlx-community/Qwen3.5-35B-A3B-4bit \
  --prompt "What is 2+2?" --max-tokens 50

# Pre-download dense alternative
python -c "from mlx_lm import load; load('mlx-community/Qwen3-32B-4bit')"

# Pre-download reasoning model
python -c "from mlx_lm import load; load('mlx-community/QwQ-32B-4bit')"
```

### Text Mode (Not Vision)

Local Qwen models are text-only (the VL variants are separate). Use `--no-vision` (or `--use_vision false`) to send grid frames as text matrices instead of images.

The framework already supports this — the Explorer agent's `_get_want_vision()` checks `model_config.is_multimodal`. Since MLX configs set `is_multimodal: false`, it will automatically use text grid mode.

Grid encoding matters. The current `grid_to_text_matrix()` outputs something like:
```
0 0 0 1 1 0
0 0 0 1 1 0
0 2 2 0 0 0
```

This is fine for small grids but verbose for 64x64. Consider adding a **compressed grid encoding** that groups repeated values:
```
Row 0: 3×0, 2×1, 1×0
Row 1: 3×0, 2×1, 1×0
Row 2: 1×0, 2×2, 3×0
```

This reduces token count significantly for sparse grids. Implement as an option in `utils/formatting.py`.

---

## 9. ARC-AGI-3 Autoresearch Strategy

### The Core Challenge

ARC-AGI-3 is hard because:
1. **No instructions** — Agent must discover rules through exploration
2. **Every environment is different** — No training, no memorization
3. **Action efficiency matters** — Wasted exploration costs score
4. **Frontier models scored 0%** in the preview — This is genuinely unsolved

### Strategy Evolution (What to Research)

#### Tier 1: Low-Hanging Fruit (First Week)

These are prompt/config changes that require no code modifications:

1. **Prompt engineering sweeps**
   - Systematic instructions for grid analysis
   - Chain-of-thought vs direct action
   - Few-shot examples of reasoning about grid changes
   - Confidence scoring in output

2. **Temperature/sampling sweeps**
   - Temperature: 0.3, 0.5, 0.7, 1.0
   - Top-p: 0.8, 0.9, 0.95
   - Repetition penalty: 1.0, 1.1, 1.2

3. **Probe phase variations**
   - Probe 5 actions vs 7 vs all available
   - Probe in different orders
   - Double-probe (try each action twice)

#### Tier 2: Agent Architecture (Weeks 2-3)

Code changes to the Explorer agent:

4. **State graph building**
   - Hash grid states, build a graph of state transitions
   - Detect loops (same state reached twice)
   - Find shortest path to unexplored states

5. **Object detection preprocessing**
   - Before LLM call, analyze grid for:
     - Connected components (objects)
     - Color distribution
     - Symmetry patterns
     - Edge detection
   - Feed structured analysis to LLM instead of raw grid

6. **Action sequencing**
   - Instead of choosing one action at a time, plan sequences
   - "Move right 3 times, then perform" as a single decision
   - Reduces LLM calls per level

7. **Multi-level transfer**
   - After completing level 1, carry forward:
     - Verified action effects
     - Confirmed rules
     - Successful strategies
   - But reset position-specific knowledge

#### Tier 3: Advanced Approaches (Weeks 3+)

These draw from competition research:

8. **Programmatic exploration**
   - Reduce LLM dependency for simple exploration
   - Use programmatic heuristics for systematic grid coverage
   - LLM only for hypothesis formation and goal identification

9. **Reinforcement learning elements**
   - Track which actions lead to score increases
   - Build a simple reward model from experience
   - Guided exploration based on past rewards

10. **Ensemble strategies**
    - Run multiple agent variants on same game
    - Take the best result
    - Identify which strategies work for which game types

### Metrics to Track

For each experiment, log:
- **Total score** (primary metric — sum of per-game scores)
- **Per-game score** (which games improved/regressed)
- **Total actions** (fewer = better)
- **Actions per level** (are we getting more efficient over levels?)
- **LLM calls** (how many inference calls per game)
- **Time per experiment** (throughput matters for overnight runs)
- **Token usage** (track context window utilization)

### Baseline Experiments (Run First)

Before any autoresearch, establish baselines:

```
exp_001: Explorer agent, qwen3.5-35b-local (MoE), all 3 games, 100 actions
exp_002: Explorer agent, qwen3-32b-local (dense), all 3 games, 100 actions
exp_003: ADCR agent, qwen3.5-35b-local, all 3 games, 100 actions
exp_004: Explorer agent, qwq-32b-local (reasoning), all 3 games, 100 actions
```

These establish: MoE vs dense quality, agent architecture impact, reasoning model benefit, and set the bar.

---

## 10. File Structure After Implementation

```
autoresearch-arcagi3/
├── CLAUDE.md                        # Updated with MLX + autoresearch commands
├── autoresearch.py                  # Main entry point for autoresearch loop
├── pyproject.toml                   # Updated with mlx + dashboard deps
│
├── src/arcagi3/
│   ├── adapters/
│   │   ├── mlx_adapter.py          # NEW: Local MLX inference
│   │   ├── provider.py             # (exists)
│   │   ├── open_ai.py              # (exists)
│   │   └── ...                     # (other adapters, unchanged)
│   │
│   ├── autoresearch/
│   │   ├── __init__.py
│   │   ├── runner.py               # Batch experiment runner
│   │   ├── researcher.py           # Idea generation (LLM-driven)
│   │   ├── executor.py             # Experiment execution + evaluation
│   │   ├── experiment_db.py        # SQLite experiment tracker
│   │   ├── mutations.py            # Agent modification strategies
│   │   └── queue_cli.py            # CLI for managing experiment queue
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── app.py                  # Dash application
│   │   └── layouts/
│   │       ├── overview.py         # Score timeline, summary stats
│   │       ├── experiments.py      # Experiment table + detail view
│   │       ├── games.py            # Per-game analysis
│   │       └── live.py             # Live experiment monitor
│   │
│   ├── explorer_agent/             # (exists, will be modified by autoresearch)
│   ├── adcr_agent/                 # (exists, unchanged)
│   ├── agent.py                    # (exists, unchanged)
│   ├── models.yml                  # Updated with MLX configs
│   └── ...
│
├── experiments/
│   ├── experiments.db              # SQLite database
│   ├── experiment_log.jsonl        # (exists, still used as human-readable log)
│   └── ideas.md                    # Researcher's idea list
│
├── docs/
│   ├── AUTORESEARCH.md             # Updated with new architecture
│   ├── MLX_SETUP.md                # NEW: MLX model setup guide
│   └── DASHBOARD.md                # NEW: Dashboard usage guide
│
└── results/                        # (exists, experiment results)
```

---

## 11. Implementation Order & Dependencies

### Phase 1: MLX Adapter (Do This First)
**Dependency:** None
**Files:** `mlx_adapter.py`, `models.yml` update, adapter registry update
**Test:** Run explorer agent on ls20 with `qwen3.5-122b-local`, verify it plays the game
**Estimated effort:** 2-3 hours

### Phase 2: Experiment Database + Batch Runner
**Dependency:** Phase 1 (needs working local inference)
**Files:** `experiment_db.py`, `runner.py`, `queue_cli.py`
**Test:** Queue 3 baseline experiments, run batch, verify SQLite has results
**Estimated effort:** 3-4 hours

### Phase 3: Dashboard
**Dependency:** Phase 2 (needs experiment data to display)
**Files:** `dashboard/app.py`, `dashboard/layouts/*.py`
**Test:** Start dashboard, view baseline experiment results with graphs
**Estimated effort:** 3-4 hours

### Phase 4: Two-Agent Autoresearch
**Dependency:** Phases 1-3
**Files:** `researcher.py`, `executor.py`, `mutations.py`, `autoresearch.py`
**Test:** Run 3 automated experiments, verify researcher proposes ideas, executor runs them
**Estimated effort:** 4-6 hours

### Quick Start After All Phases

```bash
# 1. Install dependencies
uv sync --extra mlx --extra dashboard

# 2. Download model (one-time, ~20GB)
python -c "from mlx_lm import load; load('mlx-community/Qwen3.5-35B-A3B-4bit')"

# 3. Run baselines
uv run python -m arcagi3.autoresearch.runner --baselines

# 4. Start dashboard
uv run python -m arcagi3.dashboard.app --port 8050 &

# 5. Start autoresearch loop (let it crank overnight)
uv run python autoresearch.py --config qwen3.5-35b-local --continuous
```

---

## 12. Appendix: Research References

### ARC-AGI-3 Competition

- **Official docs:** https://docs.arcprize.org/
- **GitHub toolkit:** https://github.com/arcprize/ARC-AGI
- **Agent examples:** https://github.com/arcprize/ARC-AGI-3-Agents
- **Benchmarking harness:** https://github.com/arcprize/arc-agi-3-benchmarking

### Winning Approaches (ARC-AGI-2, applicable strategies)

- **Poetiq** (54% SOTA) — Refinement loops. Meta-system that iteratively improves solutions. https://github.com/poetiq-ai/poetiq-arc-agi-solver
- **SOAR** (52% ARC-AGI-1) — Self-improving evolutionary program synthesis. Fine-tuned Qwen 32B available. https://github.com/flowersteam/SOAR
- **NVARC** (24% ARC-AGI-2, Kaggle winner) — Fine-tuned Qwen 4B + TRM. Fully local. https://github.com/1ytic/NVARC
- **E. Pang** (77% ARC-AGI-1, 26% ARC-AGI-2) — DreamCoder-inspired program synthesis. https://github.com/epang080516/arc_agi
- **Graph-Based Exploration for ARC-AGI-3** — https://arxiv.org/html/2512.24156v1

### Preview Competition Results

- **1st place:** StochasticGoose @ Tufa Labs — 12.58% score, CNN + simple RL
- **Frontier models scored 0%** — Pure LLM approaches don't work out of the box
- **Key finding:** RL/hybrid approaches dominate pure LLM approaches

### MLX / Local Models

- **mlx-lm:** https://github.com/ml-explore/mlx-lm
- **Qwen3.5 MLX collection:** https://huggingface.co/collections/mlx-community/qwen-35
- **Qwen3 MLX collection:** https://huggingface.co/collections/mlx-community/qwen3
- **SOAR fine-tuned Qwen 32B:** https://huggingface.co/julien31/Soar-qwen-32b (could be converted to MLX)

### Key Papers

- Chollet (2019): "On the Measure of Intelligence" — the original ARC paper
- ARC-AGI-2 Technical Report: https://arxiv.org/html/2603.06590v1
- ARC Prize 2025 Technical Report: https://arxiv.org/html/2601.10904v1
- TRM (Tiny Recursive Model): 7M param recursive transformer, 45% ARC-AGI-1

---

## Notes for Claude Code

### Environment Setup
- Python 3.12 via uv
- macOS 15+ required for MLX
- Model weights auto-download from HuggingFace on first use
- Games run locally via `arcengine` — no API key needed for development

### Testing
- Always test with `--offline` flag (no ARC server communication)
- Start with `--max_actions 10` for quick smoke tests
- Use `qwen3.5-35b-local` (MoE, fastest) for overnight runs, `qwen3-32b-local` (dense, smarter) for validation

### Key Constraints
- **One model in memory at a time** — Don't try to load multiple models simultaneously on 64GB. Switch models by restarting the process.
- **Text mode only** — MLX Qwen models are text-only. Always use `--no-vision` / `is_multimodal: false`.
- **Token limits** — Qwen3.5 supports 256K context but keep prompts reasonable. A 64x64 grid as text is ~4K tokens. With history and context, stay under 16K total.
- **Thinking mode** — Qwen3/3.5 support `/think` mode for extended reasoning. Consider enabling this for the explore phase but not the convert phase.

### Existing Code Quality
The repo is well-structured. The adapter pattern is clean. The `PromptManager` with Jinja2 templates is solid. Build on what exists — don't rewrite the framework.

### What NOT to Change
- Don't modify the `arcengine` / `arc-agi` library (it's a dependency, not our code)
- Don't change the `MultimodalAgent` base class interface (other agents depend on it)
- Don't remove existing provider adapters (API adapters are still useful for comparison)
- Don't change the game file format in `environment_files/`
