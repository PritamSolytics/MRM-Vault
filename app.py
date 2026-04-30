"""
MRM Vault | Enterprise Explorer v3
Streamlit dashboard — production grade

Fixes vs v2:
  - applymap → map (pandas 2.1+)
  - Multi-entity selection now works with proper session state
  - Full interactive canvas (single-page unified view)
  - Solytics color scheme: white base, navy #003366, teal #00A5A8, orange #FF6B35
  - Clean, uncluttered layout with beautiful typography
  - All KT-sourced content integrated (workflows, templates, automations, document templates,
    variables, reports, landscape, conditional sections, attribute types)

Run:
  pip install streamlit pandas plotly
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import math
import io
import csv
from typing import List, Dict, Optional

from data_model import (
    NODES, LINKS, REL_TYPES, NODE_SCHEMA, STAGE_TRANSITIONS,
    ENTITY, WORKFLOW, QUICK_ACCESS,
    get_risk_score, get_status_color, get_risk_color,
    ATTRIBUTE_LIBRARY, TEMPLATE_CONFIGS, SECTION_RULES,
    DOCUMENT_TEMPLATES, AUTOMATION_RULES,
    MASTER_ENTITY_TABLE, WORKFLOW_ENTITY_TABLE, STAGE_ENTITY_TABLE, TASK_ENTITY_TABLE,
    MASTER_PERMISSION_TABLE, SECTION_TYPE_REGISTRY, get_permission,
    MASTER_RELATIONSHIP_TABLE, RELATIONSHIP_SUBSETS,
    VERSION_REGISTRY, EXECUTION_EVENTS, AUDIT_LOG, API_LOG,
)
from graph_engine import (
    get_outgoing, get_incoming, get_visible_ids, get_visible_links,
    get_directed_link, impact_trace, upstream_trace,
    get_consumers, advance_stage,
)

# ─────────────────────────────────────────────────────────────────────────────
# SOLYTICS BRAND PALETTE
# Primary navy: #003366 | Teal accent: #00A5A8 | Orange: #FF6B35
# Text: #1A1A2E | Surface: #FFFFFF | Background: #F7F9FC | Border: #E4E8EF
# ─────────────────────────────────────────────────────────────────────────────
BRAND = {
    "navy":    "#003366",
    "teal":    "#00A5A8",
    "orange":  "#FF6B35",
    "text":    "#1A1A2E",
    "surface": "#FFFFFF",
    "bg":      "#F7F9FC",
    "border":  "#E4E8EF",
    "muted":   "#6B7280",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger":  "#EF4444",
}

st.set_page_config(
    page_title="MRM Vault | Solytics Partners",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Solytics white theme with clean enterprise typography
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  color: {BRAND['text']};
}}
.main .block-container {{
  padding: 1.2rem 2rem 2rem;
  max-width: 1700px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
  background: {BRAND['navy']} !important;
  border-right: none;
}}
[data-testid="stSidebar"] * {{ color: #C8D8EC !important; }}
[data-testid="stSidebar"] label {{
  color: #7FA3CC !important;
  font-size: 11px !important;
  text-transform: uppercase;
  letter-spacing: .06em;
}}
[data-testid="stSidebar"] h3 {{
  color: #E8F1FB !important;
  font-size: 10px !important;
  text-transform: uppercase;
  letter-spacing: .1em;
  font-weight: 700;
}}
[data-testid="stSidebar"] .stButton button {{
  background: rgba(255,255,255,0.07) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  color: #C8D8EC !important;
  border-radius: 6px !important;
  font-size: 12px !important;
  text-align: left !important;
  width: 100% !important;
  transition: all .15s !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{
  background: rgba(0,165,168,0.25) !important;
  border-color: {BRAND['teal']} !important;
  color: white !important;
}}

/* ── Header ── */
.vault-header {{
  background: white;
  border-bottom: 2px solid {BRAND['border']};
  padding: 16px 0 12px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}}
.vault-wordmark {{
  font-size: 20px;
  font-weight: 800;
  color: {BRAND['navy']};
  letter-spacing: -.02em;
}}
.vault-wordmark span {{
  color: {BRAND['teal']};
}}
.vault-subtitle {{
  font-size: 12px;
  color: {BRAND['muted']};
  margin-top: 1px;
}}
.vault-badge {{
  display: inline-block;
  background: {BRAND['navy']};
  color: white;
  font-size: 9px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  letter-spacing: .08em;
  text-transform: uppercase;
  margin-right: 6px;
}}
.vault-badge.teal {{ background: {BRAND['teal']}; }}
.vault-badge.orange {{ background: {BRAND['orange']}; }}

/* ── KPI bar ── */
.kpi-row {{
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}}
.kpi-card {{
  background: white;
  border: 1px solid {BRAND['border']};
  border-radius: 10px;
  padding: 12px 16px;
  flex: 1;
  min-width: 120px;
  position: relative;
  overflow: hidden;
}}
.kpi-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 3px; height: 100%;
  background: {BRAND['teal']};
  border-radius: 10px 0 0 10px;
}}
.kpi-label {{ font-size: 10px; font-weight: 600; color: {BRAND['muted']}; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 4px; }}
.kpi-value {{ font-size: 22px; font-weight: 800; color: {BRAND['navy']}; line-height: 1; }}
.kpi-sub   {{ font-size: 10.5px; color: {BRAND['muted']}; margin-top: 3px; }}

/* ── Section header ── */
.sec-hdr {{
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .09em;
  color: {BRAND['muted']};
  border-bottom: 1px solid {BRAND['border']};
  padding-bottom: 5px;
  margin: 14px 0 8px;
}}

/* ── Badges / pills ── */
.pill {{
  display: inline-block;
  font-size: 9.5px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: .05em;
}}
.pill-entity   {{ background: #EBF5FF; color: {BRAND['navy']}; border: 1px solid #BDD8F5; }}
.pill-workflow {{ background: #E6FAFA; color: {BRAND['teal']}; border: 1px solid #A3DFE0; }}
.pill-high     {{ background: #FEE2E2; color: #991B1B; }}
.pill-medium   {{ background: #FEF3C7; color: #92400E; }}
.pill-low      {{ background: #D1FAE5; color: #065F46; }}
.pill-static   {{ background: #EDE9FE; color: #5B21B6; }}
.pill-dynamic  {{ background: #FFF7ED; color: #C2410C; }}
.pill-system   {{ background: #F3F4F6; color: #374151; }}
.pill-M        {{ background: #D1FAE5; color: #065F46; font-weight: 800; }}
.pill-V        {{ background: #DBEAFE; color: #1E40AF; }}
.pill-H        {{ background: #F3F4F6; color: #9CA3AF; }}

/* ── Node detail ── */
.node-hero   {{ padding-bottom: 10px; margin-bottom: 10px; border-bottom: 1px solid {BRAND['border']}; }}
.node-name   {{ font-size: 16px; font-weight: 800; color: {BRAND['navy']}; margin: 6px 0 4px; }}
.node-desc   {{ font-size: 12px; color: {BRAND['muted']}; line-height: 1.6; }}
.meta-grid   {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0; }}
.meta-item .ml {{ font-size: 9px; font-weight: 700; color: {BRAND['muted']}; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 2px; }}
.meta-item .mv {{ font-size: 12px; font-weight: 600; color: {BRAND['text']}; }}

/* ── Relationship items ── */
.rel-row {{
  display: flex;
  align-items: center;
  padding: 7px 10px;
  background: {BRAND['bg']};
  border: 1px solid {BRAND['border']};
  border-radius: 8px;
  margin-bottom: 4px;
  font-size: 12px;
  gap: 8px;
  cursor: pointer;
  transition: all .12s;
}}
.rel-row:hover {{ border-color: {BRAND['teal']}; background: #E6FAFA; }}
.rel-icon-e {{ background: #EBF5FF; color: {BRAND['navy']}; border-radius: 4px; padding: 1px 5px; font-size: 8px; font-weight: 800; flex-shrink: 0; }}
.rel-icon-w {{ background: #E6FAFA; color: {BRAND['teal']}; border-radius: 4px; padding: 1px 5px; font-size: 8px; font-weight: 800; flex-shrink: 0; }}
.cat-pill   {{ font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 12px; flex-shrink: 0; }}

/* ── Stage tracker ── */
.stage-item {{ display: flex; align-items: center; gap: 8px; padding: 5px 0; border-bottom: 1px solid {BRAND['bg']}; font-size: 12px; }}
.s-done {{ color: {BRAND['success']}; font-weight: 600; }}
.s-cur  {{ color: {BRAND['teal']}; font-weight: 700; }}
.s-pend {{ color: {BRAND['muted']}; }}

/* ── Score bar ── */
.sbar-wrap {{ background: {BRAND['border']}; border-radius: 4px; height: 5px; margin: 3px 0; }}
.sbar      {{ height: 5px; border-radius: 4px; }}

/* ── Impact chips ── */
.chip-impact {{ background: #D1FAE5; border: 1px solid #6EE7B7; border-radius: 6px; padding: 4px 8px; font-size: 11px; color: #065F46; margin-bottom: 3px; }}
.chip-up     {{ background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 6px; padding: 4px 8px; font-size: 11px; color: #C2410C; margin-bottom: 3px; }}
.chip-deg    {{ background: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 6px; padding: 4px 8px; font-size: 11px; color: #991B1B; margin-bottom: 3px; }}

/* ── Artifact pill ── */
.art-pill {{ display:inline-flex; align-items:center; gap:4px; padding:3px 9px; background:{BRAND['bg']}; border:1px solid {BRAND['border']}; border-radius:5px; font-size:11px; margin:2px; color:{BRAND['text']}; }}

/* ── Activity ── */
.act-item {{ display:flex; gap:8px; padding:5px 0; border-bottom:1px solid {BRAND['bg']}; }}
.act-dot  {{ width:6px; height:6px; border-radius:50%; background:{BRAND['teal']}; margin-top:5px; flex-shrink:0; }}
.act-text {{ font-size:11.5px; color:{BRAND['text']}; line-height:1.5; }}
.act-time {{ font-size:10px; color:{BRAND['muted']}; }}

/* ── Timeline event ── */
.tl-evt {{
  background: white;
  border: 1px solid {BRAND['border']};
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 6px;
  border-left: 3px solid {BRAND['teal']};
}}
.tl-evt.approved {{ border-left-color: {BRAND['success']}; }}
.tl-evt.review   {{ border-left-color: {BRAND['warning']}; }}

/* ── Version chain ── */
.ver-node {{
  display: inline-block;
  background: white;
  border: 1.5px solid {BRAND['border']};
  border-radius: 8px;
  padding: 8px 14px;
  min-width: 130px;
  margin: 4px;
  vertical-align: top;
  text-align: center;
}}
.ver-node.active   {{ border-color: {BRAND['teal']};   background: #E6FAFA; }}
.ver-node.approved {{ border-color: {BRAND['success']}; background: #D1FAE5; }}
.ver-node.superseded {{ border-color: {BRAND['muted']}; background: {BRAND['bg']}; opacity: .7; }}

/* ── Audit row ── */
.aud-row {{
  padding: 8px 12px;
  border-left: 3px solid {BRAND['border']};
  background: {BRAND['bg']};
  border-radius: 0 7px 7px 0;
  margin-bottom: 6px;
  font-size: 11.5px;
}}

/* ── API pill ── */
.apill {{
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}}
.apill-GET   {{ background: #D1FAE5; color: #065F46; }}
.apill-POST  {{ background: #DBEAFE; color: #1E40AF; }}
.apill-PATCH {{ background: #FEF3C7; color: #92400E; }}
.apill-200   {{ background: #D1FAE5; color: #065F46; }}
.apill-201   {{ background: #DBEAFE; color: #1E40AF; }}

/* ── Section perm card ── */
.spc {{
  background: white;
  border: 1px solid {BRAND['border']};
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
}}
.spc h4 {{ font-size: 13px; font-weight: 700; color: {BRAND['navy']}; margin: 0 0 4px; }}

/* ── Canvas panel ── */
.canvas-wrap {{
  background: white;
  border: 1px solid {BRAND['border']};
  border-radius: 12px;
  overflow: hidden;
}}

/* ── Mono ── */
.mono {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; }}

/* ── Breadcrumb ── */
.breadcrumb {{ display:flex; align-items:center; gap:4px; margin-bottom:10px; flex-wrap:wrap; }}
.bc-item {{ font-size:12px; color:{BRAND['muted']}; }}
.bc-sep  {{ font-size:12px; color:{BRAND['border']}; }}
.bc-curr {{ font-size:12px; color:{BRAND['teal']}; font-weight:600; }}

/* ── Table fix ── */
.stDataFrame {{ border-radius: 8px; overflow: hidden; border: 1px solid {BRAND['border']} !important; }}

/* ── Tab underline ── */
.stTabs [data-baseweb="tab-list"] {{ background: {BRAND['bg']}; border-radius: 10px 10px 0 0; border-bottom: 2px solid {BRAND['border']}; padding: 0 8px; }}
.stTabs [data-baseweb="tab"] {{ font-size: 12.5px; font-weight: 600; color: {BRAND['muted']}; }}
.stTabs [aria-selected="true"] {{ color: {BRAND['navy']} !important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def _init():
    defs = dict(
        selected_id="credit_risk_model",
        depth=1,
        show_entities=True,
        show_workflows=True,
        cat_filter="All",
        history=["credit_risk_model"],
        multi_entity_sel=["Model"],    # for entity sub-template tab
        ver_entity="All",
        aud_entity="All",
        aud_field="All",
        aud_user="All",
        exec_entity="All",
        subset_filter="All",
        perm_entity="All",
    )
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY COLOURS
# ─────────────────────────────────────────────────────────────────────────────
CAT_CLR = {
    "lineage":    {"stroke": "#1D4ED8", "bg": "#DBEAFE", "text": "#1D4ED8"},
    "governance": {"stroke": "#7C3AED", "bg": "#EDE9FE", "text": "#6D28D9"},
    "validation": {"stroke": "#0891B2", "bg": "#CFFAFE", "text": "#0E7490"},
    "monitoring": {"stroke": "#059669", "bg": "#D1FAE5", "text": "#065F46"},
    "lifecycle":  {"stroke": BRAND["orange"], "bg": "#FFF7ED", "text": "#C2410C"},
    "issue":      {"stroke": BRAND["danger"], "bg": "#FEE2E2", "text": "#991B1B"},
    "output":     {"stroke": BRAND["teal"],   "bg": "#E6FAFA", "text": "#0E5F60"},
    "default":    {"stroke": BRAND["muted"],  "bg": BRAND["bg"], "text": BRAND["muted"]},
}

def navigate_to(node_id: str):
    if node_id not in NODES:
        return
    st.session_state.selected_id = node_id
    h = st.session_state.history
    if not h or h[-1] != node_id:
        h.append(node_id)
    if len(h) > 8:
        h.pop(0)
    st.rerun()

def trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n-1] + "…"

# ─────────────────────────────────────────────────────────────────────────────
# SAFE PANDAS MAP HELPER (works on pandas 1.x and 2.x)
# ─────────────────────────────────────────────────────────────────────────────
def safe_map(styler, fn, subset=None):
    """Use Styler.map (pandas≥2.1) or fall back to applymap."""
    try:
        return styler.map(fn, subset=subset)
    except AttributeError:
        return styler.applymap(fn, subset=subset)

# ─────────────────────────────────────────────────────────────────────────────
# SVG GRAPH
# ─────────────────────────────────────────────────────────────────────────────
def _radial_pos(ids, sel, W=920, H=560):
    pos = {}
    if sel not in ids:
        return pos
    pos[sel] = (W / 2, H / 2)
    others = [i for i in ids if i != sel]
    others.sort(key=lambda i: (0 if NODES[i]["type"] == WORKFLOW else 1))
    n = len(others)
    r = min(min(W, H) * 0.36, 235)
    for idx, nid in enumerate(others):
        a = (2 * math.pi * idx / max(n, 1)) - math.pi / 2
        pos[nid] = (W / 2 + r * math.cos(a), H / 2 + r * math.sin(a))
    return pos

def render_svg(ids, sel, cat_filter="All"):
    W, H, NW, NH = 920, 560, 200, 72
    pos = _radial_pos(ids, sel, W, H)
    links = get_visible_links(ids)

    MARKERS = {
        "lineage": "arr-blue", "governance": "arr-purple", "validation": "arr-teal",
        "monitoring": "arr-green", "lifecycle": "arr-orange", "issue": "arr-red",
        "output": "arr-teal",
    }
    MDEF = {
        "arr-blue": "#1D4ED8", "arr-purple": "#7C3AED", "arr-teal": "#0891B2",
        "arr-green": "#059669", "arr-orange": BRAND["orange"], "arr-red": BRAND["danger"],
    }

    p = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" xmlns="http://www.w3.org/2000/svg">']
    p.append("<defs>")
    for mid, col in MDEF.items():
        p.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M2 1L8 5L2 9" fill="none" stroke="{col}" stroke-width="1.4" stroke-linecap="round"/></marker>')
    p.append('<marker id="arr-dark" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
             '<path d="M2 1L8 5L2 9" fill="none" stroke="#9CA3AF" stroke-width="1.2" stroke-linecap="round"/></marker>')
    p.append('<filter id="shd"><feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#003366" flood-opacity="0.07"/></filter>')
    p.append('<filter id="shd-sel"><feDropShadow dx="0" dy="4" stdDeviation="12" flood-color="#00A5A8" flood-opacity="0.22"/></filter>')
    p.append('<pattern id="dots" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">'
             '<circle cx="14" cy="14" r="0.8" fill="#D1D5DB" opacity="0.5"/></pattern>')
    p.append("</defs>")

    p.append(f'<rect width="{W}" height="{H}" fill="#FAFBFD" rx="12"/>')
    p.append(f'<rect width="{W}" height="{H}" fill="url(#dots)" rx="12"/>')

    # Edges
    for lk in links:
        src, tgt = lk["source"], lk["target"]
        if src not in pos or tgt not in pos:
            continue
        rt  = REL_TYPES.get(lk["relType"], {})
        cat = rt.get("category", "default")
        if cat_filter != "All" and cat != cat_filter.lower():
            continue
        hi = (src == sel or tgt == sel)
        clr = CAT_CLR.get(cat, CAT_CLR["default"])
        stroke = clr["stroke"] if hi else "#E4E8EF"
        sw     = "1.8" if hi else "0.9"
        mid    = MARKERS.get(cat, "arr-dark") if hi else "arr-dark"

        x1, y1 = pos[src]
        x2, y2 = pos[tgt]
        dx, dy = x2 - x1, y2 - y1
        dist   = math.sqrt(dx*dx + dy*dy) or 1
        cx_    = (x1+x2)/2 - dy/dist * 20
        cy_    = (y1+y2)/2 + dx/dist * 20
        pad    = math.sqrt((NW/2)**2*(dx/dist)**2 + (NH/2)**2*(dy/dist)**2)
        sx, sy = x1 + dx/dist*(pad+4),  y1 + dy/dist*(pad+4)
        ex, ey = x2 - dx/dist*(pad+14), y2 - dy/dist*(pad+14)

        p.append(f'<path d="M{sx:.1f} {sy:.1f} Q{cx_:.1f} {cy_:.1f} {ex:.1f} {ey:.1f}" '
                 f'fill="none" stroke="{stroke}" stroke-width="{sw}" marker-end="url(#{mid})"/>')

        if hi:
            lx = 0.25*sx + 0.5*cx_ + 0.25*ex
            ly = 0.25*sy + 0.5*cy_ + 0.25*ey
            lbl = rt.get("label", lk["relType"])[:14]
            card = lk.get("cardinality", "")
            full = f"{lbl}  {card}" if card else lbl
            lw   = len(full) * 6.1 + 12
            p.append(f'<rect x="{lx-lw/2:.1f}" y="{ly-9:.1f}" width="{lw:.1f}" height="18" '
                     f'rx="5" fill="{clr["bg"]}" stroke="{clr["stroke"]}" stroke-width="0.6"/>')
            p.append(f'<text x="{lx:.1f}" y="{ly+1:.1f}" text-anchor="middle" dominant-baseline="middle" '
                     f'font-size="8.5" font-weight="700" fill="{clr["text"]}" font-family="Plus Jakarta Sans,system-ui">{full}</text>')

    # Nodes
    order = [i for i in ids if i != sel] + ([sel] if sel in ids else [])
    for nid in order:
        if nid not in pos:
            continue
        nd = NODES[nid]
        x, y = pos[nid]
        rx_, ry_ = x - NW/2, y - NH/2
        is_sel  = (nid == sel)
        is_ent  = nd["type"] == ENTITY
        fill    = "white" if is_ent else BRAND["navy"]
        bdr_col = BRAND["teal"] if is_sel else (BRAND["border"] if is_ent else BRAND["navy"])
        bdr_w   = "2.5" if is_sel else "1"
        filt    = "url(#shd-sel)" if is_sel else "url(#shd)"
        accent  = BRAND["teal"] if is_ent else BRAND["orange"]

        p.append(f'<g filter="{filt}">')
        p.append(f'<rect x="{rx_:.1f}" y="{ry_:.1f}" width="{NW}" height="{NH}" '
                 f'rx="12" fill="{fill}" stroke="{bdr_col}" stroke-width="{bdr_w}"/>')
        p.append(f'<rect x="{rx_:.1f}" y="{ry_:.1f}" width="4" height="{NH}" '
                 f'rx="2" fill="{accent}"/>')

        ic_bg  = "#EBF5FF" if is_ent else "rgba(255,255,255,0.12)"
        ic_col = BRAND["navy"] if is_ent else BRAND["teal"]
        ic_lbl = "EN" if is_ent else "WF"
        icx, icy = rx_+24, y
        p.append(f'<circle cx="{icx:.1f}" cy="{icy:.1f}" r="12" fill="{ic_bg}"/>')
        p.append(f'<text x="{icx:.1f}" y="{icy:.1f}" text-anchor="middle" dominant-baseline="middle" '
                 f'font-size="8" font-weight="800" fill="{ic_col}" font-family="Plus Jakarta Sans,system-ui">{ic_lbl}</text>')

        nm_col = BRAND["navy"] if is_ent else "#E8F1FB"
        sb_col = BRAND["muted"] if is_ent else "#7FA3CC"
        p.append(f'<text x="{rx_+44:.1f}" y="{ry_+22:.1f}" dominant-baseline="middle" '
                 f'font-size="12" font-weight="700" fill="{nm_col}" '
                 f'font-family="Plus Jakarta Sans,system-ui">{trunc(nd["name"], 21)}</text>')
        p.append(f'<text x="{rx_+44:.1f}" y="{ry_+37:.1f}" dominant-baseline="middle" '
                 f'font-size="10" fill="{sb_col}" font-family="Plus Jakarta Sans,system-ui">{nd["subtype"]}</text>')

        bv = nd.get("risk") or nd.get("status", "")
        if bv and bv not in ("-", ""):
            bg_b, tc_b = get_risk_color(bv) if nd.get("risk") else get_status_color(nd.get("status",""))
            bw_ = len(str(bv)) * 6 + 12
            p.append(f'<rect x="{rx_+44:.1f}" y="{ry_+49:.1f}" width="{bw_:.1f}" height="14" rx="7" fill="{bg_b}"/>')
            p.append(f'<text x="{rx_+44+bw_/2:.1f}" y="{ry_+56:.1f}" text-anchor="middle" dominant-baseline="middle" '
                     f'font-size="8.5" font-weight="700" fill="{tc_b}" font-family="Plus Jakarta Sans,system-ui">{bv}</text>')
        p.append("</g>")

    # Legend
    leg = [("lineage","Lineage"),("governance","Governance"),("validation","Validation"),
           ("monitoring","Monitoring"),("lifecycle","Lifecycle"),("issue","Issue")]
    lx_ = 14
    lw_total = 16 + len(leg) * 92
    p.append(f'<rect x="10" y="{H-28}" width="{lw_total}" height="20" rx="5" '
             f'fill="rgba(255,255,255,0.92)" stroke="{BRAND["border"]}" stroke-width="0.5"/>')
    for cat_, lab_ in leg:
        c = CAT_CLR.get(cat_, CAT_CLR["default"])
        p.append(f'<rect x="{lx_:.1f}" y="{H-20}" width="14" height="2" rx="1" fill="{c["stroke"]}"/>')
        p.append(f'<text x="{lx_+18:.1f}" y="{H-16}" font-size="9" fill="{c["text"]}" '
                 f'font-family="Plus Jakarta Sans,system-ui">{lab_}</text>')
        lx_ += 92
    p.append("</svg>")
    return "".join(p)

# ─────────────────────────────────────────────────────────────────────────────
# DETAIL PANEL
# ─────────────────────────────────────────────────────────────────────────────
def render_detail(node_id: str):
    nd = NODES.get(node_id)
    if not nd:
        st.caption("No entity selected.")
        return
    out_lk = get_outgoing(node_id)
    in_lk  = get_incoming(node_id)
    impacted = impact_trace(node_id)
    upstream = upstream_trace(node_id)
    consumers = get_consumers(node_id)
    score  = get_risk_score(node_id)
    is_ent = nd["type"] == ENTITY
    sc_col = BRAND["danger"] if score >= 70 else BRAND["warning"] if score >= 40 else BRAND["success"]
    sc_bg  = "#FEE2E2" if score >= 70 else "#FEF3C7" if score >= 40 else "#D1FAE5"

    type_cls = "pill-entity" if is_ent else "pill-workflow"
    st.markdown(f"""
    <div class="node-hero">
      <span class="pill {type_cls}">{nd['type']}</span>
      <span style="font-size:10px;color:{BRAND['muted']};margin-left:5px">{nd['subtype']}</span>
      <div class="node-name">{nd['name']}</div>
      <div class="node-desc">{nd.get('summary','')}</div>
    </div>""", unsafe_allow_html=True)

    sc_, _ = get_status_color(nd.get("status",""))
    ver    = nd.get("current_version","—")
    st.markdown(f"""
    <div class="meta-grid">
      <div class="meta-item"><div class="ml">Owner</div><div class="mv">{nd['owner']}</div></div>
      <div class="meta-item"><div class="ml">Status</div>
        <div class="mv" style="color:{sc_}">{nd.get('status','—')}</div></div>
      <div class="meta-item"><div class="ml">{"Risk" if is_ent else "Stage"}</div>
        <div class="mv">{nd.get('risk','—') if is_ent else nd.get('stage','—')}</div></div>
      <div class="meta-item"><div class="ml">Version</div>
        <div class="mv mono">{ver}</div></div>
      {"<div class='meta-item'><div class='ml'>Risk Score</div><div class='mv'><span style='background:"+sc_bg+";color:"+sc_col+";padding:2px 8px;border-radius:4px;font-weight:800'>"+str(score)+"/100</span></div></div>" if is_ent else ""}
      <div class="meta-item"><div class="ml">Jurisdiction</div>
        <div class="mv" style="font-size:11px">{nd.get('jurisdiction','—')}</div></div>
    </div>""", unsafe_allow_html=True)

    if is_ent and score > 0:
        st.markdown(f'<div class="sbar-wrap"><div class="sbar" style="width:{score}%;background:{sc_col}"></div></div>',
                    unsafe_allow_html=True)

    # Downstream
    if impacted:
        st.markdown(f'<div class="sec-hdr">Downstream impact — {len(impacted)} affected</div>', unsafe_allow_html=True)
        for iid in impacted[:5]:
            n2 = NODES.get(iid,{})
            lk = get_directed_link(node_id, iid)
            cat = REL_TYPES.get(lk["relType"] if lk else "",{}).get("category","default")
            c   = CAT_CLR.get(cat, CAT_CLR["default"])
            st.markdown(f'<div class="chip-impact">↓ {n2.get("name",iid)} '
                        f'<span class="cat-pill" style="background:{c["bg"]};color:{c["text"]}">{cat}</span></div>',
                        unsafe_allow_html=True)

    # Upstream
    if upstream:
        deg = [u for u in upstream if NODES.get(u,{}).get("status") in ("Under Review","Not Started")]
        st.markdown(f'<div class="sec-hdr">Upstream dependencies — {len(upstream)}</div>', unsafe_allow_html=True)
        for uid in upstream[:5]:
            n2   = NODES.get(uid,{})
            lk   = get_directed_link(uid, node_id)
            lbl  = REL_TYPES.get(lk["relType"] if lk else "",{}).get("label","")
            is_d = uid in deg
            cls  = "chip-deg" if is_d else "chip-up"
            st.markdown(f'<div class="{cls}">↑ {n2.get("name",uid)} '
                        f'<span style="font-size:10px"> via {lbl}{"  ⚠" if is_d else ""}</span></div>',
                        unsafe_allow_html=True)

    # Outgoing
    if out_lk:
        st.markdown(f'<div class="sec-hdr">Outgoing — {len(out_lk)}</div>', unsafe_allow_html=True)
        for lk in out_lk:
            n2 = NODES.get(lk["target"],{})
            rt = REL_TYPES.get(lk["relType"],{})
            cat = rt.get("category","default")
            c   = CAT_CLR.get(cat, CAT_CLR["default"])
            ic  = "rel-icon-e" if n2.get("type")==ENTITY else "rel-icon-w"
            il  = "E" if n2.get("type")==ENTITY else "WF"
            col1, col2 = st.columns([5,1])
            with col1:
                st.markdown(f'<div class="rel-row"><span class="{ic}">{il}</span>'
                            f'<span style="flex:1">{n2.get("name","")}</span>'
                            f'<span class="cat-pill" style="background:{c["bg"]};color:{c["text"]}">{rt.get("label","")}</span>'
                            f'<span style="font-size:9px;color:{BRAND["muted"]}">{lk.get("cardinality","")}</span>'
                            f'</div>', unsafe_allow_html=True)
            with col2:
                if st.button("→", key=f"o_{node_id}_{lk['target']}"):
                    navigate_to(lk["target"])

    # Incoming
    if in_lk:
        st.markdown(f'<div class="sec-hdr">Incoming — {len(in_lk)}</div>', unsafe_allow_html=True)
        for lk in in_lk:
            n2 = NODES.get(lk["source"],{})
            rt = REL_TYPES.get(lk["relType"],{})
            cat = rt.get("category","default")
            c   = CAT_CLR.get(cat, CAT_CLR["default"])
            ic  = "rel-icon-e" if n2.get("type")==ENTITY else "rel-icon-w"
            il  = "E" if n2.get("type")==ENTITY else "WF"
            col1, col2 = st.columns([5,1])
            with col1:
                st.markdown(f'<div class="rel-row"><span class="{ic}">{il}</span>'
                            f'<span style="flex:1">{n2.get("name","")}</span>'
                            f'<span class="cat-pill" style="background:{c["bg"]};color:{c["text"]}">← {rt.get("label","")}</span>'
                            f'<span style="font-size:9px;color:{BRAND["muted"]}">{lk.get("cardinality","")}</span>'
                            f'</div>', unsafe_allow_html=True)
            with col2:
                if st.button("→", key=f"i_{node_id}_{lk['source']}"):
                    navigate_to(lk["source"])

    # Stages
    if nd.get("stages"):
        st.markdown('<div class="sec-hdr">Lifecycle stages</div>', unsafe_allow_html=True)
        for s in nd["stages"]:
            if s["status"]=="done":    ico,cls = "✓","s-done"
            elif s["status"]=="current": ico,cls = "●","s-cur"
            else:                        ico,cls = "○","s-pend"
            st.markdown(f'<div class="stage-item"><span>{ico}</span><span class="{cls}">{s["name"]}</span></div>',
                        unsafe_allow_html=True)
        ci = next((i for i,s in enumerate(nd["stages"]) if s["status"]=="current"), -1)
        if 0 <= ci < len(nd["stages"])-1:
            if st.button("⏭ Advance stage", key=f"adv_{node_id}", type="primary"):
                r = advance_stage(node_id)
                st.success(r["new_stage"]) if r["ok"] else st.error(r["message"])
                if r["ok"]: st.rerun()

    # Attributes
    if nd.get("attributes"):
        st.markdown('<div class="sec-hdr">Attributes</div>', unsafe_allow_html=True)
        rows = [{"Attribute": nd.get("attr_defs",{}).get(k,{}).get("display_name",k),
                 "Value": str(v),
                 "Section": nd.get("attr_defs",{}).get(k,{}).get("section","—")}
                for k, v in nd["attributes"].items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Artifacts
    if nd.get("artifacts"):
        st.markdown('<div class="sec-hdr">Artifacts</div>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="art-pill">📄 {a}</span>' for a in nd["artifacts"]),
                    unsafe_allow_html=True)

    # Activity
    if nd.get("activity"):
        st.markdown('<div class="sec-hdr">Recent activity</div>', unsafe_allow_html=True)
        for act in nd["activity"]:
            st.markdown(f'<div class="act-item"><div class="act-dot"></div>'
                        f'<div><div class="act-text">{act["text"]}</div>'
                        f'<div class="act-time">{act["time"]}</div></div></div>',
                        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:4px 0 16px">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,{BRAND['teal']},{BRAND['orange']});
                    border-radius:9px;display:flex;align-items:center;justify-content:center">
          <span style="color:white;font-size:18px;font-weight:900">⬡</span>
        </div>
        <div>
          <div style="font-size:15px;font-weight:800;color:white;letter-spacing:-.01em">MRM Vault</div>
          <div style="font-size:10px;color:#7FA3CC">Solytics Partners</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    q = st.text_input("🔍 Search entities", placeholder="model, dataset…", label_visibility="collapsed")
    if q:
        matches = [(nid, n) for nid, n in NODES.items() if q.lower() in n["name"].lower()]
        for nid, n in matches[:6]:
            if st.button(n["name"], key=f"s_{nid}"):
                navigate_to(nid)
        if not matches:
            st.caption("No results")

    st.markdown("### Display")
    st.session_state.show_entities  = st.checkbox("Show entities",  value=st.session_state.show_entities)
    st.session_state.show_workflows = st.checkbox("Show workflows", value=st.session_state.show_workflows)

    st.markdown("### Depth")
    dm = {"1 hop":1,"2 hops":2,"All":999}
    dl = st.radio("d", list(dm.keys()), horizontal=True, label_visibility="collapsed")
    st.session_state.depth = dm[dl]

    st.markdown("### Category")
    st.session_state.cat_filter = st.selectbox("c", ["All","Lineage","Governance","Validation","Monitoring","Lifecycle","Issue","Output"], label_visibility="collapsed")

    st.markdown("### Quick access")
    for qa in QUICK_ACCESS:
        if st.button(qa["label"], key=f"qa_{qa['id']}"):
            navigate_to(qa["id"])

    st.markdown("---")
    if st.button("↺ Reset view"):
        st.session_state.selected_id = "credit_risk_model"
        st.session_state.depth = 1
        st.session_state.history = ["credit_risk_model"]
        st.rerun()

    st.markdown(f"""
    <div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:4px">
      <span style="font-size:9px;padding:2px 7px;background:rgba(255,255,255,0.08);
             border:1px solid rgba(255,255,255,0.12);border-radius:3px;color:#7FA3CC">RegTech100 2026</span>
      <span style="font-size:9px;padding:2px 7px;background:rgba(255,255,255,0.08);
             border:1px solid rgba(255,255,255,0.12);border-radius:3px;color:#7FA3CC">Chartis #45</span>
      <span style="font-size:9px;padding:2px 7px;background:rgba(255,255,255,0.08);
             border:1px solid rgba(255,255,255,0.12);border-radius:3px;color:#7FA3CC">SR 11-7</span>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — compute state
