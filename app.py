import streamlit as st
import json
import time
import random
import math
from groq import Groq
from warehouse_config import (
    ITEMS, DISPATCH_ZONE, ROBOT_START, ROBOT_COLORS,
    ORCHESTRATOR_SYSTEM, CHARGING_STATIONS
)
from warehouse_engine import simulate_fleet
from warehouse_grid import render_grid

st.set_page_config(
    page_title="Warehouse Fleet Intelligence Platform",
    page_icon="🏭",
    layout="wide",
)

# ── Dark UI CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

  html, body, [class*="css"] {
    background-color: #0a0f1e !important;
    color: #c9d8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
  }
  .stApp { background-color: #0a0f1e !important; }
  .block-container { padding-top: 1.5rem !important; }

  h1, h2, h3 { color: #00d4ff !important; letter-spacing: 1px; }
  .stCaption  { color: #5a7a9a !important; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background-color: #060c1a !important;
    border-right: 1px solid #1e3a5f !important;
  }

  /* Buttons */
  .stButton > button {
    background: #0d1f3c !important;
    color: #00d4ff !important;
    border: 1px solid #00d4ff44 !important;
    border-radius: 6px !important;
    font-family: monospace !important;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    background: #00d4ff22 !important;
    border-color: #00d4ff !important;
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00d4ff22, #7c3aed22) !important;
    border: 1px solid #00d4ff !important;
    color: #00d4ff !important;
    font-weight: bold !important;
  }

  /* Metrics */
  [data-testid="stMetric"] {
    background: #0d1526 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 8px !important;
    padding: 10px !important;
  }
  [data-testid="stMetricValue"] { color: #00d4ff !important; font-size: 1.4rem !important; }
  [data-testid="stMetricLabel"] { color: #5a7a9a !important; font-size: 0.7rem !important; }

  /* Checkboxes */
  .stCheckbox label { color: #8aaccc !important; font-size: 12px !important; }

  /* Selectbox / slider */
  .stSelectbox label, .stSlider label { color: #5a7a9a !important; font-size: 12px !important; }

  /* Log cards */
  .log-card {
    border-radius: 6px;
    padding: 7px 12px;
    margin: 3px 0;
    font-size: 11px;
    font-family: monospace;
    border-left: 3px solid #1e3a5f;
    background: #0d1526;
    color: #8aaccc;
  }
  .log-card.move   { border-color: #00d4ff44; }
  .log-card.pick   { border-color: #7c3aed; background: #130d26; }
  .log-card.drop   { border-color: #00ff88; background: #0a1f14; }
  .log-card.done   { border-color: #ffd700; background: #1a1a0d; }
  .log-card.wait   { border-color: #ff440044; }
  .log-card.charge { border-color: #ffd700; background: #1a1500; }
  .log-card.emergency { border-color: #ff4444; background: #1f0a0a; }

  .robot-header {
    font-weight: 700;
    font-size: 13px;
    margin: 10px 0 4px 0;
    font-family: monospace;
    letter-spacing: 1px;
  }
  .stat-bar-label { font-size: 10px; color: #5a7a9a; font-family: monospace; }

  /* Progress bar */
  .stProgress > div > div { background: #00d4ff !important; }

  /* Divider */
  hr { border-color: #1e3a5f !important; }

  /* Expander */
  .streamlit-expanderHeader { color: #00d4ff !important; }
  [data-testid="stExpander"] { border: 1px solid #1e3a5f !important; background: #0d1526 !important; }

  /* Text input */
  .stTextInput input {
    background: #0d1526 !important;
    border: 1px solid #1e3a5f !important;
    color: #c9d8f0 !important;
    font-family: monospace !important;
  }

  /* Success/warning/error */
  .stSuccess { background: #0a1f14 !important; border: 1px solid #00ff88 !important; color: #00ff88 !important; }
  .stWarning { background: #1a1500 !important; border: 1px solid #ffd700 !important; color: #ffd700 !important; }
  .stError   { background: #1f0a0a !important; border: 1px solid #ff4444 !important; color: #ff4444 !important; }
</style>
""", unsafe_allow_html=True)

# ── Secrets ───────────────────────────────────────────────────────────────────
default_key = st.secrets.get("GROQ_API_KEY", "")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ FLEET CONFIG")
    st.markdown('<span style="color:#5a7a9a;font-size:11px">🆓 Free key: console.groq.com</span>', unsafe_allow_html=True)
    api_key = st.text_input("GROQ API KEY", value=default_key, type="password", placeholder="gsk_...")
    model = st.selectbox("LLM MODEL", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])
    speed = st.slider("ANIMATION SPEED (s/frame)", 0.02, 0.3, 0.08)
    st.divider()

    st.markdown("### 🗺️ WAREHOUSE MAP")
    st.markdown(f'<span style="color:#5a7a9a;font-size:11px">Grid: 10×10 | Dispatch: {DISPATCH_ZONE}</span>', unsafe_allow_html=True)
    st.markdown('<span style="color:#5a7a9a;font-size:11px">Shelves:</span>', unsafe_allow_html=True)
    for item, pos in ITEMS.items():
        st.markdown(f'<span style="color:#7c3aed;font-size:11px">▸ `{item}` → {pos}</span>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🤖 ROBOTS")
    for name, pos in ROBOT_START.items():
        color = ROBOT_COLORS[name]
        st.markdown(f'<span style="color:{color};font-size:12px">◉ {name}</span> <span style="color:#5a7a9a;font-size:11px">starts {pos} | charge {CHARGING_STATIONS[name]}</span>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<span style="color:#5a7a9a;font-size:10px">⚠️ Static obstacles: 6 cells<br>🚶 Dynamic: 3 humans + 1 forklift<br>🔋 Auto-charge below 15%</span>', unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🏭 WAREHOUSE FLEET INTELLIGENCE PLATFORM")
st.caption("Multi-Robot Coordination · MAPF · Dynamic Obstacles · Real-Time KPIs · Powered by Groq + Llama 3")
st.divider()

# ── Item selection ────────────────────────────────────────────────────────────
st.markdown("### 📋 MISSION ORDERS")
item_list = list(ITEMS.keys())

pc1, pc2, pc3, pc4 = st.columns(4)
with pc1:
    if st.button("🎯 First 5", use_container_width=True):
        for i, item in enumerate(item_list):
            st.session_state[f"item_{item}"] = (i < 5)
with pc2:
    if st.button("📦 All 10", use_container_width=True):
        for item in item_list:
            st.session_state[f"item_{item}"] = True
with pc3:
    if st.button("🔀 Random 4", use_container_width=True):
        picks = set(random.sample(item_list, 4))
        for item in item_list:
            st.session_state[f"item_{item}"] = (item in picks)
with pc4:
    if st.button("🧹 Clear", use_container_width=True):
        for item in item_list:
            st.session_state[f"item_{item}"] = False

cols = st.columns(5)
selected = []
for i, item in enumerate(item_list):
    with cols[i % 5]:
        default = st.session_state.get(f"item_{item}", i < 5)
        if st.checkbox(f"📦 {item}", value=default, key=f"item_{item}"):
            selected.append(item)

st.markdown(f'<span style="color:#00d4ff;font-size:12px">SELECTED: {", ".join(selected) if selected else "none"}</span>', unsafe_allow_html=True)
st.divider()

run_btn = st.button("▶ LAUNCH MISSION", type="primary", disabled=not selected or not api_key)
if not api_key:
    st.warning("⚠️ GROQ API KEY REQUIRED")
if not selected:
    st.markdown('<span style="color:#5a7a9a;font-size:12px">Select items above to begin mission</span>', unsafe_allow_html=True)


# ── Orchestrator ──────────────────────────────────────────────────────────────
def assign_tasks(selected_items, api_key):
    client = Groq(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=120,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": f"Assign these items to Robot-A and Robot-B: {selected_items}"},
            ],
        )
        raw = resp.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        s = raw.find("{"); e = raw.rfind("}") + 1
        assignment = json.loads(raw[s:e])
        assignment = {k: [i for i in v if i in selected_items] for k, v in assignment.items()}
        if "Robot-A" not in assignment: assignment["Robot-A"] = []
        if "Robot-B" not in assignment: assignment["Robot-B"] = []
        # Ensure all items assigned
        assigned_all = assignment["Robot-A"] + assignment["Robot-B"]
        unassigned = [i for i in selected_items if i not in assigned_all]
        for idx, item in enumerate(unassigned):
            key = "Robot-A" if idx % 2 == 0 else "Robot-B"
            assignment[key].append(item)
        return assignment
    except Exception:
        half = len(selected_items) // 2
        return {
            "Robot-A": selected_items[:half] or selected_items,
            "Robot-B": selected_items[half:],
        }


# ── KPI Dashboard ─────────────────────────────────────────────────────────────
def render_kpi(kpi, robot_frame, total_items):
    delivered = kpi.get("total_delivered", 0)
    steps = kpi.get("total_steps", 0)
    avoided = kpi.get("collisions_avoided", 0)
    rerouts = kpi.get("emergency_rerouts", 0)
    dt = kpi.get("delivery_times", [])
    avg_dt = round(sum(dt)/len(dt), 1) if dt else "--"
    idle_a = kpi.get("idle_steps", {}).get("Robot-A", 0)
    idle_b = kpi.get("idle_steps", {}).get("Robot-B", 0)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("📦 DELIVERED", f"{delivered}/{total_items}")
    k2.metric("⏱ STEPS", steps)
    k3.metric("🛡 COLLISIONS AVOIDED", avoided)
    k4.metric("⚠️ EMERGENCY REROUTS", rerouts)
    k5.metric("⏳ AVG DELIVERY", f"{avg_dt}s")
    k6.metric("💤 IDLE (A/B)", f"{idle_a}/{idle_b}")

    # Robot stat bars
    sc1, sc2 = st.columns(2)
    for col, name in zip([sc1, sc2], ["Robot-A", "Robot-B"]):
        rs = robot_frame.get(name, {})
        stats = rs.get("stats", {})
        color = ROBOT_COLORS[name]
        with col:
            batt = stats.get("battery", 100)
            health = stats.get("health", 100)
            vel = stats.get("velocity", 1.0)
            risk = stats.get("collision_risk", 0.0)
            emergency = rs.get("emergency", False)

            label = "⚠️ EMERGENCY" if emergency else ("✅ ACTIVE" if not rs.get("done") else "🏁 DONE")
            st.markdown(
                f'<div style="background:#0d1526;border:1px solid {color}44;border-radius:8px;padding:10px;margin:4px 0;">'
                f'<span style="color:{color};font-weight:bold;font-size:13px">◉ {name}</span> '
                f'<span style="color:#5a7a9a;font-size:10px">{label}</span><br>'
                f'<span style="color:#5a7a9a;font-size:10px">🔋 Battery</span><br>'
                f'<div style="background:#1e3a5f;border-radius:3px;height:6px;margin:2px 0 6px 0;">'
                f'<div style="background:{"#00ff88" if batt>50 else "#ffd700" if batt>20 else "#ff4444"};'
                f'width:{batt}%;height:6px;border-radius:3px;"></div></div>'
                f'<span style="color:#5a7a9a;font-size:10px">❤️ Health</span><br>'
                f'<div style="background:#1e3a5f;border-radius:3px;height:6px;margin:2px 0 6px 0;">'
                f'<div style="background:#00d4ff;width:{health:.0f}%;height:6px;border-radius:3px;"></div></div>'
                f'<span style="color:#5a7a9a;font-size:10px">⚡ Velocity: {vel} m/s &nbsp;|&nbsp; ⚠️ Risk: {risk:.0%}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Log renderer ──────────────────────────────────────────────────────────────
def render_logs(robots):
    html = ""
    for name, rs in robots.items():
        color = ROBOT_COLORS[name]
        pos = rs["pos"]
        inv = rs["inventory"]
        comp = rs["completed"]
        done = rs.get("done", False)
        emg = rs.get("emergency", False)

        status = "🏁 DONE" if done else "⚠️ EMERGENCY" if emg else "🤖 ACTIVE"
        html += (
            f'<div class="robot-header" style="color:{color}">'
            f'{status} {name} | pos={pos} | carrying={inv or "∅"} | delivered={len(comp)}'
            f'</div>'
        )
        for entry in rs.get("log", []):
            action = entry.get("action","move")
            css = "emergency" if emg and action=="move" else action
            html += (
                f'<div class="log-card {css}">'
                f'<b>{action.upper()}</b> {entry.get("result","")}<br>'
                f'<span style="color:#334e6e">💭 {entry.get("thought","")}</span>'
                f'</div>'
            )
    return html


# ── Main mission ──────────────────────────────────────────────────────────────
def run_mission(selected_items, api_key):
    # Orchestrator
    st.markdown("### 🎯 ORCHESTRATOR — TASK ASSIGNMENT")
    with st.spinner("Fleet AI assigning tasks…"):
        assignment = assign_tasks(selected_items, api_key)
    st.success(f"✅ Robot-A: {assignment['Robot-A']}  |  Robot-B: {assignment['Robot-B']}")

    # Pre-compute simulation
    with st.spinner("Computing optimal fleet paths (A* + MAPF)…"):
        frames, final_kpi = simulate_fleet(assignment, ROBOT_START)

    st.markdown(f'<span style="color:#5a7a9a;font-size:12px">Simulation ready — {len(frames)} frames computed</span>', unsafe_allow_html=True)
    st.divider()

    # Layout
    st.markdown("### 🤖 LIVE FLEET OPERATIONS")
    kpi_container  = st.container()
    grid_col, log_col = st.columns([3, 2])
    grid_ph = grid_col.empty()
    log_ph  = log_col.empty()
    prog    = st.progress(0, text="Mission in progress…")

    total_items = len(selected_items)

    for i, frame in enumerate(frames):
        with kpi_container:
            render_kpi(frame["kpi"], frame["robots"], total_items)

        grid_ph.markdown(render_grid(frame), unsafe_allow_html=True)
        log_ph.markdown(render_logs(frame["robots"]), unsafe_allow_html=True)
        prog.progress(int((i+1)/len(frames)*100), text=f"Step {i+1}/{len(frames)}")
        time.sleep(speed)

    prog.progress(100, text="Mission complete ✅")

    # Final summary
    st.divider()
    st.markdown("### 📊 MISSION DEBRIEF")
    delivered = final_kpi.get("total_delivered", 0)
    if delivered >= total_items:
        st.success(f"✅ MISSION COMPLETE — All {delivered} items delivered!")
    else:
        st.warning(f"⚠️ MISSION ENDED — {delivered}/{total_items} items delivered")

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total Steps",      final_kpi.get("total_steps", 0))
    d2.metric("Collisions Avoided", final_kpi.get("collisions_avoided", 0))
    d3.metric("Emergency Rerouts",  final_kpi.get("emergency_rerouts", 0))
    dt = final_kpi.get("delivery_times", [])
    d4.metric("Avg Delivery Time", f"{round(sum(dt)/len(dt),1) if dt else '--'} steps")

    with st.expander("📋 Full KPI Report"):
        st.json(final_kpi)


# ── Trigger ───────────────────────────────────────────────────────────────────
if run_btn and selected and api_key:
    try:
        run_mission(selected, api_key)
    except Exception as e:
        st.error(f"⚠️ MISSION ERROR: {e}")
        import traceback
        st.code(traceback.format_exc())
