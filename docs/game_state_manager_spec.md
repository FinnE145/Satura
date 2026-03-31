# Game State Manager (GSM) Specification — Corrected

## Overview
The Game State Manager (GSM) is the authoritative controller of game flow and state.
It owns:
- Turn sequencing
- Phase control
- Current game state
- Win and stalemate detection

The engine is responsible for:
- Compilation
- Execution
- State mutation
- Rollback on reset

GSM does NOT handle execution errors or rollback.

---

## Core Game Loop

The GSM runs the game loop:

while not game_over:
    run_execution_phase(player)
    check_win()
    if not game_over:
        check_stalemate()
    if not game_over:
        run_write_phase(player)
    switch_player()

---

## Turn Structure

Each player’s turn follows:

exec2 → write → exec1

Turns alternate between players. Each player’s write and execution phases are sandwiched between the opponent’s executions.

---

## Game State

GSM stores:

- current_program_p1
- current_program_p2
- board_state (delegated updates from engine)
- game_over flag
- winner (if applicable)

GSM does NOT store:
- function definitions
- previous scripts
- execution history (handled by persistence layer)

---

## Execution Phase

To execute:

result = engine.run_execution(player, program)

Where result is one of:
- "normal"
- "halt"
- "reset"

The engine:
- snapshots before execution
- restores on reset
- returns final state

GSM must NOT perform rollback logic.

After EVERY execution (regardless of result):
1. check_win()
2. if no win → check_stalemate()

---

## Win Condition

A player wins if they control ≥ 60% of total cells.

This must be true at the END of execution.

If a script temporarily reaches win condition but loses it before completion, it does NOT count as a win.

---

## Stalemate Condition

A stalemate (draw) occurs when neither player can mathematically reach the win threshold:

max_possible = total_cells - cells_where_opponent_has_5

If max_possible < required_cells_to_win for BOTH players → stalemate.

Stalemate is checked immediately after win check, after every execution.

---

## Write Phase

During write phase:

1. Player submits source code
2. GSM calls:
   result = engine.compile(source)

3. If result.ok == False:
   - Script is rejected
   - Player must retry
   - No state changes

4. If result.ok == True:
   - current_program_player = result.program

Players may retry indefinitely until their write timer expires.

If time expires before a valid script is submitted:
- player loses on time

---

## Script Lifecycle

- Only ONE active script per player exists
- Script is replaced at successful compile during write phase
- Old script is discarded (not used by GSM)

---

## Engine Boundary

Engine responsibilities:
- compile(source)
- run_execution(player, program)
- maintain function definitions
- handle rollback
- return execution outcome

GSM responsibilities:
- pass program to engine
- manage turn order
- evaluate win/stalemate

---

## Notes

- No recurring function costs
- No function tracking in GSM
- No special exec1/exec2 snapshot handling
- No cycle-based win/stalemate checks
