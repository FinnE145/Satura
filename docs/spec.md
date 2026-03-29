# SATURA
### Game Design Specification
*A competitive programming strategy game*

**Draft — Work In Progress**

---

# 1. Key Tenets

These principles define the design philosophy behind Satura and should apply to any game built in this tradition. They are the filter against which every mechanic must be evaluated.

## 1.1 Code Is Irreplaceable

The scripting system must not be a friction layer over an action that could otherwise be performed with a mouse, keyboard, or any other direct input. If a player could achieve an equivalent result by clicking cells or selecting options from a menu, the code is merely a cumbersome interface — not a game mechanic.

Code becomes irreplaceable when the goal of a script cannot be fully specified at write time. The script must contain conditional logic that resolves against future board state that the player cannot fully predict. A move is a single committed action. A script is a policy — a decision procedure that will execute in contexts that do not yet exist.

## 1.2 Game Strategy and Code Strategy Are Coupled But Untransferable

No single system — human, LLM, or algorithm — should be able to dominate both the game-side and code-side decisions simultaneously. Specifically:

- A program that can predict board states well enough to identify optimal sub-goals has no mechanism for translating those sub-goals into efficient scripts.
- An LLM that can write efficient, well-structured code has no model of the board state three turns out, and cannot determine whether a given abstraction is worth defining.
- These two competencies cannot be pipelined. A board state description is not a code-writing prompt. A code snippet is not a game tree node. The interface between them exists only in the player's mind.

This means the game's depth is irreducibly human. Experience, pattern recognition, and the ability to hold strategic intent and code economics in mind simultaneously are the core skills — not programming knowledge, and not game theory alone.

## 1.3 Not Deterministic, Not Solvable, Not Random

The game must resist algorithmic domination without introducing luck. These are separate requirements:

- **No luck:** Starting positions are fixed and symmetric. No random elements exist anywhere in the game.
- **Not deterministic:** The optimal action at any point depends on what the opponent will do, which depends on what you will do. This circular dependency is irreducible — it cannot be computed without simulating both players simultaneously, which requires knowing both players' scripts.
- **Not solvable:** The game's future state is a dynamical system whose behavior emerges from the interaction of two competing programs. Predicting it requires simulation. Simulation requires knowing both scripts. Both scripts are the unknown. No closed-form solution or known-good heuristic dominates.

This is distinct from complexity-by-complication. The game should have simple rules. The unsolvability must emerge from the interaction of simple things — not from rule volume.

## 1.4 Sub-Goals Must Change Turn By Turn

It must never be correct to write the same script every turn, nor to aim the script directly at the win condition. The player must:

- Read the global board state and identify the correct strategic sub-goal for this moment.
- Translate that sub-goal into a script that pursues it locally.
- Recognize when that sub-goal has been achieved or is no longer viable, and adapt.

This means the game must present genuinely different situations that call for genuinely different code. Expansion, reinforcement, blocking, poisoning, and repositioning must require different logic — different functions, different primitives, different structures — so that a library built for one purpose does not serve another.

## 1.5 Code Reuse Is a Strategic Resource

The word limit means that writing a function definition is an investment. Calling it costs one word. Whether the investment pays off depends on how often you'll call it, which depends on how the board will evolve, which depends on both players' strategies.

This creates a long-horizon planning problem that no code-writing tool can solve without understanding the game. An LLM can recognize when code could be abstracted. It cannot know whether that abstraction will be used enough to justify its cost, because that requires predicting the game state across multiple turns of unknown opponent behavior.

## 1.6 Local Execution, Global Value

Scripts operate locally — agents see only their current cell and immediate neighbors. But the value of any local action is determined by global board topology that only the player can read.

This is the structural guarantee that code cannot replace strategic thinking. The script executes locally. The judgment of what to execute is global. Only the player bridges this gap.

## 1.7 Simple Rules, Near-Infinite Depth

