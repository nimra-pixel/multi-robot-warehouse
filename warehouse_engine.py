# warehouse_engine.py — Simulation engine with MAPF, obstacles, robot stats

import random
import math
from warehouse_config import (
    GRID_SIZE, ITEMS, DISPATCH_ZONE, CHARGING_STATIONS,
    STATIC_OBSTACLES, ROBOT_BASE_STATS
)

# ── Pathfinding (A*) ──────────────────────────────────────────────────────────

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(start, goal, blocked=None):
    """A* pathfinding avoiding blocked cells."""
    if blocked is None:
        blocked = set()
    blocked = blocked | STATIC_OBSTACLES
    if goal in blocked:
        blocked = blocked - {goal}  # goal must be reachable

    open_set = {start}
    came_from = {}
    g = {start: 0}
    f = {start: heuristic(start, goal)}

    while open_set:
        current = min(open_set, key=lambda x: f.get(x, 9999))
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        open_set.remove(current)
        r, c = current
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and (nr,nc) not in blocked:
                tentative_g = g[current] + 1
                if tentative_g < g.get((nr,nc), 9999):
                    came_from[(nr,nc)] = current
                    g[(nr,nc)] = tentative_g
                    f[(nr,nc)] = tentative_g + heuristic((nr,nc), goal)
                    open_set.add((nr,nc))
    # fallback: direct step
    return [goal]


# ── Dynamic obstacles ─────────────────────────────────────────────────────────

