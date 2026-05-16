# 🏭 Warehouse Fleet Intelligence Platform

A next-generation multi-robot warehouse coordination system with:

- 🤖 **2 autonomous robots** with battery, health, velocity, collision risk
- 🧠 **AI Orchestrator** (Groq + Llama 3) assigns tasks intelligently
- 🗺️ **A* pathfinding + MAPF** — collision-free routing between robots
- 🚶 **Dynamic obstacles** — moving humans and forklifts, real-time rerouting
- ⚡ **Auto-charging** — robots return to station below 15% battery
- 📊 **Live KPI dashboard** — tasks/hour, idle time, collisions avoided, delivery time
- 🌑 **Dark futuristic UI** — industrial-grade interface with robot trails and stat bars
- 10×10 warehouse grid with 10 shelf locations, static obstacles, dispatch zone

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

```bash
git add .
git commit -m "v2: Fleet Intelligence Platform"
git push
```

Streamlit Cloud secrets: `GROQ_API_KEY = "gsk_..."`