Like chess, the rules must be learnable in minutes. The depth must be nearly unlimited. Complexity should emerge from the interaction of simple mechanics, not from rule volume or multiple resource systems. Every mechanic added must justify itself by creating meaningful strategic decisions, not by adding surface variety.

---

# 2. Game Rules

## 2.1 The Board

The board is a square grid of cells. All cells begin blank. Board dimensions are determined by game mode and are always symmetric.

| Term | Definition |
|---|---|
| Cell state | Each cell stores two paint values: p1 (0–5) and p2 (0–5), one per player. All cells begin at (0, 0). |
| Blank cell | A cell where both p1 = 0 and p2 = 0. |
| Dominated cell | A cell where one player's paint strictly exceeds the other's. That player owns it. |
| Black cell | A cell where p1 = 5 and p2 = 5. Owned by nobody. Cannot be painted further. |

## 2.2 Agents

Each player controls one agent. Agents begin at fixed starting positions on opposite sides of the board, offset toward the center. For an N×N board, agents start at approximately (N/4, N/4) and (3N/4, 3N/4).

- Agents are always visible to both players.
- No two agents may occupy the same cell at the same time.
- If a moving agent attempts to enter a cell occupied by the opponent's agent, the moving agent's script resets (see Section 2.5).
- An agent that cannot leave its current cell in any direction within its op budget is considered trapped (see Section 2.6).

## 2.3 Paint and Friction

Agents paint cells by calling the `paint()` function. Paint values are integers from 0 to 5 per player per cell.

### Friction Formula

Friction determines how many ops it costs to move into a cell. It is computed as follows:

```
get_friction(cell):
    if cell.p1 + cell.p2 == 0:  return 1    // blank cell
    if cell.p1 + cell.p2 == 10: return 10   // black cell
    return opponent_paint(cell)              // default case
```

For Player 1, opponent_paint = p2. For Player 2, opponent_paint = p1. Key properties of this formula:

| Cell state (p1, p2) | Friction for Player 1 |
|---|---|
| (5, 0) — your territory | 0 — movement is free on your own paint |
| (0, 0) — blank | 1 — small cost to expand |
| (0, 3) — lightly contested | 3 |
| (4, 5) — nearly black | 5 |
| (5, 5) — black | 10 — near-impassable, but pushable |

> Moving through your own paint is free. All friction cost comes from opponent paint and black cells. Black cells cost exactly double a maximally contested cell, making mutual aggression self-punishing.

### Paint Rules

- Painting a cell costs ops equal to the amount painted. `paint(3)` costs 3 ops.
- You may paint as much as you choose in a single call, up to the cell's remaining capacity.
- Attempting to paint more than the cell can accept (e.g. your paint is already 5, or the total would exceed 10) is a game state error and resets the turn.
- Painting is a separate action from movement. Moving through a cell does not automatically paint it.
- You may not paint a black cell. Attempting to do so is a game state error and resets the turn.

## 2.4 Operations (Ops)

Each script execution has an op budget. Board-interacting operations consume ops. Exceeding the op budget is a game state error and resets the entire turn execution.

| Operation | Op cost |
|---|---|
| `move(dir)` | Costs `get_friction(target_cell)` ops |
| `paint(num)` | Costs `num` ops |
| `get_friction(loc)` | 1 op |
| `has_agent(dir)` | 1 op |
| `my_paint(loc)` | 1 op |
| `opp_paint(loc)` | 1 op |
| All other operations | 0 ops (internal computation is free) |

> Op limit is TBD and subject to playtesting. It may vary by game mode. See Section 5.1 (Undecided).

## 2.5 Turn Reset vs. Halt

Script executions can end in three ways:

| Outcome | Effect |
|---|---|
| Normal completion | Script runs to end. All actions taken stand. |
| Halt | Script stops early via `halt` keyword or runtime error. All actions taken up to that point stand. |
| Reset | Entire execution is undone. Board returns to its state before the execution began. Words are still spent. |

Conditions that cause a **reset:**
- Op budget exceeded
- Agent collides with opponent agent (moving agent resets)
- Painting a black cell
- Painting more than a cell can accept

