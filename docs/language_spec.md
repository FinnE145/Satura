# Satura Language Reference

*The definitive specification for the Satura scripting language. This document is intended to be sufficient to implement a compiler and runtime.*

---

## 1. Overview

The Satura scripting language is a small, compiled, statically-inferred language used by players to control their agents. It is designed to be learnable quickly while keeping script complexity a strategic resource through its word count economy.

Key properties:
- **Compiled.** Scripts are compiled before execution. The maximum number of errors are caught and surfaced before a script runs.
- **Type-safe with inference.** Types are inferred from usage — never declared. The compiler flags mismatches at compile time where possible, and at runtime otherwise.
- **No type annotations.** Players never write type names.
- **Word-counted.** A subset of tokens count as "words," which are the primary resource governing script complexity. See Section 3.

---

## 2. Lexical Structure

### 2.1 Source Encoding

Source text is UTF-8. The language is case-sensitive.

### 2.2 Whitespace

Whitespace (spaces, tabs, newlines, carriage returns) is insignificant beyond separating tokens. Statements may span multiple lines freely.

### 2.3 Comments

Single-line comments begin with `//` and extend to the end of the line. Comments are stripped before parsing and have no effect on execution or word count.

```
// This is a comment
$x = 5  // inline comment
```

### 2.4 Keywords

The following identifiers are reserved and may not be used as variable or function names:

```
if  elif  else  for  while  break  halt  return  def  call  in
and  or  not  min  max  range  index  length  push  pop  list
```

### 2.5 Punctuation

The following punctuation tokens are syntactically significant but **never count as words:**

```
{  }  (  )  ,  ;
```

Semicolons are optional statement terminators with no semantic effect. They may be used to place multiple statements on one line but are never required.

### 2.6 Identifiers

An identifier is a sequence of letters (`a–z`, `A–Z`), digits (`0–9`), and underscores (`_`) that does not begin with a digit and is not a reserved keyword or direction/location constant.

Identifiers are used for variable names, function names, and parameter names in `def` signatures. Identifiers themselves **never count as words.**

### 2.7 Integer Literals

An integer literal is a non-empty sequence of decimal digits (`0–9`). Integer literals are **free** (no word cost).

### 2.8 Float Literals

A float literal is a decimal number containing a `.` character. All of the following forms are valid:

```
1.5
3.0
.5
42.
```

Float literals are **free** (no word cost).

**Coercion:** A float value may be implicitly coerced to `int` when an integer is required, but only if the value has no fractional component (e.g. `2.0` → `2`). A float with a non-zero fractional component in an integer-required context is a **runtime halt.** The compiler warns whenever a `could_be_float = true` expression reaches an integer-required context (see Section 4.2).

### 2.9 Direction and Location Constants

The following constants are globally available and do not count as words:

| Constant | Valid as `direction` | Valid as `location` |
|---|---|---|
| `UP` | Yes | Yes |
| `DOWN` | Yes | Yes |
| `LEFT` | Yes | Yes |
| `RIGHT` | Yes | Yes |
| `HERE` | No | Yes |

Constants may be assigned to variables:

```
$dir = UP
move($dir)
```

### 2.10 The NULL Sentinel

`NULL` is a keyword constant that represents the absence of a value. It is **free** (no word cost). It is returned by board query operations (`get_friction`, `has_agent`, `my_paint`, `opp_paint`) when the target location is outside the board boundary.

`NULL` may only appear in `==` and `!=` comparisons. Using `NULL` in any other context — arithmetic, boolean condition, board operation argument, ordered comparison — is a **runtime halt.**

```
$f = get_friction(UP)
if $f == NULL { halt }    // edge-of-board guard
move(UP)                   // safe — $f is not NULL here
```

### 2.10 The `$` Sigil

`$` is a required prefix for **every variable access and assignment** — both user-defined variables and built-in variables. It costs **1 word** per occurrence. The identifier following `$` is free.

```
$x = 5                        // assignment: 2 words ($ + =)
$y = $x + 1                   // two accesses + operator: 4 words ($ + = + $ + +)
$ops_remaining                 // built-in: 1 word (for $)
```

