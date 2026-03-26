"""
Mutation strategy definitions for ARC-AGI-3 autoresearch.

Defines categories of agent modifications the researcher can propose.
Each category lists target files and example changes.
"""

MUTATION_CATEGORIES = {
    "prompt_engineering": {
        "description": "Modify prompt templates to change how the LLM reasons about games",
        "targets": [
            "src/arcagi3/explorer_agent/prompts/system.prompt",
            "src/arcagi3/explorer_agent/prompts/explore.prompt",
            "src/arcagi3/explorer_agent/prompts/convert.prompt",
        ],
        "examples": [
            "Add explicit step-by-step reasoning instructions",
            "Include grid analysis heuristics in system prompt",
            "Change JSON output format to include confidence scores",
            "Add few-shot examples of reasoning about grid changes",
            "Instruct the model to identify objects/patterns before choosing actions",
            "Add explicit hypothesis-testing instructions",
        ],
    },
    "exploration_strategy": {
        "description": "Change how the agent explores game environments",
        "targets": [
            "src/arcagi3/explorer_agent/agent.py",
        ],
        "examples": [
            "Extend probe phase to test action combinations (e.g., up then right)",
            "Add grid scanning (try actions at different positions)",
            "Implement random exploration fallback when stuck",
            "Try each action twice to detect non-deterministic effects",
            "Systematic boundary exploration (test actions near grid edges)",
        ],
    },
    "state_tracking": {
        "description": "Improve how the agent tracks and uses game state",
        "targets": [
            "src/arcagi3/explorer_agent/agent.py",
        ],
        "examples": [
            "Track position history to detect navigation loops",
            "Build transition table: state + action -> new state",
            "Count and compare frame changes to measure progress",
            "Hash grid states to detect revisited states",
            "Track color distribution changes across actions",
        ],
    },
    "phase_transitions": {
        "description": "Change when and how the agent switches between phases",
        "targets": [
            "src/arcagi3/explorer_agent/agent.py",
        ],
        "examples": [
            "Dynamic probe length based on grid complexity",
            "Add exploit phase when hypothesis confidence > threshold",
            "Re-enter probe when score stalls for N actions",
            "Switch to random exploration after N failed hypotheses",
            "Implement a re-probe phase after level completion",
        ],
    },
    "memory_management": {
        "description": "Change what the agent remembers and how it uses memory",
        "targets": [
            "src/arcagi3/explorer_agent/agent.py",
            "src/arcagi3/explorer_agent/prompts/explore.prompt",
        ],
        "examples": [
            "Structured memory: separate observations from hypotheses",
            "Sliding window memory with importance scoring",
            "Cross-level memory transfer (carry knowledge between levels)",
            "Compress old observations into summaries",
            "Track which actions led to score changes",
        ],
    },
    "preprocessing": {
        "description": "Add preprocessing steps before LLM calls",
        "targets": [
            "src/arcagi3/explorer_agent/agent.py",
        ],
        "examples": [
            "Object detection: identify connected components by color",
            "Symmetry detection in grid patterns",
            "Edge detection to identify boundaries",
            "Grid differencing to highlight changes between frames",
            "Compressed grid encoding to reduce token usage",
        ],
    },
    "action_sequencing": {
        "description": "Plan multi-step action sequences instead of single actions",
        "targets": [
            "src/arcagi3/explorer_agent/agent.py",
            "src/arcagi3/explorer_agent/prompts/explore.prompt",
        ],
        "examples": [
            "Plan 3-action sequences instead of single actions",
            "Implement macro actions (e.g., 'move right 3 times')",
            "Queue actions and execute without LLM call for each",
            "Conditional action plans (if X then do Y, else Z)",
        ],
    },
}

# Tier ordering for the researcher to prioritize
TIER_ORDER = [
    # Tier 1: Low-hanging fruit (prompt/config only)
    "prompt_engineering",
    # Tier 2: Agent architecture
    "exploration_strategy",
    "state_tracking",
    "phase_transitions",
    "memory_management",
    # Tier 3: Advanced
    "preprocessing",
    "action_sequencing",
]


def get_mutation_summary() -> str:
    """Get a formatted summary of all mutation categories for the researcher prompt."""
    lines = []
    for cat_name in TIER_ORDER:
        cat = MUTATION_CATEGORIES[cat_name]
        lines.append(f"\n## {cat_name}: {cat['description']}")
        lines.append(f"Target files: {', '.join(cat['targets'])}")
        lines.append("Example changes:")
        for ex in cat["examples"]:
            lines.append(f"  - {ex}")
    return "\n".join(lines)