Conditions that cause a **halt:**
- `halt` keyword executed
- Runtime error (type mismatch, empty pop, bad index, division by zero, non-boolean condition, `paint(0)` or `paint(negative)`, etc.)

Syntax errors are caught at compile time before the turn begins — they are not a runtime condition.

## 2.6 Win, Loss, and Stalemate

### Win Condition

A player wins when they dominate 60% or more of total cells on the board simultaneously at any point during turn resolution. A cell is dominated when one player's paint strictly exceeds the other's.

> **Alternative win condition (decide during playtesting):** First player to dominate 80% of non-black cells. This adjusts dynamically with black cell accumulation but may incentivize generating black cells intentionally to shrink the denominator. The 60% total threshold is the primary design.

Black cells are never counted toward either player's total. They reduce the maximum achievable score for both players.

### Stalemate

A stalemate occurs under either of these conditions:

- **Trapped agent:** A player's agent cannot leave its current cell in any valid direction given the current op budget and opponent agent position. The game ends immediately as a draw.
- **Unreachable threshold:** Sufficient black cells have accumulated that neither player can mathematically reach the win threshold. The game ends as a draw.

> Oscillating agents (moving back and forth between two cells indefinitely) are not explicitly banned by rule. However, this behavior is self-defeating since the player accumulates no score and burns their execution. It is considered a degenerate strategy, not a rules violation.

### Time Loss

A player who runs out of game time loses. Time management is discussed in Section 3.2.

> Maximum turn count or game time cap is TBD. See Section 5.1 (Undecided).

---

# 3. Scripting — Design Guide

This section describes how scripting works as a game system. The specific language syntax and primitives are in Section 4.

## 3.1 Words and the Word Bank

Every script has a word count. Words are the primary resource governing script complexity. The word bank works as follows:

- Words accumulate in real time at a constant rate (tentatively 1 word per second) for both players equally.
- Accumulation begins for a player at the moment the execution phase immediately preceding their write phase ends.
- Deploying a script spends words equal to the script's word count. Words cannot be refunded.
- If a script resets or halts, the words are still spent — deployment is the point of commitment, not successful completion.
- There is no cap on the word bank. Words accumulate indefinitely, but game time is finite (chess-style clock), so hoarding words is naturally self-limiting.
- A player may not deploy a script if their bank does not contain enough words for it.

> Word accumulation rate is TBD and may vary by game mode. See Section 5.1 (Undecided).

## 3.2 Time Control

Satura uses a chess-style game clock. Each player has a total time budget for the entire game. Time spent writing, thinking, and waiting all counts against this budget.

- A player's clock runs during their write phase and stops when they deploy their script.
- Players may begin drafting scripts at any time, including during their opponent's execution phases. The script editor is always accessible.
- The word bank is the pacing mechanism. Writing earlier does not grant more words — only clock time determines accumulation.
- A player who deploys early (before their clock runs out) earns no bonus, but preserves clock time for future turns.
- A player who runs out of clock time loses immediately, regardless of board state.

> Because players can write scripts at any time, there is no fairness concern about writing during an opponent's turn. Both players see the same board, accumulate words at the same rate, and their clock only runs during their own write phase.

## 3.3 Turn Structure and Execution Order

Each player's script executes twice per cycle: once intentionally (exec1) and once reactionary (exec2). The execution order is designed so that:

- Each player's exec1 is written against a known board state.
- Each player's exec2 runs on a board state their opponent has already modified — specifically to disrupt it.
- After watching exec1, a player writes a new script whose own exec1 is intended to sabotage the opponent's exec2.

Full cycle:

```
P1 exec1         ← P1's intentional execution on known board state
P2 exec1         ← P2's intentional execution on known board state
--- Both players observe each other's exec1 ---
P1 writes        ← P1 observes P2's exec1, drafts sabotage script
P1 exec1'        ← P1's new script's first run; intended to disrupt P2's exec2
P2 exec2         ← P2's OLD script runs on a board P1 just modified
--- P2 observes full picture ---
P2 writes        ← P2 observes P1's full behavior, drafts their sabotage script
P2 exec1'        ← P2's new script's first run; intended to disrupt P1's exec2
P1 exec2         ← P1's OLD script runs on a board P2 just modified
--- Cycle repeats ---
P1 writes...
```

