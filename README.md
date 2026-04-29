# MRM Vault | Relationship Explorer — Streamlit Dashboard

Built from 10 KT session transcripts (Solytics Partners MRM Vault product).

## Quick start (3 steps)

```bash
# 1. Install dependencies
pip install streamlit pandas

# 2. Navigate to the project folder
cd mrm_vault_dashboard

# 3. Launch
streamlit run app.py
```

Opens at http://localhost:8501

---

## Project structure

```
mrm_vault_dashboard/
├── app.py          — Streamlit UI: graph, detail panel, 4 tabs, sidebar
├── data_model.py   — All entities, attributes, links, REL_TYPES, STAGE_TRANSITIONS
├── graph_engine.py — Traversal: impact_trace, upstream_trace, advance_stage
└── requirements.txt
```

## What's in the dashboard

**Graph tab**
- SVG relationship graph with radial layout, pan, zoom
- Edges coloured by category: lineage (blue), governance (purple), validation (teal), monitoring (green)
- Click "Connected nodes" buttons to navigate
- Category filter in sidebar to isolate one rel type
- Relationship table below graph with cardinality column
- CSV export (includes cardinality, category, and edge notes)

**Inventory tab**
- Full entity sheet — every node as a row
- Filter by type (Entity / Workflow) and risk (High / Medium / Low)
- Click any row to select and inspect in the graph

**Relationship table tab**
- All visible links with typed, directed relationship labels
- Expandable edge notes explaining the business reason for each link

**Attribute schema tab**
- Common attributes (present on all entity types)
- Entity-specific sub-tables: Model, Assessment, Subprocess, Finding, Use Case, Query
- Stage transition machine per workflow subtype

**Detail panel** (right side of Graph tab)
- Derived risk score (base + upstream dependency + status penalties)
- Downstream impact trace (directed BFS following source→target)
- Upstream dependencies (directed BFS following target→source)
- Consumer display for sink nodes (datasets with no outgoing edges)
- Relationship category breakdown (outgoing / incoming counts)
- Outgoing and incoming links with cardinality and category badges
- Lifecycle stages with "Advance stage" button
- Attribute sub-table (zoom-in view of entity-specific attributes)
- Artifacts list
- Recent activity log

## Key logic

### Impact tracing
`impact_trace(node_id)` — follows outgoing edges (source→target).
"If Dataset A degrades, what breaks?" → traverses downstream.

`upstream_trace(node_id)` — follows incoming edges (target→source).
"What does Credit Risk Model depend on?" → traverses upstream.

Both seed the visited set with `node_id` to handle graph cycles correctly.

### Sink nodes
Dataset A has no outgoing edges. `impact_trace` correctly returns `[]`.
The UI shows `get_consumers()` instead — who directly depends on this node.

### State machine
`advance_stage("validation_workflow")` moves one stage forward.
When it reaches "Validation Sign-off", the Approval Workflow is automatically
unblocked — its first stage changes from `pending` to `current`.

### Risk score
`score = base(risk) + upstream_count×3 + status_penalty + degraded_upstream×8`
MRM Policy "Under Review" is upstream of Credit Risk Model → adds 8 to score.

## Demo journey
1. Start with **Credit Risk Model** → see 5 outgoing links, downstream impact
2. Click **Dataset A** in connected nodes → see "Direct consumers" (no outgoing edges)
3. Click **Validation Workflow** → advance a stage → watch Approval Workflow change
4. Switch to **2 hops** depth → see full picture
5. Use **Category filter = Governance** → isolate policy links
6. Open **Inventory tab** → click any row to navigate
7. Open **Attribute schema tab** → explore the full entity sub-table definitions
