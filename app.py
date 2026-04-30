"""
MRM Vault — Command Centre v2
Dash + Cytoscape | Solytics Partners

Design: One screen, maximum info, minimum clicks.
  • Graph (centre) + instant detail panel (right) always visible
  • 5 panel tabs: Overview / Linked / Permissions / Attributes / Activity
  • Linked tab: clickable entity chips + workflow chips with mini progress bar
  • Deep-dive drawer slides in from sidebar for full tables
  • Relationship table always visible below graph

Deploy: python app.py  →  http://localhost:8050
"""

import dash, json as _json
from dash import dcc, html, Input, Output, State, callback_context, dash_table, no_update, ALL
import dash_cytoscape as cyto

from data_model import (
    NODES, LINKS, REL_TYPES, STAGE_TRANSITIONS, ENTITY, WORKFLOW,
    QUICK_ACCESS, get_risk_score, get_status_color,
    ATTRIBUTE_LIBRARY, TEMPLATE_CONFIGS, AUTOMATION_RULES,
    MASTER_ENTITY_TABLE, WORKFLOW_ENTITY_TABLE, STAGE_ENTITY_TABLE,
    TASK_ENTITY_TABLE, MASTER_PERMISSION_TABLE, SECTION_TYPE_REGISTRY,
    get_permission, MASTER_RELATIONSHIP_TABLE, RELATIONSHIP_SUBSETS,
    VERSION_REGISTRY, EXECUTION_EVENTS, AUDIT_LOG, API_LOG,
)
from graph_engine import (
    get_outgoing, get_incoming, get_visible_ids, get_visible_links,
    get_directed_link, impact_trace, upstream_trace, advance_stage,
)

cyto.load_extra_layouts()

# ── Brand ─────────────────────────────────────────────────────────────────────
NAVY    = "#003366"
TEAL    = "#00A5A8"
ORANGE  = "#FF6B35"
WHITE   = "#FFFFFF"
BG      = "#F5F7FA"
SURFACE = "#FFFFFF"
BORDER  = "#E2E8F0"
MUTED   = "#64748B"
TEXT    = "#0F172A"
SUCCESS = "#10B981"
WARN    = "#F59E0B"
DANGER  = "#EF4444"
PURPLE  = "#7C3AED"

CAT_CLR = {
    "lineage":    {"line":"#2563EB","bg":"#EFF6FF","txt":"#1D4ED8"},
    "governance": {"line":PURPLE,   "bg":"#F5F3FF","txt":PURPLE},
    "validation": {"line":"#0891B2","bg":"#ECFEFF","txt":"#0E7490"},
    "monitoring": {"line":SUCCESS,  "bg":"#F0FDF4","txt":"#15803D"},
    "lifecycle":  {"line":ORANGE,   "bg":"#FFF7ED","txt":"#C2410C"},
    "issue":      {"line":DANGER,   "bg":"#FFF1F2","txt":"#BE123C"},
    "output":     {"line":TEAL,     "bg":"#F0FDFA","txt":"#0F766E"},
    "default":    {"line":MUTED,    "bg":BG,        "txt":MUTED},
}
RISK_CLR  = {"High":(DANGER,"#FFF1F2"),"Medium":(WARN,"#FFFBEB"),"Low":(SUCCESS,"#F0FDF4")}
PERM_CLR  = {"M":("#D1FAE5","#065F46"),"V":("#DBEAFE","#1E40AF"),"H":("#F1F5F9","#94A3B8")}
STYPE_CLR = {"static":("#EDE9FE","#5B21B6"),"dynamic":("#FFF7ED","#C2410C"),"system":("#F1F5F9","#374151")}

# ── Cytoscape stylesheet ──────────────────────────────────────────────────────
CY_SS = [
    {"selector":"node","style":{
        "width":175,"height":68,"shape":"round-rectangle",
        "background-color":WHITE,"border-color":BORDER,"border-width":1.5,
        "label":"data(label)","text-wrap":"wrap","text-max-width":148,
        "font-size":11.5,"font-weight":"600",
        "font-family":"'DM Sans',system-ui,sans-serif",
        "color":TEXT,"text-valign":"center","text-halign":"center","padding":10,
        "shadow-blur":12,"shadow-color":"rgba(15,23,42,0.07)","shadow-offset-y":3,
        "transition-property":"border-color,border-width,shadow-blur",
        "transition-duration":"0.15s",
    }},
    {"selector":"node[node_type='Entity']","style":{
        "background-color":WHITE,"border-color":BORDER,
        "border-left-color":TEAL,"border-left-width":3,
    }},
    {"selector":"node[node_type='Workflow']","style":{
        "background-color":NAVY,"border-color":NAVY,"color":"#E2E8F0",
    }},
    {"selector":"node:selected","style":{
        "border-color":TEAL,"border-width":2.5,
        "shadow-blur":24,"shadow-color":"rgba(0,165,168,0.28)",
    }},
    {"selector":"node.dimmed","style":{"opacity":0.25}},
    {"selector":"node[risk='High']","style":{"border-color":DANGER,"border-width":2}},
    {"selector":"node[risk='Medium']","style":{"border-color":WARN,"border-width":1.8}},
    {"selector":"edge","style":{
        "curve-style":"bezier","target-arrow-shape":"triangle",
        "target-arrow-color":"#CBD5E1","line-color":"#CBD5E1","width":1.2,
        "font-size":9,"font-family":"'DM Sans',system-ui,sans-serif","color":MUTED,
        "label":"data(short_label)","text-background-color":WHITE,
        "text-background-opacity":1,"text-background-padding":"2px",
        "edge-text-rotation":"autorotate",
        "transition-property":"line-color,width,opacity","transition-duration":"0.15s",
    }},
    *[{"selector":f"edge[category='{cat}']","style":{
        "line-color":info["line"],"target-arrow-color":info["line"],"color":info["txt"],
    }} for cat, info in CAT_CLR.items()],
    {"selector":"edge.active","style":{"width":2.5,"opacity":1}},
    {"selector":"edge.dimmed","style":{"opacity":0.12}},
]

# ── Build elements ────────────────────────────────────────────────────────────
def build_elements(sel="credit_risk_model", depth=2, cat_filter="All"):
    vis  = get_visible_ids(sel, depth)
    lnks = get_visible_links(vis)
    els  = []
    for nid in vis:
        nd  = NODES[nid]
        els.append({"data":{
            "id":nid,"label":f"{nd['name']}\n{nd['subtype']}",
            "name":nd["name"],"node_type":nd["type"],"subtype":nd["subtype"],
            "risk":nd.get("risk",""),"status":nd.get("status",""),
            "score":get_risk_score(nid),"owner":nd.get("owner",""),
        },"selected":nid==sel})
    for lk in lnks:
        rt  = REL_TYPES.get(lk["relType"],{})
        cat = rt.get("category","default")
        if cat_filter != "All" and cat != cat_filter.lower():
            continue
        els.append({"data":{
            "id":f"{lk['source']}__{lk['target']}",
            "source":lk["source"],"target":lk["target"],
            "label":f"{rt.get('label','')}  {lk.get('cardinality','')}",
            "short_label":rt.get("label","")[:14],
            "category":cat,"cardinality":lk.get("cardinality",""),
        }})
    return els

# ── Helpers ───────────────────────────────────────────────────────────────────
def _pill(text, bg=NAVY, col=WHITE, size=9.5):
    return html.Span(text, style={
        "background":bg,"color":col,"fontSize":size,"fontWeight":700,
        "padding":"2px 9px","borderRadius":20,"display":"inline-block",
        "textTransform":"uppercase","letterSpacing":".05em","marginRight":4,
    })

def _tag(text, bg=BG, col=MUTED):
    return html.Span(text, style={
        "background":bg,"color":col,"fontSize":10,"fontWeight":600,
        "padding":"2px 8px","borderRadius":5,"display":"inline-block","marginRight":4,
    })

def _sec(text):
    return html.Div(text, style={
        "fontSize":9.5,"fontWeight":700,"textTransform":"uppercase","letterSpacing":".09em",
        "color":MUTED,"borderBottom":f"1px solid {BORDER}",
        "paddingBottom":4,"marginBottom":8,"marginTop":14,
    })

def _card(children, p=14, mb=12, extra=None):
    s = {"background":SURFACE,"border":f"1px solid {BORDER}","borderRadius":10,
         "padding":p,"marginBottom":mb}
    if extra: s.update(extra)
    return html.Div(children, style=s)

def _chip(nid, label, is_wf=False):
    bg  = "#EFF6FF" if not is_wf else "#F0FDFA"
    col = NAVY if not is_wf else TEAL
    bdr = "#BFDBFE" if not is_wf else "#99F6E4"
    return html.Button(
        [html.Span("WF " if is_wf else "E ", style={"fontSize":8,"fontWeight":800,"opacity":.65}),
         html.Span(label, style={"fontWeight":600})],
        id={"type":"chip","index":nid},
        n_clicks=0,
        style={
            "background":bg,"border":f"1px solid {bdr}","color":col,
            "borderRadius":8,"padding":"6px 12px","fontSize":12,
            "cursor":"pointer","margin":"3px",
            "fontFamily":"'DM Sans',sans-serif","transition":"all .12s",
        }
    )

def _tbl(**kw):
    return dict(
        style_table={"overflowX":"auto"},
        style_header={"background":BG,"fontWeight":700,"fontSize":10,"color":MUTED,
                       "textTransform":"uppercase","border":f"1px solid {BORDER}",
                       "borderBottom":f"2px solid {BORDER}"},
        style_cell={"fontSize":12,"padding":"7px 10px","border":f"1px solid {BORDER}",
                     "fontFamily":"'DM Sans',sans-serif","color":TEXT,
                     "whiteSpace":"normal","textAlign":"left"},
        **kw,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                title="MRM Vault | Solytics Partners",
                meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}])
server = app.server

FONTS = ("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;"
         "0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&family=DM+Mono:wght@400;500&"
         "family=Plus+Jakarta+Sans:wght@700;800&display=swap")

