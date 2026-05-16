# warehouse_runner.py — Deterministic robot navigation (no LLM for movement)

from warehouse_agents import ITEMS, DISPATCH_ZONE

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def step_toward(pos, target):
    """Move one step closer to target using simple Manhattan path."""
    r, c = pos
    tr, tc = target
    if r != tr:
        return (r + (1 if tr > r else -1), c)
    if c != tc:
        return (r, c + (1 if tc > c else -1))
    return pos  # already there

def get_robot_thought(robot_name, action, target_pos, inventory, remaining):
    """Generate a human-readable thought string (no LLM needed)."""
    if action == "move":
        return f"navigating toward {target_pos}"
    elif action == "pick":
        return f"at shelf, picking up item"
    elif action == "drop":
        return f"at dispatch zone, dropping {inventory}"
    elif action == "done":
        return f"all tasks complete!"
    return ""

def simulate_robot_full(robot_state: dict) -> list:
    """
    Run a full deterministic simulation for one robot.
    Returns list of step entries.
    """
    pos = tuple(robot_state["pos"])
    inventory = list(robot_state["inventory"])
    completed = list(robot_state["completed"])
    assigned = list(robot_state["assigned"])
    name = robot_state["name"]
    steps = []

    remaining = [i for i in assigned if i not in completed]

    while remaining or inventory:
        if remaining:
            # Navigate to next item shelf
            next_item = remaining[0]
            shelf = ITEMS[next_item]

            while pos != shelf:
                new_pos = step_toward(pos, shelf)
                steps.append({
                    "action": "move",
                    "thought": f"heading to {next_item} at {shelf}",
                    "result": f"Moved → {new_pos}",
                    "pos": new_pos,
                    "inventory": list(inventory),
                    "completed": list(completed),
                })
                pos = new_pos

            # Pick up item
            inventory.append(next_item)
            remaining.pop(0)
            steps.append({
                "action": "pick",
                "thought": f"at shelf {shelf}, picking {next_item}",
                "result": f"Picked up {next_item} ✅",
                "pos": pos,
                "inventory": list(inventory),
                "completed": list(completed),
            })

        # Go to dispatch if inventory full or no more remaining
        if inventory and (not remaining or len(inventory) >= 2):
            while pos != DISPATCH_ZONE:
                new_pos = step_toward(pos, DISPATCH_ZONE)
                steps.append({
                    "action": "move",
                    "thought": f"heading to dispatch zone with {inventory}",
                    "result": f"Moved → {new_pos}",
                    "pos": new_pos,
                    "inventory": list(inventory),
                    "completed": list(completed),
                })
                pos = new_pos

            # Drop items
            dropped = list(inventory)
            completed.extend(dropped)
            inventory = []
            steps.append({
                "action": "drop",
                "thought": f"at dispatch zone, dropping all items",
                "result": f"Dropped {dropped} ✅",
                "pos": pos,
                "inventory": [],
                "completed": list(completed),
            })

    steps.append({
        "action": "done",
        "thought": "all assigned items delivered",
        "result": "Mission complete 🏁",
        "pos": pos,
        "inventory": [],
        "completed": list(completed),
    })

    return steps

def all_items_collected(robot_states: dict) -> bool:
    for rs in robot_states.values():
        assigned_set = set(rs["assigned"])
        completed_set = set(rs["completed"])
        if assigned_set - completed_set:
            return False
    return True
