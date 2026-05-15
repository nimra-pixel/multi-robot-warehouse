# 🏭 Multi-Robot Warehouse Coordinator

A multi-agent AI system where two autonomous robots collaborate to fulfil warehouse orders — powered by **Groq (free)** + Llama 3 + Streamlit.

---

## How It Works

```
User selects items to fetch
        │
        ▼
Orchestrator Agent (Llama 3)
  └── Assigns items to Robot-A and Robot-B
        │
        ├── Robot-A Agent → plans moves → navigates → picks items → drops at dispatch
        └── Robot-B Agent → plans moves → navigates → picks items → drops at dispatch
```

- **8×8 warehouse grid** with 8 shelf locations and a dispatch zone at (7,7)
- **Orchestrator** balances the item load between robots
- **Each robot** is its own LLM agent reasoning step-by-step
- **Live SVG grid** shows both robots moving in real time
- **Side-by-side logs** show each robot's thoughts and actions

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste your free Groq API key in the sidebar → select items → click **Start Mission**.

---

## Deploy to Streamlit Cloud

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/multi-robot-warehouse.git
git push -u origin main
```

Then on [share.streamlit.io](https://share.streamlit.io):
- Main file: `app.py`
- Secrets: `GROQ_API_KEY = "gsk_..."`

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI + mission orchestration |
| `warehouse_agents.py` | Agent system prompts, item/robot definitions |
| `warehouse_runner.py` | Robot movement simulation logic |
| `warehouse_grid.py` | SVG grid renderer |
| `requirements.txt` | groq + streamlit only |