Key rules governing this cycle:

- Exec1 and exec2 always run the same script. A script cannot be modified between its two executions.
- If exec1 resets or halts, exec2 still runs. It runs from the start of the script, against whatever board state exists at that point (which, after a reset, is the pre-exec1 state).
- If exec2 resets, only exec2 is undone. The board returns to its state immediately before exec2 began.
- Function definitions persist for the entire match, across all rewrites and both execution phases.

## 3.4 Strategic Tradeoffs in Scripting

The scripting system is designed to present genuine, non-trivial decisions on every turn. These are the primary tradeoffs a player must navigate:

### Op Tracking

Players must manage their op budget manually. Three approaches exist:

- **Deterministic scripting:** Calculate the op cost of the script precisely before deploying. Works only if friction values are predictable — i.e., the board behaves as expected. Cheap in words, brittle against disruption.
- **Conservative buffer:** Design the script to stop well short of the op limit. Wastes potential ops but never resets. Safe but suboptimal.
- **Self-tracking:** Write an op counter into the script using `get_friction()` before each move and a running variable. Costs significantly in both words and ops, but gives precise real-time budget control.

### Opponent Detection

The script cannot know the opponent's global position — only whether they are in an adjacent cell via `has_agent()`. The player reads global position from the board UI. Tradeoffs:

- Checking `has_agent()` every step costs ops and words but prevents collision resets.
- Skipping checks saves resources but risks the opponent parking in your path, resetting your turn.
- The player must decide which risk is worth taking based on their read of the opponent's behavior.

### Path Planning

Scripts have no pathfinding primitives. Route planning is either:

- Hardcoded in the script based on the player's read of the board at write time — cheap but brittle if the board changes before exec2.
- Dynamically sensed using `get_friction()` at each step — expensive but adaptive.

### Exec2 Strategy

The player must decide how much of their script to dedicate to exec2 robustness. Options:

- **Full robustness:** Write extensive conditional logic so exec2 behaves correctly across many possible disrupted board states. Costs many words.
- **Intentional halt:** Design exec2 to halt quickly and do little — accept that it won't be productive, but avoid doing something actively harmful on a disrupted board.
- **Optimistic:** Write exec2 as if the board will be in a favorable state. High upside, high reset risk.

### Function Library Investment

Defining a function costs its full word count upfront and saves one word per call thereafter. Whether the investment pays off depends on:

- How often the function will be called across future turns.
- Whether the current sub-goal will remain relevant long enough to recoup the cost.
- Whether the board state evolution makes the function's logic correct in future executions.

> This is the core decision that resists automation. An LLM can identify modularization opportunities within a single script. It cannot determine whether a given function will be called enough over future turns to justify its cost — because that requires predicting board state evolution across unknown opponent behavior.

---

# 4. Language Reference

This section is the definitive specification for the Satura scripting language.

## 4.1 Syntax

### General

- The language uses C-style brace syntax for blocks. Braces may appear anywhere — whitespace and newlines are ignored beyond word boundary detection.
- Semicolons are optional statement terminators. They may be used to place multiple statements on one line but are never required.
- Variable names, function names, literal values, parentheses, commas, and braces do not count as words.
- Comparison operators and logical operators count as words.

```
// Both of these are identical in word count and meaning:
if x > 3 { move(UP) }

if x > 3
{
    move(UP)
}

// Semicolons optional:
move(UP); paint(2); move(DOWN)
```

### Comments

Single-line comments use `//`. Comments do not count as words and have no effect on execution.

### Word Counting Rules

A word is any keyword, operator, or board function that appears in the script. Specifically:

