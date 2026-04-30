# MRM Vault — Command Centre
**Dash + Cytoscape | Solytics Partners**

---

## ⚡ Run locally (30 seconds)

```bash
# Step 1 — Install
pip install dash dash-cytoscape gunicorn

# Step 2 — Run
python app.py

# Step 3 — Open browser
http://localhost:8050
```

That's it. No config needed.

---

## 🚀 Deploy on Render (free public URL — 10 minutes)

### Step 1 — Push to GitHub

```bash
# In your project folder (where app.py lives):
git init
git add .
git commit -m "MRM Vault initial commit"

# Create repo on github.com → New repository → name it "mrm-vault"
# Then:
git remote add origin https://github.com/YOUR_USERNAME/mrm-vault.git
git branch -M main
git push -u origin main
```

### Step 2 — Deploy on Render

1. Go to **https://render.com** → Sign up free (use GitHub login)
2. Click **New +** → **Web Service**
3. Connect your GitHub account → Select the `mrm-vault` repo
4. Fill these fields:

| Field | Value |
|-------|-------|
| Name | `mrm-vault` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:server --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT` |
| Instance Type | **Free** |

5. Click **Create Web Service**
6. Wait ~3 minutes for build
7. Your URL: `https://mrm-vault.onrender.com` ✅

### Step 3 — Share the URL

Copy the Render URL and share. Anyone with the link can use it — no login required.

---

## 📁 Project files

```
mrm-vault/
├── app.py           ← Main dashboard (Dash + Cytoscape)
├── data_model.py    ← All data: nodes, links, permissions, audit, API log
├── graph_engine.py  ← BFS traversal, impact trace, stage machine
├── requirements.txt ← Python dependencies
├── Procfile         ← Render start command
└── README.md        ← This file
```

---

## 🖥 Dashboard layout

```
┌─ Sidebar (navy) ───┬─ Top bar (KPI strip) ──────────────────────────────┐
│ Logo               │ MRM Vault  · entity · links · score · status       │
│ Search             ├─ [Deep-dive drawer — slides in on sidebar click] ───┤
│ Depth 1|2|All      │                                                     │
│ Category filter    ├─ Graph (centre) ──────────┬─ Detail Panel ─────────┤
│ Layout picker      │                            │ [Overview][Linked]     │
│ Quick access       │  Cytoscape interactive     │ [Perms][Attrs][Activity│
│ ─────────────      │  force-directed graph      │                        │
│ Deep Dive tabs     │  Drag · Zoom · Click       │ • Entity header        │
│ 📦 Entity System   │                            │ • Score bar            │
│ 🔗 Relationships   ├─ Relationship Table ───────│ • Downstream impact    │
│ ⚙ Workflows        │ Source → Rel → Target      │ • Upstream deps        │
│ 🔐 Permissions     │ with cardinality labels     │ • Linked entities      │
│ ⏱ Execution        └────────────────────────────│ • Linked workflows     │
│ 🌳 Versions                                     │ • Permissions (NOW)    │
│ 📋 Audit                                        │ • Attributes by section│
│ 🌐 API Log                                      │ • Audit + events       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key interactions

| Action | Result |
|--------|--------|
| Click any node on graph | Detail panel updates instantly |
| Click **Linked** tab | See entity chips + workflow chips with progress bars |
| Click any chip | Navigates to that entity |
| Click sidebar deep-dive | Drawer slides in with full tables |
| Click **Advance Stage** | Moves workflow to next stage |
| Change depth | Graph expands/contracts |
| Change layout | Graph re-arranges (animated) |

---

## 🔧 Common issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: dash_cytoscape` | `pip install dash-cytoscape` |
| Port 8050 in use | `python app.py` → change port in last line |
| Render build fails | Check `requirements.txt` — exact versions matter |
| Slow on free tier | Normal — free Render spins down after 15min idle, takes ~30s to wake |
