# Breakthroughs

Games where the agent scored > 0. Each entry explains what strategy worked.

## su15 — Level 1 Completed (Exp 010)
- **Game type**: Click-only puzzle. Move a colored square along a dotted line to reach a target circle.
- **Mechanic**: A diagonal line of green dots connects a purple square (bottom-left) to a blue circle (top-right). Click coordinates map 1:1 to the 64x64 grid. Clicking on each dot along the line "moves" the purple square to that position. Must click sequentially — can't skip ahead.
- **Strategy that worked**: Identify the dotted line path (each dot at +2 cols, -2 rows from previous). Click each waypoint in order from start to destination. The purple square moves to each clicked position, consuming the dot.
- **Key insight**: The 0-127 click coordinate range maps 1:1 to the 64x64 grid (not 2:1). Non-background pixels need careful grid analysis to locate.
- **Level 2**: Different mechanic — scattered paired dots instead of a line. Clicking one dot changes it to a new color and removes its pair. Didn't solve in remaining actions.

## sb26 — Level 1 Completed (Exp 012)
- **Game type**: Color matching puzzle. Paint dots in a center box to match a target color sequence.
- **Mechanic**: Top row shows N colored swatches (the target order). Bottom row has N selectable color buttons. Center has a bordered box with N dots (initially red/unset). Click a bottom square to SELECT a color (gets a black border), then click a center dot to PAINT it. "Perform" submits the answer.
- **Strategy that worked**: Read the top swatch order (L to R), then paint each dot in order matching the top sequence. Level 1 had 4 colors (9, 14, 11, 15).
- **Key insight**: Select color FIRST (bottom), then click target dot (center). Perform submits. The target order matches the top color swatch sequence left to right.
- **Level 2**: 7 colors, two nested boxes. Painted dots in the top order but got the wrong assignment — possibly needed to handle the green frame in the top box differently.

## re86 — Level 1 Completed (Exp 013)
- **Game type**: Cross alignment puzzle. Position two colored crosses so their lines pass through all matching colored dots.
- **Mechanic**: Two crosses (teal/11 and blue/9) can be moved with arrow keys. "Perform" switches which cross is controlled. Small 3x3 dots with matching colored centers are scattered around. Each cross must be positioned so its horizontal AND vertical lines pass through all dots of its color.
- **Strategy that worked**: Find all dot positions, solve for the cross center where row R covers some dots and column C covers the rest. For 4 dots at (r1,c1), (r1,c2), (r2,c1), (r2,c2), the cross center is (r1,c1) or similar overlapping solution.
- **Key insight**: Each arrow move shifts the active cross by 3 pixels. "Perform" switches control between crosses (not submit). After both crosses are positioned correctly, the last move auto-completes the level.
