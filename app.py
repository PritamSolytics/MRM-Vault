"""
MRM Vault | Entity Relationship Explorer
Streamlit Dashboard — Production Prototype

Architecture:
  data_model.py  — All entities, attributes, relationships, state machines (pure data, no UI)
  graph_engine.py — Graph traversal: impact trace, upstream trace, BFS, cardinality
  app.py         — Streamlit UI: graph, detail panel, sub-tables, filters, export

Run:
  pip install streamlit pandas plotly
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import math
import json
import io
import csv
from typing import List, Dict, Optional

# ── local modules ──────────────────────────────────────────────────────────────
from data_model import (
    NODES, LINKS, REL_TYPES, NODE_SCHEMA, STAGE_TRANSITIONS,
    ENTITY, WORKFLOW, QUICK_ACCESS,
    get_risk_score, get_status_color, get_risk_color, get_rel_category_color,
)
from graph_engine import (
    get_related_ids, get_outgoing, get_incoming, get_visible_ids,
    get_visible_links, get_directed_link, impact_trace, upstream_trace,
    get_consumers, advance_stage,
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="MRM Vault | Relationship Explorer",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Layout */
.main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1600px; }
[data-testid="stSidebar"] { background: #0f172a !important; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCheckbox label { color: #94a3b8 !important; font-size: 11px !important; }
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; font-size: 13px !important; }

/* Hero */
.hero { background: linear-gradient(135deg,#0f172a 0%,#1e3a5f 60%,#1e293b 100%);
        border-radius: 16px; padding: 22px 28px; margin-bottom: 16px; color: white; }
.hero h1 { font-size: 26px; font-weight: 800; margin: 0 0 6px; color: #f1f5f9; }
.hero p  { font-size: 13px; color: #94a3b8; margin: 0; line-height: 1.6; }

/* Metric pills */
.metric-row { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.metric-pill { background: white; border: 1px solid #e2e8f0; border-radius: 12px;
               padding: 12px 16px; min-width: 130px; flex: 1;
               box-shadow: 0 1px 4px rgba(15,23,42,.06); }
.metric-pill .mlabel { font-size: 10px; font-weight: 700; text-transform: uppercase;
                       letter-spacing: .06em; color: #64748b; margin-bottom: 4px; }
.metric-pill .mvalue { font-size: 22px; font-weight: 800; color: #0f172a; }
.metric-pill .mhelp  { font-size: 11px; color: #94a3b8; margin-top: 2px; }

/* Entity / Workflow badges */
.badge { display: inline-block; font-size: 9px; font-weight: 700; padding: 2px 8px;
         border-radius: 4px; text-transform: uppercase; letter-spacing: .05em; }
.badge-entity   { background: #dbeafe; color: #1d4ed8; }
.badge-workflow { background: #cffafe; color: #0e7490; }
.badge-high     { background: #fee2e2; color: #991b1b; }
.badge-medium   { background: #fef3c7; color: #92400e; }
.badge-low      { background: #dcfce7; color: #166534; }
.badge-na       { background: #f1f5f9; color: #64748b; }

/* Detail panel */
.detail-hero { border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 12px; }
.detail-name { font-size: 18px; font-weight: 700; color: #0f172a; margin: 6px 0; }
.detail-sum  { font-size: 12.5px; color: #64748b; line-height: 1.6; }
.meta-grid   { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }
.meta-item .ml { font-size: 10px; color: #94a3b8; font-weight: 600; margin-bottom: 2px; }
.meta-item .mv { font-size: 12.5px; font-weight: 500; color: #0f172a; }

/* Section titles */
.sec-title { font-size: 10px; font-weight: 700; text-transform: uppercase;
             letter-spacing: .07em; color: #94a3b8; border-bottom: 1px solid #e2e8f0;
             padding-bottom: 5px; margin: 12px 0 8px; }

/* Related items */
.rel-item { display: flex; align-items: center; justify-content: space-between;
            padding: 7px 10px; background: #f8fafc; border: 1px solid #e2e8f0;
            border-radius: 8px; margin-bottom: 4px; font-size: 12px; }
.rel-item:hover { border-color: #2563eb; background: #eff6ff; cursor: pointer; }
.rel-icon-e { background: #dbeafe; color: #1d4ed8; border-radius: 4px;
              padding: 2px 6px; font-size: 9px; font-weight: 700; margin-right: 7px; }
.rel-icon-w { background: #cffafe; color: #0e7490; border-radius: 4px;
              padding: 2px 6px; font-size: 9px; font-weight: 700; margin-right: 7px; }
.rel-cat    { font-size: 9px; font-weight: 600; padding: 1px 6px; border-radius: 3px; }

/* Stages */
.stage-row { display: flex; align-items: center; gap: 8px; padding: 6px 0;
             border-bottom: 1px solid #f1f5f9; font-size: 12px; }
.stage-done { color: #16a34a; font-weight: 500; }
.stage-cur  { color: #2563eb; font-weight: 600; }
.stage-pend { color: #94a3b8; }

/* Score bar */
.score-bar-wrap { background: #f1f5f9; border-radius: 4px; height: 6px; margin-top: 4px; }
.score-bar      { height: 6px; border-radius: 4px; }

/* Impact chip */
.impact-chip { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 5px;
               padding: 5px 8px; font-size: 11px; color: #15803d; margin-bottom: 3px; }
.upstream-chip { background: #fefce8; border: 1px solid #fde68a; border-radius: 5px;
                 padding: 5px 8px; font-size: 11px; color: #92400e; margin-bottom: 3px; }
.deg-chip   { background: #fee2e2; border: 1px solid #fca5a5; border-radius: 5px;
              padding: 5px 8px; font-size: 11px; color: #991b1b; margin-bottom: 3px; }

/* Table */
.attr-table { width: 100%; font-size: 12px; border-collapse: collapse; }
.attr-table th { background: #f8fafc; padding: 6px 10px; text-align: left;
                 font-size: 10px; font-weight: 700; text-transform: uppercase;
                 letter-spacing: .05em; color: #64748b; border-bottom: 1px solid #e2e8f0; }
.attr-table td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.attr-table tr:hover td { background: #f8fafc; }

/* Artifact pill */
.art-pill { display: inline-flex; align-items: center; gap: 5px; padding: 4px 9px;
            background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;
            font-size: 11px; color: #334155; margin: 2px; }

/* Activity */
.act-item { display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; }
.act-dot  { width: 7px; height: 7px; border-radius: 50%; background: #93c5fd;
            margin-top: 4px; flex-shrink: 0; }
.act-text { font-size: 12px; color: #334155; line-height: 1.5; }
.act-time { font-size: 10px; color: #94a3b8; }

/* Tooltip */
div[data-testid="stTooltipIcon"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def _init_state():
    defaults = {
        "selected_id": "credit_risk_model",
        "depth": 1,
        "show_entities": True,
        "show_workflows": True,
        "cat_filter": "All",
        "active_tab": "Graph",
        "history": ["credit_risk_model"],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def navigate_to(node_id: str):
    """Navigate to a node and update breadcrumb history."""
    if node_id not in NODES:
        return
    st.session_state.selected_id = node_id
    history = st.session_state.history
    if not history or history[-1] != node_id:
        history.append(node_id)
    if len(history) > 8:
        history.pop(0)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SVG GRAPH RENDERER
# ══════════════════════════════════════════════════════════════════════════════
CATEGORY_COLORS = {
    "lineage":     {"stroke": "#2563eb", "bg": "#dbeafe", "text": "#1d4ed8"},
    "governance":  {"stroke": "#7c3aed", "bg": "#ede9fe", "text": "#6d28d9"},
    "validation":  {"stroke": "#0891b2", "bg": "#cffafe", "text": "#0e7490"},
    "monitoring":  {"stroke": "#16a34a", "bg": "#dcfce7", "text": "#15803d"},
    "default":     {"stroke": "#94a3b8", "bg": "#f1f5f9", "text": "#64748b"},
}


def _radial_positions(visible_ids: List[str], selected_id: str, W=860, H=540):
    positions = {}
    cx, cy = W / 2, H / 2
    if selected_id not in visible_ids:
        return positions
    positions[selected_id] = (cx, cy)
    others = [i for i in visible_ids if i != selected_id]
    # Sort: workflows first for visual clarity
    others.sort(key=lambda i: (0 if NODES[i]["type"] == WORKFLOW else 1))
    n = len(others)
    radius = min(min(W, H) * 0.36, 230)
    for idx, nid in enumerate(others):
        angle = (2 * math.pi * idx / max(n, 1)) - math.pi / 2
        positions[nid] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    return positions


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n-1] + "…"


def render_graph_svg(visible_ids: List[str], selected_id: str,
                     cat_filter: str = "All") -> str:
    W, H = 860, 540
    NW, NH = 192, 70  # node width / height
    pos = _radial_positions(visible_ids, selected_id, W, H)
    vis_links = get_visible_links(visible_ids)

    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
             f'xmlns="http://www.w3.org/2000/svg">']

    # Defs
    parts.append("""<defs>
  <marker id="arr-dark" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="#334155" stroke-width="1.4" stroke-linecap="round"/>
  </marker>
  <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="#2563eb" stroke-width="1.4" stroke-linecap="round"/>
  </marker>
  <marker id="arr-purple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="#7c3aed" stroke-width="1.4" stroke-linecap="round"/>
  </marker>
  <marker id="arr-teal" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="#0891b2" stroke-width="1.4" stroke-linecap="round"/>
  </marker>
  <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="#16a34a" stroke-width="1.4" stroke-linecap="round"/>
  </marker>
  <filter id="shd"><feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#0f172a" flood-opacity="0.09"/></filter>
  <filter id="shd-sel"><feDropShadow dx="0" dy="4" stdDeviation="9" flood-color="#2563eb" flood-opacity="0.22"/></filter>
