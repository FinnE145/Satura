# Satura

A competitive programming strategy game.

> Disclaimer: I'm a busy student and don't have time to write docs right now, so this readme is AI-generated (and unfortunately very much sounds like it). I will update it manually in the future. In the meantime, the spec and language docs in the [docs folder](./docs/) are more technical and I kept them at a much higher standard of care than this readme. Treat them as the source of truth and use them if you find AI slop unbearable to read.

Satura is a turn-based strategy game where your moves are programs. Each turn, you write a short script that governs your agent's behavior on a shared grid — painting territory, navigating friction, and disrupting your opponent's plans. The board is fully visible and the starting position is fixed and symmetric.

---

## The Game

The board is a grid of cells. Each cell holds paint — yours, your opponent's, or a mixture of both. Your agent moves through the board, painting cells to claim territory. Cells where both players have painted heavily turn black and belong to nobody. The first player to dominate 60% of the board wins.

Your move is a script. The script runs twice each cycle: once on a board state you know, and once on a board your opponent has already modified. Between executions, you watch your opponent's script run and write a new one in response.

The game involves two coupled problems:

- **Game strategy** — reading the board, identifying the right sub-goal, predicting what your opponent is building toward
- **Code strategy** — writing an efficient script within tight resource constraints, and building a library of reusable functions that pay off over future turns

Understanding the board doesn't tell you how to write the code. Writing efficient code doesn't tell you whether it's the right strategy. Both have to be solved every turn.

The scripting language is intentionally minimal — movement, painting, conditionals, loops, and function definitions. Movement through contested territory costs ops. Functions cost words to define and one word to call. Writing defensively for your second execution costs both. Every script involves tradeoffs.

Full game rules and language documentation are in [`/docs`](./docs).

---

## Implementation

Satura is a Flask web application. Games are played in the browser with no client-side installation required.

### Stack

- **Backend:** Python / Flask
- **Frontend:** HTML, CSS, JavaScript
- **Scripting runtime:** Custom compiler and interpreter for the Satura scripting language, implemented server-side
- **Game state:** Server-managed, with real-time updates pushed to both clients

### Project Structure

```
satura/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── game/
│   │   ├── board.py          # Board state, paint, friction logic
│   │   ├── agent.py          # Agent movement and collision
│   │   ├── engine.py         # Turn execution, reset/halt logic
│   │   └── session.py        # Game session and clock management
│   ├── lang/
│   │   ├── lexer.py          # Tokenizer / word counter
│   │   ├── parser.py         # AST construction
│   │   ├── compiler.py       # Type inference, compile-time error detection
│   │   └── interpreter.py    # Script execution against board state
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── docs/                     # Full game rules and language reference
├── tests/
├── config.py
├── requirements.txt
└── README.md
```

### Getting Started

```bash
git clone https://github.com/FinnE145/satura.git
cd satura
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask run
```

The app will be available at `http://localhost:45630`.

### Configuration

Copy `.env.example` to `.env` and set the relevant values before running.

```
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

---

## Interface

On large screens, the board and script editor are displayed side by side. On small screens, they are stacked with a swipe-between interface — one screen for the board and game controls, one for the editor and keyboard — to avoid keyboard overlap and scrolling issues on mobile.

The scripting panel includes:

- Live word count and time-to-deploy estimate based on current bank balance
- Defined functions viewer showing your persistent function library and word costs
- Script history with one-click restore for reuse and iteration
- Real-time compiler output for syntax and type errors before deployment
- Runtime error log showing what failed and where after each execution

---

## Docs

- [Game Rules](./docs/rules.md)
- [Language Reference](./docs/language.md)
- [Game Design Specification](./docs/spec.md)

---

## Status

Early development. The game design specification is complete. Implementation is in progress.

---

## License

Proprietary for now, will be revisited.