| Category | Word cost |
|---|---|
| Keywords | `if`, `elif`, `else`, `for`, `while`, `halt`, `return`, `def` — each counts as 1 word |
| Operators | `=`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `+`, `-`, `*`, `/`, `%`, `and`, `or`, `not`, `min`, `max` — each counts as 1 word |
| Language mechanics | `call`, `$`, `range`, `index`, `length`, `push`, `pop` — each counts as 1 word |
| Board operations | `get_friction`, `has_agent`, `my_paint`, `opp_paint`, `paint`, `move` — each counts as 1 word |
| Variable names | Free — never count as words |
| Function names | Free — never count as words |
| Parameter names | Free — never count as words |
| Literal values | Free — numbers, direction constants, etc. |
| Parentheses, commas, braces, semicolons | Free — pure syntax |

> `elif` counts as 1 word. Writing `} else { if` instead counts as 2 words (`else` + `if`) and is equivalent but more expensive. Always use `elif`.

## 4.2 Types

| Type | Description |
|---|---|
| `int` | Integer. Division returns int if exact, float if not. |
| `float` | Floating point. Produced by inexact division. |
| `direction` | Enum: `UP`, `DOWN`, `LEFT`, `RIGHT`. |
| `location` | Enum: `UP`, `DOWN`, `LEFT`, `RIGHT`, `HERE`. |
| `list` | Ordered collection. Built with `push()`. No literal syntax. |
| `0` and `1` | Boolean values. `if`, `while`, and `elif` require exactly 0 or 1. Any other value in a boolean context is a runtime halt. |

## 4.3 Variables and Scope

- Variables are globally scoped within a script, except inside function bodies.
- Variables declared inside `if`, `elif`, `else`, `for`, and `while` blocks are still globally scoped — there is no block scope.
- Variables declared inside a function body are locally scoped to that function.
- Functions receive parameters by value. Modifying a parameter does not affect the caller's variable.
- Lists passed to functions are copied locally — mutations inside the function do not affect the original.
- Functions can return values with `return`. A function that reaches its end without returning returns 0.
- Function definitions persist for the entire match across all script rewrites and both execution phases.

## 4.4 Built-in Variables

These variables are always available at no word or op cost:

| Variable | Value |
|---|---|
| `$directions` | Read-only list: `[UP, DOWN, LEFT, RIGHT]` |
| `$locations` | Read-only list: `[HERE, UP, DOWN, LEFT, RIGHT]` |
| `$ops_remaining` | Current ops remaining in this execution |
| `$op_limit` | Total op budget for this execution |

> `$` is a word that must be written before accessing any built-in variable. `$ops_remaining` costs 1 word to access. The value itself is free.

## 4.5 Direction and Location Constants

The following constants are globally available and do not count as words:

```
UP, DOWN, LEFT, RIGHT     // direction constants
HERE                      // location constant (current cell)

// Constants can be assigned to variables:
dir = UP
move(dir)
```

## 4.6 Control Flow

### if / elif / else

```
if condition {
    // body
} elif condition {
    // body
} else {
    // body
}
```

### for

Iterates over a list or range:

```
for dir in $directions {
    move(dir)
}

for i in range(5) {
    paint(1)
}

for i in range(0, 10, 2) {   // start, stop, step
    // i = 0, 2, 4, 6, 8
}
```

### while

```
while $ops_remaining > 10 {
    move(UP)
}
```

### halt

Immediately stops execution. All actions taken up to this point stand. Counts as 1 word.

```
if get_friction(UP) > 8 {
    halt
}
move(UP)
```

## 4.7 Functions

### Defining a Function

```
def function_name(param1, param2) {
    // body
    return value
}
```

- `def` counts as 1 word. The function name and parameter names are free.
- Function definitions persist for the whole match across rewrites.
- A function may call other defined functions. Stack overflow halts execution (implementation-defined depth limit).

### Calling a Function

```
call function_name(arg1, arg2)

// Capture return value:
result = call function_name(arg1, arg2)
```

- `call` counts as 1 word regardless of the function's definition length.
- This is the key word-efficiency mechanic: a function defined once for N words can be called repeatedly for 1 word each.

