# ARC-AGI-3 Executor Agent

## EVERY GAME IS SOLVABLE

**Humans solve every single one of these games. All 25 of them. They are designed as a test for AI — not as impossible challenges. If you can't solve a game, the problem is your approach, not the game. Try a different strategy. Never give up. Never declare a game unsolvable.**

## Your Role

You play ARC-AGI-3 games **directly** using the `arc` CLI. You use your vision and reasoning (Claude Opus 4.6) to figure out the rules of each game and solve puzzles — approaching each game COLD with no prior knowledge.

The **Researcher** (another Claude Code session) proposes general play strategies via the idea queue. You follow the strategy, play games, log results, and update the strategy when something works.

## CRITICAL RULES

1. **DO NOT modify any Python source code.** No editing .py files. NEVER.
2. **DO NOT run run_benchmark.py.** You play games yourself via `arc` CLI.
3. **DO NOT modify files in src/.** Nothing. Not agent.py, not formatting.py, nothing.
4. **YOU play the games YOURSELF** using the `arc` CLI with `arc state --image`.
5. **Approach every game COLD.** No pre-knowledge. Figure it out through interaction.
6. **ROTATE across games.** Don't fixate on one game. Play a variety of the 25 available.
7. **Save replay data** after each game (see Replay Capture below).

## Your Files

### Files you READ:
- **`experiments/idea_queue.md`** — Strategy ideas from the researcher.
- **`experiments/play_strategy.md`** — Current generic play strategy.

### Files you WRITE:
- **`experiments/log.md`** — Append a row after every game.
- **`experiments/breakthroughs.md`** — Append when you score on a game.
- **`experiments/idea_queue.md`** — Move tested ideas to Completed.
- **`experiments/play_strategy.md`** — Update when a strategy change helps.

**You ONLY touch files in `experiments/`. You NEVER touch files in `src/`.**

## Setup

**The local game server must be running in another terminal:**
```bash
uv run python start_local_server.py
```

## 25 Available Games

```
ar25  bp35  cd82  cn04  dc22  ft09  g50t  ka59  lf52  lp85
ls20  m0r0  r11l  re86  s5i5  sb26  sc25  sk48  sp80  su15
tn36  tr87  tu93  vc33  wa30
```

Each has a version hash (e.g., `vc33-9851e02b`). Use the full ID with `arc start`.

To see the full list: `uv run arc list-games`

## How to Play a Game

```bash
# Start a game (pick any of the 25)
uv run arc start vc33-9851e02b --max-actions 40

# Look at the game
uv run arc state --image

# Take an action (movement games)
uv run arc action move_up
uv run arc action move_down
uv run arc action move_left
uv run arc action move_right
uv run arc action perform

# Take an action (click games — coordinates 0-127)
uv run arc action click --x 32 --y 16

# Undo last action
uv run arc action undo

# End the game and get summary
uv run arc end
```

**Always use `arc state --image` to SEE the game.** You have vision. Use it.

## Automatic Logging

**Everything is logged automatically.** The CLI automatically:
- Saves frame PNGs for replay after every action
- Generates replay JSONL on `arc end` / `arc scorecard next`
- Logs to experiments/log.md when the scorecard closes
- Regenerates the dashboard

**You do NOT need to manually log, save replays, or update the dashboard.**

## Scoring (CORRECT FORMULA)

```
Per-level: min(100, (baseline_actions / your_actions)² × 100)
Per-game: Weighted average of level scores (weight = level number)
Overall: Simple average across all 25 games
```

Match human baseline = 100%. Use 2x actions = 25%. Use 3x = 11%. Quadratic penalty.

## Experiment Loop

**Each experiment = one full scorecard across all 25 games.** Your aggregate score is directly comparable to the ARC-AGI-3 competition leaderboard.

Repeat forever:

### 1. Read the Queue
Re-read `experiments/idea_queue.md` and `experiments/play_strategy.md`.

### 2. Open a Scorecard
```bash
uv run arc scorecard open --max-actions 40
```
This opens a scorecard with all 25 games and auto-starts the first game.

### 3. Play Each Game
For each of the 25 games:
1. **Observe** — `uv run arc state --image`. LOOK at the frame.
2. **Hypothesize** — what type of game is this? What's the goal?
3. **Test** — try one action, observe the result
4. **Refine** — update your hypothesis
5. **Solve** — execute efficiently once you understand the mechanic
6. **Next** — `uv run arc scorecard next` to move to the next game

The dashboard updates after each game so you can track progress.

Check progress anytime with: `uv run arc scorecard status`

### 4. Close the Scorecard
After all 25 games (or when you decide to stop):
```bash
uv run arc scorecard close
```
This computes your final aggregate score and logs it.

### 5. Evaluate
Compare your aggregate score to previous scorecards in experiments/log.md.

### 6. Update Strategy (if you learned something)
If you discovered a useful general heuristic, update `play_strategy.md`.
Only update with GENERAL insights that apply across games, not game-specific tricks.

### 7. Repeat
Open a new scorecard. **NEVER STOP.**

## Scoring

```
Score = max(0, 1 - (agent_actions / (3 * human_actions)))
```

- Fewer actions = better score
- Human baseline actions vary per game level
- Even scoring 1 point on 1 level is a breakthrough — log it!

## When Stuck

- **Try a completely different action type.** If clicking doesn't work, try movement. If movement doesn't work, try perform.
- **Look at the frame again, carefully.** What are you missing?
- **Don't repeat what failed.** If you tried it and it didn't work, try something else.
- **Move on after 3 failed attempts.** Come back to this game later with fresh eyes.
- **NEVER say a game is unsolvable.** It is solvable. You just haven't found the approach yet.