# ─────────────────────────────────────────────────────────────────────────────
sel_id   = st.session_state.selected_id
sel_nd   = NODES.get(sel_id, {})
depth    = st.session_state.depth

vis_ids = get_visible_ids(sel_id, depth)
if not st.session_state.show_entities:
    vis_ids = [i for i in vis_ids if NODES[i]["type"] != ENTITY or i == sel_id]
if not st.session_state.show_workflows:
    vis_ids = [i for i in vis_ids if NODES[i]["type"] != WORKFLOW or i == sel_id]
if sel_id not in vis_ids:
    vis_ids.insert(0, sel_id)

vis_links = get_visible_links(vis_ids)
impacted  = impact_trace(sel_id)
score     = get_risk_score(sel_id)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="vault-header">
  <div>
    <div class="vault-wordmark">MRM <span>Vault</span></div>
    <div class="vault-subtitle">Enterprise Model Risk Governance Explorer · Solytics Partners</div>
  </div>
  <div>
    <span class="vault-badge">SR 11-7</span>
    <span class="vault-badge teal">OSFI E-23</span>
    <span class="vault-badge teal">PRA SS1/23</span>
    <span class="vault-badge orange">EU AI Act</span>
    <span class="vault-badge">RegTech100 2026</span>
  </div>
</div>""", unsafe_allow_html=True)

# Breadcrumb
hist = st.session_state.history
if hist:
    parts = []
    for hi in hist[-6:]:
        n_ = NODES.get(hi, {})
        is_last = (hi == hist[-1])
        cls = "bc-curr" if is_last else "bc-item"
        parts.append(f'<span class="{cls}">{n_.get("name", hi)}</span>')
    bc = ' <span class="bc-sep">›</span> '.join(parts)
    st.markdown(f'<div class="breadcrumb">{bc}</div>', unsafe_allow_html=True)

# KPI bar
ent_cnt = sum(1 for i in vis_ids if NODES[i]["type"]==ENTITY)
wf_cnt  = sum(1 for i in vis_ids if NODES[i]["type"]==WORKFLOW)
sc_col  = BRAND["danger"] if score>=70 else BRAND["warning"] if score>=40 else BRAND["success"]

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-label">Selected entity</div>
    <div class="kpi-value" style="font-size:13px;margin-top:2px">{sel_nd.get('name','—')}</div>
    <div class="kpi-sub">{sel_nd.get('type','—')} · {sel_nd.get('subtype','—')}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Visible nodes</div>
    <div class="kpi-value">{len(vis_ids)}</div>
    <div class="kpi-sub">{ent_cnt} entities · {wf_cnt} workflows</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Visible links</div>
    <div class="kpi-value">{len(vis_links)}</div>
    <div class="kpi-sub">Directed relationships</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Downstream impact</div>
    <div class="kpi-value">{len(impacted)}</div>
    <div class="kpi-sub">Nodes affected by changes</div>
  </div>
  <div class="kpi-card" style="border-left-color:{sc_col}">
    <div class="kpi-label">Risk score</div>
    <div class="kpi-value" style="color:{sc_col}">{score}<span style="font-size:13px">/100</span></div>
    <div class="kpi-sub">Upstream-weighted</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Audit events</div>
    <div class="kpi-value">{len(AUDIT_LOG)}</div>
    <div class="kpi-sub">Field changes logged</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">API calls</div>
    <div class="kpi-value">{len(API_LOG)}</div>
    <div class="kpi-sub">Request log entries</div>
  </div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
(t_graph, t_canvas, t_entity, t_rel, t_workflow,
 t_perm, t_exec, t_version, t_audit, t_api) = st.tabs([
    "🔷 Graph",
    "🗺 Full Canvas",
    "📦 Entity System",
    "🔗 Relationships",
    "⚙ Workflows",
    "🔐 Permissions",
    "⏱ Execution",
    "🌳 Versions",
    "📋 Audit",
    "🌐 API",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GRAPH
# ══════════════════════════════════════════════════════════════════════════════
with t_graph:
    gc, dc = st.columns([2.3, 1], gap="large")
    with gc:
        st.markdown(f"**Relationship graph** "
                    f"<span style='font-size:12px;color:{BRAND['muted']}'>"
                    f"{'all' if depth==999 else depth}-hop · {sel_nd.get('name','')}</span>",
                    unsafe_allow_html=True)
        st.components.v1.html(render_svg(vis_ids, sel_id, st.session_state.cat_filter), height=580)

        all_nav = list(dict.fromkeys(
            [l["target"] for l in get_outgoing(sel_id)] +
            [l["source"] for l in get_incoming(sel_id)]
        ))
        if all_nav:
            st.markdown("**Navigate to connected node:**")
            cols = st.columns(min(len(all_nav), 5))
            for i, nid in enumerate(all_nav[:10]):
                n2 = NODES.get(nid,{})
                with cols[i%5]:
                    if st.button(n2.get("name",nid)[:18], key=f"nav_{sel_id}_{nid}",
                                 help=f"{n2.get('type')} · {n2.get('subtype')}"):
                        navigate_to(nid)

        st.markdown("---")
        st.markdown("**Visible relationship table**")
        if vis_links:
            rows = []
            for lk in vis_links:
                src = NODES.get(lk["source"],{})
                tgt = NODES.get(lk["target"],{})
                rt  = REL_TYPES.get(lk["relType"],{})
                rows.append({"Source": src.get("name",""), "Relationship": rt.get("label",""),
                             "Target": tgt.get("name",""), "Cardinality": lk.get("cardinality",""),
                             "Category": rt.get("category",""), "Directed": "→" if rt.get("directed",True) else "↔"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with st.expander("📝 Relationship notes"):
            for lk in vis_links:
                sn = NODES.get(lk["source"],{}).get("name","")
                tn = NODES.get(lk["target"],{}).get("name","")
                rt = REL_TYPES.get(lk["relType"],{})
                cat = rt.get("category","default")
                c = CAT_CLR.get(cat, CAT_CLR["default"])
                st.markdown(f'<span class="cat-pill" style="background:{c["bg"]};color:{c["text"]}">{cat}</span> '
                            f'**{sn}** → [{rt.get("label","")}] → **{tn}** `{lk.get("cardinality","")}`',
                            unsafe_allow_html=True)
                st.caption(lk.get("notes",""))

        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["Source","Relationship","Target","Cardinality","Category","Notes"])
        w.writeheader()
        for lk in vis_links:
            w.writerow({"Source": NODES.get(lk["source"],{}).get("name",""),
                        "Relationship": REL_TYPES.get(lk["relType"],{}).get("label",""),
                        "Target": NODES.get(lk["target"],{}).get("name",""),
                        "Cardinality": lk.get("cardinality",""),
                        "Category": REL_TYPES.get(lk["relType"],{}).get("category",""),
                        "Notes": lk.get("notes","")})
        st.download_button("⬇ Export CSV", buf.getvalue().encode(),
                           f"mrm_vault_{sel_id}.csv", "text/csv")

    with dc:
        st.markdown("**Entity detail**")
        render_detail(sel_id)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FULL CANVAS (single white-space interactive view)
# ══════════════════════════════════════════════════════════════════════════════
with t_canvas:
    st.markdown("**Full System Canvas** — all entities, relationships, workflows, and permissions in one unified view")
    st.caption("Select an entity below to explore. The canvas shows the complete system graph at full depth.")

    # Entity selector row
    all_node_ids = list(NODES.keys())
    all_node_names = [NODES[n]["name"] for n in all_node_ids]
    canvas_sel_name = st.selectbox(
        "Select entity to explore:",
        all_node_names,
        index=all_node_ids.index(sel_id) if sel_id in all_node_ids else 0,
        key="canvas_sel"
    )
    canvas_sel_id = all_node_ids[all_node_names.index(canvas_sel_name)]

    # Full-depth graph
    canvas_ids = get_visible_ids(canvas_sel_id, 999)
    st.markdown(f"""
    <div class="canvas-wrap">""", unsafe_allow_html=True)
    st.components.v1.html(render_svg(canvas_ids, canvas_sel_id, "All"), height=620)
    st.markdown("</div>", unsafe_allow_html=True)

    # Three-column details
    col_a, col_b, col_c = st.columns(3, gap="large")

    with col_a:
        st.markdown("**Entity details**")
        nd = NODES.get(canvas_sel_id, {})
        is_e = nd.get("type") == ENTITY
        r_col = BRAND["danger"] if score>=70 else BRAND["warning"] if score>=40 else BRAND["success"]
        s_col, _ = get_status_color(nd.get("status",""))
        st.markdown(f"""
        <div style="background:white;border:1px solid {BRAND['border']};border-radius:10px;padding:14px">
          <div style="font-size:15px;font-weight:800;color:{BRAND['navy']};margin-bottom:6px">{nd.get('name','')}</div>
          <div style="font-size:11px;color:{BRAND['muted']};margin-bottom:10px">{nd.get('summary','')[:200]}…</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div><div style="font-size:9px;font-weight:700;color:{BRAND['muted']};text-transform:uppercase">Owner</div>
                 <div style="font-size:12px;font-weight:600">{nd.get('owner','—')}</div></div>
            <div><div style="font-size:9px;font-weight:700;color:{BRAND['muted']};text-transform:uppercase">Status</div>
                 <div style="font-size:12px;font-weight:600;color:{s_col}">{nd.get('status','—')}</div></div>
            <div><div style="font-size:9px;font-weight:700;color:{BRAND['muted']};text-transform:uppercase">{"Risk" if is_e else "Stage"}</div>
                 <div style="font-size:12px;font-weight:600">{nd.get('risk','—') if is_e else nd.get('stage','—')}</div></div>
            <div><div style="font-size:9px;font-weight:700;color:{BRAND['muted']};text-transform:uppercase">Risk Score</div>
                 <div style="font-size:13px;font-weight:800;color:{r_col}">{get_risk_score(canvas_sel_id)}/100</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

        if nd.get("stages"):
            st.markdown("**Lifecycle stages**")
            for s in nd["stages"]:
                if s["status"]=="done":    ico,cls="✓","s-done"
                elif s["status"]=="current": ico,cls="●","s-cur"
                else:                        ico,cls="○","s-pend"
                st.markdown(f'<div class="stage-item"><span>{ico}</span><span class="{cls}">{s["name"]}</span></div>',
                            unsafe_allow_html=True)
            ci = next((i for i,s in enumerate(nd["stages"]) if s["status"]=="current"), -1)
            if 0 <= ci < len(nd["stages"])-1:
                if st.button("⏭ Advance stage", key=f"canvas_adv_{canvas_sel_id}", type="primary"):
                    r = advance_stage(canvas_sel_id)
                    st.success(r["new_stage"]) if r["ok"] else st.error(r["message"])
                    if r["ok"]: st.rerun()

    with col_b:
        st.markdown("**Relationships**")
        out = get_outgoing(canvas_sel_id)
        inc = get_incoming(canvas_sel_id)
        for lk in out:
            n2 = NODES.get(lk["target"],{})
            rt = REL_TYPES.get(lk["relType"],{})
            cat = rt.get("category","default")
            c = CAT_CLR.get(cat, CAT_CLR["default"])
            st.markdown(f'<div class="rel-row">'
                        f'<span class="rel-icon-e">E</span>'
                        f'<span style="flex:1;font-size:12px">{n2.get("name","")}</span>'
                        f'<span class="cat-pill" style="background:{c["bg"]};color:{c["text"]}">{rt.get("label","")}</span>'
                        f'<span style="font-size:9px;color:{BRAND["muted"]}">{lk.get("cardinality","")}</span>'
                        f'</div>', unsafe_allow_html=True)
        for lk in inc:
            n2 = NODES.get(lk["source"],{})
            rt = REL_TYPES.get(lk["relType"],{})
            cat = rt.get("category","default")
            c = CAT_CLR.get(cat, CAT_CLR["default"])
            st.markdown(f'<div class="rel-row">'
                        f'<span class="rel-icon-w">WF</span>'
                        f'<span style="flex:1;font-size:12px">{n2.get("name","")}</span>'
                        f'<span class="cat-pill" style="background:{c["bg"]};color:{c["text"]}">← {rt.get("label","")}</span>'
                        f'<span style="font-size:9px;color:{BRAND["muted"]}">{lk.get("cardinality","")}</span>'
                        f'</div>', unsafe_allow_html=True)

        # Navigate from canvas
        st.markdown("**Navigate:**")
        all_connected = list(dict.fromkeys(
            [l["target"] for l in out] + [l["source"] for l in inc]
        ))
        for nid in all_connected:
            n2 = NODES.get(nid,{})
            if st.button(f"→ {n2.get('name','')[:24]}", key=f"cv_{canvas_sel_id}_{nid}"):
                navigate_to(nid)
                st.session_state.canvas_sel = n2.get("name","")

    with col_c:
        st.markdown("**Section permissions**")
        nd_entity_type = "Model" if nd.get("subtype") in [
            "Statistical Model","ML Model","AI/GenAI Model","Vendor Model"] else \
            "Dataset" if nd.get("subtype")=="Dataset" else \
            "Validation" if nd.get("subtype") in ["Validation"] else "Model"
        perm_rows = [r for r in MASTER_PERMISSION_TABLE if r["entity"] == nd_entity_type]
        if perm_rows:
            current_stage = nd.get("stage") or nd.get("workflow_state","—")
            for r in perm_rows[:6]:
                sec_t = SECTION_TYPE_REGISTRY.get(r["section"],{}).get("type","dynamic")
                tc = {"static":"pill-static","dynamic":"pill-dynamic","system":"pill-system"}.get(sec_t,"pill-dynamic")
                st.markdown(f"""
                <div class="spc">
                  <h4>📁 {r['section']} <span class="pill {tc}">{sec_t}</span></h4>
                  <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
                    <span class="pill pill-{r['analyst']}">A: {r['analyst']}</span>
                    <span class="pill pill-{r['validator']}">V: {r['validator']}</span>
                    <span class="pill pill-{r['approver']}">Ap: {r['approver']}</span>
                    <span style="font-size:10px;color:{BRAND['muted']}">{r['stage']}</span>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("**Attributes**")
        if nd.get("attributes"):
            for k, v in list(nd["attributes"].items())[:6]:
                ad = nd.get("attr_defs",{}).get(k,{})
                st.markdown(f'<div style="font-size:11px;padding:3px 0;border-bottom:1px solid {BRAND["border"]}">'
                            f'<span style="color:{BRAND["muted"]}">{ad.get("display_name",k)}</span>: '
                            f'<span style="font-weight:600">{v}</span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ENTITY SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
with t_entity:
    st.markdown("**Master Entity Table** — all entity types (Business + Process)")
    st.caption("From KT sessions: Assessment → creates Model → creates Subprocesses (Validation, Monitoring, etc.) → creates Findings. Use Case links to multiple Models. Query tracks justification queries.")

    et_df = pd.DataFrame(MASTER_ENTITY_TABLE)
    st.dataframe(et_df, use_container_width=True, hide_index=True,
                 column_config={
                     "entity_type": st.column_config.TextColumn("Entity Type", width="medium"),
                     "category": st.column_config.TextColumn("Category", width="small"),
                     "id_prefix": st.column_config.TextColumn("ID Prefix", width="small"),
                     "description": st.column_config.TextColumn("Description", width="large"),
                 })

    st.markdown("---")
    st.markdown("**Entity Sub-Template Explorer** — click entity type to view its template sections and permissions")
    st.caption("Multi-select supported. Each entity type is a projection of the master template — Preliminary (top) + Descriptive sections (below).")

    all_et = [e["entity_type"] for e in MASTER_ENTITY_TABLE]
    # Use widget key directly tied to session state
    sel_entities = st.multiselect(
        "Select entity type(s) to view sub-templates:",
        all_et,
        default=st.session_state.multi_entity_sel,
        key="multi_entity_sel_widget"
    )
    # Sync
    st.session_state.multi_entity_sel = sel_entities

    if sel_entities:
        sub_tabs = st.tabs(sel_entities)
        for tab_obj, etype in zip(sub_tabs, sel_entities):
            with tab_obj:
                prows = [r for r in MASTER_PERMISSION_TABLE if r["entity"] == etype]

                # Template config
                if etype in TEMPLATE_CONFIGS:
                    tmpl = TEMPLATE_CONFIGS[etype]
                    ca, cb = st.columns(2, gap="large")
                    with ca:
                        st.markdown(f"**Template: {etype}** — `{tmpl['id_prefix']}-XXX`")
                        st.markdown(f"*{tmpl['description']}*")
                        st.markdown(f"**Default workflow:** {tmpl['workflow']}")
                        st.markdown("**Preliminary attributes** (top of entity page):")
                        st.code(", ".join(tmpl["preliminary_attrs"]))
                    with cb:
                        st.markdown("**Descriptive sections:**")
                        for sn, attrs in tmpl["sections"].items():
                            st.markdown(f"*{sn}* → `{', '.join(attrs)}`")
                        if tmpl.get("conditional_sections"):
                            st.markdown("**Conditional sections:**")
                            for sn, cond in tmpl["conditional_sections"].items():
                                st.markdown(f"- **{sn}** shown when: `{cond}`")

                st.markdown("---")

                if prows:
                    st.markdown(f"**Section-wise permissions for {etype}**")
                    sections_seen = []
                    for r in prows:
                        if r["section"] not in sections_seen:
                            sections_seen.append(r["section"])

                    for sec in sections_seen:
                        sec_type_info = SECTION_TYPE_REGISTRY.get(sec, {})
                        sec_t = sec_type_info.get("type","dynamic")
                        tc = {"static":"pill-static","dynamic":"pill-dynamic","system":"pill-system"}.get(sec_t,"pill-dynamic")
                        st.markdown(f"""
                        <div class="spc">
                          <h4>📁 {sec} <span class="pill {tc}">{sec_t}</span></h4>
                          <div style="font-size:11px;color:{BRAND['muted']};margin-bottom:6px">{sec_type_info.get('description','')}</div>
                        </div>""", unsafe_allow_html=True)

                        sec_perms = [r for r in prows if r["section"] == sec]
                        perm_rows = [{"Stage": r["stage"], "Analyst": r["analyst"],
                                      "Validator": r["validator"], "Approver": r["approver"]}
                                     for r in sec_perms]
                        perm_df = pd.DataFrame(perm_rows)

                        def cperm(val):
                            if val=="M": return "background-color:#D1FAE5;color:#065F46;font-weight:800"
                            if val=="V": return "background-color:#DBEAFE;color:#1E40AF"
                            if val=="H": return "background-color:#F3F4F6;color:#9CA3AF"
                            return ""

                        styled = safe_map(perm_df.style, cperm, subset=["Analyst","Validator","Approver"])
                        st.dataframe(styled, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No permission data for {etype} in MASTER_PERMISSION_TABLE. Add rows in data_model.py.")

                # Attribute library for this entity type
                st.markdown("**Attribute library**")
                etype_attrs = [a for a in ATTRIBUTE_LIBRARY
                               if etype in a.get("entity_types",[]) or "All" in a.get("entity_types",[])]
                if etype_attrs:
                    attr_rows = [{"Field name": a["field_name"], "Display name": a["display_name"],
                                  "Data type": a["data_type"], "Section": a["section"],
                                  "Required": "✓" if a["required"] else "", "Example": a["example"]}
                                 for a in etype_attrs]
                    st.dataframe(pd.DataFrame(attr_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RELATIONSHIPS
# ══════════════════════════════════════════════════════════════════════════════
with t_rel:
    st.markdown("**Master Relationship Table** — all valid entity-to-entity connections")

    # Subset pills
    st.markdown("**Relationship subsets:**")
    sub_cols = st.columns(len(RELATIONSHIP_SUBSETS))
    for col_o, (subset, info) in zip(sub_cols, RELATIONSHIP_SUBSETS.items()):
        with col_o:
            st.markdown(f'<div style="background:{info["color"]};color:{info["text"]};padding:7px 10px;'
                        f'border-radius:8px;font-size:11px;font-weight:700;margin-bottom:4px">{subset}</div>'
                        f'<div style="font-size:10px;color:{BRAND["muted"]}">{info["description"]}</div>',
                        unsafe_allow_html=True)

    st.markdown("---")
    subset_filter = st.selectbox("Filter by subset:", ["All"]+list(RELATIONSHIP_SUBSETS.keys()), key="subset_filter_widget")
    st.session_state.subset_filter = subset_filter

    frels = MASTER_RELATIONSHIP_TABLE if subset_filter=="All" else \
            [r for r in MASTER_RELATIONSHIP_TABLE if r["subset"]==subset_filter]

    st.dataframe(pd.DataFrame(frels), use_container_width=True, hide_index=True,
                 column_config={
                     "rel_id": st.column_config.TextColumn("ID", width="small"),
                     "from_entity": st.column_config.TextColumn("From", width="small"),
                     "rel_type": st.column_config.TextColumn("Type", width="medium"),
                     "to_entity": st.column_config.TextColumn("To", width="small"),
                     "cardinality": st.column_config.TextColumn("Cardinality", width="small"),
                     "category": st.column_config.TextColumn("Category", width="small"),
                     "subset": st.column_config.TextColumn("Subset", width="small"),
                     "description": st.column_config.TextColumn("Description", width="large"),
                 })

    st.markdown("---")
    # Cardinality guide
    st.markdown("**Cardinality types**")
    cc = st.columns(4)
    cards = [("1:1","#DBEAFE","#1E40AF","One-to-One","e.g. Model → Validation Workflow"),
             ("1:N","#FEF3C7","#92400E","One-to-Many","e.g. Workflow → Stages"),
             ("N:1","#EDE9FE","#6D28D9","Many-to-One","e.g. Models → Dataset"),
             ("N:M","#D1FAE5","#065F46","Many-to-Many","e.g. Model → Policy")]
    for col_o,(card,bg,tc,name,ex) in zip(cc,cards):
        with col_o:
            st.markdown(f'<div style="background:{bg};color:{tc};padding:10px 12px;border-radius:8px;margin-bottom:4px">'
                        f'<div style="font-size:18px;font-weight:800;font-family:JetBrains Mono,monospace">{card}</div>'
                        f'<div style="font-size:12px;font-weight:600">{name}</div></div>'
                        f'<div style="font-size:11px;color:{BRAND["muted"]}">{ex}</div>',
                        unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Live relationship instances**")
    all_live = get_visible_links(list(NODES.keys()))
    live_rows = []
    for lk in all_live:
        src = NODES.get(lk["source"],{})
        tgt = NODES.get(lk["target"],{})
        rt  = REL_TYPES.get(lk["relType"],{})
        live_rows.append({"Source":src.get("name",""), "Relationship":rt.get("label",""),
                          "Category":rt.get("category",""), "Target":tgt.get("name",""),
                          "Cardinality":lk.get("cardinality",""),
                          "Directed":"→" if rt.get("directed",True) else "↔"})
    st.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WORKFLOWS
# ══════════════════════════════════════════════════════════════════════════════
with t_workflow:
    st.markdown("**Workflow Entity System** — workflows, stages, and tasks as first-class process entities")
    st.caption("From KT sessions: Workflow is the backbone. Templates act as organs inside the backbone. "
               "Stages map to section permissions. Entity transition triggers automations.")

    wt1, wt2, wt3, wt4 = st.tabs(["📋 Workflow Table","🔢 Stage Table","✅ Task Table","⚡ Automation Rules"])

    with wt1:
        st.dataframe(pd.DataFrame(WORKFLOW_ENTITY_TABLE), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("**Live workflow instances with stage tracker**")
        for nid, nd in NODES.items():
            if nd["type"] != WORKFLOW: continue
            stages = nd.get("stages",[])
            ci = next((i for i,s in enumerate(stages) if s["status"]=="current"), -1)
            total = len(stages)
            pct = int((ci/max(total-1,1))*100) if ci>=0 else 0
            sc_, _ = get_status_color(nd["status"])

            with st.expander(f"**{nd['name']}** — {nd['subtype']} · {nd.get('stage','—')}"):
                c1, c2 = st.columns([3,1])
                with c1:
                    stage_parts = []
                    for i, s in enumerate(stages):
                        if s["status"]=="done":
                            stage_parts.append(f'<span style="background:{BRAND["success"]};color:white;'
                                               f'padding:3px 10px;border-radius:4px;font-size:10px;'
                                               f'font-weight:700;margin:2px;display:inline-block">✓ {s["name"]}</span>')
                        elif s["status"]=="current":
                            stage_parts.append(f'<span style="background:{BRAND["teal"]};color:white;'
                                               f'padding:3px 10px;border-radius:4px;font-size:10px;'
                                               f'font-weight:800;margin:2px;display:inline-block;'
                                               f'box-shadow:0 0 0 3px rgba(0,165,168,0.25)">● {s["name"]}</span>')
                        else:
                            stage_parts.append(f'<span style="background:{BRAND["bg"]};color:{BRAND["muted"]};'
                                               f'border:1px solid {BRAND["border"]};'
                                               f'padding:3px 10px;border-radius:4px;font-size:10px;'
                                               f'margin:2px;display:inline-block">○ {s["name"]}</span>')
                    arrow = f'<span style="color:{BRAND["muted"]};margin:0 2px">›</span>'
                    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:2px;align-items:center;margin-bottom:8px">'
                                f'{arrow.join(stage_parts)}</div>', unsafe_allow_html=True)
                    st.progress(pct/100 if pct>0 else 0)
                    st.caption(f"Progress: {pct}% · stage {ci+1 if ci>=0 else 0}/{total}")
                with c2:
                    st.markdown(f"**Owner:** {nd['owner']}")
                    st.markdown(f"**Status:** <span style='color:{sc_}'>{nd['status']}</span>", unsafe_allow_html=True)
                    if 0<=ci<total-1:
                        if st.button("⏭ Advance", key=f"wf_{nid}", type="primary"):
                            r = advance_stage(nid)
                            if r["ok"]: st.success(f"→ {r['new_stage']}"); st.rerun()
                            else: st.error(r["message"])

    with wt2:
        st.markdown("**Stage Entity Table**")
        st.dataframe(pd.DataFrame(STAGE_ENTITY_TABLE), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("**Legal stage transitions (state machine)**")
        for subtype, stages in STAGE_TRANSITIONS.items():
            parts = [f'<span style="background:#EBF5FF;color:{BRAND["navy"]};padding:3px 9px;'
                     f'border-radius:4px;font-size:11px;font-weight:600">{s}</span>'
                     for s in stages]
            arrow = f'<span style="color:{BRAND["muted"]}"> → </span>'
            st.markdown(f"**{subtype}:** {arrow.join(parts)}", unsafe_allow_html=True)
            st.markdown("")

    with wt3:
        st.markdown("**Task Entity Table** — atomic actions within stages")
        st.dataframe(pd.DataFrame(TASK_ENTITY_TABLE), use_container_width=True, hide_index=True)

    with wt4:
        st.markdown("**Automation Rules** — trigger → action engine")
        st.caption("From KT sessions: 4 trigger types — entity transition, attribute updated, time-based, entity created. "
                   "Actions: update attribute, entity transition, generate event, generate association (subprocess), "
                   "generate document, send mail, create entity, archive entity, generate report.")

        tc_colors = {
            "Entity transition": ("#DBEAFE","#1E40AF"),
            "Time-based":        ("#FEF3C7","#92400E"),
            "Attribute updated": ("#EDE9FE","#6D28D9"),
            "Entity created":    ("#D1FAE5","#065F46"),
        }
        for rule in AUTOMATION_RULES:
            bg_, tc_ = tc_colors.get(rule["trigger_type"],("#F3F4F6","#374151"))
            with st.expander(f"**{rule['name']}** — {rule['trigger_type']}"):
                c1_, c2_ = st.columns([1,2])
                with c1_:
                    st.markdown(f'<span style="background:{bg_};color:{tc_};padding:4px 10px;'
                                f'border-radius:6px;font-size:11px;font-weight:700">{rule["trigger_type"]}</span>',
                                unsafe_allow_html=True)
                    st.markdown(f"**Entity:** {rule['entity_type']}")
                with c2_:
                    st.markdown(f"**When:** `{rule['trigger_condition']}`")
                    st.markdown(f"**Then:** {rule['action']}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
with t_perm:
    st.markdown("**Permission Matrix** — section × stage × role")
    st.caption("From KT sessions: Permissions are per section, per workflow stage. "
               "Sections can be Manage (editable), View (read-only), or Hidden. "
               "Hidden section technique: used for derived attributes the user should not see but system uses.")

    # Rule cards
    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(f"""<div style="background:#F0FDF4;border:1px solid #6EE7B7;border-radius:8px;padding:12px">
        <div style="font-size:11px;font-weight:800;color:#065F46;margin-bottom:4px">🟢 STATIC</div>
        <div style="font-size:11px;color:#064E3B">Editable <b>only</b> at Registration/Creation.<br>
        Frozen in all later stages. Preserves data integrity.<br><em>Examples: Preliminary, Model Identification, General Info</em></div>
        </div>""", unsafe_allow_html=True)
    with r2:
        st.markdown(f"""<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;padding:12px">
        <div style="font-size:11px;font-weight:800;color:#C2410C;margin-bottom:4px">🟡 DYNAMIC</div>
        <div style="font-size:11px;color:#9A3412">Editable during <b>specific workflow stages</b>.<br>
        Different roles own at different stages.<br><em>Examples: Governance, Testing, Findings, Remediation</em></div>
        </div>""", unsafe_allow_html=True)
    with r3:
        st.markdown(f"""<div style="background:#F9FAFB;border:1px solid {BRAND['border']};border-radius:8px;padding:12px">
        <div style="font-size:11px;font-weight:800;color:#374151;margin-bottom:4px">⚫ SYSTEM</div>
        <div style="font-size:11px;color:#374151">Never user-editable. Hidden pre-Approval.<br>
        Auto-computed by derivation engine.<br><em>Examples: Derived risk score, Audit Trail, Lineage</em></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Interactive Permission Derivation**")
    fc1, fc2, fc3 = st.columns(3)
    with fc1: demo_sec = st.selectbox("Section type",["static","dynamic","system"],key="ds")
    with fc2: demo_stg = st.selectbox("Stage",["Registration","Documentation Review","Validation","Approval","Monitoring","Active","Created","Closed"],key="dstg")
    with fc3: demo_rol = st.selectbox("Role",["analyst","validator","approver"],key="dr")

    perm_r = get_permission(demo_sec, demo_stg, demo_rol)
    pc = {BRAND["success"]:"manage",BRAND["teal"]:"view",BRAND["muted"]:"hidden"}
    pc = BRAND["success"] if perm_r=="manage" else BRAND["teal"] if perm_r=="view" else BRAND["muted"]
    pb = "#D1FAE5" if perm_r=="manage" else "#DBEAFE" if perm_r=="view" else "#F3F4F6"
    st.markdown(f'<div style="background:{pb};border:1px solid {pc}33;border-radius:8px;padding:12px 16px;'
                f'display:inline-block;margin:8px 0">'
                f'<span style="font-size:16px;font-weight:800;color:{pc}">{perm_r.upper()}</span>'
                f'<span style="font-size:12px;color:{pc};margin-left:8px">({demo_sec} · {demo_stg} · {demo_rol})</span>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("---")
    perm_e = st.selectbox("Filter by entity:", ["All"]+sorted(set(r["entity"] for r in MASTER_PERMISSION_TABLE)),
                           key="perm_e")
    fp = MASTER_PERMISSION_TABLE if perm_e=="All" else \
         [r for r in MASTER_PERMISSION_TABLE if r["entity"]==perm_e]

    def cperm2(val):
        if val=="M": return "background-color:#D1FAE5;color:#065F46;font-weight:800"
        if val=="V": return "background-color:#DBEAFE;color:#1E40AF"
        if val=="H": return "background-color:#F3F4F6;color:#9CA3AF"
        return ""

    styled_full = safe_map(pd.DataFrame(fp).style, cperm2, subset=["analyst","validator","approver"])
    st.dataframe(styled_full, use_container_width=True, hide_index=True)
    st.caption("M = Manage (editable) · V = View (read-only) · H = Hidden")

    st.markdown("---")
    st.markdown("**Section Type Registry**")
    st.dataframe(pd.DataFrame([{"Section": k, "Type": v["type"], "Description": v["description"]}
                                for k, v in SECTION_TYPE_REGISTRY.items()]),
                 use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — EXECUTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
with t_exec:
    st.markdown("**Execution Engine** — event timeline with state transitions")
    st.caption("Each event = one state transition. API call links each event to its external trigger.")

    ef = st.selectbox("Filter:", ["All"]+list({e["entity_name"] for e in EXECUTION_EVENTS}), key="exec_ef")
    fevts = EXECUTION_EVENTS if ef=="All" else [e for e in EXECUTION_EVENTS if e["entity_name"]==ef]

    for evt in fevts:
        res_col = BRAND["success"] if evt["result"] in ("Approved","Published","Active") else \
                  BRAND["warning"] if evt["result"] in ("Under Review","In Progress") else BRAND["teal"]
        cls = "approved" if "Approv" in evt["result"] else "review" if "Review" in evt["result"] else ""
        c1, c2 = st.columns([1,5])
        with c1:
            st.markdown(f'<div class="mono" style="color:{BRAND["muted"]};font-size:10px;text-align:right;padding-top:4px">'
                        f'{evt["timestamp"][:10]}<br>{evt["timestamp"][11:]}</div>', unsafe_allow_html=True)
        with c2:
            ver_tag = f'<span class="mono" style="font-size:10px;color:{BRAND["muted"]};margin-left:4px">{evt["version"]}</span>' if evt["version"] else ""
            st.markdown(f'<div class="tl-evt {cls}">'
                        f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                        f'<span style="font-size:12.5px;font-weight:700;color:{BRAND["navy"]}">{evt["action"]}</span>'
                        f'<span style="background:{BRAND["bg"]};color:{BRAND["text"]};padding:1px 7px;border-radius:4px;font-size:10px">{evt["entity_name"]}</span>'
                        f'<span style="background:#EBF5FF;color:{BRAND["navy"]};padding:1px 7px;border-radius:4px;font-size:10px">{evt["stage"]}</span>'
                        f'<span style="color:{res_col};font-size:10.5px;font-weight:700">{evt["result"]}</span>'
                        f'</div>'
                        f'<div style="display:flex;gap:10px;margin-top:4px;flex-wrap:wrap;align-items:center">'
                        f'<span style="font-size:10px;color:{BRAND["muted"]}">👤 {evt["actor"]}</span>'
                        f'<span class="apill apill-POST mono">{evt["api_call"]}</span>'
                        f'{ver_tag}</div></div>',
                        unsafe_allow_html=True)

    st.markdown("---")
    st.dataframe(pd.DataFrame(fevts)[["event_id","timestamp","entity_name","stage","action","actor","result","api_call","version"]],
                 use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — VERSION REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
with t_version:
    st.markdown("**Version Registry** — entity version history with parent lineage")
    st.caption("Each version is a snapshot. Versions form a chain: root → v1 → v2 → v3 (current). "
               "Branching possible for hotfixes. Click a version to see its state snapshot.")

    ve = st.selectbox("Filter:", ["All"]+list({v["entity_id"] for v in VERSION_REGISTRY}), key="ve")
    fvers = VERSION_REGISTRY if ve=="All" else [v for v in VERSION_REGISTRY if v["entity_id"]==ve]

    grouped: dict = {}
    for v in fvers:
        grouped.setdefault(v["entity_id"], []).append(v)

    for eid, versions in grouped.items():
        st.markdown(f"**{versions[0]['entity_name']}** — version chain")
        chain = []
        for i, v in enumerate(versions):
            is_act = v["status"] in ("Active","Under Review")
            is_app = v["status"] == "Approved"
            cls = "active" if is_act else "approved" if is_app else "superseded"
            sc = BRAND["teal"] if is_act else BRAND["success"] if is_app else BRAND["muted"]
            chain.append(f'<div class="ver-node {cls}">'
                         f'<div style="font-size:14px;font-weight:800;color:{BRAND["navy"]};font-family:JetBrains Mono,monospace">{v["version_id"]}</div>'
                         f'<div style="font-size:10px;font-weight:700;color:{sc}">{v["status"]}</div>'
                         f'<div style="font-size:10px;color:{BRAND["muted"]}">{v["stage"]}</div>'
                         f'<div style="font-size:10px;color:{BRAND["muted"]}">{v["created_at"][:10]}</div>'
                         f'<div style="font-size:10px;color:{BRAND["muted"]}">{v["created_by"]}</div>'
                         f'</div>')
            if i < len(versions)-1:
                chain.append(f'<span style="display:inline-block;color:{BRAND["muted"]};font-size:18px;'
                             f'vertical-align:middle;margin:0 2px">→</span>')
        st.markdown(f'<div style="overflow-x:auto;white-space:nowrap;padding:8px 0">{"".join(chain)}</div>',
                    unsafe_allow_html=True)

        vrows = [{"Version":v["version_id"],"Parent":v["parent_version"] or "root",
                  "Status":v["status"],"Stage":v["stage"],"By":v["created_by"],
                  "Date":v["created_at"][:10],"Changes":v["changes"]} for v in versions]
        st.dataframe(pd.DataFrame(vrows), use_container_width=True, hide_index=True)
        st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 — AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════
with t_audit:
    st.markdown("**Audit Log** — field-level change tracking")
    st.caption("From KT sessions: Activity report tracks user logging and field changes. "
               "Every API call that updates an attribute is logged here with old→new values.")

    ae = st.selectbox("Entity:", ["All"]+list({a["entity_name"] for a in AUDIT_LOG}), key="ae")
    af = st.selectbox("Field:", ["All"]+sorted({a["field"] for a in AUDIT_LOG}), key="af")
    au = st.selectbox("User:", ["All"]+sorted({a["changed_by"] for a in AUDIT_LOG}), key="au")

    fa = AUDIT_LOG
    if ae!="All": fa = [a for a in fa if a["entity_name"]==ae]
    if af!="All": fa = [a for a in fa if a["field"]==af]
    if au!="All": fa = [a for a in fa if a["changed_by"]==au]

    st.markdown(f"**{len(fa)} audit events**")
    for a in fa:
        st.markdown(f'<div class="aud-row">'
                    f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                    f'<span class="mono" style="font-size:10px;color:{BRAND["muted"]}">{a["timestamp"]}</span>'
                    f'<span style="font-size:12px;font-weight:700;color:{BRAND["navy"]}">{a["entity_name"]}</span>'
                    f'<span class="mono" style="background:{BRAND["bg"]};color:{BRAND["text"]};padding:1px 6px;border-radius:4px;font-size:10px">{a["field"]}</span>'
                    f'<span style="font-size:10px;color:{BRAND["muted"]}">changed by</span>'
                    f'<span style="font-size:11.5px;font-weight:700">{a["changed_by"]}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:6px;margin-top:4px;flex-wrap:wrap">'
                    f'<span style="background:#FEE2E2;color:#991B1B;padding:1px 7px;border-radius:4px;font-size:11px">{a["old_value"] or "null"}</span>'
                    f'<span style="color:{BRAND["muted"]}">→</span>'
                    f'<span style="background:#D1FAE5;color:#065F46;padding:1px 7px;border-radius:4px;font-size:11px">{a["new_value"]}</span>'
                    f'<span style="background:#EBF5FF;color:{BRAND["navy"]};padding:1px 6px;border-radius:4px;font-size:10px">{a["stage"]}</span>'
                    f'<span style="font-size:10px;color:{BRAND["muted"]}">via: {a["triggered_by"]}</span>'
                    f'</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.dataframe(pd.DataFrame(fa), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 10 — API LOG
# ══════════════════════════════════════════════════════════════════════════════
with t_api:
    st.markdown("**API Log** — external request/response trace")
    st.caption("From KT sessions: Document template, automation, reports all triggered via API. "
               "Generate document, generate report, send mail — all API calls that external systems trigger.")

    posts  = sum(1 for a in API_LOG if a["method"]=="POST")
    patches= sum(1 for a in API_LOG if a["method"]=="PATCH")
    gets   = sum(1 for a in API_LOG if a["method"]=="GET")
    avg_lat = sum(a["latency_ms"] for a in API_LOG)//len(API_LOG)

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card"><div class="kpi-label">Total calls</div><div class="kpi-value">{len(API_LOG)}</div></div>
      <div class="kpi-card" style="border-left-color:#1D4ED8"><div class="kpi-label">POST</div><div class="kpi-value" style="color:#1D4ED8">{posts}</div><div class="kpi-sub">Create/Advance/Generate</div></div>
      <div class="kpi-card" style="border-left-color:{BRAND['warning']}"><div class="kpi-label">PATCH</div><div class="kpi-value" style="color:{BRAND['warning']}">{patches}</div><div class="kpi-sub">Update fields</div></div>
      <div class="kpi-card" style="border-left-color:{BRAND['success']}"><div class="kpi-label">GET</div><div class="kpi-value" style="color:{BRAND['success']}">{gets}</div><div class="kpi-sub">Read/Fetch</div></div>
      <div class="kpi-card"><div class="kpi-label">Avg latency</div><div class="kpi-value">{avg_lat}<span style="font-size:13px">ms</span></div></div>
    </div>""", unsafe_allow_html=True)

    for a in API_LOG:
        mc = f"apill-{a['method']}"
        sc_c = f"apill-{a['status_code']}"
        lc = BRAND["danger"] if a["latency_ms"]>1000 else BRAND["warning"] if a["latency_ms"]>200 else BRAND["success"]
        st.markdown(f'<div style="background:white;border:1px solid {BRAND["border"]};border-radius:8px;'
                    f'padding:10px 14px;margin-bottom:6px">'
                    f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                    f'<span class="apill {mc}">{a["method"]}</span>'
                    f'<span class="mono" style="font-size:11px;color:{BRAND["text"]}">{a["endpoint"]}</span>'
                    f'<span class="apill {sc_c}">{a["status_code"]}</span>'
                    f'<span style="font-size:10.5px;color:{lc};font-weight:700">{a["latency_ms"]}ms</span>'
                    f'<span class="mono" style="font-size:10px;color:{BRAND["muted"]}">{a["timestamp"]}</span>'
                    f'</div>'
                    f'<div style="margin-top:4px;font-size:11.5px">'
                    f'<span style="color:{BRAND["text"]};font-weight:600">{a["payload_summary"]}</span>'
                    f' → <span style="color:{BRAND["muted"]}">{a["response_summary"]}</span>'
                    f'</div>'
                    f'<div style="font-size:10px;color:{BRAND["muted"]};margin-top:2px">Actor: {a["actor"]} · Entity: {a["entity_id"]}</div>'
                    f'</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.dataframe(pd.DataFrame(API_LOG)[["api_id","timestamp","method","endpoint","status_code",
                                        "latency_ms","actor","entity_id","payload_summary","response_summary"]],
                 use_container_width=True, hide_index=True)