def generate_dynamic_obstacles(step, robot_positions):
    """Simulate moving humans/forklifts."""
    random.seed(step // 3)  # slow movement
    obstacles = set()
    # 3 moving humans
    for i in range(3):
        r = (step // 2 + i * 3) % GRID_SIZE
        c = (i * 4 + step // 4) % GRID_SIZE
        pos = (r, c)
        if pos not in robot_positions and pos not in STATIC_OBSTACLES:
            obstacles.add(pos)
    # 1 forklift
    fr = (step // 5) % GRID_SIZE
    fc = 5
    pos = (fr, fc)
    if pos not in robot_positions:
        obstacles.add(pos)
    return obstacles


# ── Robot stats simulation ────────────────────────────────────────────────────

def update_robot_stats(stats, action, carrying):
    """Update battery, health, velocity per step."""
    # Battery drain
    drain = 0.8 if action == "move" else 0.3
    if carrying:
        drain += 0.4
    stats["battery"] = max(0, stats["battery"] - drain)

    # Health degrades slowly
    stats["health"] = max(0, stats["health"] - random.uniform(0, 0.15))

    # Velocity affected by battery
    base_vel = ROBOT_BASE_STATS[stats["name"]]["velocity"]
    if stats["battery"] > 50:
        stats["velocity"] = base_vel
    elif stats["battery"] > 20:
        stats["velocity"] = round(base_vel * 0.75, 2)
    else:
        stats["velocity"] = round(base_vel * 0.5, 2)

    # Collision risk based on nearby robots/obstacles
    stats["collision_risk"] = round(random.uniform(0, 0.3), 2)

    return stats


# ── Collision detection ───────────────────────────────────────────────────────

def check_collision(pos_a, pos_b, next_a, next_b):
    """Detect head-on or cell collision between two robots."""
    # Same cell collision
    if next_a == next_b:
        return True
    # Swap collision (passing through each other)
    if next_a == pos_b and next_b == pos_a:
        return True
    return False


# ── Full simulation ───────────────────────────────────────────────────────────

def simulate_fleet(assignment, start_positions):
    """
    Run full simulation for both robots simultaneously with MAPF.
    Returns list of frames, each frame = snapshot of both robots.
    """
    stats = {
        name: {**ROBOT_BASE_STATS[name], "name": name, "collision_risk": 0.0}
        for name in ["Robot-A", "Robot-B"]
    }

    robot_states = {}
    for name in ["Robot-A", "Robot-B"]:
        robot_states[name] = {
            "name": name,
            "pos": tuple(start_positions[name]),
            "inventory": [],
            "completed": [],
            "assigned": list(assignment.get(name, [])),
            "remaining": list(assignment.get(name, [])),
            "done": False,
            "trail": [tuple(start_positions[name])],
            "stats": stats[name],
            "log": [],
            "needs_charge": False,
            "emergency": False,
        }

    frames = []
    kpi = {
        "total_steps": 0,
        "total_delivered": 0,
        "collisions_avoided": 0,
        "emergency_rerouts": 0,
        "idle_steps": {"Robot-A": 0, "Robot-B": 0},
        "delivery_times": [],
        "step_start": {},
    }

    MAX_FRAMES = 300

    for step in range(MAX_FRAMES):
        pos_a = robot_states["Robot-A"]["pos"]
        pos_b = robot_states["Robot-B"]["pos"]
        dyn_obs = generate_dynamic_obstacles(step, {pos_a, pos_b})

        # Compute next positions for both robots
        next_positions = {}
        actions = {}

        for name, rs in robot_states.items():
            if rs["done"]:
                next_positions[name] = rs["pos"]
                actions[name] = "idle"
                kpi["idle_steps"][name] += 1
                continue

            # Need charging?
            if rs["stats"]["battery"] < 15 and not rs["needs_charge"]:
                rs["needs_charge"] = True
                rs["emergency"] = True
                kpi["emergency_rerouts"] += 1

            if rs["needs_charge"]:
                target = CHARGING_STATIONS[name]
                if rs["pos"] == target:
                    rs["stats"]["battery"] = min(100, rs["stats"]["battery"] + 40)
                    rs["needs_charge"] = False
                    rs["emergency"] = False
                    actions[name] = "charge"
                    next_positions[name] = rs["pos"]
                    continue

            # Determine target
            remaining = rs["remaining"]
            inventory = rs["inventory"]

            if remaining:
                next_item = remaining[0]
                shelf = ITEMS[next_item]
                if rs["pos"] == shelf:
                    # Pick up
                    inventory.append(next_item)
                    remaining.pop(0)
                    if name not in kpi["step_start"]:
                        kpi["step_start"][name] = step
                    actions[name] = "pick"
                    next_positions[name] = rs["pos"]
                    rs["log"].append({"action": "pick", "thought": f"picking {next_item}", "result": f"Picked {next_item} ✅", "pos": rs["pos"], "inventory": list(inventory), "completed": list(rs["completed"])})
                    continue
                else:
                    target = shelf
            elif inventory:
                target = DISPATCH_ZONE
            else:
                rs["done"] = True
                rs["log"].append({"action": "done", "thought": "all tasks done", "result": "Mission complete 🏁", "pos": rs["pos"], "inventory": [], "completed": list(rs["completed"])})
                actions[name] = "done"
                next_positions[name] = rs["pos"]
                continue

            # Pathfind
            other_pos = pos_b if name == "Robot-A" else pos_a
            blocked = dyn_obs | {other_pos}
            path = astar(rs["pos"], target, blocked)
            next_pos = path[0] if path else rs["pos"]

            actions[name] = "move"
            next_positions[name] = next_pos

        # MAPF collision resolution
        np_a = next_positions.get("Robot-A", robot_states["Robot-A"]["pos"])
        np_b = next_positions.get("Robot-B", robot_states["Robot-B"]["pos"])

        if check_collision(pos_a, pos_b, np_a, np_b):
            kpi["collisions_avoided"] += 1
            # Robot-B waits (lower priority)
            next_positions["Robot-B"] = pos_b
            actions["Robot-B"] = "wait"

        # Apply moves
        for name, rs in robot_states.items():
            if actions.get(name) in ("idle", "pick", "done", "charge"):
                continue

            new_pos = next_positions[name]
            old_pos = rs["pos"]

            # Check dynamic obstacle collision → emergency reroute
            if new_pos in dyn_obs:
                kpi["emergency_rerouts"] += 1
                rs["emergency"] = True
                new_pos = old_pos  # stay put
                rs["log"].append({"action": "move", "thought": "emergency reroute — obstacle ahead", "result": f"⚠️ Blocked! Waiting at {old_pos}", "pos": old_pos, "inventory": list(rs["inventory"]), "completed": list(rs["completed"])})
            else:
                rs["emergency"] = False
                if new_pos != old_pos:
                    rs["log"].append({"action": "move", "thought": f"navigating to target", "result": f"Moved → {new_pos}", "pos": new_pos, "inventory": list(rs["inventory"]), "completed": list(rs["completed"])})

            rs["pos"] = new_pos
            rs["trail"].append(new_pos)
            if len(rs["trail"]) > 20:
                rs["trail"] = rs["trail"][-20:]

            # Drop at dispatch
            if rs["pos"] == DISPATCH_ZONE and rs["inventory"]:
                dropped = list(rs["inventory"])
                rs["completed"].extend(dropped)
                rs["inventory"] = []
                kpi["total_delivered"] += len(dropped)
                if name in kpi["step_start"]:
                    kpi["delivery_times"].append(step - kpi["step_start"].pop(name))
                rs["log"].append({"action": "drop", "thought": "at dispatch, dropping all", "result": f"Dropped {dropped} ✅", "pos": rs["pos"], "inventory": [], "completed": list(rs["completed"])})

            # Update stats
            rs["stats"] = update_robot_stats(
                rs["stats"], actions.get(name, "move"), bool(rs["inventory"])
            )

        kpi["total_steps"] = step + 1

        # Snapshot frame
        frames.append({
            "step": step,
            "dyn_obs": set(dyn_obs),
            "robots": {
                name: {
                    "pos": rs["pos"],
                    "inventory": list(rs["inventory"]),
                    "completed": list(rs["completed"]),
                    "remaining": list(rs["remaining"]),
                    "trail": list(rs["trail"]),
                    "stats": dict(rs["stats"]),
                    "done": rs["done"],
                    "emergency": rs["emergency"],
                    "log": rs["log"][-3:] if rs["log"] else [],
                }
                for name, rs in robot_states.items()
            },
            "kpi": dict(kpi),
        })

        # Stop when all done
        if all(rs["done"] for rs in robot_states.values()):
            break

    return frames, kpi