There is no way to access or assign a variable without writing `$`. The four built-in variable names (`directions`, `locations`, `ops_remaining`, `op_limit`) are additionally read-only — assigning to them is a compile error.

`$` followed by any identifier that has not been assigned and is not a built-in is a compile error where the compiler can detect it statically (see Section 6.1).

---

## 3. Word Counting

A word is any keyword, operator, or board function that appears in the script. The word count of a script is the total number of words it contains. Deploying a script spends words equal to its word count from the player's word bank.

| Category | Token(s) | Word cost |
|---|---|---|
| Conditional keywords | `if`, `elif`, `else` | 1 each |
| Loop keywords | `for`, `while` | 1 each |
| Flow keywords | `halt`, `break`, `return`, `def` | 1 each |
| Call keyword | `call` | 1 |
| Variable sigil | `$` | 1 per occurrence |
| Assignment operator | `=` | 1 |
| Arithmetic operators | `+`, `-`, `*`, `/`, `%` | 1 each |
| Comparison operators | `==`, `!=`, `<`, `>`, `<=`, `>=` | 1 each |
| Logical operators | `and`, `or`, `not` | 1 each |
| Utility operators | `min`, `max` | 1 each |
| List operations | `push`, `pop`, `index`, `length`, `range` | 1 each |
| List constructor | `list` | 0 (free) |
| Board operations | `move`, `paint`, `get_friction`, `has_agent`, `my_paint`, `opp_paint` | 1 each |
| `in` (for-loop only) | `in` | 0 (free; `for` accounts for the loop) |
| Null sentinel | `NULL` | 0 (free) |
| Variable / function / parameter names | any identifier | 0 (free) |
| Literals | integers, floats, constants | 0 (free) |
| Punctuation | `(`, `)`, `{`, `}`, `,`, `;` | 0 (free) |

> **`$` cost:** Every variable reference and assignment requires `$`, which costs 1 word. The identifier itself is free. So `$x` costs 1 word (for `$`), and `$x = $y + 1` costs 4 words (two `$` sigils, `=`, and `+`).

> **Note on `elif`:** `elif` costs 1 word. Writing `} else { if` instead is syntactically equivalent but costs 2 words. Always prefer `elif`.

> **Note on `list()`:** The `list()` constructor is free. Creating an empty list costs 0 words.

---

## 4. Type System

### 4.1 Types

| Type | Description |
|---|---|
| `int` | Integer value. |
| `float` | Floating-point value. Produced by `/` or float literals. |
| `direction` | Enum: `UP`, `DOWN`, `LEFT`, `RIGHT`. |
| `location` | Enum: `UP`, `DOWN`, `LEFT`, `RIGHT`, `HERE`. A superset of `direction`. |
| `list` | An ordered, mutable, heterogeneous sequence. Created with `list()`. |
| `NULL` | Sentinel value returned by board query operations when the target location is outside the board. May only appear in `==` and `!=` comparisons. Any other use is a **runtime halt.** |

There is no distinct boolean type. Conditions (`if`, `elif`, `while`) require integer values of exactly `0` or `1`. Any other value in a boolean context is a **runtime halt.**

### 4.2 Type Inference and the `could_be_float` Flag

Types are inferred — players never write type names. For the purposes of numeric type tracking, the compiler assigns every expression and variable a boolean flag: `could_be_float`. This flag propagates upward through the AST as a one-way taint: once an expression is marked `true`, no operation can clear it.

**Flag assignment rules:**

| Expression | `could_be_float` |
|---|---|
| Integer literal | `false` |
| Float literal | `true` |
| `/` | always `true` |
| `+`, `-`, `*`, `%`, `min`, `max`, unary `-` | `true` if any operand is `true` |
| Comparison, logical operator | always `false` (result is always 0 or 1) |
| `get_friction`, `has_agent`, `my_paint`, `opp_paint` | always `false` — but these operations may return `NULL` for out-of-bounds locations (see Section 11) |
| `$ops_remaining`, `$op_limit` | always `false` |
| `length` | always `false` |
| Direction/location constant | always `false` |
| Variable reference | `true` if any assignment to that variable anywhere in reachable scope has `could_be_float = true` |
| Function call | `true` if any `return` statement in the function body has `could_be_float = true` |
| `index`, `pop` | `true` if any `push` to the same list variable has `could_be_float = true` |