</defs>""")

    # Background
    parts.append(f'<rect width="{W}" height="{H}" fill="#f8fafc" rx="16"/>')

    # Grid dots (subtle)
    parts.append('<g opacity="0.25">')
    for gx in range(30, W, 30):
        for gy in range(30, H, 30):
            parts.append(f'<circle cx="{gx}" cy="{gy}" r="1" fill="#cbd5e1"/>')
    parts.append('</g>')

    # Edges
    MARKER_MAP = {
        "lineage": "arr-blue", "governance": "arr-purple",
        "validation": "arr-teal", "monitoring": "arr-green",
    }
    for link in vis_links:
        src, tgt, label_key = link["source"], link["target"], link["relType"]
        if src not in pos or tgt not in pos:
            continue
        rt = REL_TYPES.get(label_key, {})
        cat = rt.get("category", "default")
        # apply category filter
        if cat_filter != "All" and cat != cat_filter.lower():
            continue

        highlighted = (src == selected_id or tgt == selected_id)
        colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
        stroke = colors["stroke"] if highlighted else "#cbd5e1"
        sw = "1.8" if highlighted else "1"
        marker_id = MARKER_MAP.get(cat, "arr-dark") if highlighted else "arr-dark"

        x1, y1 = pos[src]
        x2, y2 = pos[tgt]
        # curve control point (slight offset perpendicular)
        dx, dy = x2 - x1, y2 - y1
        dist = math.sqrt(dx*dx + dy*dy) or 1
        cx_ = (x1+x2)/2 - dy/dist * 18
        cy_ = (y1+y2)/2 + dx/dist * 18

        # shorten to node edge
        pad = math.sqrt((NW/2)**2*(dx/dist)**2 + (NH/2)**2*(dy/dist)**2)
        sx = x1 + dx/dist * (pad+4)
        sy = y1 + dy/dist * (pad+4)
        ex = x2 - dx/dist * (pad+14)
        ey = y2 - dy/dist * (pad+14)

        path = f'M{sx:.1f} {sy:.1f} Q{cx_:.1f} {cy_:.1f} {ex:.1f} {ey:.1f}'
        parts.append(f'<path d="{path}" fill="none" stroke="{stroke}" '
                     f'stroke-width="{sw}" marker-end="url(#{marker_id})"/>')

        # Edge label
        lx = 0.25*sx + 0.5*cx_ + 0.25*ex
        ly = 0.25*sy + 0.5*cy_ + 0.25*ey
        label = rt.get("label", label_key)[:18]
        lw = len(label) * 6.5 + 14
        if highlighted:
            parts.append(f'<rect x="{lx-lw/2:.1f}" y="{ly-9:.1f}" width="{lw:.1f}" height="17" '
                         f'rx="5" fill="{colors["bg"]}" stroke="{colors["stroke"]}" stroke-width="0.5"/>')
            parts.append(f'<text x="{lx:.1f}" y="{ly+1:.1f}" text-anchor="middle" '
                         f'dominant-baseline="middle" font-size="9" font-weight="600" '
                         f'fill="{colors["text"]}" font-family="system-ui">{label}</text>')
        else:
            parts.append(f'<rect x="{lx-lw/2:.1f}" y="{ly-9:.1f}" width="{lw:.1f}" height="17" '
                         f'rx="5" fill="#f8fafc" stroke="#e2e8f0" stroke-width="0.5"/>')
            parts.append(f'<text x="{lx:.1f}" y="{ly+1:.1f}" text-anchor="middle" '
                         f'dominant-baseline="middle" font-size="9" fill="#94a3b8" '
                         f'font-family="system-ui">{label}</text>')

    # Nodes (non-selected first, selected on top)
    sorted_ids = [i for i in visible_ids if i != selected_id] + \
                 ([selected_id] if selected_id in visible_ids else [])

    for nid in sorted_ids:
        if nid not in pos:
            continue
        node = NODES[nid]
        x, y = pos[nid]
        rx_, ry_ = x - NW/2, y - NH/2
        is_sel = (nid == selected_id)
        is_entity = node["type"] == ENTITY

        # Card
        fill = "#ffffff" if is_entity else "#1e293b"
        stroke_c = "#2563eb" if is_sel else ("#334155" if is_entity else "#334155")
        sw = "2.5" if is_sel else "1"
        filt = 'url(#shd-sel)' if is_sel else 'url(#shd)'
        parts.append(f'<g filter="{filt}">')
        parts.append(f'<rect x="{rx_:.1f}" y="{ry_:.1f}" width="{NW}" height="{NH}" '
                     f'rx="14" fill="{fill}" stroke="{stroke_c}" stroke-width="{sw}"/>')

        # Left accent bar (4px)
        accent = "#2563eb" if is_entity else "#0ea5e9"
        if is_sel:
            accent = "#2563eb" if is_entity else "#0ea5e9"
        parts.append(f'<rect x="{rx_:.1f}" y="{ry_:.1f}" width="4" height="{NH}" '
                     f'rx="14" fill="{accent}"/>')
        parts.append(f'<rect x="{rx_:.1f}" y="{ry_:.1f}" width="6" height="{NH}" '
                     f'fill="{fill}"/>')
        parts.append(f'<rect x="{rx_:.1f}" y="{ry_:.1f}" width="4" height="{NH}" '
                     f'fill="{accent}"/>')

        # Type icon
        icon_bg = "#eff6ff" if is_entity else "rgba(255,255,255,0.12)"
        icon_txt = "#2563eb" if is_entity else "#7dd3fc"
        icon_label = "EN" if is_entity else "WF"
        cx_ic, cy_ic = rx_ + 22, y
        parts.append(f'<circle cx="{cx_ic:.1f}" cy="{cy_ic:.1f}" r="11" '
                     f'fill="{icon_bg}" stroke="{"#bfdbfe" if is_entity else "rgba(255,255,255,0.15)"}" '
                     f'stroke-width="1"/>')
        parts.append(f'<text x="{cx_ic:.1f}" y="{cy_ic:.1f}" text-anchor="middle" '
                     f'dominant-baseline="middle" font-size="8" font-weight="700" '
                     f'fill="{icon_txt}" font-family="system-ui">{icon_label}</text>')

        # Node name
        name_col = "#0f172a" if is_entity else "#f1f5f9"
        sub_col  = "#64748b" if is_entity else "#94a3b8"
        parts.append(f'<text x="{rx_+40:.1f}" y="{ry_+20:.1f}" dominant-baseline="middle" '
                     f'font-size="12.5" font-weight="600" fill="{name_col}" '
                     f'font-family="system-ui">{_truncate(node["name"], 22)}</text>')
        parts.append(f'<text x="{rx_+40:.1f}" y="{ry_+36:.1f}" dominant-baseline="middle" '
                     f'font-size="10.5" fill="{sub_col}" '
                     f'font-family="system-ui">{node["subtype"]}</text>')

        # Risk / status badge
        badge_val = node.get("risk") or node.get("status", "")
        if badge_val and badge_val not in ("-", ""):
            bg, tc = get_risk_color(badge_val) if node.get("risk") not in (None, "-", "") \
                     else get_status_color(node.get("status", ""))
            bw = len(str(badge_val)) * 6.2 + 14
            bx = rx_ + 40
            by = ry_ + 48
            parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="15" '
                         f'rx="5" fill="{bg}"/>')
            parts.append(f'<text x="{bx+bw/2:.1f}" y="{by+7.5:.1f}" text-anchor="middle" '
                         f'dominant-baseline="middle" font-size="9" font-weight="700" '
                         f'fill="{tc}" font-family="system-ui">{badge_val}</text>')

        parts.append('</g>')

    # Legend
    legend_items = [
        ("lineage", "Lineage"), ("governance", "Governance"),
        ("validation", "Validation"), ("monitoring", "Monitoring"),
    ]
    lx_ = 16
    parts.append(f'<rect x="12" y="{H-34}" width="{16+len(legend_items)*108}" height="24" '
                 f'rx="6" fill="rgba(255,255,255,0.9)" stroke="#e2e8f0" stroke-width="0.5"/>')
    for cat, cat_label in legend_items:
        c = CATEGORY_COLORS[cat]
        parts.append(f'<rect x="{lx_:.1f}" y="{H-26}" width="18" height="2" '
                     f'rx="1" fill="{c["stroke"]}"/>')
        parts.append(f'<text x="{lx_+22:.1f}" y="{H-21}" font-size="9.5" '
                     f'fill="{c["text"]}" font-family="system-ui">{cat_label}</text>')
        lx_ += 108

    parts.append('</svg>')
    return "".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_detail_panel(node_id: str):
    node = NODES.get(node_id)
    if not node:
        st.caption("No entity selected.")
        return

    incoming = get_incoming(node_id)
    outgoing = get_outgoing(node_id)
    impacted = impact_trace(node_id)
    upstream = upstream_trace(node_id)
    consumers = get_consumers(node_id)
    score = get_risk_score(node_id)
    score_color = "#dc2626" if score >= 70 else "#d97706" if score >= 40 else "#16a34a"
    score_bg = "#fee2e2" if score >= 70 else "#fef3c7" if score >= 40 else "#dcfce7"

    is_entity = node["type"] == ENTITY
    type_cls = "badge-entity" if is_entity else "badge-workflow"

    # Hero
    st.markdown(f"""
    <div class="detail-hero">
      <span class="badge {type_cls}">{node['type']}</span>
      <span style="font-size:11px;color:#94a3b8;margin-left:6px">{node['subtype']}</span>
      <div class="detail-name">{node['name']}</div>
      <div class="detail-sum">{node['summary']}</div>
    </div>""", unsafe_allow_html=True)

    # Meta grid
    status_col, _ = get_status_color(node.get("status", ""))
    st.markdown(f"""
    <div class="meta-grid">
      <div class="meta-item"><div class="ml">Owner</div><div class="mv">{node['owner']}</div></div>
      <div class="meta-item"><div class="ml">Status</div>
        <div class="mv" style="color:{status_col}">{node.get('status','—')}</div></div>
      {"<div class='meta-item'><div class='ml'>Risk level</div><div class='mv'>" +
       str(node.get('risk','—')) + "</div></div>" if is_entity else
       "<div class='meta-item'><div class='ml'>Stage</div><div class='mv'>" +
       str(node.get('stage','—')) + "</div></div>"}
      {"<div class='meta-item'><div class='ml'>Derived risk score</div>" +
       "<div class='mv'><span style='background:" + score_bg + ";color:" + score_color +
       ";padding:2px 8px;border-radius:4px;font-weight:700;font-size:13px'>" +
       str(score) + "/100</span></div></div>" if is_entity else
       "<div class='meta-item'><div class='ml'>Subtype</div><div class='mv'>" +
       node['subtype'] + "</div></div>"}
    </div>""", unsafe_allow_html=True)

    if node.get("jurisdiction"):
        st.markdown(f'<div style="font-size:11px;color:#64748b;margin-bottom:8px">'
                    f'⚖ {node["jurisdiction"]}</div>', unsafe_allow_html=True)

    if is_entity and score > 0:
        st.markdown(f"""
        <div class="score-bar-wrap">
          <div class="score-bar" style="width:{score}%;background:{score_color}"></div>
        </div>""", unsafe_allow_html=True)

    # Relationship category breakdown
    cat_counts = {}
    for link in outgoing + incoming:
        cat = REL_TYPES.get(link["relType"], {}).get("category", "default")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    if cat_counts:
        st.markdown('<div class="sec-title">Relationship categories</div>', unsafe_allow_html=True)
        cats_html = ""
        for cat, cnt in cat_counts.items():
            c = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
            cats_html += (f'<span class="rel-cat" style="background:{c["bg"]};'
                          f'color:{c["text"]}">{cat} ({cnt})</span> ')
        st.markdown(f'<div style="margin-bottom:4px">{cats_html}</div>'
                    f'<div style="font-size:11px;color:#94a3b8">↗ {len(outgoing)} outgoing '
                    f'&nbsp; ↙ {len(incoming)} incoming</div>', unsafe_allow_html=True)

    # Impact trace
    if impacted:
        st.markdown(f'<div class="sec-title">Downstream impact ({len(impacted)} affected)</div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#94a3b8;margin-bottom:6px">'
                    'Changes here propagate downstream to:</div>', unsafe_allow_html=True)
        for iid in impacted[:6]:
            n2 = NODES.get(iid, {})
            link = get_directed_link(node_id, iid)
            cat = REL_TYPES.get(link["relType"] if link else "", {}).get("category", "default")
            c = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
            st.markdown(f'<div class="impact-chip">↓ {n2.get("name", iid)} '
                        f'<span class="rel-cat" style="background:{c["bg"]};color:{c["text"]};'
                        f'margin-left:4px">{cat}</span></div>', unsafe_allow_html=True)
        if len(impacted) > 6:
            st.caption(f"+ {len(impacted)-6} more downstream…")
    elif consumers:
        st.markdown(f'<div class="sec-title">Direct consumers ({len(consumers)})</div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#94a3b8;margin-bottom:6px">'
                    'This is a shared resource — these nodes depend on it:</div>',
                    unsafe_allow_html=True)
        for cid in consumers:
            n2 = NODES.get(cid, {})
            link = get_directed_link(cid, node_id)
            lbl = REL_TYPES.get(link["relType"] if link else "", {}).get("label", "")
            st.markdown(f'<div class="impact-chip">← {n2.get("name",cid)} '
                        f'<span style="font-size:10px;color:#15803d">via {lbl}</span></div>',
                        unsafe_allow_html=True)

    # Upstream dependencies
    if upstream:
        degraded = [uid for uid in upstream if NODES.get(uid, {}).get("status") in
                    ("Under Review", "Not Started")]
        st.markdown(f'<div class="sec-title">Upstream dependencies ({len(upstream)})</div>',
                    unsafe_allow_html=True)
        for uid in upstream[:5]:
            n2 = NODES.get(uid, {})
            is_deg = uid in degraded
            chip_cls = "deg-chip" if is_deg else "upstream-chip"
            deg_label = " ⚠ degraded" if is_deg else ""
            link = get_directed_link(uid, node_id)
            lbl = REL_TYPES.get(link["relType"] if link else "", {}).get("label", "")
            st.markdown(f'<div class="{chip_cls}">↑ {n2.get("name",uid)} '
                        f'<span style="font-size:10px">via {lbl}{deg_label}</span></div>',
                        unsafe_allow_html=True)

    # Outgoing / Incoming links (directed)
    if outgoing:
        st.markdown(f'<div class="sec-title">Outgoing relationships ({len(outgoing)})</div>',
                    unsafe_allow_html=True)
        for link in outgoing:
            n2 = NODES.get(link["target"], {})
            rt = REL_TYPES.get(link["relType"], {})
            cat = rt.get("category", "default")
            c = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
            icon_cls = "rel-icon-e" if n2.get("type") == ENTITY else "rel-icon-w"
            icon_lbl = "E" if n2.get("type") == ENTITY else "WF"
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f'<div class="rel-item">'
                    f'<span class="{icon_cls}">{icon_lbl}</span>'
                    f'<span>{n2.get("name", link["target"])}</span>'
                    f'<span class="rel-cat" style="background:{c["bg"]};color:{c["text"]};'
                    f'margin-left:6px">{rt.get("label","")}</span>'
                    f'<span style="font-size:9px;color:#94a3b8;margin-left:4px">'
                    f'{link.get("cardinality","")}</span>'
                    f'</div>', unsafe_allow_html=True)
            with col2:
                if st.button("→", key=f"out_{node_id}_{link['target']}", help="Navigate"):
                    navigate_to(link["target"])

    if incoming:
        st.markdown(f'<div class="sec-title">Incoming relationships ({len(incoming)})</div>',
                    unsafe_allow_html=True)
        for link in incoming:
            n2 = NODES.get(link["source"], {})
            rt = REL_TYPES.get(link["relType"], {})
            cat = rt.get("category", "default")
            c = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
            icon_cls = "rel-icon-e" if n2.get("type") == ENTITY else "rel-icon-w"
            icon_lbl = "E" if n2.get("type") == ENTITY else "WF"
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f'<div class="rel-item">'
                    f'<span class="{icon_cls}">{icon_lbl}</span>'
                    f'<span>{n2.get("name", link["source"])}</span>'
                    f'<span class="rel-cat" style="background:{c["bg"]};color:{c["text"]};'
                    f'margin-left:6px">← {rt.get("label","")}</span>'
                    f'<span style="font-size:9px;color:#94a3b8;margin-left:4px">'
                    f'{link.get("cardinality","")}</span>'
                    f'</div>', unsafe_allow_html=True)
            with col2:
                if st.button("→", key=f"in_{node_id}_{link['source']}", help="Navigate"):
                    navigate_to(link["source"])

    # Workflow stages + advance button
    if node.get("stages"):
        st.markdown('<div class="sec-title">Lifecycle stages</div>', unsafe_allow_html=True)
        for s in node["stages"]:
            if s["status"] == "done":
                icon, cls = "✓", "stage-done"
            elif s["status"] == "current":
                icon, cls = "●", "stage-cur"
            else:
                icon, cls = "○", "stage-pend"
            st.markdown(f'<div class="stage-row"><span>{icon}</span>'
                        f'<span class="{cls}">{s["name"]}</span></div>',
                        unsafe_allow_html=True)

        cur_idx = next((i for i, s in enumerate(node["stages"]) if s["status"] == "current"), -1)
        if 0 <= cur_idx < len(node["stages"]) - 1:
            if st.button("⏭ Advance stage", key=f"adv_{node_id}", type="primary"):
                result = advance_stage(node_id)
                if result["ok"]:
                    st.success(f"Advanced to: {result['new_stage']}")
                    st.rerun()
                else:
                    st.error(result["message"])

    # Attribute sub-table (zoom-in)
    if node.get("attributes"):
        st.markdown('<div class="sec-title">Attribute sub-table (zoom-in view)</div>',
                    unsafe_allow_html=True)
        rows = []
        for attr_name, attr_val in node["attributes"].items():
            attr_def = node.get("attr_defs", {}).get(attr_name, {})
            rows.append({
                "Attribute": attr_def.get("display_name", attr_name),
                "Value": str(attr_val),
                "Type": attr_def.get("data_type", "—"),
                "Section": attr_def.get("section", "—"),
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             "Attribute": st.column_config.TextColumn(width="medium"),
                             "Value": st.column_config.TextColumn(width="medium"),
                             "Type": st.column_config.TextColumn(width="small"),
                             "Section": st.column_config.TextColumn(width="small"),
                         })

    # Artifacts
    if node.get("artifacts"):
        st.markdown('<div class="sec-title">Artifacts</div>', unsafe_allow_html=True)
        art_html = "".join(
            f'<span class="art-pill">📄 {a}</span>' for a in node["artifacts"]
        )
        st.markdown(art_html, unsafe_allow_html=True)

    # Activity
    if node.get("activity"):
        st.markdown('<div class="sec-title">Recent activity</div>', unsafe_allow_html=True)
        for act in node["activity"]:
            st.markdown(
                f'<div class="act-item"><div class="act-dot"></div>'
                f'<div><div class="act-text">{act["text"]}</div>'
                f'<div class="act-time">{act["time"]}</div></div></div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP TABLE
# ══════════════════════════════════════════════════════════════════════════════
def render_rel_table(vis_links: list):
    if not vis_links:
        st.info("No relationships visible for current filters.")
        return
    rows = []
    for link in vis_links:
        src, tgt = NODES.get(link["source"], {}), NODES.get(link["target"], {})
        rt = REL_TYPES.get(link["relType"], {})
        rows.append({
            "Source": src.get("name", link["source"]),
            "Relationship": rt.get("label", link["relType"]),
            "Category": rt.get("category", "—"),
            "Target": tgt.get("name", link["target"]),
            "Cardinality": link.get("cardinality", "—"),
            "Source type": src.get("type", "—"),
            "Target type": tgt.get("type", "—"),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Source": st.column_config.TextColumn(width="medium"),
                     "Relationship": st.column_config.TextColumn(width="medium"),
                     "Category": st.column_config.TextColumn(width="small"),
                     "Target": st.column_config.TextColumn(width="medium"),
                     "Cardinality": st.column_config.TextColumn(width="small"),
                 })


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY TABLE (all entities)
# ══════════════════════════════════════════════════════════════════════════════
def render_inventory_table(filter_type: str = "All", filter_risk: str = "All",
                           search: str = ""):
    rows = []
    for nid, node in NODES.items():
        if filter_type != "All" and node["type"] != filter_type:
            continue
        if filter_risk != "All" and node.get("risk", "—") != filter_risk:
            continue
        if search and search.lower() not in node["name"].lower() and \
                search.lower() not in node["subtype"].lower():
            continue
        score = get_risk_score(nid)
        rows.append({
            "ID": nid,
            "Name": node["name"],
            "Type": node["type"],
            "Subtype": node["subtype"],
            "Owner": node["owner"],
            "Status": node.get("status", "—"),
            "Risk": node.get("risk", "—"),
            "Risk score": score,
            "Workflow state": node.get("stage") or node.get("workflow_state", "—"),
            "Outgoing links": len(get_outgoing(nid)),
            "Incoming links": len(get_incoming(nid)),
        })
    if not rows:
        st.info("No entities match current filters.")
        return

    df = pd.DataFrame(rows)
    # Highlight selected row
    sel = st.session_state.selected_id

    event = st.dataframe(
        df, use_container_width=True, hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "Name": st.column_config.TextColumn(width="large"),
            "Type": st.column_config.TextColumn(width="small"),
            "Risk score": st.column_config.ProgressColumn(
                min_value=0, max_value=100, width="small"),
            "Outgoing links": st.column_config.NumberColumn(width="small"),
            "Incoming links": st.column_config.NumberColumn(width="small"),
        },
    )
    # Handle row selection → navigate
    if event and event.selection and event.selection.rows:
        row_idx = event.selection.rows[0]
        selected_node_id = df.iloc[row_idx]["ID"]
        if selected_node_id != st.session_state.selected_id:
            navigate_to(selected_node_id)


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════════════
def export_csv(vis_links: list) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "Source", "Rel type", "Category", "Target", "Cardinality",
        "Source type", "Target type", "Source risk", "Target status", "Notes"
    ])
    writer.writeheader()
    for link in vis_links:
        src = NODES.get(link["source"], {})
        tgt = NODES.get(link["target"], {})
        rt = REL_TYPES.get(link["relType"], {})
        writer.writerow({
            "Source": src.get("name", ""),
            "Rel type": rt.get("label", link["relType"]),
            "Category": rt.get("category", ""),
            "Target": tgt.get("name", ""),
            "Cardinality": link.get("cardinality", ""),
            "Source type": src.get("type", ""),
            "Target type": tgt.get("type", ""),
            "Source risk": src.get("risk", ""),
            "Target status": tgt.get("status", ""),
            "Notes": link.get("notes", ""),
        })
    return buf.getvalue().encode()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px">
      <div style="width:32px;height:32px;background:#2563eb;border-radius:7px;
                  display:flex;align-items:center;justify-content:center">
        <span style="color:white;font-size:16px">⬡</span>
      </div>
      <div>
        <div style="font-size:14px;font-weight:700;color:#e2e8f0">MRM Vault</div>
        <div style="font-size:10px;color:#64748b">Solytics Partners</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Search
    search_q = st.text_input("🔍 Search inventory", placeholder="Model, dataset…",
                              label_visibility="collapsed")
    if search_q:
        matches = [(nid, n) for nid, n in NODES.items()
                   if search_q.lower() in n["name"].lower()]
        if matches:
            for nid, n in matches[:6]:
                if st.button(n["name"], key=f"srch_{nid}"):
                    navigate_to(nid)
        else:
            st.caption("No matches")

    st.markdown("### View settings")
    st.session_state.show_entities = st.checkbox("Show entities", value=st.session_state.show_entities)
    st.session_state.show_workflows = st.checkbox("Show workflows", value=st.session_state.show_workflows)

    st.markdown("### Relationship depth")
    depth_map = {"1 hop": 1, "2 hops": 2, "All connected": 999}
    depth_lbl = st.radio("Depth", list(depth_map.keys()), horizontal=True, label_visibility="collapsed")
    st.session_state.depth = depth_map[depth_lbl]

    st.markdown("### Category filter")
    cat_options = ["All", "Lineage", "Governance", "Validation", "Monitoring"]
    st.session_state.cat_filter = st.selectbox(
        "Filter by relationship category", cat_options, label_visibility="collapsed")

    st.markdown("### Quick access")
    for qa in QUICK_ACCESS:
        if st.button(qa["label"], key=f"qa_{qa['id']}"):
            navigate_to(qa["id"])

    st.markdown("---")
    if st.button("↺ Reset to default"):
        st.session_state.selected_id = "credit_risk_model"
        st.session_state.depth = 1
        st.session_state.history = ["credit_risk_model"]
        st.rerun()

    st.markdown("""
    <div style="margin-top:12px">
      <span style="font-size:9px;padding:2px 7px;background:rgba(255,255,255,0.07);
             border:1px solid rgba(255,255,255,0.1);border-radius:3px;color:#64748b">
        RegTech100 2026</span>
      <span style="font-size:9px;padding:2px 7px;background:rgba(255,255,255,0.07);
             border:1px solid rgba(255,255,255,0.1);border-radius:3px;color:#64748b;
             margin-left:4px">Chartis #45</span>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