## 4.8 Operators

### Arithmetic

| Operator | Description |
|---|---|
| `+` | Addition |
| `-` | Subtraction |
| `*` | Multiplication |
| `/` | Division. Returns int if exact, float otherwise. No exponentiation operator exists. |
| `%` | Modulo. Integer only. |
| `min` | `min(a, b)` — returns the smaller of two values |
| `max` | `max(a, b)` — returns the larger of two values |

### Comparison

| Operator | Description |
|---|---|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### Logical

| Operator | Description |
|---|---|
| `and` | Logical AND. Both operands must be 0 or 1. |
| `or` | Logical OR. Both operands must be 0 or 1. |
| `not` | Logical NOT. Operand must be 0 or 1. Returns 1 if 0, 0 if 1. |

Comparison operators return 0 or 1. These can be stored and used in boolean contexts:

```
result = x > 3          // result is 0 or 1
if result { move(UP) }  // valid
if x > 3 { move(UP) }  // also valid, inline
```

## 4.9 List Operations

### push(list, value, [pos])

- Appends value to end of list if pos is omitted.
- `push(mylist, x, 0)` — prepends to front. Position 0 is a free literal.
- Counts as 1 word.

### pop(list, [pos])

- Removes and returns the last element if pos is omitted.
- `pop(mylist, 0)` — removes and returns the first element.
- Calling `pop` on an empty list is a runtime halt.
- Counts as 1 word.

### index(list, pos)

- Returns the element at position pos without removing it.
- Out-of-bounds access is a runtime halt.
- Counts as 1 word.

### length(list)

- Returns the number of elements in the list.
- Counts as 1 word.

### range([start], stop, [step])

- Returns a lazy iterator (usable only in `for` loops, not assignable).
- All arguments must be integers.
- Counts as 1 word.

## 4.10 Board Operations

All board operations cost ops in addition to counting as words. See Section 2.4 for op costs.

### move(dir)

```
move(UP)      // move agent one cell in direction dir
move(mydir)   // variable also accepted
```

- Costs `get_friction(target_cell)` ops.
- Attempting to move into a cell occupied by the opponent's agent resets the turn.
- Attempting to move outside the board is a runtime halt.

### paint(num)

```
paint(3)    // add 3 to your paint on the current cell
```

- Costs `num` ops.
- `num` must be a positive integer. `paint(0)` or `paint(negative)` is a runtime halt.
- Painting more than the cell can accept resets the turn.
- Painting a black cell resets the turn.

### get_friction(loc)

```
get_friction(HERE)   // friction of current cell
get_friction(UP)     // friction of cell above
```

- Returns the friction value for the specified cell from your perspective.
- Uses the formula defined in Section 2.3.
- `loc` is a location type (includes `HERE`).
- Costs 1 op.

### has_agent(dir)

```
has_agent(UP)   // returns 1 if any agent is in that cell, 0 otherwise
```

- `dir` is a direction type (does not include `HERE` — you always know your own position).
- Returns 1 if any agent occupies the adjacent cell, 0 otherwise.
- Costs 1 op.

### my_paint(loc)

```
my_paint(HERE)   // your paint on the current cell (0-5)
my_paint(UP)     // your paint on the cell above
```

- Returns your paint value at the specified location.
- Costs 1 op.

### opp_paint(loc)

```
opp_paint(HERE)  // opponent paint on the current cell (0-5)
```

- Returns the opponent's paint value at the specified location.
- Note: `get_friction(loc)` encodes opponent paint implicitly, but `opp_paint` lets you distinguish between a blank cell (opp=0) and a lightly painted cell (opp=1) when both have friction=1.
- Costs 1 op.

---

# 5. Future Changes

This section covers items that are deliberately deferred — either because they require playtesting to tune, or because they belong to the implementation phase rather than the design phase.

## 5.1 Undecided — Requires Playtesting

The following values and mechanics are intentionally left open. They require playtesting to tune correctly and should not be fixed prematurely.

