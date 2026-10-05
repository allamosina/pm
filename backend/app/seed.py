import sqlite3
from uuid import uuid4

# Initial content copied from frontend/src/lib/kanban.ts; never reapplied to existing boards.
STAGES = [
    ("col-backlog", "Backlog", [
        ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
        ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ]),
    ("col-discovery", "Discovery", [
        ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    ]),
    ("col-progress", "In Progress", [
        ("Refine status language", "Standardize column labels and tone across the board."),
        ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ]),
    ("col-review", "Review", [
        ("QA micro-interactions", "Verify hover, focus, and loading states."),
    ]),
    ("col-done", "Done", [
        ("Ship marketing page", "Final copy approved and asset pack delivered."),
        ("Close onboarding sprint", "Document release notes and share internally."),
    ]),
]


def create_board(db: sqlite3.Connection, user_id: int) -> None:
    board_id = db.execute("INSERT INTO boards(user_id) VALUES (?)", (user_id,)).lastrowid
    for position, (column_id, title, cards) in enumerate(STAGES):
        db.execute("INSERT INTO columns VALUES (?, ?, ?, ?)", (board_id, column_id, title, position))
        for card_position, (card_title, details) in enumerate(cards):
            db.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?)",
                       (str(uuid4()), board_id, column_id, card_title, details, card_position))
