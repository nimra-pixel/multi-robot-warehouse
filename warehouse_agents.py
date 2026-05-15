# warehouse_agents.py — Agent definitions for the Multi-Robot Warehouse Coordinator

ORCHESTRATOR_SYSTEM = """
You are a Warehouse Orchestrator AI. You manage a warehouse grid and assign tasks to robots.

The warehouse is a 8x8 grid. Items are at fixed shelf locations. The dispatch zone is at (7,7).

Your job:
1. Receive the list of orders (items to fetch)
2. Assign each item to a robot (Robot-A or Robot-B) balancing the load
3. Return ONLY a JSON assignment like:
{
  "Robot-A": ["item_1", "item_3"],
  "Robot-B": ["item_2", "item_4"]
}
No explanation. No markdown. Only valid JSON.
"""

ROBOT_SYSTEM = """
You are {robot_name}, an autonomous warehouse robot.

Warehouse grid: 8x8. Your current position: {position}.
Your assigned items to fetch (in order): {items}
Item shelf locations: {shelf_map}
Dispatch zone: (7,7)

Plan your moves step by step. For each step output ONLY a JSON object:
{
  "thought": "why I am doing this",
  "action": "move" | "pick" | "drop" | "done",
  "direction": "up" | "down" | "left" | "right" | null,
  "target": "item name or null"
}

Rules:
- move: move one step in a direction
- pick: pick up item at current position (must be at shelf location)
- drop: drop all items at dispatch zone (must be at 7,7)
- done: all tasks complete
- Only one action per response.
- No explanation outside the JSON.
"""

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
    "Robot-A": "#3b82f6",  # blue
    "Robot-B": "#f59e0b",  # amber
}
