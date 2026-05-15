# warehouse_runner.py — Robot movement and task execution logic

import json
from warehouse_agents import ITEMS, DISPATCH_ZONE

DIRECTIONS = {
    "up":    (-1, 0),
    "down":  ( 1, 0),
    "left":  ( 0,-1),
    "right": ( 0, 1),
}

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def move(pos, direction):
    dr, dc = DIRECTIONS.get(direction, (0, 0))
    return (clamp(pos[0] + dr, 0, 7), clamp(pos[1] + dc, 0, 7))

def parse_action(raw: str) -> dict:
    """Extract JSON from model response robustly."""
    raw = raw.strip()
    # Strip markdown fences
    for fence in ["```json", "```"]:
        raw = raw.replace(fence, "")
    raw = raw.strip()
    # Find first { ... }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {"action": "done", "thought": "could not parse", "direction": None, "target": None}
    try:
        return json.loads(raw[start:end])
    except Exception:
        return {"action": "done", "thought": "parse error", "direction": None, "target": None}

def simulate_robot_step(robot_state: dict, action_obj: dict) -> dict:
    """
    Apply one action to robot state.
    robot_state keys: pos, inventory, completed, log
    Returns updated robot_state.
    """
    pos = robot_state["pos"]
    inventory = robot_state["inventory"]
    completed = robot_state["completed"]
    log = robot_state["log"]

    action = action_obj.get("action", "done")
    thought = action_obj.get("thought", "")
    direction = action_obj.get("direction")
    target = action_obj.get("target")

    entry = {"thought": thought, "action": action, "pos_before": pos}

    if action == "move" and direction:
        new_pos = move(pos, direction)
        robot_state["pos"] = new_pos
        entry["pos_after"] = new_pos
        entry["result"] = f"Moved {direction} → {new_pos}"

    elif action == "pick":
        # Check if any assigned item is at current pos
        picked = False
        for item in list(robot_state["assigned"]):
            if ITEMS.get(item) == pos and item not in inventory and item not in completed:
                inventory.append(item)
                entry["result"] = f"Picked up {item} at {pos}"
                picked = True
                break
        if not picked:
            entry["result"] = f"Nothing to pick at {pos}"
        entry["pos_after"] = pos

    elif action == "drop":
        if pos == DISPATCH_ZONE and inventory:
            for item in inventory:
                completed.append(item)
            entry["result"] = f"Dropped {inventory} at dispatch zone ✅"
            robot_state["inventory"] = []
        elif pos != DISPATCH_ZONE:
            entry["result"] = f"Cannot drop — not at dispatch zone (need {DISPATCH_ZONE}, at {pos})"
        else:
            entry["result"] = "Nothing in inventory to drop"
        entry["pos_after"] = pos

    elif action == "done":
        entry["result"] = "Robot signals task complete 🏁"
        entry["pos_after"] = pos
        robot_state["done"] = True

    else:
        entry["result"] = f"Unknown action: {action}"
        entry["pos_after"] = pos

    log.append(entry)
    return robot_state

def all_items_collected(robot_states: dict) -> bool:
    for rs in robot_states.values():
        if not rs.get("done") and rs["assigned"]:
            assigned_set = set(rs["assigned"])
            completed_set = set(rs["completed"])
            if assigned_set - completed_set:
                return False
    return True