A **compiler warning** is emitted whenever an expression with `could_be_float = true` is passed to an integer-required context. This is conservative — it will fire even on expressions that are always whole numbers at runtime (e.g. `$x / 1` where `$x` is always even). That is intentional: the warning exists to surface potential runtime halts, not to prove safety.

### 4.3 Type Coercion

The only implicit coercion is **float-to-int**: a float value with no fractional component may be used wherever an integer is required (e.g. `paint(2.0)` is valid). A float with a non-zero fractional component in an integer-required context is a runtime halt.

No other implicit coercions exist. Passing a `direction` to a function expecting an `int`, or using a `list` in an arithmetic expression, is a type error.

---

## 5. Expressions

### 5.1 Operator Precedence

Operators are evaluated according to the following precedence table, from highest to lowest binding (C-style):

| Level | Operator(s) | Associativity | Notes |
|---|---|---|---|
| 7 (highest) | Unary `-`, `not` | Right | Prefix unary |
| 6 | `*`, `/`, `%` | Left | |
| 5 | `+`, `-` (binary) | Left | |
| 4 | `<`, `>`, `<=`, `>=` | Left | |
| 3 | `==`, `!=` | Left | |
| 2 | `and` | Left | Short-circuits on `0` |
| 1 (lowest) | `or` | Left | Short-circuits on `1` |

`min` and `max` are function-call syntax and do not participate in operator precedence.

### 5.2 Unary Minus

`-expr` negates a numeric (`int` or `float`) value. It is **free** (no word cost). Applying unary minus to a non-numeric type is a runtime halt.

```
$x = -5
$y = -$x
```

### 5.3 Grouping

Parentheses `( expr )` override precedence. They are **free** (no word cost) and may be nested arbitrarily.

```
$result = ($x + $y) * $z
```

### 5.4 Arithmetic

`+`, `-`, `*`, `/`, `%` — each costs **1 word.**

| Operator | Operand types | Result type |
|---|---|---|
| `+`, `-`, `*` | int × int | int |
| `+`, `-`, `*` | float × float, or int × float | float |
| `/` | any numeric × any numeric | always float |
| `%` | int × int | int |

Applying arithmetic operators to non-numeric types is a runtime halt. Applying `%` to a float operand is a runtime halt. Division or modulo by zero is a runtime halt.

> **There is no integer division.** `/` always returns a float, even when both operands are integers. `2 / 3` is `0.6666...`, not `0`.

### 5.5 min and max

`min(a, b)` and `max(a, b)` — each costs **1 word.** Both parentheses and the comma are free. Operands must be numeric (`int` or `float`). Mixed int/float returns float.

```
$x = min(my_paint(HERE), 3)
$y = max($a, $b)
```

### 5.6 Comparison Operators

`==`, `!=`, `<`, `>`, `<=`, `>=` — each costs **1 word.** All comparisons return `int` `0` or `1`.

- `==` and `!=` are valid between two values of the same type.
- `<`, `>`, `<=`, `>=` are valid on numeric types only.
- Comparing incompatible types (e.g. `direction == int`) is a runtime halt.

Comparison results may be stored and reused:

```
$result = $x > 3          // $result is int 0 or 1
if $result { move(UP) }   // valid
if $x > 3 { move(UP) }   // also valid, inline
```

### 5.7 Logical Operators

`and`, `or`, `not` — each costs **1 word.**

All operands must be `int` `0` or `1`. Any other value is a runtime halt.

- `a and b` — returns `1` if both are `1`, else `0`. **Short-circuits:** if `a` is `0`, `b` is not evaluated.
- `a or b` — returns `1` if either is `1`, else `0`. **Short-circuits:** if `a` is `1`, `b` is not evaluated.
- `not a` — prefix operator. Returns `1` if `a` is `0`, `0` if `a` is `1`.

```
if $x > 0 and $y > 0 { move(UP) }
if not has_agent(UP) { move(UP) }
```

### 5.8 Function Call Expressions

