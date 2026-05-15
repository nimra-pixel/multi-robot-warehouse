# warehouse_grid.py — Renders the warehouse as an SVG grid

from warehouse_agents import ITEMS, DISPATCH_ZONE, ROBOT_COLORS

CELL = 60
GRID = 8
PAD = 30

def render_grid(robot_states: dict) -> str:
    W = GRID * CELL + PAD * 2
    H = GRID * CELL + PAD * 2

    lines = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;max-width:{W}px;background:#f8fafc;border-radius:12px;">',
    ]

    # Grid lines + cells
    for r in range(GRID):
        for c in range(GRID):
            x = PAD + c * CELL
            y = PAD + r * CELL
            fill = "#f1f5f9"
            if (r, c) == DISPATCH_ZONE:
                fill = "#dcfce7"
            lines.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'fill="{fill}" stroke="#cbd5e1" stroke-width="1"/>'
            )

    # Row/col labels
    for i in range(GRID):
        cx = PAD + i * CELL + CELL // 2
        cy = PAD + i * CELL + CELL // 2
        lines.append(f'<text x="{cx}" y="{PAD - 8}" text-anchor="middle" font-size="10" fill="#94a3b8">{i}</text>')
        lines.append(f'<text x="{PAD - 10}" y="{cy + 4}" text-anchor="middle" font-size="10" fill="#94a3b8">{i}</text>')

    # Dispatch zone label
    dx = PAD + DISPATCH_ZONE[1] * CELL + CELL // 2
    dy = PAD + DISPATCH_ZONE[0] * CELL + CELL // 2
    lines.append(f'<text x="{dx}" y="{dy - 6}" text-anchor="middle" font-size="9" fill="#16a34a" font-weight="bold">DISPATCH</text>')
    lines.append(f'<text x="{dx}" y="{dy + 8}" text-anchor="middle" font-size="9" fill="#16a34a">📦</text>')

    # Item shelves
    collected_all = []
    for rs in robot_states.values():
        collected_all.extend(rs.get("completed", []))
        collected_all.extend(rs.get("inventory", []))

    for item, (r, c) in ITEMS.items():
        x = PAD + c * CELL + CELL // 2
        y = PAD + r * CELL + CELL // 2
        if item in collected_all:
            color = "#94a3b8"
            emoji = "✓"
        else:
            color = "#7c3aed"
            emoji = "📦"
        lines.append(f'<text x="{x}" y="{y - 4}" text-anchor="middle" font-size="10" fill="{color}">{emoji}</text>')
        lines.append(f'<text x="{x}" y="{y + 10}" text-anchor="middle" font-size="8" fill="{color}">{item}</text>')

    # Robots
    robot_list = list(robot_states.items())
    for name, rs in robot_list:
        pos = rs["pos"]
        r, c = pos
        color = ROBOT_COLORS.get(name, "#64748b")
        cx = PAD + c * CELL + CELL // 2
        cy = PAD + r * CELL + CELL // 2

        # Offset if two robots on same cell
        offsets = {"Robot-A": -8, "Robot-B": 8}
        offset = offsets.get(name, 0)
        other_positions = [rs2["pos"] for n2, rs2 in robot_list if n2 != name]
        if pos not in other_positions:
            offset = 0

        rx = cx + offset
        label = "A" if name == "Robot-A" else "B"
        inv_count = len(rs.get("inventory", []))

        lines.append(f'<circle cx="{rx}" cy="{cy}" r="16" fill="{color}" opacity="0.9"/>')
        lines.append(f'<text x="{rx}" y="{cy + 5}" text-anchor="middle" font-size="13" fill="white" font-weight="bold">{label}</text>')
        if inv_count > 0:
            lines.append(f'<circle cx="{rx+12}" cy="{cy-12}" r="8" fill="#ef4444"/>')
            lines.append(f'<text x="{rx+12}" y="{cy-8}" text-anchor="middle" font-size="9" fill="white">{inv_count}</text>')

    # Legend
    ly = H - 16
    lines.append(f'<text x="{PAD}" y="{ly}" font-size="10" fill="#3b82f6">● Robot-A</text>')
    lines.append(f'<text x="{PAD + 80}" y="{ly}" font-size="10" fill="#f59e0b">● Robot-B</text>')
    lines.append(f'<text x="{PAD + 160}" y="{ly}" font-size="10" fill="#7c3aed">📦 Shelf</text>')
    lines.append(f'<text x="{PAD + 240}" y="{ly}" font-size="10" fill="#16a34a">■ Dispatch</text>')

    lines.append("</svg>")
    return "\n".join(lines)
