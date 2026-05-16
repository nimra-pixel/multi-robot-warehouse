# warehouse_config.py — All constants for the Warehouse Fleet Intelligence Platform

GRID_SIZE = 10  # 10x10 grid

ITEMS = {
    "item_A": (1, 1),
    "item_B": (1, 8),
    "item_C": (3, 2),
    "item_D": (3, 7),
    "item_E": (5, 1),
    "item_F": (5, 8),
    "item_G": (7, 2),
    "item_H": (7, 7),
    "item_I": (2, 5),
    "item_J": (6, 5),
}

DISPATCH_ZONE = (9, 9)

CHARGING_STATIONS = {
    "Robot-A": (0, 0),
    "Robot-B": (0, 9),
}

ROBOT_START = {
    "Robot-A": (0, 0),
    "Robot-B": (0, 9),
}

ROBOT_COLORS = {
    "Robot-A": "#00d4ff",   # cyan
    "Robot-B": "#ff6b35",   # orange
}

# Static obstacles (shelving units / walls)
STATIC_OBSTACLES = {
    (4, 0), (4, 1), (4, 3),
    (4, 6), (4, 8), (4, 9),
}

# Robot base stats
ROBOT_BASE_STATS = {
    "Robot-A": {"battery": 100, "health": 100, "velocity": 1.2, "priority": 1},
    "Robot-B": {"battery": 100, "health": 100, "velocity": 1.0, "priority": 2},
}

ORCHESTRATOR_SYSTEM = """You are a Warehouse Fleet Orchestrator AI.
Assign items to robots to balance load. Return ONLY compact single-line JSON:
{"Robot-A": ["item_1"], "Robot-B": ["item_2"]}
No explanation. No markdown. No newlines."""