Function calls via `call` may appear as expressions (right-hand side of assignment, inside larger expressions, or as standalone statements). See Section 8.2.

---

## 6. Variables and Scope

### 6.1 Declaration

Variables are declared implicitly by their first assignment. There is no declaration keyword. All variable access and assignment requires the `$` prefix.

```
$x = 5        // declares and assigns x
$x = $x + 1   // modifies x
```

Reading a variable before any assignment to it is a **compile error** where the compiler can statically determine that no assignment precedes the read. Where control flow makes this impossible to determine statically, it is a **runtime halt.**

### 6.2 Scope Rules

- Variables assigned at the **top level** of a script are **globally scoped** within that script execution.
- Variables assigned inside `if`, `elif`, `else`, `for`, and `while` blocks are still **globally scoped** — there is no block scope.
- The **loop variable** in a `for` loop (e.g. `$dir` in `for $dir in $directions`) is globally scoped and remains accessible after the loop ends, holding the last value it was assigned. Anonymous range loops (`for range(...)`) define no loop variable.
- Variables assigned inside a **function body** are **locally scoped** to that function. They are not visible outside the function.
- **Function scope is fully isolated.** A function body can only access its own parameters and variables assigned within the body. It has no access to script-level (global) variables. This is because functions persist across turns and may be called from scripts that define entirely different global variables.
- **Function parameters** are declared without `$` in the `def` signature but are accessed with `$` inside the function body (like any other local variable).
- Functions receive all arguments **by value**. Modifying a parameter inside the function has no effect on the caller's variable.
- **Lists passed to functions are copied** on entry. Mutations to list parameters inside the function do not affect the original list.

### 6.3 Variable Lifetime

Script-level (global) variables are created fresh at the start of each execution and do not persist between turns. **Only function definitions persist across turns** (see Section 8.4).

---

## 7. Control Flow

### 7.1 if / elif / else

```
if condition {
    // body
} elif condition {
    // body
} else {
    // body
}
```

`if` costs **1 word.** `elif` costs **1 word.** `else` costs **1 word.**

The condition must evaluate to `int` `0` or `1`. Any other value is a runtime halt. Zero or more `elif` branches and zero or one `else` branch may follow an `if`. Branches are evaluated top-to-bottom; the first matching branch executes and the rest are skipped.

> `elif` always costs 1 word. The equivalent `} else { if` costs 2 words and should be avoided.

### 7.2 for

Iterates over a `list` value or a `range`:

```
for $dir in $directions { ... }
for $i in range(5) { ... }
for $i in range(0, 10, 2) { ... }   // $i = 0, 2, 4, 6, 8
```

When iterating over a `range` and the loop index is not needed, the `$var in` part may be omitted:

```
for range(5) { ... }               // runs 5 times, no loop variable
for range(0, 10, 2) { ... }        // runs 5 times, no loop variable
```

`for` costs **1 word.** `in` is free.

The loop variable is globally scoped (see Section 6.2). Anonymous range loops (`for range(...)`) define no loop variable. Iterating over a non-list, non-range value is a runtime halt.

### 7.3 range

`range` costs **1 word.**

```
range(stop)               // start=0, step=1
range(start, stop)        // step=1
range(start, stop, step)  // custom step
```

All arguments must be `int`. Passing a non-integer argument is a runtime halt.

`range` returns a lazy iterator usable **only inside a `for` loop.** It cannot be assigned to a variable, passed to a function, or used in any other expression context. Attempting to use `range` outside a `for` loop is a **compile error.**

### 7.4 while

```
while condition {
    // body
}
```

`while` costs **1 word.** Condition rules are the same as `if`.

### 7.5 break

```
break
```

`break` costs **1 word.** Immediately exits the innermost enclosing `for` or `while` loop. Execution then continues with the first statement after that loop.

`break` is valid only inside loop bodies. Using `break` outside a `for`/`while` loop is a **compile error.**

### 7.6 halt

```
halt
```

`halt` costs **1 word.** Immediately stops the entire script execution. All actions taken up to this point **stand** (are not undone). See Section 12 for the distinction between halt and reset.

---

## 8. Functions

