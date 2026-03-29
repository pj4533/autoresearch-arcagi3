# Play Strategy

This file describes HOW the executor (Claude Code) should play each game.
The researcher proposes changes to this strategy. The executor follows it.

## General Approach

1. Start the game with `arc start <game_id> --max-actions 40`
2. View the initial frame with `arc state --image`
3. Analyze what you see — look for patterns, objects, interactive elements
4. Form a hypothesis about what the game wants
5. Take an action to test your hypothesis
6. View the result with `arc state --image`
7. Update your understanding based on what changed
8. Repeat until you solve the level or run out of actions
9. End with `arc end`

**Be efficient.** The scoring formula rewards fewer actions. Don't click randomly — think first, then act deliberately.

## VC33 Strategy

VC33 is a click-only puzzle game. What we know:
- Only ACTION6 (click) is available
- Color 9 objects are interactive (produce 265 cell changes when clicked)
- Wrong clicks consume lives → GAME_OVER
- It's a balance/sorting puzzle — buttons adjust boundaries
- Level 1: solved by trial-and-lock approach (baseline: 6 human actions)
- Level 2: solved similarly (baseline: 13 human actions)
- Level 3: vertical bar chart layout with 8 buttons, unsolved

**Approach:**
1. Look at the frame image carefully
2. Identify the puzzle layout — what needs to change to match a goal?
3. Look for buttons/interactive elements (small colored objects)
4. Try clicking one button and observe the effect
5. Based on the effect, form a theory about the mechanic
6. Click strategically to solve the puzzle

## LS20 Strategy

LS20 is a navigation game with latent/hidden state.
- Actions: move_up, move_down, move_left, move_right, perform
- Every move creates a new state (enormous state space)
- Has health drain — agent dies if it takes too many actions
- Baseline actions per level: 29, 41, 172, 49, 53, 62, 82

**Approach:**
1. Look at the frame image
2. Identify any goal indicators, paths, or objectives
3. Try to navigate purposefully, not randomly
4. Use perform action when you think you've reached a goal
5. Be conservative — health drain means wasted moves kill you

## FT09 Strategy

FT09 appears broken in the local game version (9ab2447a). No actions produce meaningful frame changes. **Skip this game for now** — focus on vc33 and ls20.
