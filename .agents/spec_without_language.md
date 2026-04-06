# WORKING SPEC --- NO LANGUAGE (Pure Game Logic)

## Core Model

-   Grid-based territory control game
-   Each player controls 1 agent
-   Cells store (p1, p2)
-   Ownership:
    -   Dominated: higher value
    -   Black: (5,5), neutral

## Win / End Conditions

-   Win: ≥60% control
-   Draw: win condition unreachable (too many black cells)
-   Loss: time expires

## Movement + Interaction

-   Move 1 cell
-   No shared cells
-   Collision → execution loss
-   Moving outside board → execution reset

## Friction System

-   Empty: low cost
-   Own: free
-   Opponent: high cost
-   Black: very high cost

## Painting System

-   Increase paint on current cell
-   Max 5 per player
-   Black cells immutable

## Execution Model

-   Script runs twice per turn
-   Second run reacts to updated board

## Turn Structure

-   Alternating execution and rewrite phases

## Resources

-   Ops: execution budget
-   Words: script complexity budget

## Strategic Axes

-   Local vs Global
-   Efficiency vs Robustness
-   Planning Horizon
-   Prediction vs Adaptation

## Design Guarantees

-   No randomness
-   Requires opponent modeling
-   High emergent complexity