### 8.1 Defining a Function

```
def function_name(param1, param2) {
    // body — access parameters as $param1, $param2
    return $value
}
```

`def` costs **1 word.** The function name and all parameter names are free. Zero or more parameters are allowed.

Parameters are declared without `$` in the `def` signature. Inside the function body, they are accessed with `$` like any other local variable.

All `def` statements must appear **at the top level of a script.** Nested function definitions (a `def` inside another function body or inside a block) are a **compile error.**

### 8.2 Calling a Function

```
call function_name($arg1, $arg2)          // void call (return value discarded)
$result = call function_name($arg1, $arg2) // capture return value
```

`call` costs **1 word,** regardless of the function's definition length or complexity. This is the key word-efficiency mechanic: a function defined once for N words can be called repeatedly for 1 word each (plus `$` for each argument variable and the return value capture, if any).

Function calls are also valid as sub-expressions:

```
if call is_safe(UP) { move(UP) }
$x = call compute($a) + 1
```

Since the language is compiled, all function definitions in the script are registered before any execution begins. **Forward references are valid** — a function may be called before its `def` appears in the source.

### 8.3 return

`return` costs **1 word.** It is valid only inside a function body; using `return` at the top level of a script is a **compile error.**

```
return $expr   // returns the value of $expr
return         // returns 0
```

A function that reaches the end of its body without a `return` statement implicitly returns `0`.

### 8.4 Function Persistence

Function definitions persist **for the entire match**, across all script rewrites and both execution phases (exec1 and exec2). A script does not need to redefine functions written in previous turns — they are available automatically.

If a new script includes a `def` with the same name as an existing function, the **new definition replaces the old one immediately upon deployment.** The replacement takes effect for all subsequent calls.

### 8.5 Recursion

Functions may call themselves or call other defined functions. Exceeding the host implementation's stack depth is a **runtime halt.** The exact stack depth limit is implementation-defined (governed by the host language's call stack).

---

## 9. Built-in Variables

Built-in variables are accessed with `$` like all other variables. They are **read-only** — assigning to them is a **compile error.** The four built-in names are:

| Variable | Type | Description |
|---|---|---|
| `$directions` | `list` of `direction` | Read-only: `[UP, DOWN, LEFT, RIGHT]` |
| `$locations` | `list` of `location` | Read-only: `[HERE, UP, DOWN, LEFT, RIGHT]` |
| `$ops_remaining` | `int` | Current ops remaining in this execution |
| `$op_limit` | `int` | Total op budget for this execution |

---

## 10. List Operations

Lists are ordered, mutable, heterogeneous sequences. They have no literal syntax — they must be created with `list()`.

### 10.1 list()

```
$mylist = list()
```

Creates an empty list. `list` is **free** (no word cost). The parentheses are free. Only `$` costs 1 word (for the assignment).

### 10.2 push($list, value [, pos])

`push` costs **1 word.**

```
push($mylist, $x)      // appends $x to the end
push($mylist, $x, 0)   // inserts $x at position 0 (front)
push($mylist, $x, $i)  // inserts $x at position $i
```

If `pos` is omitted, the value is appended to the end. If `pos` is provided, the value is inserted at that integer index. Out-of-bounds `pos` is a **runtime halt.**

### 10.3 pop($list [, pos])

`pop` costs **1 word.**

```
$x = pop($mylist)      // removes and returns the last element
$x = pop($mylist, 0)   // removes and returns the element at position 0 (front)
$x = pop($mylist, $i)  // removes and returns the element at position $i
```

If `pos` is omitted, the last element is removed and returned. Calling `pop` on an empty list is a **runtime halt.** Out-of-bounds `pos` is a **runtime halt.**

### 10.4 index($list [, pos])

`index` costs **1 word.**

```
$x = index($mylist)       // returns the last element without removing it
$x = index($mylist, 0)    // returns element at position 0 without removing it
$x = index($mylist, $i)   // variable index
```

If `pos` is omitted, the last element is returned. Calling `index` on an empty list is a **runtime halt.** Out-of-bounds `pos` is a **runtime halt.**

### 10.5 length($list)

`length` costs **1 word.**