| Item | Notes |
|---|---|
| Board dimensions | Variable by game mode. Must be square and symmetric. Starting positions scale as approx. N/4 from each corner toward center. |
| Op limit per turn | TBD. Likely variable by game mode. Core balance number — determines how far an agent can travel and how much it can paint per execution. |
| Paint value cap | Currently specified as 0–5 per player. Exact cap may require adjustment based on how quickly cells go black in practice. |
| Word accumulation rate | Tentatively 1 word per second of real time. May vary by game mode (bullet, rapid, classical). |
| Word/op values by game mode | Bullet, rapid, and classical modes likely need different op limits and/or accumulation rates. Relationship between time control and resource availability is TBD. |
| Win threshold | Set at 60% of total cells. Alternative: 80% of non-black cells. 60% total is primary design; 80% non-black adjusts dynamically but may incentivize generating black cells. |
| Maximum game length | No explicit turn cap defined. Game clock is the primary time limit. Whether a maximum turn count is needed as a backstop is TBD. |
| Tiebreaker at time expiry | If both players' clocks expire simultaneously (unlikely but possible in correspondence mode), resolution is TBD. Options: paint volume, cell count, draw. |
| Stalemate — oscillating agents | Two agents moving back and forth indefinitely is not banned by rule. Whether this constitutes a formal stalemate condition, or is simply a self-defeating strategy, is TBD. |
| Multiple agents (shelved) | Originally considered: multiple agents per player sharing one op pool. Shelved to keep the core design clean. Candidate for a variant mode once the single-agent game is stable. Key questions if revisited: death mechanics, op pool splitting, and collision rules between own agents. |

## 5.2 Implementation Notes

The following are not game design decisions but implementation details to carry into the build phase.

### Layout and UI

The game view adapts to screen size with two distinct layouts:

- **Large screens:** Split view. The board and game controls (clock, resign, etc.) occupy one side. The script editor and scripting controls occupy the other. Both are visible simultaneously with no scrolling required.
- **Small screens:** Stacked view with a swipe-between interface. One screen shows the board and game controls; the other shows the script editor with the system keyboard. The interface handles keyboard show/hide cleanly — the two-screen model avoids the common problem of a popped keyboard obscuring content or requiring awkward scrolling to reach the editor.

### Scripting Controls

The scripting panel includes the following controls alongside the text editor:

- **Defined functions viewer:** A collapsible panel showing all functions currently in the player's library, with their word costs. Useful for referencing existing vocabulary when writing a new script.
- **Word count and wait time:** Live display of the current script's word cost, the player's current word bank balance, and the time remaining until the bank reaches the script's cost if not yet sufficient.
- **Restore last script:** A button to reload the previous turn's script into the editor. A script history covering at minimum the last several turns should be browsable and restorable, to allow reuse and iteration without retyping.
- **Compiler output:** Syntax and type errors are shown continuously as the player types, before deployment. The compiler runs against the current editor content in real time.
- **Runtime error log:** After an execution that halted or reset due to a runtime or game state error, the error type and the line that caused it are displayed. This helps the player diagnose and fix scripts between turns.

> These scripting controls are included intentionally to level the playing field. All of them — drafting scripts during an opponent's turn, tracking word counts, restoring past scripts — could be achieved with external software and a clipboard. Providing them in-app removes any advantage from external tooling and ensures both players operate under identical conditions.

### Language Implementation

- **Compiled:** The scripting language is compiled before execution rather than interpreted line by line. This allows the maximum number of errors to be caught and surfaced to the player before the script runs, minimizing unexpected failures from simple mistakes.
- **Type-safe with inference:** The language is relatively type-safe. Types are inferred rather than declared — the compiler determines types from usage and flags mismatches such as passing a direction to `paint()` or using a list in a boolean context at compile time where possible, and at runtime otherwise.
- **No explicit type annotations:** Players never write type names in their scripts. Type safety is enforced silently by the compiler and runtime. This keeps the language lightweight and accessible while still catching a large class of errors early.