app.layout = html.Div([
    html.Link(rel="stylesheet", href=FONTS),
    dcc.Store(id="sel",       data="credit_risk_model"),
    dcc.Store(id="ptab",      data="overview"),
    dcc.Store(id="dv-active", data=""),

    html.Div([

        # ══════════════════════════════════════════════════════════════════
        # SIDEBAR
        # ══════════════════════════════════════════════════════════════════
        html.Div([
            # Logo
            html.Div([
                html.Div("⬡", style={"fontSize":22,"color":WHITE}),
                html.Div([
                    html.Div("MRM Vault", style={"fontSize":14,"fontWeight":800,"color":WHITE,
                                                  "fontFamily":"'Plus Jakarta Sans',sans-serif"}),
                    html.Div("Solytics Partners", style={"fontSize":9.5,"color":"#7FA3CC"}),
                ]),
            ], style={"display":"flex","alignItems":"center","gap":9,
                      "padding":"16px 14px 12px","borderBottom":"1px solid rgba(255,255,255,0.08)"}),

            # Search
            html.Div([
                dcc.Input(id="search-inp", placeholder="🔍  Search entities…", debounce=True,
                          style={"width":"100%","background":"rgba(255,255,255,0.08)",
                                 "border":"1px solid rgba(255,255,255,0.12)","borderRadius":7,
                                 "padding":"7px 11px","color":WHITE,"fontSize":12,
                                 "fontFamily":"'DM Sans',sans-serif","outline":"none",
                                 "boxSizing":"border-box"}),
                html.Div(id="search-res"),
            ], style={"padding":"10px 12px"}),

            # Controls
            html.Div([
                html.Div("DEPTH", style={"fontSize":9,"fontWeight":700,"color":"#7FA3CC","letterSpacing":".1em","marginBottom":4}),
                dcc.RadioItems(id="depth-r",
                               options=[{"label":"1","value":1},{"label":"2","value":2},{"label":"All","value":999}],
                               value=2, inline=True,
                               inputStyle={"marginRight":3,"accentColor":TEAL},
                               labelStyle={"color":"#C8D8EC","fontSize":12.5,"marginRight":10}),
            ], style={"padding":"4px 14px 10px","borderBottom":"1px solid rgba(255,255,255,0.07)"}),

            html.Div([
                html.Div("CATEGORY", style={"fontSize":9,"fontWeight":700,"color":"#7FA3CC","letterSpacing":".1em","marginBottom":4}),
                dcc.Dropdown(id="cat-dd",
                             options=[{"label":c.title(),"value":c} for c in
                                      ["All","lineage","governance","validation","monitoring","lifecycle","issue"]],
                             value="All", clearable=False, style={"fontSize":12}),
            ], style={"padding":"8px 12px 10px","borderBottom":"1px solid rgba(255,255,255,0.07)"}),

            html.Div([
                html.Div("LAYOUT", style={"fontSize":9,"fontWeight":700,"color":"#7FA3CC","letterSpacing":".1em","marginBottom":4}),
                dcc.Dropdown(id="layout-dd",
                             options=[{"label":l,"value":l} for l in
                                      ["cose-bilkent","dagre","cola","concentric","grid"]],
                             value="cose-bilkent", clearable=False, style={"fontSize":12}),
            ], style={"padding":"8px 12px 10px","borderBottom":"1px solid rgba(255,255,255,0.07)"}),

            # Quick access
            html.Div([
                html.Div("QUICK ACCESS", style={"fontSize":9,"fontWeight":700,"color":"#7FA3CC","letterSpacing":".1em","marginBottom":6}),
                *[html.Button(qa["label"], id=f"qa-{qa['id']}", n_clicks=0,
                              style={"width":"100%","textAlign":"left",
                                     "background":"rgba(255,255,255,0.05)",
                                     "border":"1px solid rgba(255,255,255,0.09)","borderRadius":6,
                                     "color":"#C8D8EC","padding":"6px 10px","fontSize":11.5,
                                     "cursor":"pointer","marginBottom":3,
                                     "fontFamily":"'DM Sans',sans-serif"})
                  for qa in QUICK_ACCESS],
            ], style={"padding":"8px 12px"}),

            # Deep-dive nav
            html.Div([
                html.Div("DEEP DIVE", style={"fontSize":9,"fontWeight":700,"color":"#7FA3CC","letterSpacing":".1em","marginBottom":5}),
                *[html.Button(lbl, id=f"dv-{tid}", n_clicks=0,
                              style={"width":"100%","textAlign":"left","background":"transparent",
                                     "border":"none","color":"#7FA3CC","padding":"5px 6px",
                                     "fontSize":11.5,"cursor":"pointer","borderRadius":5,
                                     "fontFamily":"'DM Sans',sans-serif"})
                  for lbl, tid in [("📦 Entity System","entity"),("🔗 Relationships","rel"),
                                    ("⚙ Workflows","workflow"),("🔐 Permissions","perm"),
                                    ("⏱ Execution","exec"),("🌳 Versions","version"),
                                    ("📋 Audit","audit"),("🌐 API Log","api")]],
            ], style={"padding":"8px 12px","borderTop":"1px solid rgba(255,255,255,0.07)"}),

            html.Div([
                html.Span("SR 11-7", style={"fontSize":8.5,"padding":"2px 6px","background":"rgba(255,255,255,0.07)","border":"1px solid rgba(255,255,255,0.1)","borderRadius":3,"color":"#7FA3CC","marginRight":3}),
                html.Span("RegTech100", style={"fontSize":8.5,"padding":"2px 6px","background":"rgba(255,255,255,0.07)","border":"1px solid rgba(255,255,255,0.1)","borderRadius":3,"color":"#7FA3CC"}),
            ], style={"padding":"10px 12px","marginTop":"auto"}),

        ], style={"width":210,"flexShrink":0,"background":NAVY,"height":"100vh",
                  "overflowY":"auto","display":"flex","flexDirection":"column",
                  "position":"sticky","top":0}),

        # ══════════════════════════════════════════════════════════════════
        # MAIN CONTENT
        # ══════════════════════════════════════════════════════════════════
        html.Div([

            # Top bar
            html.Div([
                html.Div([
                    html.Span("MRM ", style={"fontWeight":800,"color":NAVY,"fontSize":18,"fontFamily":"'Plus Jakarta Sans',sans-serif"}),
                    html.Span("Vault", style={"fontWeight":800,"color":TEAL,"fontSize":18,"fontFamily":"'Plus Jakarta Sans',sans-serif"}),
                    html.Span(" · Enterprise Model Risk Governance", style={"fontSize":12,"color":MUTED,"marginLeft":8}),
                ]),
                html.Div(id="kpi-strip"),
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "padding":"10px 18px","background":SURFACE,
                      "borderBottom":f"1px solid {BORDER}","flexWrap":"wrap","gap":8}),

            # Deep-dive drawer (all sections except entity which has permanent panel below)
            html.Div(id="dv-drawer",
                     style={"display":"none","padding":"14px 18px","background":BG,
                            "borderBottom":f"2px solid {BORDER}","maxHeight":"55vh","overflowY":"auto"}),

            # ── Permanent Entity System panel (always in DOM so callbacks work) ──
            html.Div(id="entity-panel", style={"display":"none"},
                     children=[
                         html.Div([
                             html.Div([
                                 html.Span("📦 Entity System — Master Template",
                                           style={"fontSize":15,"fontWeight":800,"color":NAVY}),
                                 html.Span("  ·  Click '📦 Entity System' in sidebar to toggle",
                                           style={"fontSize":11,"color":MUTED,"marginLeft":8}),
                             ], style={"marginBottom":12}),

                             # Master entity table
                             html.Div([
                                 html.Div("Master Entity Table",
                                          style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":6}),
                                 html.Div("Assessment → Model → Subprocesses → Findings. "
                                          "Workflow is a process-level entity.",
                                          style={"fontSize":11,"color":MUTED,"marginBottom":10}),
                                 dash_table.DataTable(
                                     id="master-entity-tbl",
                                     data=MASTER_ENTITY_TABLE,
                                     columns=[{"name":c.replace("_"," ").title(),"id":c}
                                              for c in ["entity_type","category","id_prefix","description"]],
                                     **_tbl(),
                                     style_data_conditional=[
                                         {"if":{"filter_query":"{category} = 'Business'"},"backgroundColor":"#EFF6FF"},
                                         {"if":{"filter_query":"{category} = 'Process'"},"backgroundColor":"#FFF7ED"},
                                         {"if":{"filter_query":"{category} = 'Output'"},"backgroundColor":"#F0FDF4"},
                                     ],
                                 ),
                             ], style={"background":SURFACE,"border":f"1px solid {BORDER}",
                                        "borderRadius":10,"padding":14,"marginBottom":14}),

                             # Sub-template explorer
                             html.Div([
                                 html.Div("Entity Sub-Template Explorer",
                                          style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":4}),
                                 html.Div("Select entity type to see: sections, section types, "
                                          "attributes, stage × role permissions, conditional sections, "
                                          "document template placeholders.",
                                          style={"fontSize":11,"color":MUTED,"marginBottom":10}),
                                 dcc.Dropdown(
                                     id="et-sel",
                                     options=[{"label":e["entity_type"],"value":e["entity_type"]}
                                              for e in MASTER_ENTITY_TABLE],
                                     value=["Model"],
                                     multi=True,
                                     placeholder="Select entity type(s)…",
                                     style={"fontSize":12,"marginBottom":12},
                                 ),
                                 html.Div(id="et-subtpl",
                                          children=[html.Div("Select an entity type above.",
                                                              style={"color":MUTED,"fontSize":12})]),
                             ], style={"background":SURFACE,"border":f"1px solid {BORDER}",
                                        "borderRadius":10,"padding":14,"marginBottom":14}),

                             # Section type registry
                             html.Div([
                                 html.Div("Section Type Registry",
                                          style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":8}),
                                 html.Div([
                                     html.Div([html.Div("🟢 STATIC",style={"fontWeight":800,"color":"#065F46","marginBottom":3,"fontSize":11.5}),
                                               html.Div("Editable only at Registration/Creation. Frozen in later stages.",style={"fontSize":11,"color":"#064E3B"})],
                                              style={"background":"#F0FDF4","border":"1px solid #6EE7B7","borderRadius":8,"padding":"10px 12px","flex":1}),
                                     html.Div([html.Div("🟡 DYNAMIC",style={"fontWeight":800,"color":"#C2410C","marginBottom":3,"fontSize":11.5}),
                                               html.Div("Editable during specific workflow stages. Role-dependent.",style={"fontSize":11,"color":"#9A3412"})],
                                              style={"background":"#FFF7ED","border":"1px solid #FED7AA","borderRadius":8,"padding":"10px 12px","flex":1}),
                                     html.Div([html.Div("⚫ SYSTEM",style={"fontWeight":800,"color":"#374151","marginBottom":3,"fontSize":11.5}),
                                               html.Div("Never user-editable. Hidden pre-Approval. Auto-computed.",style={"fontSize":11,"color":"#374151"})],
                                              style={"background":BG,"border":f"1px solid {BORDER}","borderRadius":8,"padding":"10px 12px","flex":1}),
                                 ], style={"display":"flex","gap":10,"marginBottom":10}),
                                 dash_table.DataTable(
                                     id="sec-registry-tbl",
                                     data=[{"Section":k,"Type":v["type"],"Description":v["description"]}
                                           for k,v in SECTION_TYPE_REGISTRY.items()],
                                     columns=[{"name":c,"id":c} for c in ["Section","Type","Description"]],
                                     **_tbl(), page_size=12,
                                     style_data_conditional=[
                                         {"if":{"filter_query":"{Type} = 'static'"},"backgroundColor":"#F5F3FF","color":"#5B21B6","fontWeight":600},
                                         {"if":{"filter_query":"{Type} = 'dynamic'"},"backgroundColor":"#FFF7ED","color":"#C2410C","fontWeight":600},
                                         {"if":{"filter_query":"{Type} = 'system'"},"backgroundColor":"#F1F5F9","color":"#374151"},
                                     ],
                                 ),
                             ], style={"background":SURFACE,"border":f"1px solid {BORDER}",
                                        "borderRadius":10,"padding":14,"marginBottom":14}),

                             # Full attribute library
                             html.Div([
                                 html.Div("Full Attribute Library",
                                          style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":4}),
                                 html.Div("field_name = system key · display_name = shown in UI · "
                                          "doc_placeholder used in Word document generation.",
                                          style={"fontSize":11,"color":MUTED,"marginBottom":10}),
                                 dash_table.DataTable(
                                     id="attr-lib-tbl",
                                     data=[{"Field":a["field_name"],"Display":a["display_name"],
                                            "Type":a["data_type"],"Section":a["section"],
                                            "Entities":", ".join(a["entity_types"]),
                                            "Req":"✓" if a["required"] else "","Example":a["example"]}
                                           for a in ATTRIBUTE_LIBRARY],
                                     columns=[{"name":c,"id":c}
                                              for c in ["Field","Display","Type","Section","Entities","Req","Example"]],
                                     **_tbl(), page_size=10,
                                     style_data_conditional=[
                                         {"if":{"filter_query":"{Req} = '✓'"},"fontWeight":700,"color":NAVY},
                                     ],
                                 ),
                             ], style={"background":SURFACE,"border":f"1px solid {BORDER}",
                                        "borderRadius":10,"padding":14}),
                         ], style={"padding":"14px 18px","background":BG,
                                    "borderBottom":f"2px solid {BORDER}"}),
                     ]),

            # ── COMMAND CENTRE: graph | detail panel ──────────────────────
            html.Div([

                # Graph column
                html.Div([
                    _card([
                        html.Div([
                            html.Div(id="graph-ttl", style={"fontSize":13,"fontWeight":700,"color":NAVY}),
                            html.Div([
                                html.Span("Drag · Scroll to zoom · ", style={"fontSize":10,"color":MUTED}),
                                html.Span("Click node → inspect panel  →", style={"fontSize":10,"color":TEAL,"fontWeight":700}),
                            ]),
                        ], style={"marginBottom":10}),

                        cyto.Cytoscape(
                            id="cy",
                            elements=build_elements("credit_risk_model"),
                            stylesheet=CY_SS,
                            layout={"name":"cose-bilkent","animate":True,"animationDuration":500,
                                     "fit":True,"padding":40,"nodeRepulsion":9000,"idealEdgeLength":150},
                            style={"width":"100%","height":490,"border":f"1px solid {BORDER}",
                                   "borderRadius":8,"background":"#FAFBFD"},
                            minZoom=0.25, maxZoom=3.5, responsive=True,
                        ),

                        # Legend
                        html.Div([
                            html.Div([
                                html.Span(style={"display":"inline-block","width":12,"height":2,
                                                  "background":info["line"],"borderRadius":1,
                                                  "verticalAlign":"middle","marginRight":4}),
                                html.Span(cat.title(), style={"fontSize":9.5,"color":info["txt"]}),
                            ], style={"display":"inline-flex","alignItems":"center","marginRight":14})
                            for cat, info in list(CAT_CLR.items())[:6]
                        ], style={"marginTop":8,"display":"flex","flexWrap":"wrap"}),
                    ], mb=10),

                    # Relationship table
                    _card([
                        html.Div("All Relationships", style={"fontSize":12,"fontWeight":700,"color":NAVY,"marginBottom":8}),
                        html.Div(id="rel-quick"),
                    ]),
                ], style={"flex":"1.55","minWidth":0}),

                # ── DETAIL PANEL ──────────────────────────────────────────
                html.Div([
                    # Panel tab row
                    html.Div([
                        *[html.Button(lbl, id=f"ptab-{tid}", n_clicks=0,
                                      style={"background":"transparent","border":"none",
                                             "borderBottom":"2px solid transparent",
                                             "color":MUTED,"fontSize":11.5,"fontWeight":600,
                                             "padding":"6px 10px","cursor":"pointer",
                                             "fontFamily":"'DM Sans',sans-serif",
                                             "transition":"color .12s"})
                          for lbl, tid in [("Overview","overview"),("Linked","linked"),
                                            ("Permissions","perms"),("Attributes","attrs"),
                                            ("Activity","activity")]],
                    ], style={"display":"flex","borderBottom":f"1px solid {BORDER}","marginBottom":10,"gap":2}),

                    html.Div(id="panel",
                             style={"height":"calc(100vh - 230px)","overflowY":"auto","paddingRight":2}),
                ], style={
                    "width":320,"flexShrink":0,"background":SURFACE,
                    "border":f"1px solid {BORDER}","borderRadius":10,"padding":"10px 14px",
                    "height":"calc(100vh - 120px)","position":"sticky","top":70,"overflowY":"auto",
                }),

            ], style={"display":"flex","gap":14,"padding":"14px 18px 0","alignItems":"flex-start"}),

        ], style={"flex":1,"background":BG,"overflowY":"auto","minHeight":"100vh"}),

    ], style={"display":"flex","fontFamily":"'DM Sans',system-ui,sans-serif","minHeight":"100vh"}),
], style={"margin":0,"padding":0})


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Quick access ──────────────────────────────────────────────────────────────
@app.callback(Output("sel","data"),
              [Input(f"qa-{qa['id']}","n_clicks") for qa in QUICK_ACCESS],
              prevent_initial_call=True)
def qa_sel(*_):
    ctx = callback_context
    if not ctx.triggered: return no_update
    nid = ctx.triggered[0]["prop_id"].split(".")[0].replace("qa-","")
    return nid if nid in NODES else no_update

# ── Chip click → select ───────────────────────────────────────────────────────
@app.callback(Output("sel","data",allow_duplicate=True),
              Input({"type":"chip","index":ALL},"n_clicks"),
              prevent_initial_call=True)
def chip_sel(clicks):
    ctx = callback_context
    if not ctx.triggered: return no_update
    try:
        nid = _json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]
        return nid if nid in NODES else no_update
    except Exception:
        return no_update

# ── Cytoscape node click ──────────────────────────────────────────────────────
@app.callback(Output("sel","data",allow_duplicate=True),
              Input("cy","tapNodeData"), prevent_initial_call=True)
def cy_click(data):
    if data and data.get("id") in NODES: return data["id"]
    return no_update

# ── Search ────────────────────────────────────────────────────────────────────
@app.callback(Output("search-res","children"), Input("search-inp","value"))
def search(q):
    if not q or len(q)<2: return []
    m = [(nid,nd) for nid,nd in NODES.items() if q.lower() in nd["name"].lower()]
    return [html.Button(nd["name"], id=f"qa-{nid}", n_clicks=0,
                        style={"width":"100%","textAlign":"left","background":"rgba(255,255,255,0.06)",
                               "border":"1px solid rgba(255,255,255,0.1)","borderRadius":5,
                               "color":WHITE,"padding":"5px 9px","fontSize":11,"cursor":"pointer",
                               "marginBottom":2,"fontFamily":"'DM Sans',sans-serif"})
            for nid,nd in m[:5]]

# ── Graph update ──────────────────────────────────────────────────────────────
@app.callback(
    [Output("cy","elements"),Output("cy","layout"),Output("graph-ttl","children")],
    [Input("sel","data"),Input("depth-r","value"),Input("cat-dd","value"),Input("layout-dd","value")])
def upd_graph(sel, depth, cat, layout):
    nd  = NODES.get(sel,{})
    vis = get_visible_ids(sel, depth or 2)
    lnk = get_visible_links(vis)
    ttl = html.Span([
        html.Span(nd.get("name",""), style={"color":NAVY,"fontWeight":700}),
        html.Span(f"  ·  {len(vis)} nodes · {len(lnk)} links",
                  style={"color":MUTED,"fontWeight":400,"fontSize":12}),
    ])
    return (build_elements(sel, depth or 2, cat or "All"),
            {"name":layout or "cose-bilkent","animate":True,"animationDuration":450,
             "fit":True,"padding":40,"nodeRepulsion":9000,"idealEdgeLength":150},
            ttl)

# ── Panel tab switch ──────────────────────────────────────────────────────────
@app.callback(Output("ptab","data"),
              [Input(f"ptab-{t}","n_clicks") for t in ["overview","linked","perms","attrs","activity"]],
              prevent_initial_call=True)
def ptab_switch(*_):
    ctx = callback_context
    if not ctx.triggered: return no_update
    return ctx.triggered[0]["prop_id"].split(".")[0].replace("ptab-","")

# ── KPI strip ─────────────────────────────────────────────────────────────────
@app.callback(Output("kpi-strip","children"), Input("sel","data"))
def kpi_strip(sel):
    nd  = NODES.get(sel,{})
    sc  = get_risk_score(sel)
    imp = impact_trace(sel)
    out = get_outgoing(sel)
    inc = get_incoming(sel)
    sc_col = DANGER if sc>=70 else WARN if sc>=40 else SUCCESS
    rsk = nd.get("risk","")
    rc, rb = RISK_CLR.get(rsk,(MUTED,BG))
    return html.Div([
        html.Span(nd.get("name","")[:24], style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginRight":8}),
        _tag(f"🔗 {len(out)+len(inc)} links", "#EFF6FF", NAVY),
        _tag(f"↓ {len(imp)} impacted", "#FFF7ED", ORANGE),
        _tag(f"⚡ {sc}/100", "#F0FDF4" if sc<40 else "#FFFBEB" if sc<70 else "#FFF1F2", sc_col),
        _tag(nd.get("status","—"), "#F0FDFA", TEAL),
        _tag(rsk, rb, rc) if rsk else html.Span(),
    ], style={"display":"flex","alignItems":"center","gap":4,"flexWrap":"wrap"})

# ── Relationship quick table ───────────────────────────────────────────────────
@app.callback(Output("rel-quick","children"), Input("sel","data"))
def rel_quick(sel):
    lnks = get_visible_links(get_visible_ids(sel, 999))
    if not lnks:
        return html.Div("No relationships.", style={"color":MUTED,"fontSize":12})
    rows = []
    for lk in lnks:
        src = NODES.get(lk["source"],{})
        tgt = NODES.get(lk["target"],{})
        rt  = REL_TYPES.get(lk["relType"],{})
        cat = rt.get("category","default")
        c   = CAT_CLR.get(cat,CAT_CLR["default"])
        rows.append(html.Div([
            html.Span(src.get("name","")[:16], style={"fontSize":11.5,"fontWeight":600,"color":TEXT,"flex":1,"minWidth":0}),
            html.Span(rt.get("label",""),
                      style={"fontSize":9.5,"background":c["bg"],"color":c["txt"],
                             "padding":"1px 7px","borderRadius":4,"fontWeight":600,
                             "flexShrink":0,"margin":"0 6px"}),
            html.Span(lk.get("cardinality",""),
                      style={"fontSize":9,"color":MUTED,"fontFamily":"'DM Mono',monospace",
                             "flexShrink":0,"marginRight":6}),
            html.Span(tgt.get("name","")[:16],
                      style={"fontSize":11.5,"fontWeight":600,"color":TEXT,"flex":1,"textAlign":"right","minWidth":0}),
        ], style={"display":"flex","alignItems":"center","padding":"5px 0","borderBottom":f"1px solid {BG}"}))
    return rows

# ── MAIN PANEL ────────────────────────────────────────────────────────────────
@app.callback(Output("panel","children"), [Input("sel","data"),Input("ptab","data")])
def panel(sel, tab):
    nd = NODES.get(sel)
    if not nd:
        return html.Div("Click any node on the graph →",
                         style={"color":MUTED,"fontSize":13,"padding":20})

    tab  = tab or "overview"
    is_e = nd["type"] == ENTITY
    sc   = get_risk_score(sel)
    imp  = impact_trace(sel)
    up_  = upstream_trace(sel)
    out  = get_outgoing(sel)
    inc  = get_incoming(sel)

    sc_col = DANGER if sc>=70 else WARN if sc>=40 else SUCCESS
    sc_bg  = "#FFF1F2" if sc>=70 else "#FFFBEB" if sc>=40 else "#F0FDF4"
    rsk    = nd.get("risk","")
    rc, rb = RISK_CLR.get(rsk,(MUTED,BG))

    # ── Fixed header ──────────────────────────────────────────────────────
    hdr = html.Div([
        html.Div([
            _pill("Entity" if is_e else "Workflow",
                  bg="#EFF6FF" if is_e else "#F0FDFA",
                  col=NAVY if is_e else TEAL),
            html.Span(nd["subtype"], style={"fontSize":10,"color":MUTED}),
        ], style={"marginBottom":5}),
        html.Div(nd["name"], style={"fontSize":15,"fontWeight":800,"color":NAVY,"marginBottom":6,
                                     "fontFamily":"'Plus Jakarta Sans',sans-serif","lineHeight":1.2}),
        html.Div([
            html.Div([html.Div("OWNER",style={"fontSize":8.5,"fontWeight":700,"color":MUTED,"textTransform":"uppercase","letterSpacing":".07em"}),
                      html.Div(nd["owner"],style={"fontSize":11,"fontWeight":600,"color":TEXT})],style={"flex":1}),
            html.Div([html.Div("STATUS",style={"fontSize":8.5,"fontWeight":700,"color":MUTED,"textTransform":"uppercase","letterSpacing":".07em"}),
                      html.Div(nd.get("status","—"),style={"fontSize":11,"fontWeight":700,"color":TEAL})],style={"flex":1}),
            html.Div([html.Div("RISK" if is_e else "STAGE",style={"fontSize":8.5,"fontWeight":700,"color":MUTED,"textTransform":"uppercase","letterSpacing":".07em"}),
                      html.Div(nd.get("risk","—") if is_e else (nd.get("stage") or "—"),
                               style={"fontSize":11,"fontWeight":700,"color":rc if is_e else NAVY})],style={"flex":1}),
        ], style={"display":"flex","gap":6,"marginBottom":6}),

        # Score bar
        html.Div([html.Div(style={"width":f"{sc}%","height":3,"background":sc_col,"borderRadius":2,"transition":"width .4s"})],
                  style={"background":BORDER,"borderRadius":2,"height":3,"marginBottom":5}) if is_e else html.Div(),
        html.Div([
            html.Span(f"Risk score: {sc}/100",
                      style={"background":sc_bg,"color":sc_col,"fontSize":10,"fontWeight":700,"padding":"2px 8px","borderRadius":4}),
            html.Span(f"  ↓{len(imp)} downstream · ↑{len(up_)} upstream",
                      style={"fontSize":10,"color":MUTED,"marginLeft":8}),
        ]) if is_e else html.Div(),
    ], style={"paddingBottom":10,"marginBottom":8,"borderBottom":f"1px solid {BORDER}"})

    # ── TAB: OVERVIEW ─────────────────────────────────────────────────────
    if tab == "overview":
        body = []

        if nd.get("summary"):
            body.append(html.Div(
                nd["summary"][:320]+"…" if len(nd.get("summary",""))>320 else nd["summary"],
                style={"fontSize":11.5,"color":MUTED,"lineHeight":1.7,"background":BG,
                       "borderRadius":8,"padding":"10px 12px","marginBottom":10}))

        # Impact
        if imp:
            body.append(_sec(f"↓ Downstream impact — {len(imp)} nodes"))
            body += [html.Div([
                html.Span("↓ ",style={"color":SUCCESS,"fontWeight":700}),
                html.Span(NODES.get(i,{}).get("name",i),style={"fontSize":11.5}),
                html.Span(f" · {NODES.get(i,{}).get('type','')}",style={"fontSize":10,"color":MUTED}),
            ], style={"padding":"4px 9px","background":"#F0FDF4","border":"1px solid #BBF7D0",
                       "borderRadius":6,"marginBottom":3}) for i in imp[:5]]

        # Upstream
        if up_:
            deg = [u for u in up_ if NODES.get(u,{}).get("status") in ("Under Review","Not Started")]
            body.append(_sec(f"↑ Upstream dependencies — {len(up_)}"))
            body += [html.Div([
                html.Span("↑ ",style={"color":WARN if u in deg else ORANGE,"fontWeight":700}),
                html.Span(NODES.get(u,{}).get("name",u),style={"fontSize":11.5}),
                html.Span(" ⚠",style={"fontSize":9,"color":DANGER,"fontWeight":700}) if u in deg else html.Span(),
            ], style={"padding":"4px 9px",
                       "background":"#FFFBEB" if u in deg else "#FFF7ED",
                       "border":f"1px solid {'#FCA5A5' if u in deg else '#FED7AA'}",
                       "borderRadius":6,"marginBottom":3}) for u in up_[:5]]

        # Stages
        if nd.get("stages"):
            body.append(_sec("Lifecycle stages"))
            ci = next((i for i,s in enumerate(nd["stages"]) if s["status"]=="current"),-1)
            for s in nd["stages"]:
                ic  = "✓" if s["status"]=="done" else "●" if s["status"]=="current" else "○"
                col = SUCCESS if s["status"]=="done" else TEAL if s["status"]=="current" else MUTED
                body.append(html.Div([
                    html.Span(ic,style={"color":col,"marginRight":7,"fontSize":11,"fontWeight":700}),
                    html.Span(s["name"],style={"color":col,"fontSize":11.5,
                                                "fontWeight":700 if s["status"]=="current" else 500}),
                    html.Span(" ← now" if s["status"]=="current" else "",
                              style={"fontSize":9.5,"color":TEAL,"marginLeft":5,"fontWeight":700}),
                ], style={"padding":"5px 0","borderBottom":f"1px solid {BG}",
                           "display":"flex","alignItems":"center"}))
            if 0<=ci<len(nd["stages"])-1:
                body.append(html.Button("⏭  Advance Stage", id="adv-btn", n_clicks=0,
                                        style={"marginTop":10,"background":TEAL,"color":WHITE,
                                               "border":"none","borderRadius":7,"padding":"7px 14px",
                                               "fontSize":12,"fontWeight":700,"cursor":"pointer",
                                               "width":"100%","fontFamily":"'DM Sans',sans-serif"}))
                body.append(html.Div(id="adv-msg"))

    # ── TAB: LINKED ───────────────────────────────────────────────────────
    elif tab == "linked":
        body = []

        ent_out = [(lk, NODES.get(lk["target"],{})) for lk in out
                   if NODES.get(lk["target"],{}).get("type")==ENTITY]
        ent_in  = [(lk, NODES.get(lk["source"],{})) for lk in inc
                   if NODES.get(lk["source"],{}).get("type")==ENTITY]
        wf_out  = [(lk, NODES.get(lk["target"],{})) for lk in out
                   if NODES.get(lk["target"],{}).get("type")==WORKFLOW]
        wf_in   = [(lk, NODES.get(lk["source"],{})) for lk in inc
                   if NODES.get(lk["source"],{}).get("type")==WORKFLOW]

        all_ent = ent_out + ent_in
        all_wf  = wf_out + wf_in

        if all_ent:
            body.append(_sec(f"Linked Entities ({len(all_ent)})"))
            for lk, n2 in all_ent:
                rt  = REL_TYPES.get(lk["relType"],{})
                cat = rt.get("category","default")
                c   = CAT_CLR.get(cat,CAT_CLR["default"])
                nid2= lk["target"] if lk.get("target") in NODES else lk["source"]
                body.append(html.Div([
                    html.Div([
                        _chip(nid2, n2.get("name",""), is_wf=False),
                    ]),
                    html.Div([
                        html.Span(rt.get("label",""),
                                  style={"fontSize":9.5,"background":c["bg"],"color":c["txt"],
                                         "padding":"1px 6px","borderRadius":4,"fontWeight":600,
                                         "marginRight":6,"marginLeft":4}),
                        html.Span(lk.get("cardinality",""),
                                  style={"fontSize":9.5,"color":MUTED,"fontFamily":"'DM Mono',monospace"}),
                    ], style={"marginTop":2}),
                    html.Div(lk.get("notes","")[:110]+"…" if lk.get("notes","") else "",
                             style={"fontSize":10.5,"color":MUTED,"marginTop":3,"lineHeight":1.5,"marginLeft":4}),
                ], style={"background":BG,"borderRadius":8,"padding":"8px 10px","marginBottom":7}))

        if all_wf:
            body.append(_sec(f"Linked Workflows ({len(all_wf)})"))
            for lk, n2 in all_wf:
                nid2 = lk["target"] if lk.get("target") in NODES else lk["source"]
                wnd  = NODES.get(nid2,{})
                stgs = wnd.get("stages",[])
                ci   = next((i for i,s in enumerate(stgs) if s["status"]=="current"),-1)
                pct  = int((ci/max(len(stgs)-1,1))*100) if ci>=0 else 0
                body.append(html.Div([
                    _chip(nid2, n2.get("name",""), is_wf=True),
                    html.Div([
                        html.Span(wnd.get("stage","—") or "—",
                                  style={"fontSize":11,"color":TEAL,"fontWeight":600}),
                        html.Span(f" · {wnd.get('status','—')}",
                                  style={"fontSize":10.5,"color":MUTED}),
                    ], style={"marginTop":3,"marginLeft":4}),
                    html.Div([html.Div(style={"width":f"{pct}%","height":3,"background":TEAL,"borderRadius":2})],
                              style={"background":BORDER,"borderRadius":2,"height":3,"marginTop":5,"marginLeft":4}),
                    html.Div(f"{pct}% complete",
                              style={"fontSize":9.5,"color":MUTED,"marginTop":2,"marginLeft":4}),
                ], style={"background":"#F0FDFA","border":"1px solid #99F6E4",
                           "borderRadius":8,"padding":"8px 10px","marginBottom":7}))

        if not all_ent and not all_wf:
            body = [html.Div("No linked entities or workflows for this node.",
                              style={"color":MUTED,"fontSize":12})]

    # ── TAB: PERMISSIONS ──────────────────────────────────────────────────
    elif tab == "perms":
        et_map = {
            "Statistical Model":"Model","ML Model":"Model","AI/GenAI Model":"Model","Vendor Model":"Model",
            "Dataset":"Dataset","Validation":"Validation","Policy Document":"Policy",
        }
        etype = et_map.get(nd.get("subtype",""), "Model")
        prows = [r for r in MASTER_PERMISSION_TABLE if r["entity"]==etype]
        cur   = nd.get("stage") or nd.get("workflow_state") or "Registration"
        body  = [
            html.Div(f"Entity type: {etype}",style={"fontSize":11,"color":MUTED,"marginBottom":6}),
            html.Span(f"Current stage: {cur}",
                      style={"fontSize":11,"fontWeight":700,"color":TEAL,"padding":"3px 9px",
                             "background":"#F0FDFA","borderRadius":5,"display":"inline-block","marginBottom":10}),
        ]
        secs_seen = []
        for r in prows:
            if r["section"] not in secs_seen: secs_seen.append(r["section"])
        for sec in secs_seen:
            st_   = SECTION_TYPE_REGISTRY.get(sec,{}).get("type","dynamic")
            stbg, stcl = STYPE_CLR.get(st_,("#F1F5F9","#374151"))
            sp = [r for r in prows if r["section"]==sec]
            body.append(html.Div([
                html.Div([
                    html.Span(f"📁 {sec}",style={"fontSize":12,"fontWeight":700,"color":NAVY}),
                    html.Span(st_,style={"fontSize":9,"fontWeight":700,"padding":"2px 7px","borderRadius":12,
                                          "background":stbg,"color":stcl,"marginLeft":6,
                                          "textTransform":"uppercase","letterSpacing":".05em"}),
                ], style={"marginBottom":6}),
                *[html.Div([
                    html.Span(r["stage"][:18],style={"fontSize":10.5,"color":TEXT,"flex":1}),
                    *[html.Span(lbl,style={"fontSize":10,"fontWeight":800 if r[role]=="M" else 600,
                                            "padding":"2px 7px","borderRadius":5,"marginLeft":3,
                                            "background":PERM_CLR.get(r[role],PERM_CLR["H"])[0],
                                            "color":PERM_CLR.get(r[role],PERM_CLR["H"])[1]})
                      for role, lbl in [("analyst","A"),("validator","V"),("approver","Ap")]],
                    html.Span("← NOW",style={"fontSize":9,"color":TEAL,"marginLeft":4,"fontWeight":700})
                    if (r["stage"].lower() in cur.lower() or cur.lower() in r["stage"].lower()) else html.Span(),
                ], style={"display":"flex","alignItems":"center","padding":"3px 0",
                           "borderBottom":f"1px solid {BG}",
                           "background":"#F0FDFA" if (r["stage"].lower() in cur.lower() or cur.lower() in r["stage"].lower()) else "transparent"})
                  for r in sp],
            ], style={"background":BG,"borderRadius":8,"padding":"9px 10px","marginBottom":8}))

    # ── TAB: ATTRIBUTES ───────────────────────────────────────────────────
    elif tab == "attrs":
        body = []
        if nd.get("attributes"):
            sgroups: dict = {}
            for k, v in nd["attributes"].items():
                ad  = nd.get("attr_defs",{}).get(k,{})
                sec = ad.get("section","General")
                sgroups.setdefault(sec,[]).append((k,v,ad))
            for sec, attrs in sgroups.items():
                body.append(_sec(sec))
                for k, v, ad in attrs:
                    body.append(html.Div([
                        html.Div(ad.get("display_name",k),
                                 style={"fontSize":10,"fontWeight":600,"color":MUTED,"marginBottom":1}),
                        html.Div(str(v),style={"fontSize":12.5,"fontWeight":600,"color":TEXT}),
                    ], style={"padding":"6px 0","borderBottom":f"1px solid {BG}"}))
        sc = get_risk_score(sel)
        body.append(_sec("Derived"))
        body.append(html.Div([
            html.Div("Risk Score",style={"fontSize":10,"fontWeight":600,"color":MUTED,"marginBottom":1}),
            html.Div(f"{sc} / 100",style={"fontSize":14,"fontWeight":800,
                                           "color":DANGER if sc>=70 else WARN if sc>=40 else SUCCESS}),
            html.Div("base + upstream×3 + status + degraded×8",
                     style={"fontSize":10,"color":MUTED,"marginTop":2}),
        ], style={"padding":"6px 0","borderBottom":f"1px solid {BG}"}))
        if nd.get("artifacts"):
            body.append(_sec("Artifacts"))
            body += [html.Div([html.Span("📄 ",style={"marginRight":4}),
                               html.Span(a,style={"fontSize":11.5,"color":TEXT})],
                               style={"padding":"4px 0","borderBottom":f"1px solid {BG}"})
                     for a in nd["artifacts"]]

    # ── TAB: ACTIVITY ─────────────────────────────────────────────────────
    elif tab == "activity":
        body = []
        if nd.get("activity"):
            body.append(_sec("Recent activity"))
            for act in nd["activity"]:
                body.append(html.Div([
                    html.Div(style={"width":6,"height":6,"borderRadius":"50%","background":TEAL,
                                    "marginTop":5,"flexShrink":0}),
                    html.Div([
                        html.Div(act["text"],style={"fontSize":11.5,"color":TEXT,"lineHeight":1.5}),
                        html.Div(act["time"],style={"fontSize":10,"color":MUTED}),
                    ]),
                ], style={"display":"flex","gap":8,"padding":"5px 0","borderBottom":f"1px solid {BG}"}))

        aud = [a for a in AUDIT_LOG if a["entity_id"]==sel]
        if aud:
            body.append(_sec(f"Audit — {len(aud)} changes"))
            for a in aud[:8]:
                body.append(html.Div([
                    html.Div([
                        html.Span(a["field"],style={"fontSize":10,"fontFamily":"'DM Mono',monospace",
                                                     "background":BG,"padding":"1px 6px","borderRadius":4}),
                        html.Span(f" by {a['changed_by']}",style={"fontSize":10,"color":MUTED,"marginLeft":5}),
                        html.Span(a["timestamp"][:10],style={"fontSize":9.5,"color":MUTED,"marginLeft":5,
                                                               "fontFamily":"'DM Mono',monospace"}),
                    ], style={"marginBottom":3}),
                    html.Div([
                        html.Span(str(a["old_value"] or "null"),
                                  style={"background":"#FEE2E2","color":"#991B1B","fontSize":10.5,"padding":"1px 6px","borderRadius":4}),
                        html.Span(" → ",style={"color":MUTED,"margin":"0 4px"}),
                        html.Span(str(a["new_value"]),
                                  style={"background":"#D1FAE5","color":"#065F46","fontSize":10.5,"padding":"1px 6px","borderRadius":4}),
                    ]),
                ], style={"padding":"6px 9px","background":BG,"borderRadius":7,"marginBottom":5}))

        evts = [e for e in EXECUTION_EVENTS if e["entity_id"]==sel]
        if evts:
            body.append(_sec(f"Execution events ({len(evts)})"))
            for e in evts[:6]:
                body.append(html.Div([
                    html.Span(e["timestamp"][:10],style={"fontSize":9.5,"color":MUTED,
                                                           "fontFamily":"'DM Mono',monospace","marginRight":8}),
                    html.Span(e["action"],style={"fontSize":11.5,"fontWeight":600,"color":TEXT}),
                    html.Span(f" → {e['result']}",style={"fontSize":10.5,"color":SUCCESS,"marginLeft":6}),
                ], style={"padding":"4px 0","borderBottom":f"1px solid {BG}",
                           "display":"flex","flexWrap":"wrap","alignItems":"center"}))

        if not body:
            body = [html.Div("No activity recorded.",style={"color":MUTED,"fontSize":12})]
    else:
        body = []

    return [hdr] + (body if isinstance(body,list) else [body])


# ── Advance stage ─────────────────────────────────────────────────────────────
@app.callback(Output("adv-msg","children"),
              Input("adv-btn","n_clicks"), State("sel","data"),
              prevent_initial_call=True)
def do_advance(n, sel):
    if not n: return no_update
    r = advance_stage(sel)
    col = SUCCESS if r["ok"] else DANGER
    msg = f"✓ Advanced to: {r['new_stage']}" if r["ok"] else r["message"]
    return html.Div(msg, style={"color":col,"fontSize":12,"fontWeight":700,"marginTop":6})


# ── Entity panel toggle (sidebar 📦 button) ───────────────────────────────────
@app.callback(
    Output("entity-panel","style", allow_duplicate=True),
    Input("dv-entity","n_clicks"),
    State("entity-panel","style"),
    prevent_initial_call=True,
)
def toggle_entity_panel(n, current_style):
    if not n: return no_update
    is_hidden = (current_style or {}).get("display","none") == "none"
    return {"display":"block","maxHeight":"70vh","overflowY":"auto"} if is_hidden else {"display":"none"}


# ── Entity sub-template (lives permanently in DOM — one callback, works always) ─
@app.callback(
    Output("et-subtpl","children"),
    Input("et-sel","value"),
)
def render_et_subtpl(sel_types):
    if not sel_types:
        return html.Div("Select one or more entity types above.",
                         style={"color":MUTED,"fontSize":12})

    types_list = sel_types if isinstance(sel_types, list) else [sel_types]
    out = []

    for etype in types_list:
        tmpl  = TEMPLATE_CONFIGS.get(etype, {})
        prows = [r for r in MASTER_PERMISSION_TABLE if r["entity"] == etype]
        etype_attrs = [a for a in ATTRIBUTE_LIBRARY
                       if etype in a.get("entity_types",[]) or "All" in a.get("entity_types",[])]

        # Colour accent per entity type
        accent = (TEAL if etype in ("Model","Assessment")
                  else ORANGE if etype == "Finding"
                  else PURPLE if etype in ("Validation","Approval")
                  else NAVY)

        # ── Template config ───────────────────────────────────────────────
        tmpl_hdr = html.Div([
            html.Div([
                html.Span(etype, style={"fontSize":15,"fontWeight":800,"color":NAVY,
                                         "fontFamily":"'Plus Jakarta Sans',sans-serif"}),
                html.Span(f"  {tmpl.get('id_prefix','?')}-XXX",
                          style={"fontSize":12,"color":MUTED,"marginLeft":8,
                                 "fontFamily":"'DM Mono',monospace"}),
            ], style={"marginBottom":5}),
            html.Div(tmpl.get("description","No template config — add to TEMPLATE_CONFIGS in data_model.py"),
                     style={"fontSize":11.5,"color":MUTED,"lineHeight":1.6,"marginBottom":8}),
            html.Div([
                html.Div([
                    html.Div("DEFAULT WORKFLOW",style={"fontSize":8.5,"fontWeight":700,"color":MUTED,
                                                        "textTransform":"uppercase","letterSpacing":".07em","marginBottom":2}),
                    html.Div(tmpl.get("workflow","—"),style={"fontSize":12,"fontWeight":600,"color":TEAL}),
                ], style={"flex":1}),
                html.Div([
                    html.Div("PRELIMINARY ATTRIBUTES",style={"fontSize":8.5,"fontWeight":700,"color":MUTED,
                                                               "textTransform":"uppercase","letterSpacing":".07em","marginBottom":2}),
                    html.Div([
                        html.Span(a, style={"background":"#EFF6FF","color":NAVY,"fontSize":10.5,
                                             "fontWeight":600,"padding":"2px 8px","borderRadius":5,
                                             "marginRight":4,"marginBottom":3,"display":"inline-block"})
                        for a in tmpl.get("preliminary_attrs",[])
                    ]),
                ], style={"flex":2}),
            ], style={"display":"flex","gap":14,"background":"#EFF6FF","borderRadius":8,
                       "padding":"10px 12px","border":"1px solid #BFDBFE"}) if tmpl else html.Div(),
        ])

        # ── Sections with attributes + permissions side by side ───────────
        secs_seen = []
        for r in prows:
            if r["section"] not in secs_seen: secs_seen.append(r["section"])
        if not secs_seen:
            secs_seen = list(tmpl.get("sections",{}).keys())

        section_cards = []
        for sec in secs_seen:
            st_info = SECTION_TYPE_REGISTRY.get(sec, {})
            st_     = st_info.get("type","dynamic")
            stbg, stcl = STYPE_CLR.get(st_, ("#F1F5F9","#374151"))
            sp        = [r for r in prows if r["section"] == sec]
            tmpl_attrs= tmpl.get("sections",{}).get(sec,[])
            lib_attrs = [a for a in etype_attrs if a.get("section") == sec]

            section_cards.append(html.Div([
                # Header
                html.Div([
                    html.Span(f"📁 {sec}",
                              style={"fontSize":12.5,"fontWeight":700,"color":NAVY,"marginRight":8}),
                    html.Span(st_, style={"fontSize":9,"fontWeight":700,"padding":"2px 8px",
                                           "borderRadius":12,"background":stbg,"color":stcl,
                                           "textTransform":"uppercase","letterSpacing":".05em"}),
                ], style={"marginBottom":4}),
                html.Div(st_info.get("description",""),
                         style={"fontSize":10.5,"color":MUTED,"marginBottom":10,"lineHeight":1.5}),

                # Two-col: attrs | permissions
                html.Div([
                    # Left: attributes
                    html.Div([
                        html.Div("ATTRIBUTES", style={"fontSize":8.5,"fontWeight":700,"color":MUTED,
                                                        "textTransform":"uppercase","letterSpacing":".07em","marginBottom":6}),
                        *([html.Div([
                            html.Div(a["display_name"],
                                     style={"fontSize":11.5,"fontWeight":600,"color":TEXT,"marginBottom":1}),
                            html.Div([
                                html.Span(a["data_type"],
                                          style={"fontSize":9.5,"background":"#EFF6FF","color":NAVY,
                                                 "padding":"1px 6px","borderRadius":4,"marginRight":5}),
                                html.Span("required" if a["required"] else "optional",
                                          style={"fontSize":9.5,"color":DANGER if a["required"] else MUTED,
                                                 "fontWeight":600}),
                            ]),
                            html.Div(f"e.g. {a['example']}",
                                     style={"fontSize":10,"color":MUTED,"marginTop":2,
                                            "fontFamily":"'DM Mono',monospace"}),
                        ], style={"padding":"6px 0","borderBottom":f"1px solid {BG}"})
                          for a in lib_attrs]
                         if lib_attrs
                         else [html.Div([
                            html.Span(a, style={"background":BG,"border":f"1px solid {BORDER}",
                                                 "fontSize":10.5,"padding":"2px 8px","borderRadius":4,
                                                 "marginRight":3,"marginBottom":3,"display":"inline-block"})
                            for a in tmpl_attrs
                          ]) if tmpl_attrs
                          else [html.Div("See attribute library below.",
                                          style={"fontSize":11,"color":MUTED,"fontStyle":"italic"})]]),
                    ], style={"flex":1,"minWidth":0}),

                    # Right: permission matrix
                    html.Div([
                        html.Div("STAGE × ROLE", style={"fontSize":8.5,"fontWeight":700,"color":MUTED,
                                                          "textTransform":"uppercase","letterSpacing":".07em","marginBottom":6}),
                        *([html.Div([
                            html.Span(r["stage"],
                                      style={"fontSize":11,"color":TEXT,"flex":1}),
                            *[html.Span(lbl, style={
                                "fontSize":11,"fontWeight":800 if r[role]=="M" else 600,
                                "padding":"2px 8px","borderRadius":5,"marginLeft":4,
                                "minWidth":30,"textAlign":"center","display":"inline-block",
                                "background":PERM_CLR.get(r[role],PERM_CLR["H"])[0],
                                "color":PERM_CLR.get(r[role],PERM_CLR["H"])[1],
                            }) for role, lbl in [("analyst","A"),("validator","V"),("approver","Ap")]],
                          ], style={"display":"flex","alignItems":"center","padding":"4px 0",
                                     "borderBottom":f"1px solid {BG}"})
                          for r in sp]
                         if sp
                         else [html.Div("No permission rows. Add to MASTER_PERMISSION_TABLE.",
                                         style={"fontSize":11,"color":MUTED,"fontStyle":"italic"})]),
                    ], style={"flex":1,"minWidth":0,"paddingLeft":14,
                               "borderLeft":f"1px solid {BORDER}"}),
                ], style={"display":"flex","gap":12}),

            ], style={"background":SURFACE,"border":f"1px solid {BORDER}","borderRadius":9,
                       "padding":"12px 14px","marginBottom":8}))

        # ── Conditional sections ──────────────────────────────────────────
        cond_secs = tmpl.get("conditional_sections",{})
        cond_el = html.Div([
            html.Div("Conditional Sections",
                     style={"fontSize":10,"fontWeight":700,"color":"#C2410C",
                            "textTransform":"uppercase","letterSpacing":".07em","marginBottom":6}),
            html.Div("These sections show/hide based on attribute values — no page reload needed.",
                     style={"fontSize":11,"color":MUTED,"marginBottom":8}),
            *[html.Div([
                html.Span(f"📋 {sn}",
                          style={"fontWeight":700,"color":NAVY,"fontSize":12,"marginRight":8}),
                html.Span("shown when: ",style={"fontSize":11,"color":MUTED}),
                html.Code(cond, style={"fontSize":11,"background":"#F1F5F9","padding":"2px 8px",
                                        "borderRadius":5,"color":NAVY,
                                        "fontFamily":"'DM Mono',monospace"}),
            ], style={"padding":"5px 0","borderBottom":f"1px solid {BORDER}",
                       "display":"flex","alignItems":"center","flexWrap":"wrap","gap":4})
              for sn, cond in cond_secs.items()],
        ], style={"background":"#FFF7ED","border":"1px solid #FED7AA","borderRadius":8,
                   "padding":"10px 14px","marginBottom":10}) if cond_secs else html.Div()

        # ── Document placeholders ─────────────────────────────────────────
        doc_phs = tmpl.get("doc_placeholders",[])
        doc_el = html.Div([
            html.Div("Document Template Placeholders",
                     style={"fontSize":10,"fontWeight":700,"color":MUTED,
                            "textTransform":"uppercase","letterSpacing":".07em","marginBottom":6}),
            html.Div("Upload a Word .docx with these {{placeholders}} — system auto-fills from entity data.",
                     style={"fontSize":11,"color":MUTED,"marginBottom":8}),
            html.Div([
                html.Code(p, style={"fontSize":10.5,"background":"#F5F3FF","color":PURPLE,
                                     "padding":"2px 8px","borderRadius":5,"border":"1px solid #DDD6FE",
                                     "marginRight":4,"marginBottom":4,"display":"inline-block",
                                     "fontFamily":"'DM Mono',monospace"})
                for p in doc_phs
            ]),
        ], style={"background":BG,"border":f"1px solid {BORDER}","borderRadius":8,
                   "padding":"10px 14px","marginBottom":10}) if doc_phs else html.Div()

        # ── Entity-type attribute library ─────────────────────────────────
        attr_tbl = html.Div([
            html.Div(f"Attribute Library — {etype} ({len(etype_attrs)} attributes)",
                     style={"fontSize":10,"fontWeight":700,"color":MUTED,
                            "textTransform":"uppercase","letterSpacing":".07em","marginBottom":6}),
            dash_table.DataTable(
                data=[{"Field":a["field_name"],"Display":a["display_name"],
                       "Type":a["data_type"],"Section":a["section"],
                       "Req":"✓" if a["required"] else "","Example":a["example"]}
                      for a in etype_attrs],
                columns=[{"name":c,"id":c} for c in ["Field","Display","Type","Section","Req","Example"]],
                **_tbl(), page_size=8,
                style_data_conditional=[
                    {"if":{"filter_query":"{Req} = '✓'"},"fontWeight":700,"color":NAVY},
                ],
            ),
        ], style={"marginTop":10}) if etype_attrs else html.Div()

        out.append(html.Div([
            # Left colour bar
            html.Div(style={"width":4,"background":accent,"borderRadius":"4px 0 0 4px","flexShrink":0}),
            html.Div([
                tmpl_hdr,
                html.Div("Sections & Permissions",
                          style={"fontSize":11,"fontWeight":700,"color":NAVY,
                                 "borderBottom":f"1px solid {BORDER}",
                                 "paddingBottom":6,"marginBottom":10,"marginTop":10}),
                *section_cards,
                cond_el,
                doc_el,
                attr_tbl,
            ], style={"flex":1,"minWidth":0,"padding":"14px 16px"}),
        ], style={"display":"flex","background":SURFACE,"border":f"1px solid {BORDER}",
                   "borderRadius":10,"overflow":"hidden","marginBottom":14}))

    return out if out else html.Div("No data for selected types.",style={"color":MUTED})


# ── Deep-dive drawer ──────────────────────────────────────────────────────────
@app.callback(
    [Output("dv-drawer","children"), Output("dv-drawer","style")],
    [Input(f"dv-{t}","n_clicks") for t in ["entity","rel","workflow","perm","exec","version","audit","api"]],
    prevent_initial_call=True,
)
def dv(*_):
    ctx = callback_context
    if not ctx.triggered: return no_update, no_update
    tid = ctx.triggered[0]["prop_id"].split(".")[0].replace("dv-","")
    # Entity is handled by its own permanent panel — drawer stays hidden for it
    if tid == "entity":
        return html.Div(), {"display":"none"}
    show = {"display":"block","padding":"14px 18px","background":BG,
            "borderBottom":f"2px solid {BORDER}","maxHeight":"55vh","overflowY":"auto"}
    return _dv_content(tid), show


def _dv_content(tid):
    titles = {"entity":"📦 Entity System","rel":"🔗 Relationships","workflow":"⚙ Workflows",
               "perm":"🔐 Permissions","exec":"⏱ Execution","version":"🌳 Versions",
               "audit":"📋 Audit","api":"🌐 API Log"}
    hdr = html.Div([
        html.Span(titles.get(tid,tid),style={"fontSize":15,"fontWeight":800,"color":NAVY}),
        html.Span("  ·  Click sidebar button again to close",
                  style={"fontSize":11,"color":MUTED,"marginLeft":8}),
    ], style={"marginBottom":12})

    if tid == "entity":
        # ── 1. Master Entity Table ────────────────────────────────────────
        master_tbl = html.Div([
            html.Div("Master Entity Table",
                     style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":6}),
            html.Div("Assessment → Model → Subprocesses (Validation/Monitoring) → Findings. "
                     "Use Case links to many models. Workflow is a process-level entity.",
                     style={"fontSize":11,"color":MUTED,"marginBottom":10,"lineHeight":1.6}),
            dash_table.DataTable(
                data=MASTER_ENTITY_TABLE,
                columns=[{"name":c.replace("_"," ").title(),"id":c}
                         for c in ["entity_type","category","id_prefix","description"]],
                **_tbl(),
                style_data_conditional=[
                    {"if":{"filter_query":"{category} = 'Business'"},
                     "backgroundColor":"#EFF6FF"},
                    {"if":{"filter_query":"{category} = 'Process'"},
                     "backgroundColor":"#FFF7ED"},
                    {"if":{"filter_query":"{category} = 'Output'"},
                     "backgroundColor":"#F0FDF4"},
                ],
            ),
        ], style={"marginBottom":20})

        # ── 2. Entity sub-template selector ──────────────────────────────
        all_et = [e["entity_type"] for e in MASTER_ENTITY_TABLE]
        selector = html.Div([
            html.Div("Entity Sub-Template Explorer",
                     style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":6}),
            html.Div("Select an entity type to see its full template: sections, section types, "
                     "attribute library, conditional sections, and permission matrix.",
                     style={"fontSize":11,"color":MUTED,"marginBottom":10,"lineHeight":1.6}),
            dcc.Dropdown(
                id="et-sel",
                options=[{"label":e,"value":e} for e in all_et],
                value=["Model"],
                multi=True,
                placeholder="Select entity type(s)…",
                style={"fontSize":12,"marginBottom":14},
            ),
            html.Div(id="et-subtpl"),
        ], style={"marginBottom":20})

        # ── 3. Section Type Registry ──────────────────────────────────────
        sec_type_rows = [
            {"Section":k,"Type":v["type"],"Description":v["description"]}
            for k,v in SECTION_TYPE_REGISTRY.items()
        ]
        sec_registry = html.Div([
            html.Div("Section Type Registry",
                     style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":6}),
            html.Div([
                html.Div([
                    html.Div(["🟢 STATIC"],
                             style={"fontWeight":800,"color":"#065F46","marginBottom":3,"fontSize":11.5}),
                    html.Div("Editable only at Registration/Creation. Frozen in all later stages.",
                             style={"fontSize":11,"color":"#064E3B","lineHeight":1.5}),
                ], style={"background":"#F0FDF4","border":"1px solid #6EE7B7","borderRadius":8,
                           "padding":"10px 12px","flex":1}),
                html.Div([
                    html.Div(["🟡 DYNAMIC"],
                             style={"fontWeight":800,"color":"#C2410C","marginBottom":3,"fontSize":11.5}),
                    html.Div("Editable during specific workflow stages. Role-dependent.",
                             style={"fontSize":11,"color":"#9A3412","lineHeight":1.5}),
                ], style={"background":"#FFF7ED","border":"1px solid #FED7AA","borderRadius":8,
                           "padding":"10px 12px","flex":1}),
                html.Div([
                    html.Div(["⚫ SYSTEM"],
                             style={"fontWeight":800,"color":"#374151","marginBottom":3,"fontSize":11.5}),
                    html.Div("Never user-editable. Hidden pre-Approval. Auto-computed.",
                             style={"fontSize":11,"color":"#374151","lineHeight":1.5}),
                ], style={"background":BG,"border":f"1px solid {BORDER}","borderRadius":8,
                           "padding":"10px 12px","flex":1}),
            ], style={"display":"flex","gap":10,"marginBottom":12}),
            dash_table.DataTable(
                data=sec_type_rows,
                columns=[{"name":c,"id":c.lower()} for c in ["Section","Type","Description"]],
                **_tbl(),
                style_data_conditional=[
                    {"if":{"filter_query":"{Type} = 'static'"},
                     "backgroundColor":"#F5F3FF","color":"#5B21B6","fontWeight":600},
                    {"if":{"filter_query":"{Type} = 'dynamic'"},
                     "backgroundColor":"#FFF7ED","color":"#C2410C","fontWeight":600},
                    {"if":{"filter_query":"{Type} = 'system'"},
                     "backgroundColor":"#F1F5F9","color":"#374151"},
                ],
                page_size=12,
            ),
        ], style={"marginBottom":20})

        # ── 4. Attribute Library ──────────────────────────────────────────
        attr_rows = [{
            "Field name": a["field_name"],
            "Display name": a["display_name"],
            "Data type": a["data_type"],
            "Section": a["section"],
            "Entity types": ", ".join(a["entity_types"]),
            "Required": "✓" if a["required"] else "",
            "Example": a["example"],
        } for a in ATTRIBUTE_LIBRARY]

        attr_library = html.Div([
            html.Div("Attribute Library",
                     style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":6}),
            html.Div("All configurable attributes across all entity types. "
                     "field_name is the system key; display_name is shown in UI. "
                     "doc_placeholder is used in document template generation.",
                     style={"fontSize":11,"color":MUTED,"marginBottom":10,"lineHeight":1.6}),
            dash_table.DataTable(
                data=attr_rows,
                columns=[{"name":c,"id":c} for c in
                         ["Field name","Display name","Data type","Section","Entity types","Required","Example"]],
                **_tbl(),
                page_size=10,
                style_data_conditional=[
                    {"if":{"filter_query":"{Required} = '✓'"},
                     "fontWeight":700,"color":NAVY},
                ],
            ),
        ], style={"marginBottom":20})

        # ── 5. Document Templates ─────────────────────────────────────────
        doc_tpl = html.Div([
            html.Div("Document Templates",
                     style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":6}),
            html.Div("From KT sessions: document template uploads a pre-configured Word doc with "
                     "{{placeholders}}. System identifies unrecognised placeholders (shown in red). "
                     "Generated document auto-fills field_name → display_name values.",
                     style={"fontSize":11,"color":MUTED,"marginBottom":10,"lineHeight":1.6}),
            *[html.Div([
                html.Div([
                    html.Span(t["name"],style={"fontSize":13,"fontWeight":700,"color":NAVY}),
                    html.Span(f" · {t['entity_type']}",style={"fontSize":11,"color":MUTED,"marginLeft":6}),
                    html.Span(f" · {t['format']}",style={"fontSize":10,"background":"#EFF6FF","color":NAVY,
                                                          "padding":"1px 7px","borderRadius":4,"marginLeft":6}),
                ], style={"marginBottom":6}),
                html.Div(t["description"],style={"fontSize":11.5,"color":MUTED,"marginBottom":8}),
                html.Div("Placeholders:", style={"fontSize":10,"fontWeight":700,"color":MUTED,
                                                  "textTransform":"uppercase","letterSpacing":".06em","marginBottom":5}),
                html.Div([
                    html.Span(p["placeholder"],style={
                        "background":"#F5F3FF","color":PURPLE,"fontSize":10.5,"fontWeight":600,
                        "padding":"2px 8px","borderRadius":5,"marginRight":4,"marginBottom":4,
                        "display":"inline-block","fontFamily":"'DM Mono',monospace",
                        "border":"1px solid #DDD6FE",
                    })
                    for p in t["placeholders"]
                ], style={"marginBottom":6}),
                html.Details([
                    html.Summary("Show placeholder → field mapping",
                                  style={"fontSize":11,"cursor":"pointer","color":TEAL,"fontWeight":600}),
                    dash_table.DataTable(
                        data=[{"Placeholder":p["placeholder"],
                               "Field name":p["maps_to"],
                               "Display name":p["display_name"]}
                              for p in t["placeholders"]],
                        columns=[{"name":c,"id":c} for c in ["Placeholder","Field name","Display name"]],
                        **_tbl(),
                        style_table={"marginTop":8},
                    ),
                ]),
            ], style={"background":BG,"border":f"1px solid {BORDER}","borderRadius":10,
                       "padding":"12px 14px","marginBottom":10})
              for t in DOCUMENT_TEMPLATES],
        ], style={"marginBottom":20})

        return [hdr, master_tbl, selector, sec_registry, attr_library, doc_tpl]

    if tid == "rel":
        return [hdr, dash_table.DataTable(data=MASTER_RELATIONSHIP_TABLE,
            columns=[{"name":c.replace("_"," ").title(),"id":c}
                     for c in ["rel_id","from_entity","rel_type","to_entity","cardinality","category","subset","description"]],
            **_tbl(), page_size=10)]

    if tid == "workflow":
        wf_cards = []
        for nid, nd in NODES.items():
            if nd["type"] != WORKFLOW: continue
            stages = nd.get("stages",[])
            ci = next((i for i,s in enumerate(stages) if s["status"]=="current"),-1)
            pct = int((ci/max(len(stages)-1,1))*100) if ci>=0 else 0
            wf_cards.append(html.Div([
                html.Div(nd["name"],style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":5}),
                html.Div([
                    html.Span([
                        html.Span("✓ " if s["status"]=="done" else "● " if s["status"]=="current" else "○ "),
                        s["name"],
                    ], style={"fontSize":10.5,"fontWeight":700 if s["status"]=="current" else 500,
                               "color":SUCCESS if s["status"]=="done" else TEAL if s["status"]=="current" else MUTED,
                               "background":SURFACE,"border":f"1px solid {BORDER}","borderRadius":4,
                               "padding":"3px 8px","marginRight":3,"display":"inline-block","marginBottom":3})
                    for s in stages
                ], style={"marginBottom":6}),
                html.Div([html.Div(style={"width":f"{pct}%","height":3,"background":TEAL,"borderRadius":2})],
                          style={"background":BORDER,"borderRadius":2,"height":3}),
                html.Div(f"{pct}% · {nd.get('stage','—')} · {nd.get('status','—')}",
                          style={"fontSize":10,"color":MUTED,"marginTop":3}),
            ], style={"background":SURFACE,"border":f"1px solid {BORDER}","borderRadius":8,
                       "padding":"10px 12px","display":"inline-block","minWidth":260,
                       "verticalAlign":"top","margin":"0 8px 8px 0"}))
        return [hdr, html.Div(wf_cards)]

    if tid == "perm":
        return [hdr, dash_table.DataTable(data=MASTER_PERMISSION_TABLE,
            columns=[{"name":c.replace("_"," ").title(),"id":c}
                     for c in ["entity","section","section_type","stage","analyst","validator","approver"]],
            **_tbl(), page_size=15,
            style_data_conditional=[
                {"if":{"filter_query":f"{{{col}}} = 'M'","column_id":col},
                 "backgroundColor":"#D1FAE5","color":"#065F46","fontWeight":800}
                for col in ["analyst","validator","approver"]
            ] + [
                {"if":{"filter_query":f"{{{col}}} = 'V'","column_id":col},
                 "backgroundColor":"#DBEAFE","color":"#1E40AF"}
                for col in ["analyst","validator","approver"]
            ] + [
                {"if":{"filter_query":f"{{{col}}} = 'H'","column_id":col},
                 "backgroundColor":"#F1F5F9","color":"#9CA3AF"}
                for col in ["analyst","validator","approver"]
            ])]

    if tid == "exec":
        return [hdr]+[html.Div([
            html.Span(e["timestamp"][:16],style={"fontSize":10,"fontFamily":"'DM Mono',monospace","color":MUTED,"marginRight":10}),
            html.Span(e["action"],style={"fontSize":12.5,"fontWeight":700,"color":NAVY,"marginRight":8}),
            html.Span(e["entity_name"],style={"fontSize":10,"background":BG,"padding":"1px 7px","borderRadius":4,"marginRight":6}),
            html.Span(e["stage"],style={"fontSize":10,"background":"#EFF6FF","color":NAVY,"padding":"1px 7px","borderRadius":4,"marginRight":6}),
            html.Span(e["result"],style={"fontSize":10.5,"fontWeight":700,"color":SUCCESS if e["result"] in ("Approved","Published","Active") else TEAL,"marginRight":10}),
            html.Span(f"👤 {e['actor']}",style={"fontSize":10,"color":MUTED,"marginRight":8}),
            html.Span(e["api_call"],style={"fontSize":10,"fontFamily":"'DM Mono',monospace","background":"#DBEAFE","color":"#1E40AF","padding":"1px 7px","borderRadius":4}),
        ], style={"display":"flex","flexWrap":"wrap","alignItems":"center","gap":2,
                   "padding":"8px 12px","background":SURFACE,"border":f"1px solid {BORDER}",
                   "borderLeft":f"3px solid {TEAL}","borderRadius":"0 7px 7px 0","marginBottom":5})
                for e in EXECUTION_EVENTS]

    if tid == "version":
        out = [hdr]
        grp: dict = {}
        for v in VERSION_REGISTRY: grp.setdefault(v["entity_id"],[]).append(v)
        for eid, vers in grp.items():
            chain = []
            for i, v in enumerate(vers):
                is_a  = v["status"] in ("Active","Under Review")
                is_ap = v["status"] == "Approved"
                bg = "#E6FAFA" if is_a else "#D1FAE5" if is_ap else BG
                bdr= TEAL if is_a else SUCCESS if is_ap else BORDER
                chain.append(html.Div([
                    html.Div(v["version_id"],style={"fontSize":14,"fontWeight":800,"color":NAVY,"fontFamily":"'DM Mono',monospace"}),
                    html.Div(v["status"],style={"fontSize":10,"fontWeight":700,"color":TEAL if is_a else SUCCESS if is_ap else MUTED}),
                    html.Div(v["created_at"][:10],style={"fontSize":9.5,"color":MUTED}),
                ], style={"background":bg,"border":f"1.5px solid {bdr}","borderRadius":7,
                           "padding":"6px 12px","display":"inline-block","verticalAlign":"middle","margin":3}))
                if i<len(vers)-1: chain.append(html.Span("→",style={"color":MUTED,"fontSize":16,"verticalAlign":"middle"}))
            out.append(html.Div([
                html.Div(vers[0]["entity_name"],style={"fontSize":13,"fontWeight":700,"color":NAVY,"marginBottom":5}),
                html.Div(chain),
            ], style={"background":SURFACE,"border":f"1px solid {BORDER}","borderRadius":8,"padding":"10px","marginBottom":8}))
        return out

    if tid == "audit":
        return [hdr]+[html.Div([
            html.Div([
                html.Span(a["timestamp"][:16],style={"fontSize":9.5,"fontFamily":"'DM Mono',monospace","color":MUTED,"marginRight":8}),
                html.Span(a["entity_name"],style={"fontSize":12,"fontWeight":700,"color":NAVY,"marginRight":6}),
                html.Span(a["field"],style={"fontSize":10,"fontFamily":"'DM Mono',monospace","background":BG,"padding":"1px 6px","borderRadius":4,"marginRight":6}),
                html.Span(f"by {a['changed_by']}",style={"fontSize":10.5,"color":MUTED}),
            ],style={"marginBottom":4}),
            html.Div([
                html.Span(str(a["old_value"] or "null"),style={"background":"#FEE2E2","color":"#991B1B","fontSize":11,"padding":"1px 7px","borderRadius":4}),
                html.Span(" → ",style={"color":MUTED,"margin":"0 5px"}),
                html.Span(str(a["new_value"]),style={"background":"#D1FAE5","color":"#065F46","fontSize":11,"padding":"1px 7px","borderRadius":4}),
                html.Span(a["stage"],style={"fontSize":9.5,"background":"#EFF6FF","color":NAVY,"padding":"1px 6px","borderRadius":4,"marginLeft":8}),
            ]),
        ],style={"padding":"8px 12px","borderLeft":f"3px solid {BORDER}","background":BG,
                  "borderRadius":"0 7px 7px 0","marginBottom":5}) for a in AUDIT_LOG]

    if tid == "api":
        MC = {"POST":("#DBEAFE","#1E40AF"),"PATCH":("#FEF3C7","#92400E"),"GET":("#D1FAE5","#065F46")}
        return [hdr]+[html.Div([
            html.Span(a["method"],style={"fontSize":10,"fontWeight":800,"padding":"2px 7px","borderRadius":4,
                "background":MC.get(a["method"],("#F1F5F9",MUTED))[0],
                "color":MC.get(a["method"],("#F1F5F9",MUTED))[1],"fontFamily":"'DM Mono',monospace","marginRight":8}),
            html.Span(a["endpoint"],style={"fontSize":11,"fontFamily":"'DM Mono',monospace","marginRight":8}),
            html.Span(str(a["status_code"]),style={"fontSize":10,"fontWeight":700,"padding":"2px 6px","borderRadius":4,
                "background":"#D1FAE5" if a["status_code"]<300 else "#FEE2E2",
                "color":"#065F46" if a["status_code"]<300 else "#991B1B","marginRight":8}),
            html.Span(f"{a['latency_ms']}ms",style={"fontSize":10.5,"fontWeight":700,
                "color":DANGER if a["latency_ms"]>1000 else WARN if a["latency_ms"]>200 else SUCCESS,"marginRight":12}),
            html.Br(),
            html.Span(a["payload_summary"],style={"fontSize":11.5,"fontWeight":600,"color":TEXT}),
            html.Span(" → ",style={"color":MUTED}),
            html.Span(a["response_summary"],style={"fontSize":11,"color":MUTED}),
        ],style={"background":SURFACE,"border":f"1px solid {BORDER}","borderRadius":7,
                  "padding":"9px 12px","marginBottom":5,"display":"flex","flexWrap":"wrap",
                  "alignItems":"center","gap":2}) for a in API_LOG]

    return [hdr, html.Div("Coming soon.", style={"color":MUTED})]


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