```
$n = length($mylist)   // returns the number of elements as int
```

### 10.6 range

See Section 7.3. `range` is only valid in `for` loops and cannot be assigned or passed as a value.

---

## 11. Board Operations

All board operations cost **ops** in addition to counting as words. Exceeding the op budget during any execution resets the entire turn (see Section 12). The ops consumed by a board operation are deducted at the moment the operation executes.

| Operation | Op cost | Word cost |
|---|---|---|
| `move(dir)` | `get_friction(target_cell)` | 1 |
| `paint(num)` | `2 × num` | 1 |
| `get_friction(loc)` | 1 | 1 |
| `has_agent(dir)` | 1 | 1 |
| `my_paint(loc)` | 1 | 1 |
| `opp_paint(loc)` | 1 | 1 |

### 11.1 move(dir)

```
move(UP)       // move agent one cell upward using a constant
move($mydir)   // variable also accepted
```

- `dir` must be a `direction` value (`UP`, `DOWN`, `LEFT`, `RIGHT`). Passing `HERE` or any non-direction value is a **compile error** where detectable, otherwise a **runtime halt.**
- Costs `get_friction(target_cell)` ops, evaluated at the moment of movement.
- Moving outside the board boundary causes a **runtime reset** (execution rollback).
- Moving into a cell occupied by the opponent's agent is a **turn reset** (the moving agent's entire execution is undone).

### 11.2 paint(num)

```
paint(3)     // add 3 to your paint value on the current cell
paint($n)    // variable also accepted
```

