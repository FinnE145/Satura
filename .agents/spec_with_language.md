# WORKING SPEC --- WITH LANGUAGE (Implementation-Oriented)

## Core Model

-   Turn-based competitive programming strategy game on a square grid
-   Each player controls 1 agent
-   Cells store (p1, p2) paint values ∈ \[0--5\]
-   Ownership:
    -   Dominated: higher paint
    -   Black: (5,5), unowned, immutable

## Win / End Conditions

-   Win: ≥60% of total cells dominated, checked at end of execution
-   Draw: win condition unreachable (too many black cells)
-   Loss: time runs out

## Agent + Movement

-   Agents cannot occupy same cell
-   Moving into opponent → reset
-   Moving outside board → halt

### Friction (movement cost)

-   if p1+p2 == 0 → 1
-   if p1+p2 == 10 → 20
-   else → 2 \* opponent_paint

## Actions + Costs

-   move(dir): friction
-   paint(n): 2n
-   get_friction: 1
-   has_agent: 1
-   my_paint / opp_paint: 1
-   other logic: 0

## Paint Rules

-   n \> 0 required
-   cannot exceed capacity → reset
-   black cell → reset

## Execution Outcomes

-   Complete: commit
-   Halt: partial commit
-   Reset: full rollback

## Turn Cycle

-   Scripts run twice per turn
-   exec2 runs even if exec1 fails
-   exec2 reset only undoes exec2
-   functions persist

## Resources

-   Ops: fixed per execution
-   Words: accumulate, spent on deploy

## Language Model

### Word Cost Rules

-   keywords, operators, \$, board ops, call count
-   names/literals free

## Types

-   int, float, direction, location, list, boolean, NULL

## Variables

-   Global default
-   Functions local scope
-   Lists passed by copy

## Built-ins

-   \$directions, \$locations
-   \$ops_remaining, \$op_limit

## Control Flow

-   if / elif / else
-   for, while, halt

## Functions

-   def / call
-   persist across match

## Lists

-   list(), push, pop, index, length

## Board API

-   move, paint, get_friction, has_agent, my_paint, opp_paint
-   get_friction / has_agent / my_paint / opp_paint return NULL when called with an out-of-bounds location (op cost still deducted)
-   NULL can only be tested with == and !=; any other use is a runtime halt

## Strategic Constraints

-   Local sensing only
-   No pathfinding primitives
-   Must manage ops manually