selected_id = st.session_state.selected_id
selected_node = NODES.get(selected_id, {})
depth = st.session_state.depth

# Compute visible graph
visible_ids = get_visible_ids(selected_id, depth)
if not st.session_state.show_entities:
    visible_ids = [i for i in visible_ids if NODES[i]["type"] != ENTITY or i == selected_id]
if not st.session_state.show_workflows:
    visible_ids = [i for i in visible_ids if NODES[i]["type"] != WORKFLOW or i == selected_id]
if selected_id not in visible_ids:
    visible_ids.insert(0, selected_id)

vis_links = get_visible_links(visible_ids)
impacted = impact_trace(selected_id)
score = get_risk_score(selected_id)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <h1>MRM Vault · Relationship Explorer</h1>
  <p>Entity → sub-table → workflow · Attribute-mapped model risk inventory ·
     Impact tracing · Lifecycle state machine · Solytics Partners</p>
</div>""", unsafe_allow_html=True)

# ── Breadcrumb ────────────────────────────────────────────────────────────────
history = st.session_state.history
if history:
    bc_parts = []
    for hid in history[-5:]:
        n = NODES.get(hid, {})
        bc_parts.append(f'<span style="color:#64748b;font-size:12px">{n.get("name",hid)}</span>')
    bc_html = ' <span style="color:#cbd5e1">›</span> '.join(bc_parts)
    st.markdown(f'<div style="margin-bottom:10px">{bc_html}</div>', unsafe_allow_html=True)

# ── Metric pills ──────────────────────────────────────────────────────────────
ent_count = sum(1 for i in visible_ids if NODES[i]["type"] == ENTITY)
wf_count  = sum(1 for i in visible_ids if NODES[i]["type"] == WORKFLOW)
sc_color  = "#dc2626" if score >= 70 else "#d97706" if score >= 40 else "#16a34a"

st.markdown(f"""
<div class="metric-row">
  <div class="metric-pill">
    <div class="mlabel">Selected object</div>
    <div class="mvalue" style="font-size:15px;margin-top:2px">{selected_node.get("name","—")}</div>
    <div class="mhelp">{selected_node.get("type","—")} · {selected_node.get("subtype","—")}</div>
  </div>
  <div class="metric-pill">
    <div class="mlabel">Visible nodes</div>
    <div class="mvalue">{len(visible_ids)}</div>
    <div class="mhelp">{ent_count} entities · {wf_count} workflows</div>
  </div>
  <div class="metric-pill">
    <div class="mlabel">Visible links</div>
    <div class="mvalue">{len(vis_links)}</div>
    <div class="mhelp">Relationship edges</div>
  </div>
  <div class="metric-pill">
    <div class="mlabel">Downstream impact</div>
    <div class="mvalue">{len(impacted)}</div>
    <div class="mhelp">Nodes affected by changes</div>
  </div>
  <div class="metric-pill">
    <div class="mlabel">Derived risk score</div>
    <div class="mvalue" style="color:{sc_color}">{score}<span style="font-size:13px">/100</span></div>
    <div class="mhelp">Upstream-weighted risk</div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_graph, tab_inventory, tab_rels, tab_schema = st.tabs([
    "🔷 Relationship graph",
    "📋 Full inventory",
    "🔗 Relationship table",
    "📐 Attribute schema",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — GRAPH + DETAIL PANEL
# ─────────────────────────────────────────────────────────────────────────────
with tab_graph:
    graph_col, detail_col = st.columns([2.4, 1], gap="large")

    with graph_col:
        st.markdown(f"**Relationship graph** &nbsp; "
                    f"<span style='font-size:12px;color:#94a3b8'>"
                    f"{depth if depth < 999 else 'all'}-hop connections from "
                    f"{selected_node.get('name','')}</span>",
                    unsafe_allow_html=True)

        svg_html = render_graph_svg(
            visible_ids, selected_id, st.session_state.cat_filter
        )
        st.components.v1.html(svg_html, height=560, scrolling=False)

        # Quick navigate buttons below graph
        outgoing_ids = [l["target"] for l in get_outgoing(selected_id)]
        incoming_ids = [l["source"] for l in get_incoming(selected_id)]
        all_nav = list(dict.fromkeys(outgoing_ids + incoming_ids))

        if all_nav:
            st.markdown("**Connected nodes** — click to navigate:")
            nav_cols = st.columns(min(len(all_nav), 5))
            for i, nid in enumerate(all_nav[:10]):
                with nav_cols[i % 5]:
                    n2 = NODES.get(nid, {})
                    if st.button(n2.get("name", nid)[:20],
                                 key=f"nav_{selected_id}_{nid}",
                                 help=f"{n2.get('type')} · {n2.get('subtype')}"):
                        navigate_to(nid)

        # Relationship table below graph
        st.markdown("---")
        st.markdown("**Relationship map** — all visible connections")
        render_rel_table(vis_links)

        # Export
        col_ex1, col_ex2 = st.columns([1, 4])
        with col_ex1:
            csv_bytes = export_csv(vis_links)
            st.download_button(
                "⬇ Export CSV", data=csv_bytes,
                file_name=f"mrm_vault_{selected_id}_{depth}hop.csv",
                mime="text/csv",
            )

    with detail_col:
        st.markdown("**Detail panel**")
        render_detail_panel(selected_id)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — FULL INVENTORY
# ─────────────────────────────────────────────────────────────────────────────
with tab_inventory:
    st.markdown("**Full entity inventory** — click any row to select and inspect")
    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        inv_type = st.selectbox("Filter by type", ["All", ENTITY, WORKFLOW])
    with fc2:
        inv_risk = st.selectbox("Filter by risk", ["All", "High", "Medium", "Low"])
    with fc3:
        inv_search = st.text_input("Search name or subtype", placeholder="credit risk, dataset…")
    render_inventory_table(inv_type, inv_risk, inv_search)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — RELATIONSHIP TABLE
# ─────────────────────────────────────────────────────────────────────────────
with tab_rels:
    st.markdown("**All relationships in current view** — typed, directed, with cardinality and notes")
    render_rel_table(vis_links)

    if vis_links:
        st.markdown("---")
        st.markdown("**Relationship notes** — business reason for each edge")
        for link in vis_links:
            src_name = NODES.get(link["source"], {}).get("name", link["source"])
            tgt_name = NODES.get(link["target"], {}).get("name", link["target"])
            rt = REL_TYPES.get(link["relType"], {})
            cat = rt.get("category", "default")
            c = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])
            with st.expander(f'{src_name} → [{rt.get("label","")}] → {tgt_name}  '
                             f'({link.get("cardinality","")})'):
                st.markdown(f'<span class="rel-cat" style="background:{c["bg"]};'
                            f'color:{c["text"]}">{cat}</span>', unsafe_allow_html=True)
                st.write(link.get("notes", "No notes recorded."))

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ATTRIBUTE SCHEMA
# ─────────────────────────────────────────────────────────────────────────────
with tab_schema:
    st.markdown("**Attribute library** — all attribute definitions (the column schema for the entity sheet)")

    # Common attributes
    st.markdown("#### Common attributes (present on all entity types)")
    common_attrs = [
        {"Name": "entity_id",        "Display name": "Entity ID",         "Type": "Auto (prefix+counter)", "Section": "Preliminary"},
        {"Name": "entity_name",       "Display name": "Name",              "Type": "Text",                  "Section": "Preliminary"},
        {"Name": "owner",             "Display name": "Owner",             "Type": "Association (user)",    "Section": "Preliminary"},
        {"Name": "status",            "Display name": "Status",            "Type": "Single-select",         "Section": "Preliminary"},
        {"Name": "workflow_state",    "Display name": "Workflow state",    "Type": "Derived (system)",      "Section": "Preliminary"},
        {"Name": "template_type",     "Display name": "Template type",     "Type": "Single-select (system)","Section": "Preliminary"},
        {"Name": "created_date",      "Display name": "Created date",      "Type": "Date (system)",         "Section": "Preliminary"},
        {"Name": "modified_date",     "Display name": "Last modified",     "Type": "Date (system)",         "Section": "Preliminary"},
    ]
    st.dataframe(pd.DataFrame(common_attrs), use_container_width=True, hide_index=True)

    st.markdown("#### Entity-specific attributes (zoom-in sub-table columns)")
    schema_tabs = st.tabs(["Model", "Assessment", "Subprocess", "Finding", "Use case", "Query"])

    model_attrs = [
        {"name": "model_type",          "display_name": "Model type",            "data_type": "Single-select",    "section": "Model Identification", "note": "Statistical / ML / AI-GenAI / Vendor"},
        {"name": "risk_tier",           "display_name": "Risk tier",             "data_type": "Single-select",    "section": "Model Identification", "note": "T1 (Material) / T2 / T3"},
        {"name": "regulation",          "display_name": "Regulation",            "data_type": "Multi-select",     "section": "Governance",           "note": "SR 11-7, PRA SS1/23, OSFI E-23, EU AI Act"},
        {"name": "business_unit",       "display_name": "Business unit",         "data_type": "Single-select",    "section": "General Information",  "note": "AWM, Retail, Commercial…"},
        {"name": "region",              "display_name": "Region",                "data_type": "Conditional select","section": "General Information", "note": "Changes based on business_unit value"},
        {"name": "development_due_date","display_name": "Development due date",  "data_type": "Date",             "section": "General Information",  "note": "Used in document templates"},
        {"name": "validation_due_date", "display_name": "Validation due date",   "data_type": "Date",             "section": "General Information",  "note": "Triggers time-based automation"},
        {"name": "derived_risk_score",  "display_name": "Risk score",            "data_type": "Derived formula",  "section": "Hidden",               "note": "base + upstream_deps*3 + status_penalty"},
        {"name": "model_family",        "display_name": "Model family",          "data_type": "Single-select",    "section": "Model Identification",  "note": "Credit Risk, Fraud, Market Risk…"},
        {"name": "intended_use",        "display_name": "Intended use",          "data_type": "Text extended",    "section": "General Information",   "note": "10,000 char limit"},
        {"name": "financial_impact",    "display_name": "Financial impact",      "data_type": "Single-select",    "section": "Model Identification",  "note": "Drives risk tier derivation"},
    ]
    assess_attrs = [
        {"name": "questionnaire_sections", "display_name": "Questionnaire sections", "data_type": "Section group", "section": "Descriptive",        "note": "Conditional sections per regulation"},
        {"name": "final_model_det",        "display_name": "Final model determination","data_type": "Single-select","section": "Model Identification","note": "Model / Non-model / AI-model — drives workflow branch"},
        {"name": "identification_outcome", "display_name": "Identification outcome",  "data_type": "Single-select","section": "Descriptive",        "note": "Outcome of assessment questionnaire"},
        {"name": "involves_ai",            "display_name": "Involves AI/ML",          "data_type": "Single-select","section": "Model Identification","note": "Yes/No — shows AI-specific conditional sections"},
        {"name": "linked_model_id",        "display_name": "Linked model",            "data_type": "Association",  "section": "Preliminary",        "note": "Model entity created from this assessment"},
    ]
    subproc_attrs = [
        {"name": "subprocess_type",    "display_name": "Subprocess type",   "data_type": "Single-select",  "section": "Preliminary",      "note": "Validation / Annual Review / Monitoring / Retirement / Change"},
        {"name": "parent_model_id",    "display_name": "Parent model",      "data_type": "Association",    "section": "Preliminary",      "note": "Model this subprocess belongs to"},
        {"name": "validator_assigned", "display_name": "Assigned validator","data_type": "Association",    "section": "Preliminary",      "note": "IV team member responsible"},
        {"name": "val_start_date",     "display_name": "Validation start",  "data_type": "Date",           "section": "General",          "note": "Actual start date of validation activity"},
        {"name": "val_end_date",       "display_name": "Validation end",    "data_type": "Date",           "section": "General",          "note": "Actual completion date"},
        {"name": "sign_off_status",    "display_name": "Sign-off status",   "data_type": "Single-select",  "section": "Descriptive",      "note": "Signed off / Conditional / Rejected"},
    ]
    finding_attrs = [
        {"name": "severity",          "display_name": "Severity",           "data_type": "Single-select", "section": "Preliminary", "note": "Critical / Major / Minor"},
        {"name": "finding_type",      "display_name": "Finding type",       "data_type": "Single-select", "section": "Preliminary", "note": "Conceptual / Data / Performance / Documentation"},
        {"name": "linked_validation", "display_name": "Linked validation",  "data_type": "Association",   "section": "Preliminary", "note": "VLD-xxx that raised this finding"},
        {"name": "due_date",          "display_name": "Resolution due date","data_type": "Date",          "section": "General",     "note": "Tracked; triggers reminder automation"},
        {"name": "resolution_notes",  "display_name": "Resolution notes",   "data_type": "Text extended", "section": "Descriptive", "note": "Model owner closure notes"},
        {"name": "closure_evidence",  "display_name": "Closure evidence",   "data_type": "Association",   "section": "Descriptive", "note": "Document uploaded as proof of closure"},
    ]
    uc_attrs = [
        {"name": "use_case_desc",     "display_name": "Use case description","data_type": "Text extended","section": "Descriptive","note": "Why the model exists; linked to N models"},
        {"name": "linked_models",     "display_name": "Linked models",       "data_type": "Association",  "section": "Preliminary","note": "All models sharing this use case"},
    ]
    query_attrs = [
        {"name": "query_text",        "display_name": "Query",              "data_type": "Text extended", "section": "Descriptive","note": "Justification query raised against the model"},
        {"name": "raised_by",         "display_name": "Raised by",          "data_type": "Association",   "section": "Preliminary","note": "User who raised the query"},
        {"name": "query_resolution",  "display_name": "Resolution",         "data_type": "Text extended", "section": "Descriptive","note": "How the query was answered"},
    ]

    for tab_obj, attrs in zip(schema_tabs,
                               [model_attrs, assess_attrs, subproc_attrs,
                                finding_attrs, uc_attrs, query_attrs]):
        with tab_obj:
            st.dataframe(pd.DataFrame(attrs), use_container_width=True, hide_index=True,
                         column_config={
                             "name": st.column_config.TextColumn("Field name (formula key)", width="medium"),
                             "display_name": st.column_config.TextColumn("Display name (UI label)", width="medium"),
                             "data_type": st.column_config.TextColumn("Data type", width="medium"),
                             "section": st.column_config.TextColumn("Section", width="small"),
                             "note": st.column_config.TextColumn("Notes", width="large"),
                         })

    st.markdown("---")
    st.markdown("#### Stage transitions (lifecycle state machine)")
    for subtype, stages in STAGE_TRANSITIONS.items():
        with st.expander(f"{subtype} workflow"):
            flow = " → ".join(stages)
            st.markdown(f"`{flow}`")
            st.caption("Stages are forward-only. advanceStage() enforces this.")