- `num` must be a positive integer (after any float-to-int coercion). `paint(0)` and `paint(negative)` are **runtime halts.**
- Costs `2 × num` ops.
- Painting more than the current cell can accept (your paint + num > 5, or combined total > 10) is a **turn reset.**
- Painting a black cell (p1 = 5 and p2 = 5) is a **turn reset.**
- `paint` always operates on the **current cell** (the agent's position). There is no location argument.

### 11.3 get_friction(loc)

```
get_friction(HERE)    // friction of the current cell
get_friction(UP)      // friction of the cell immediately above
get_friction($loc)    // variable also accepted
```

- `loc` must be a `location` value (including `HERE`). Passing a non-location value is a **compile error** where detectable, otherwise a **runtime halt.**
- Returns an `int` friction value computed as:
  - `1` if the cell is blank (both paints = 0)
  - `20` if the cell is black (both paints = 5)
  - `2 × opponent_paint(cell)` otherwise (range: 2–10)
- For cells outside the board boundary, returns `NULL`. The op cost (1) is still deducted.
- Costs 1 op.

### 11.4 has_agent(dir)

```
has_agent(UP)      // returns 1 if any agent occupies the cell above, 0 otherwise
has_agent($dir)    // variable also accepted
```

- `dir` must be a `direction` value. `HERE` is not valid (a player always knows their own position). Passing `HERE` or any non-direction value is a **compile error** where detectable, otherwise a **runtime halt.**
- Returns `int` `1` if any agent (either player's) occupies the adjacent cell, `0` otherwise.
- Returns `NULL` if `dir` refers to a cell outside the board boundary. The op cost (1) is still deducted.
- Costs 1 op.

### 11.5 my_paint(loc)

```
my_paint(HERE)    // your paint value on the current cell (0–5)
my_paint(UP)      // your paint value on the cell above
my_paint($loc)    // variable also accepted
```

- `loc` must be a `location` value. Passing a non-location value is a **compile error** where detectable, otherwise a **runtime halt.**
- Returns `int` in range `[0, 5]`.
- Returns `NULL` if `loc` refers to a cell outside the board boundary. The op cost (1) is still deducted.
- Costs 1 op.

### 11.6 opp_paint(loc)

```
opp_paint(HERE)    // opponent's paint value on the current cell (0–5)
opp_paint($loc)    // variable also accepted
```

- `loc` must be a `location` value. Passing a non-location value is a **compile error** where detectable, otherwise a **runtime halt.**
- Returns `int` in range `[0, 5]`.
- Returns `NULL` if `loc` refers to a cell outside the board boundary. The op cost (1) is still deducted.
- A fully opponent-owned cell (opp = 5) has friction 10; a black cell has friction 20. `get_friction` distinguishes the two, but `opp_paint` combined with `my_paint` makes the distinction explicit — you can paint a heavily opponent-owned cell but not a black one.
- Costs 1 op.

---

## 12. Execution Outcomes

A script execution ends in one of three ways:

| Outcome | Effect |
|---|---|
| **Normal completion** | Script runs to end. All actions stand. |
| **Halt** | Execution stops early. All actions taken up to that point stand. |
| **Reset** | Entire execution is undone. Board returns to its state before the execution began. Words are still spent. |

### 12.1 Conditions that cause a Reset

- Op budget exceeded during execution
- Agent attempts to move into a cell occupied by the opponent's agent
- `paint()` called on a black cell
- `paint()` would exceed the cell's capacity

### 12.2 Conditions that cause a Halt

- `halt` keyword executed
- Runtime type mismatch (e.g. non-boolean in condition, wrong type passed to operator)
- `NULL` value used in any context other than `==` or `!=` comparison (arithmetic, boolean condition, board operation argument, ordered comparison, etc.)
- Non-integer (fractional float) value passed to an integer-required context
- `paint(0)` or `paint(negative)`
- `move()` outside board boundary
- `pop` on empty list
- `index` or `pop` out of bounds
- `push` with out-of-bounds position
- Division or modulo by zero
- `range` arguments are not integers
- `for` iterated over a non-list, non-range value
- Uninitialized variable read at runtime (where not caught at compile time)
- Stack depth exceeded (recursive call)

### 12.3 Compile Errors (caught before execution)

Compile errors prevent the script from being deployed. They do not cost words or affect game state.

- Syntax errors (malformed statements, mismatched braces, etc.)
- Uninitialized variable read (where statically detectable)
- `return` outside a function body
- `break` outside a loop body
- Nested `def` inside a function body or block
- Assignment to a built-in variable (`$directions`, `$locations`, `$ops_remaining`, `$op_limit`)
- `$` followed by an unrecognized or unassigned name (where statically detectable)
- `range` used outside a `for` loop
- Type mismatches statically detectable at compile time (e.g. literal `HERE` passed to `move()`, literal `HERE` passed to `has_agent()`)

### 12.4 Compiler Warnings

Warnings do not prevent deployment but indicate that a runtime error is possible. The primary source of warnings is the `could_be_float` flag (see Section 4.2): any expression marked `could_be_float = true` that is passed to an integer-required context produces a warning.

Integer-required contexts:
- `paint(num)` — `num` must be a positive integer
- `range(...)` arguments — all must be integers
- `push`, `pop`, `index` position arguments — must be integers

---

## 13. Formal Grammar (EBNF)

```ebnf
program         = statement* ;

statement       = def_stmt
                | assignment
                | expr_stmt
                | if_stmt
                | for_stmt
                | while_stmt
                | break_stmt
                | halt_stmt
                | return_stmt
                | ";" ;

def_stmt        = "def" IDENT "(" param_list? ")" block ;
(* Parameter names in the signature are plain IDENTs — no $ *)

param_list      = IDENT ( "," IDENT )* ;

assignment      = "$" IDENT "=" expression ";"? ;

expr_stmt       = expression ";"? ;
(* Covers standalone call, standalone board ops, etc. *)

if_stmt         = "if" expression block
                  ( "elif" expression block )*
                  ( "else" block )? ;

for_stmt        = "for" "$" IDENT "in" ( range_expr | expression ) block ;

range_expr      = "range" "(" expression
                  ( "," expression ( "," expression )? )? ")" ;

while_stmt      = "while" expression block ;

break_stmt      = "break" ";"? ;

halt_stmt       = "halt" ";"? ;

return_stmt     = "return" expression? ";"? ;

block           = "{" statement* "}" ;

(* ---- Expressions ---- *)

expression      = or_expr ;

or_expr         = and_expr ( "or" and_expr )* ;

and_expr        = not_expr ( "and" not_expr )* ;

not_expr        = "not" not_expr
                | comparison ;

comparison      = additive ( ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) additive )* ;

additive        = multiplicative ( ( "+" | "-" ) multiplicative )* ;

multiplicative  = unary ( ( "*" | "/" | "%" ) unary )* ;

unary           = "-" unary
                | primary ;

primary         = INT_LIT
                | FLOAT_LIT
                | direction_const
                | location_const
                | null_const
                | var_ref
                | list_constructor
                | min_expr
                | max_expr
                | push_expr
                | pop_expr
                | index_expr
                | length_expr
                | board_op
                | call_expr
                | "(" expression ")" ;

var_ref         = "$" IDENT ;
(* Covers both user-defined variables and built-in variables.
   The semantic checker distinguishes built-ins ($directions etc.) as read-only.
   The $ token costs 1 word; IDENT is free. *)

direction_const = "UP" | "DOWN" | "LEFT" | "RIGHT" ;
location_const  = "UP" | "DOWN" | "LEFT" | "RIGHT" | "HERE" ;
null_const      = "NULL" ;

list_constructor = "list" "(" ")" ;

min_expr        = "min" "(" expression "," expression ")" ;
max_expr        = "max" "(" expression "," expression ")" ;

push_expr       = "push" "(" expression "," expression ( "," expression )? ")" ;
pop_expr        = "pop" "(" expression ( "," expression )? ")" ;
index_expr      = "index" "(" expression ( "," expression )? ")" ;
length_expr     = "length" "(" expression ")" ;

board_op        = move_op | paint_op | friction_op | agent_op | my_paint_op | opp_paint_op ;
move_op         = "move" "(" expression ")" ;
paint_op        = "paint" "(" expression ")" ;
friction_op     = "get_friction" "(" expression ")" ;
agent_op        = "has_agent" "(" expression ")" ;
my_paint_op     = "my_paint" "(" expression ")" ;
opp_paint_op    = "opp_paint" "(" expression ")" ;

call_expr       = "call" IDENT "(" arg_list? ")" ;
arg_list        = expression ( "," expression )* ;

INT_LIT         = [0-9]+ ;
FLOAT_LIT       = [0-9]+ "." [0-9]*
                | [0-9]* "." [0-9]+ ;
IDENT           = [a-zA-Z_][a-zA-Z0-9_]* ;
(* IDENT must not be a reserved keyword or a direction/location constant *)
```

---

## 14. Examples

### Annotated word counts

```
// Assignment — 2 words ($ + =)
$x = 5

// Variable assignment with expression — 4 words ($ + = + $ + +)
$y = $x + 1

// Conditional move — 4 words (if + $ + > + move)
if $x > 3 { move(UP) }

// Loop over all directions — 3 words (for + $ + move)
// Note: in is free; $directions costs 1 word (for $) counted separately
for $dir in $directions { move($dir) }
// Full count: for(1) $(1 for $dir) $(1 for $directions) move(1) $(1 for $dir in body) = 5 words

// Define a reusable function — 5 words
def go(d) {
    if not has_agent($d) { move($d) }
}
// words: def(1) if(1) not(1) has_agent(1) move(1) = 5 words
// ($d in body costs $ each time; 2 uses = +2 words → total 7 words)

// Call costs 1 word + $ for each variable argument
call go(UP)    // 1 word (call; UP is a constant, no $)
call go(DOWN)  // 1 word
```

### Op tracking

```
def safe_move(d) {
    $cost = get_friction($d)
    if $ops_remaining > $cost { move($d) }
}
// words: def(1) $(1) =(1) get_friction(1) $(1) if(1) $(1) >(1) $(1) move(1) $(1) = 11 words
// each call: call(1) = 1 word (if passing a constant direction)
```

### Opponent detection

```
for $dir in $directions {
    if not has_agent($dir) { move($dir); halt }
}
// words: for(1) $(1) $(1) if(1) not(1) has_agent(1) $(1) move(1) $(1) halt(1) = 10 words
```

### List usage

```
$moves = list()
push($moves, UP)
push($moves, RIGHT)
for $dir in $moves {
    if not has_agent($dir) { move($dir) }
}
// $moves = list(): 2 words ($ + =); list() is free
// push costs push(1) + $(1 for $moves) each call = 2 words per push
```
