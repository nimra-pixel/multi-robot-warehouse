import streamlit as st
import json
import time
from groq import Groq
from warehouse_agents import (
    ORCHESTRATOR_SYSTEM,
    ITEMS, DISPATCH_ZONE, ROBOT_START, ROBOT_COLORS
)
from warehouse_runner import simulate_robot_full, all_items_collected
from warehouse_grid import render_grid

st.set_page_config(
    page_title="Multi-Robot Warehouse Coordinator",
    page_icon="🏭",
    layout="wide",
)

st.markdown("""
<style>
  .log-card {
    border-radius: 8px;
    padding: 8px 12px;
    margin: 4px 0;
    font-size: 13px;
    border-left: 4px solid #e2e8f0;
    background: #fff;
  }
  .log-card.move   { border-color: #3b82f6; }
  .log-card.pick   { border-color: #7c3aed; background: #faf5ff; }
  .log-card.drop   { border-color: #10b981; background: #f0fdf4; }
  .log-card.done   { border-color: #f59e0b; background: #fffbeb; }
  .robot-header    { font-weight: 700; font-size: 14px; margin: 10px 0 4px 0; }
</style>
""", unsafe_allow_html=True)

# ── Load key from secrets ─────────────────────────────────────────────────────
default_key = st.secrets.get("GROQ_API_KEY", "")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    st.markdown("🆓 Free Groq key at [console.groq.com](https://console.groq.com)")
    api_key = st.text_input("Groq API Key", value=default_key, type="password", placeholder="gsk_...")
    model = st.selectbox("Model", [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ])
    speed = st.slider("Animation speed (sec/step)", 0.05, 0.5, 0.15)
    st.divider()
    st.markdown("### 🗺️ Warehouse Map")
    st.markdown("**Grid:** 8×8  |  **Dispatch:** (7,7)")
    st.markdown("**Shelves:**")
    for item, pos in ITEMS.items():
        st.markdown(f"- `{item}` → {pos}")
    st.divider()
    st.markdown("### 🤖 Robots")
    for name, pos in ROBOT_START.items():
        color = ROBOT_COLORS[name]
        st.markdown(f'<span style="color:{color}">●</span> **{name}** starts at {pos}', unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏭 Multi-Robot Warehouse Coordinator")
st.caption("Orchestrator AI assigns tasks · Robots navigate autonomously · Groq + Llama 3")

# ── Order selection ───────────────────────────────────────────────────────────
st.markdown("### 📋 Select Items to Fetch")
item_list = list(ITEMS.keys())
import random as _random

# Preset buttons — must run BEFORE checkboxes so session_state is set first
pc1, pc2, pc3 = st.columns(3)
with pc1:
    if st.button("🎯 First 4 items", use_container_width=True):
        for i, item in enumerate(item_list):
            st.session_state[f"item_{item}"] = (i < 4)
with pc2:
    if st.button("📦 All 8 items", use_container_width=True):
        for item in item_list:
            st.session_state[f"item_{item}"] = True
with pc3:
    if st.button("🔀 Random 3", use_container_width=True):
        picks = set(_random.sample(item_list, 3))
        for item in item_list:
            st.session_state[f"item_{item}"] = (item in picks)

# Render checkboxes driven by session_state
col1, col2, col3, col4 = st.columns(4)
selected = []
for i, item in enumerate(item_list):
    col = [col1, col2, col3, col4][i % 4]
    with col:
        default = st.session_state.get(f"item_{item}", i < 4)
        if st.checkbox(f"📦 {item}", value=default, key=f"item_{item}"):
            selected.append(item)

st.markdown(f"**Selected:** {', '.join(selected) if selected else 'None'}")
st.divider()

run_btn = st.button("▶ Start Mission", type="primary", disabled=not selected or not api_key)
if not api_key:
    st.warning("Enter your Groq API key in the sidebar.")
if not selected:
    st.info("Select at least one item to fetch.")


# ── Orchestrator: uses LLM to assign tasks ────────────────────────────────────
def assign_tasks(selected_items, api_key):
    client = Groq(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=100,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": f"Items to assign: {selected_items}"},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        start = raw.find("{"); end = raw.rfind("}") + 1
        assignment = json.loads(raw[start:end])
        assignment = {k: [i for i in v if i in selected_items] for k, v in assignment.items()}
        # Ensure both robots exist
        if "Robot-A" not in assignment: assignment["Robot-A"] = []
        if "Robot-B" not in assignment: assignment["Robot-B"] = []
        # Ensure ALL selected items are assigned (fix LLM dropping items)
        assigned_all = assignment["Robot-A"] + assignment["Robot-B"]
        unassigned = [i for i in selected_items if i not in assigned_all]
        for i, item in enumerate(unassigned):
            key = "Robot-A" if i % 2 == 0 else "Robot-B"
            assignment[key].append(item)
        return assignment
    except Exception:
        half = len(selected_items) // 2
        return {
            "Robot-A": selected_items[:half] if half else selected_items,
            "Robot-B": selected_items[half:],
        }


# ── Main mission ──────────────────────────────────────────────────────────────
def run_mission(selected_items, api_key):

    # Step 1: Orchestrator assigns
    st.markdown("### 🎯 Orchestrator — Assigning Tasks")
    with st.spinner("Orchestrator thinking…"):
        assignment = assign_tasks(selected_items, api_key)

    st.success(f"**Robot-A:** {assignment['Robot-A']}  |  **Robot-B:** {assignment['Robot-B']}")

    # Step 2: Pre-compute full deterministic paths for both robots
    robot_a_state = {
        "name": "Robot-A",
        "pos": ROBOT_START["Robot-A"],
        "inventory": [],
        "completed": [],
        "assigned": assignment["Robot-A"],
    }
    robot_b_state = {
        "name": "Robot-B",
        "pos": ROBOT_START["Robot-B"],
        "inventory": [],
        "completed": [],
        "assigned": assignment["Robot-B"],
    }

    steps_a = simulate_robot_full(robot_a_state) if assignment["Robot-A"] else [{"action":"done","thought":"no tasks","result":"idle","pos":ROBOT_START["Robot-A"],"inventory":[],"completed":[]}]
    steps_b = simulate_robot_full(robot_b_state) if assignment["Robot-B"] else [{"action":"done","thought":"no tasks","result":"idle","pos":ROBOT_START["Robot-B"],"inventory":[],"completed":[]}]

    # Step 3: Animate both robots simultaneously
    st.markdown("### 🤖 Live Simulation")
    grid_col, log_col = st.columns([1, 1])
    grid_placeholder = grid_col.empty()
    log_placeholder  = log_col.empty()

    max_steps = max(len(steps_a), len(steps_b))

    # Current display state
    display = {
        "Robot-A": {"pos": ROBOT_START["Robot-A"], "inventory": [], "completed": [], "log": [], "assigned": assignment["Robot-A"]},
        "Robot-B": {"pos": ROBOT_START["Robot-B"], "inventory": [], "completed": [], "log": [], "assigned": assignment["Robot-B"]},
    }

    def render_logs():
        html = ""
        for rname, rs in display.items():
            color = ROBOT_COLORS[rname]
            html += (
                f'<div class="robot-header" style="color:{color}">'
                f'{"🏁" if rs.get("done") else "🤖"} {rname} | pos {rs["pos"]} | '
                f'carrying: {rs["inventory"] or "nothing"} | delivered: {rs["completed"]}'
                f'</div>'
            )
            for entry in rs["log"][-5:]:
                css = entry["action"]
                html += (
                    f'<div class="log-card {css}">'
                    f'<b>{entry["action"].upper()}</b> — {entry["result"]}<br>'
                    f'<span style="color:#94a3b8;font-size:11px">💭 {entry["thought"]}</span>'
                    f'</div>'
                )
        return html

    for i in range(max_steps):
        # Apply step i for each robot if available
        if i < len(steps_a):
            s = steps_a[i]
            display["Robot-A"]["pos"]       = s["pos"]
            display["Robot-A"]["inventory"] = s["inventory"]
            display["Robot-A"]["completed"] = s["completed"]
            display["Robot-A"]["log"].append(s)
            if s["action"] == "done":
                display["Robot-A"]["done"] = True

        if i < len(steps_b):
            s = steps_b[i]
            display["Robot-B"]["pos"]       = s["pos"]
            display["Robot-B"]["inventory"] = s["inventory"]
            display["Robot-B"]["completed"] = s["completed"]
            display["Robot-B"]["log"].append(s)
            if s["action"] == "done":
                display["Robot-B"]["done"] = True

        grid_placeholder.markdown(render_grid(display), unsafe_allow_html=True)
        log_placeholder.markdown(render_logs(), unsafe_allow_html=True)
        time.sleep(speed)

    # Step 4: Summary
    st.divider()
    st.markdown("### 📊 Mission Summary")
    total_delivered = len(display["Robot-A"]["completed"]) + len(display["Robot-B"]["completed"])
    total_assigned  = len(selected_items)

    if total_delivered >= total_assigned:
        st.success(f"✅ Mission Complete! All {total_delivered} items delivered to dispatch zone.")
    else:
        st.warning(f"⚠️ Mission ended. {total_delivered}/{total_assigned} items delivered.")

    sc1, sc2 = st.columns(2)
    for col, rname in zip([sc1, sc2], ["Robot-A", "Robot-B"]):
        color = ROBOT_COLORS[rname]
        rs = display[rname]
        with col:
            st.markdown(f'<b style="color:{color}">{rname}</b>', unsafe_allow_html=True)
            st.markdown(f"- Assigned: {rs['assigned']}")
            st.markdown(f"- Delivered: {rs['completed']}")
            st.markdown(f"- Steps taken: {len(rs['log'])}")


# ── Trigger ───────────────────────────────────────────────────────────────────
if run_btn and selected and api_key:
    try:
        run_mission(selected, api_key)
    except Exception as e:
        st.error(f"Mission error: {e}")
        import traceback
        st.code(traceback.format_exc())
