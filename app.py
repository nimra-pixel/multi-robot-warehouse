import streamlit as st
import json
import time
from groq import Groq
from warehouse_agents import (
    ORCHESTRATOR_SYSTEM, ROBOT_SYSTEM,
    ITEMS, DISPATCH_ZONE, ROBOT_START, ROBOT_COLORS
)
from warehouse_runner import parse_action, simulate_robot_step, all_items_collected
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
    padding: 10px 14px;
    margin: 5px 0;
    font-size: 13px;
    border-left: 4px solid #e2e8f0;
    background: #fff;
  }
  .log-card.move   { border-color: #3b82f6; }
  .log-card.pick   { border-color: #7c3aed; }
  .log-card.drop   { border-color: #10b981; }
  .log-card.done   { border-color: #f59e0b; background: #fffbeb; }
  .log-card.think  { border-color: #94a3b8; background: #f8fafc; }
  .robot-header    { font-weight: 700; font-size: 15px; margin: 12px 0 4px 0; }
  .status-bar      { padding: 8px 14px; border-radius: 8px; margin: 6px 0; font-size: 13px; }
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
    max_steps = st.slider("Max steps per robot", 10, 40, 25)
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
st.caption("Two AI agents control two robots to collaboratively fulfil warehouse orders using Groq + Llama 3.")

# ── Order selection ───────────────────────────────────────────────────────────
st.markdown("### 📋 Select Items to Fetch")
col1, col2, col3, col4 = st.columns(4)
item_list = list(ITEMS.keys())
selected = []
for i, item in enumerate(item_list):
    col = [col1, col2, col3, col4][i % 4]
    with col:
        if st.checkbox(f"📦 {item}", value=(i < 4), key=f"item_{item}"):
            selected.append(item)

preset_col1, preset_col2, preset_col3 = st.columns(3)
with preset_col1:
    if st.button("🎯 Quick order (4 items)", use_container_width=True):
        selected = item_list[:4]
        st.rerun()
with preset_col2:
    if st.button("📦 Full warehouse (all 8)", use_container_width=True):
        selected = item_list
        st.rerun()
with preset_col3:
    if st.button("🔀 Random 3 items", use_container_width=True):
        import random
        selected = random.sample(item_list, 3)
        st.rerun()

st.markdown(f"**Selected:** {', '.join(selected) if selected else 'None'}")
st.divider()

run_btn = st.button("▶ Start Mission", type="primary", disabled=not selected or not api_key)
if not api_key:
    st.warning("Enter your Groq API key in the sidebar to start.")
if not selected:
    st.info("Select at least one item to fetch.")


# ── Main pipeline ─────────────────────────────────────────────────────────────
def call_groq(client, system, user, max_tokens=300):
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


def run_mission(selected_items, api_key):
    client = Groq(api_key=api_key)

    # ── Step 1: Orchestrator assigns tasks ────────────────────────────────────
    st.markdown("### 🎯 Orchestrator — Assigning Tasks")
    with st.spinner("Orchestrator deciding assignments…"):
        orch_user = (
            f"Orders to fulfil: {selected_items}\n"
            f"Assign each item to Robot-A or Robot-B to balance the work."
        )
        raw_assign = call_groq(client, ORCHESTRATOR_SYSTEM, orch_user, max_tokens=200)

    try:
        raw_clean = raw_assign.strip().strip("```json").strip("```").strip()
        start = raw_clean.find("{"); end = raw_clean.rfind("}") + 1
        assignment = json.loads(raw_clean[start:end])
        assignment = {k: [i for i in v if i in selected_items] for k, v in assignment.items()}
    except Exception:
        # fallback: split evenly
        half = len(selected_items) // 2
        assignment = {
            "Robot-A": selected_items[:half] or selected_items,
            "Robot-B": selected_items[half:],
        }

    st.success(f"**Robot-A:** {assignment.get('Robot-A', [])}  |  **Robot-B:** {assignment.get('Robot-B', [])}")

    # ── Step 2: Init robot states ─────────────────────────────────────────────
    robot_states = {
        "Robot-A": {
            "pos": ROBOT_START["Robot-A"],
            "inventory": [],
            "completed": [],
            "assigned": assignment.get("Robot-A", []),
            "log": [],
            "done": False,
        },
        "Robot-B": {
            "pos": ROBOT_START["Robot-B"],
            "inventory": [],
            "completed": [],
            "assigned": assignment.get("Robot-B", []),
            "log": [],
            "done": False,
        },
    }

    # Mark robots with no assignments as done
    for name, rs in robot_states.items():
        if not rs["assigned"]:
            rs["done"] = True

    # ── Step 3: Live simulation ───────────────────────────────────────────────
    st.markdown("### 🤖 Live Simulation")
    grid_col, log_col = st.columns([1, 1])

    grid_placeholder = grid_col.empty()
    log_placeholder  = log_col.empty()

    step_count = 0

    def render_logs():
        html = ""
        for robot_name, rs in robot_states.items():
            color = ROBOT_COLORS[robot_name]
            inv   = rs["inventory"]
            done  = rs["done"]
            comp  = rs["completed"]
            html += (
                f'<div class="robot-header" style="color:{color}">'
                f'{"🏁" if done else "🤖"} {robot_name} '
                f'| pos {rs["pos"]} | carrying: {inv or "nothing"} | done: {comp}'
                f'</div>'
            )
            for entry in rs["log"][-6:]:
                action  = entry.get("action", "")
                thought = entry.get("thought", "")
                result  = entry.get("result", "")
                css     = action if action in ("move","pick","drop","done") else "think"
                html += (
                    f'<div class="log-card {css}">'
                    f'<b>{action.upper()}</b> — {result}<br>'
                    f'<span style="color:#94a3b8;font-size:11px">💭 {thought}</span>'
                    f'</div>'
                )
        return html

    # Initial render
    grid_placeholder.markdown(render_grid(robot_states), unsafe_allow_html=True)
    log_placeholder.markdown(render_logs(), unsafe_allow_html=True)

    while step_count < max_steps:
        if all_items_collected(robot_states):
            break

        for robot_name, rs in robot_states.items():
            if rs["done"]:
                continue
            if not rs["assigned"]:
                rs["done"] = True
                continue

            # Build robot prompt
            remaining = [i for i in rs["assigned"] if i not in rs["completed"]]
            if not remaining and not rs["inventory"]:
                rs["done"] = True
                continue

            robot_prompt = ROBOT_SYSTEM.format(
                robot_name=robot_name,
                position=rs["pos"],
                items=remaining,
                shelf_map={k: v for k, v in ITEMS.items() if k in rs["assigned"]},
            )

            context = (
                f"Current position: {rs['pos']}\n"
                f"Inventory: {rs['inventory']}\n"
                f"Items still to fetch: {remaining}\n"
                f"Items completed: {rs['completed']}\n"
                f"Dispatch zone at: {DISPATCH_ZONE}\n"
                f"What is your next single action?"
            )

            try:
                raw = call_groq(client, robot_prompt, context, max_tokens=150)
                action_obj = parse_action(raw)
            except Exception as e:
                action_obj = {"action": "move", "thought": str(e), "direction": "down", "target": None}

            robot_states[robot_name] = simulate_robot_step(rs, action_obj)

            # Re-render after each robot step
            grid_placeholder.markdown(render_grid(robot_states), unsafe_allow_html=True)
            log_placeholder.markdown(render_logs(), unsafe_allow_html=True)

            time.sleep(0.3)

        step_count += 1

    # ── Final summary ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Mission Summary")
    total_items = sum(len(rs["completed"]) for rs in robot_states.values())
    total_assigned = len(selected_items)
    success = total_items == total_assigned

    if success:
        st.success(f"✅ Mission Complete! All {total_items} items delivered to dispatch zone.")
    else:
        st.warning(f"⚠️ Mission ended. {total_items}/{total_assigned} items delivered.")

    scol1, scol2 = st.columns(2)
    for col, (name, rs) in zip([scol1, scol2], robot_states.items()):
        color = ROBOT_COLORS[name]
        with col:
            st.markdown(f'<b style="color:{color}">{name}</b>', unsafe_allow_html=True)
            st.markdown(f"- Assigned: {rs['assigned']}")
            st.markdown(f"- Delivered: {rs['completed']}")
            st.markdown(f"- Steps taken: {len(rs['log'])}")


# ── Trigger ───────────────────────────────────────────────────────────────────
if run_btn and selected and api_key:
    try:
        run_mission(selected, api_key)
    except Exception as e:
        st.error(f"Mission error: {e}")
