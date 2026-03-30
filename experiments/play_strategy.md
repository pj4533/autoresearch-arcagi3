# Play Strategy

Generic approach for playing ANY ARC-AGI-3 game cold, with no prior knowledge.

## Core Philosophy

**Every game is solvable. Humans solve these. You can too.**

You approach each game knowing NOTHING about it. You figure out the rules through interaction. This is what makes you intelligent.

## Generic Approach (for any unknown game)

### 1. Observe
- `arc state --image` — LOOK at the frame carefully
- What do you see? Grid, objects, colors, patterns, dividers, borders?
- Is there an obvious goal state or target?
- What looks interactive vs structural?

### 2. Discover Available Actions
- Check what actions the game supports (movement? clicking? perform? undo?)
- Try each available action once and observe what changes
- Note: some games are click-only, some are movement-only, some are mixed

### 3. Hypothesize
- Based on what you observed, what type of game is this?
  - Puzzle (arrange/sort/match something)
  - Navigation (move to a goal)
  - Pattern completion (fill in missing parts)
  - Transformation (change the grid to match a target)
- What's the goal? What does "solving" look like?

### 4. Test
- Take ONE deliberate action based on your hypothesis
- Observe the result — did it confirm or contradict your theory?
- If the score changed, GREAT — what did you just do? Do more of that.
- If nothing useful happened, update your hypothesis

### 5. Solve
- Once you understand the mechanic, execute efficiently
- Don't waste actions exploring when you already know what to do
- Fewer actions = better score

### 6. When Stuck
- Try something COMPLETELY different — don't repeat failed approaches
- If clicking didn't work, try movement. If movement didn't work, try perform.
- Look at the frame from a different angle — what are you missing?
- After 3 failed attempts on a game, move on to a different game

## General Heuristics

- Small colorful objects are often interactive (buttons, toggles)
- Large uniform regions are often background/structural
- Symmetry or patterns often indicate the goal state
- If an action changes many cells, it's probably important
- Score increases = you did something right. Do more of whatever that was.
- GAME_OVER = you did something wrong. Avoid whatever caused that.
- Click coordinates (0-127) map 1:1 to the 64x64 grid, NOT 2:1. Click x=40 targets grid column 40.
- Analyze the grid data numerically to find patterns — dotted lines, missing elements, paired objects.
- When a massive cell change occurs (>100 cells), it often signals level completion or major state change.
- "No changes" from a click means the action was INVALID (not even counted). Use this to identify clickable vs non-clickable areas.
- For click-only games: map out ALL non-background pixels first, then identify patterns (lines, pairs, clusters) before clicking.
- For known game types, replay efficiently: sb26 level 1 takes 9 actions (4 select+paint pairs + perform).
- "Perform" meaning varies by game: submit answer (sb26), switch control (re86), or other.
- When a game has multiple objects, movement might only affect ONE of them. Try perform to switch.
- For cross-alignment games (re86): find row R and col C where all dots of a color lie on R or C.
- For diamond shapes (re86 level 2): center at (Cr,Cc) where |dot_r - Cr| + |dot_c - Cc| = radius for ALL dots. Solve system of equations.
- re86 level 2 has 3 shapes (plus, diamond, X-cross) needing ~14 moves each = ~42 total. With 20 actions after level 1, need more efficient movement or different approach.
- Many games (lf52, s5i5, tn36) don't respond to obvious actions. May need very specific click coordinates or a mechanic not yet discovered.
