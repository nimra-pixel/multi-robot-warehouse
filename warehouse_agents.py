# warehouse_agents.py — Agent definitions for the Multi-Robot Warehouse Coordinator

ORCHESTRATOR_SYSTEM = """You are a Warehouse Orchestrator AI. Assign items to robots.
Return ONLY a single-line JSON object like: {"Robot-A": ["item_1"], "Robot-B": ["item_2"]}
No explanation. No markdown. No newlines. Only valid compact JSON."""

ROBOT_SYSTEM = """You are {robot_name}, a warehouse robot on an 8x8 grid.
Position: {position}. Items to fetch: {items}. Shelf locations: {shelf_map}. Dispatch zone: (7,7).

Reply with ONLY this compact single-line JSON (no newlines, no extra text):
{{"thought":"reason","action":"move","direction":"down","target":null}}

action must be one of: move, pick, drop, done
direction must be one of: up, down, left, right (null if not moving)
Rules: move=one step, pick=grab item at current shelf, drop=deliver at (7,7), done=finished.
One action per reply. No text outside the JSON."""

ITEMS = {
    "item_A": (1, 1),
    "item_B": (1, 6),
    "item_C": (3, 2),
    "item_D": (3, 5),
    "item_E": (5, 1),
    "item_F": (5, 6),
    "item_G": (6, 3),
    "item_H": (6, 5),
}

DISPATCH_ZONE = (7, 7)

ROBOT_START = {
    "Robot-A": (0, 0),
    "Robot-B": (0, 7),
}

ROBOT_COLORS = {
    "Robot-A": "#3b82f6",
    "Robot-B": "#f59e0b",
}
