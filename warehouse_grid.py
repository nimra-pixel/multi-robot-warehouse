# warehouse_grid.py — Dark futuristic SVG grid renderer

from warehouse_config import (
    GRID_SIZE, ITEMS, DISPATCH_ZONE, CHARGING_STATIONS,
    STATIC_OBSTACLES, ROBOT_COLORS
)

CELL = 52
PAD  = 28

def _x(c): return PAD + c * CELL + CELL // 2
def _y(r): return PAD + r * CELL + CELL // 2
def _rx(c): return PAD + c * CELL
def _ry(r): return PAD + r * CELL

W = GRID_SIZE * CELL + PAD * 2
H = GRID_SIZE * CELL + PAD * 2

def render_grid(frame: dict) -> str:
    robots   = frame["robots"]
    dyn_obs  = frame.get("dyn_obs", set())
    all_completed = []
    for rs in robots.values():
        all_completed.extend(rs["completed"])
        all_completed.extend(rs["inventory"])

    lines = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;max-width:{W}px;background:#0a0f1e;border-radius:14px;'
        f'border:1px solid #1e3a5f;">',
        # Grid background glow
        f'<defs>'
        f'<radialGradient id="glow_a" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="#00d4ff" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="#00d4ff" stop-opacity="0"/>'
        f'</radialGradient>'
        f'<radialGradient id="glow_b" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="#ff6b35" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="#ff6b35" stop-opacity="0"/>'
        f'</radialGradient>'
        f'</defs>',
    ]

    # Draw cells
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            pos = (r, c)
            rx, ry = _rx(c), _ry(r)
            if pos in STATIC_OBSTACLES:
                fill = "#1a2744"
                stroke = "#2a3f6f"
            elif pos == DISPATCH_ZONE:
                fill = "#0d3320"
                stroke = "#00ff88"
            elif pos in CHARGING_STATIONS.values():
                fill = "#1a1a0d"
                stroke = "#ffd700"
            elif pos in dyn_obs:
                fill = "#3d1a00"
                stroke = "#ff4400"
            else:
                fill = "#0d1526"
                stroke = "#1e3a5f"
            lines.append(
                f'<rect x="{rx}" y="{ry}" width="{CELL}" height="{CELL}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="0.8" rx="2"/>'
            )

    # Axis labels
    for i in range(GRID_SIZE):
        lines.append(f'<text x="{_x(i)}" y="{PAD-10}" text-anchor="middle" font-size="9" fill="#334e6e" font-family="monospace">{i}</text>')
        lines.append(f'<text x="{PAD-14}" y="{_y(i)+4}" text-anchor="middle" font-size="9" fill="#334e6e" font-family="monospace">{i}</text>')

    # Static obstacles label
    for pos in STATIC_OBSTACLES:
        r, c = pos
        lines.append(f'<text x="{_x(c)}" y="{_y(r)+4}" text-anchor="middle" font-size="9" fill="#334e6e">▓</text>')

    # Charging stations
    for name, pos in CHARGING_STATIONS.items():
        r, c = pos
        lines.append(f'<text x="{_x(c)}" y="{_y(r)-4}" text-anchor="middle" font-size="9" fill="#ffd700">⚡</text>')
        lines.append(f'<text x="{_x(c)}" y="{_y(r)+8}" text-anchor="middle" font-size="7" fill="#ffd700">CHG</text>')

    # Dynamic obstacles (humans/forklifts)
    for pos in dyn_obs:
        r, c = pos
        lines.append(f'<text x="{_x(c)}" y="{_y(r)+5}" text-anchor="middle" font-size="14">🚶</text>')

    # Dispatch zone
    dr, dc = DISPATCH_ZONE
    lines.append(f'<text x="{_x(dc)}" y="{_y(dr)-6}" text-anchor="middle" font-size="8" fill="#00ff88" font-weight="bold">DISPATCH</text>')
    lines.append(f'<text x="{_x(dc)}" y="{_y(dr)+8}" text-anchor="middle" font-size="12">📦</text>')

    # Item shelves
    for item, (r, c) in ITEMS.items():
        if item in all_completed:
            color, emoji, label_color = "#1e3a2e", "✓", "#00ff88"
        else:
            color, emoji, label_color = "#7c3aed", "📦", "#a78bfa"
        lines.append(f'<rect x="{_rx(c)+4}" y="{_ry(r)+4}" width="{CELL-8}" height="{CELL-8}" fill="{color}" rx="4" opacity="0.6"/>')
        lines.append(f'<text x="{_x(c)}" y="{_y(r)-2}" text-anchor="middle" font-size="11">{emoji}</text>')
        lines.append(f'<text x="{_x(c)}" y="{_y(r)+10}" text-anchor="middle" font-size="7" fill="{label_color}" font-family="monospace">{item}</text>')

    # Robot trails
    for name, rs in robots.items():
        color = ROBOT_COLORS[name]
        trail = rs["trail"]
        for i, pos in enumerate(trail[:-1]):
            r, c = pos
            alpha = int(255 * (i / len(trail)) * 0.4)
            hex_alpha = format(alpha, '02x')
            lines.append(
                f'<circle cx="{_x(c)}" cy="{_y(r)}" r="3" '
                f'fill="{color}{hex_alpha}" />'
            )

    # Robots
    robot_list = list(robots.items())
    for name, rs in robot_list:
        pos = rs["pos"]
        r, c = pos
        color = ROBOT_COLORS[name]
        cx, cy = _x(c), _y(r)
        emergency = rs.get("emergency", False)

        # Glow effect
        glow_id = "glow_a" if name == "Robot-A" else "glow_b"
        lines.append(f'<circle cx="{cx}" cy="{cy}" r="20" fill="url(#{glow_id})"/>')

        # Robot body
        ring_color = "#ff0000" if emergency else color
        lines.append(f'<circle cx="{cx}" cy="{cy}" r="14" fill="#0a0f1e" stroke="{ring_color}" stroke-width="2"/>')
        label = "A" if name == "Robot-A" else "B"
        lines.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="13" fill="{color}" font-weight="bold" font-family="monospace">{label}</text>')

        # Inventory badge
        inv = len(rs["inventory"])
        if inv > 0:
            lines.append(f'<circle cx="{cx+12}" cy="{cy-12}" r="7" fill="#7c3aed"/>')
            lines.append(f'<text x="{cx+12}" y="{cy-8}" text-anchor="middle" font-size="8" fill="white">{inv}</text>')

        # Emergency indicator
        if emergency:
            lines.append(f'<text x="{cx}" y="{cy-18}" text-anchor="middle" font-size="10">⚠️</text>')

        # Battery bar under robot
        batt = rs["stats"].get("battery", 100)
        batt_color = "#00ff88" if batt > 50 else "#ffd700" if batt > 20 else "#ff4444"
        bar_w = 28
        filled = int(bar_w * batt / 100)
        lines.append(f'<rect x="{cx - bar_w//2}" y="{cy+17}" width="{bar_w}" height="3" fill="#1e3a5f" rx="1"/>')
        lines.append(f'<rect x="{cx - bar_w//2}" y="{cy+17}" width="{filled}" height="3" fill="{batt_color}" rx="1"/>')

    lines.append("</svg>")
    return "\n".join(lines)
