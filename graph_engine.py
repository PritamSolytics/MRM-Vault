"""
graph_engine.py — MRM Vault Graph Traversal Engine
Pure functions only. No Streamlit, no DOM access.

Implements:
  - Directed BFS (impact_trace, upstream_trace) with cycle-safe visited seeding
  - Undirected N-hop neighbourhood (get_visible_ids) for UI display
  - Consumer lookup (get_consumers) for sink nodes with no outgoing edges
  - Lifecycle state machine (advance_stage) with cross-workflow effects
  - Link accessors (get_outgoing, get_incoming, get_directed_link)
"""

from typing import List, Dict, Optional
from data_model import NODES, LINKS, REL_TYPES, STAGE_TRANSITIONS


# ── Link accessors ─────────────────────────────────────────────────────────────

def get_outgoing(node_id: str) -> List[Dict]:
    """All links where node_id is the source (directed outgoing edges)."""
    return [l for l in LINKS if l["source"] == node_id]


def get_incoming(node_id: str) -> List[Dict]:
    """All links where node_id is the target (directed incoming edges)."""
    return [l for l in LINKS if l["target"] == node_id]


def get_directed_link(source_id: str, target_id: str) -> Optional[Dict]:
    """Get a specific directed link, or None if it doesn't exist."""
    return next((l for l in LINKS
                 if l["source"] == source_id and l["target"] == target_id), None)


def get_related_ids(node_id: str) -> List[str]:
    """
    Undirected neighbourhood — all adjacent node IDs regardless of direction.
    Use only for 'show me what's nearby' UI display, NOT for impact tracing.
    """
    related = set()
    for link in LINKS:
        if link["source"] == node_id:
            related.add(link["target"])
        if link["target"] == node_id:
            related.add(link["source"])
    return sorted(related)


def get_relationship(from_id: str, to_id: str) -> Optional[Dict]:
    """
    Undirected relationship lookup — checks both directions.
    Returns the link dict with an added 'direction' key ('out' or 'in').
    """
    fwd = get_directed_link(from_id, to_id)
    if fwd:
        rt = REL_TYPES.get(fwd["relType"], {})
        return {**fwd, "direction": "out", "label": rt.get("label", fwd["relType"])}
    rev = get_directed_link(to_id, from_id)
    if rev:
        rt = REL_TYPES.get(rev["relType"], {})
        return {**rev, "direction": "in", "label": rt.get("label", rev["relType"])}
    return None


# ── Directional BFS ────────────────────────────────────────────────────────────

def impact_trace(node_id: str) -> List[str]:
    """
    Downstream BFS: "If this node changes or degrades, what is affected?"
    Follows source→target direction.
    Seeds visited with node_id itself to handle cycles correctly.
    Returns all reachable downstream node IDs (not including node_id).
    """
    visited = {node_id}   # seed with self to prevent revisiting
    results = []
    queue   = [l["target"] for l in get_outgoing(node_id)]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        results.append(current)
        queue += [l["target"] for l in get_outgoing(current)]
    return results


def upstream_trace(node_id: str) -> List[str]:
    """
    Upstream BFS: "What does this node depend on?"
    Follows target←source direction (reverse edges).
    Seeds visited with node_id itself to handle cycles correctly.
    Returns all ancestor node IDs (not including node_id).
    """
    visited = {node_id}   # seed with self to prevent revisiting
    results = []
    queue   = [l["source"] for l in get_incoming(node_id)]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        results.append(current)
        queue += [l["source"] for l in get_incoming(current)]
    return results


def get_consumers(node_id: str) -> List[str]:
    """
    Direct consumer lookup for sink nodes (nodes with no outgoing edges).
    Returns the source node IDs of all incoming links.
    Use when impact_trace returns [] because the node has no outgoing edges.
    """
    return [l["source"] for l in get_incoming(node_id)]


# ── N-hop neighbourhood ────────────────────────────────────────────────────────

def get_visible_ids(selected_id: str, depth: int) -> List[str]:
    """
    Undirected N-hop neighbourhood for UI graph display.
    depth=999 means all connected nodes.
    Always includes selected_id even if isolated.
    """
    if not selected_id:
        return []
    visible  = {selected_id}
    frontier = {selected_id}
    for _ in range(depth):
        next_frontier = set()
        for nid in frontier:
            for related_id in get_related_ids(nid):
                if related_id not in visible:
                    next_frontier.add(related_id)
                    visible.add(related_id)
        if not next_frontier:
            break
        frontier = next_frontier
    return sorted(visible)


def get_visible_links(visible_ids: List[str]) -> List[Dict]:
    """Get all links where both endpoints are in visible_ids."""
    vis_set = set(visible_ids)
    return [l for l in LINKS if l["source"] in vis_set and l["target"] in vis_set]


def get_links_by_category(visible_ids: List[str], category: str) -> List[Dict]:
    """Filter visible links by relationship category."""
    return [l for l in get_visible_links(visible_ids)
            if REL_TYPES.get(l["relType"], {}).get("category") == category]


# ── Lifecycle state machine ────────────────────────────────────────────────────

def advance_stage(workflow_id: str) -> Dict:
    """
    Advance a workflow's current stage to the next legal stage.

    Rules:
      - Forward-only: stages cannot be skipped or reversed.
      - STAGE_TRANSITIONS[subtype] defines the legal order.
      - Cross-workflow effect: when Validation Workflow reaches 'Validation Sign-off',
        the Approval Workflow's first stage is automatically unlocked.

    Returns:
      {"ok": True,  "new_stage": "...", "message": "..."}
      {"ok": False, "message": "..."}
    """
    node = NODES.get(workflow_id)
    if not node or node.get("type") != "Workflow":
        return {"ok": False, "message": "Not a workflow node."}

    legal_stages = STAGE_TRANSITIONS.get(node.get("subtype", ""))
    if not legal_stages:
        return {"ok": False, "message": f"No stage machine for subtype: {node.get('subtype')}"}

    stages = node.get("stages", [])
    cur_idx = next((i for i, s in enumerate(stages) if s.get("status") == "current"), -1)

    if cur_idx == -1:
        return {"ok": False, "message": "No current stage found."}
    if cur_idx == len(stages) - 1:
        return {"ok": False, "message": "Already at final stage — workflow complete."}

    prev_name = stages[cur_idx]["name"]
    stages[cur_idx]["status"]     = "done"
    stages[cur_idx + 1]["status"] = "current"
    node["stage"]  = stages[cur_idx + 1]["name"]
    node["status"] = "In Progress"

    # Log the advancement
    node.setdefault("activity", []).insert(0, {
        "text": f'Stage advanced: "{prev_name}" → "{node["stage"]}"',
        "time": "just now",
    })

    # Cross-workflow effect: Validation Sign-off unblocks Approval Workflow
    if workflow_id == "validation_workflow" and node["stage"] == "Validation Sign-off":
        approval = NODES.get("approval_workflow")
        if approval:
            approval_stages = approval.get("stages", [])
            if approval_stages and approval_stages[0].get("status") == "pending":
                approval_stages[0]["status"] = "current"
                approval["stage"]  = approval_stages[0]["name"]
                approval["status"] = "In Progress"
                approval.setdefault("activity", []).insert(0, {
                    "text": "Validation Sign-off received — workflow now unblocked.",
                    "time": "just now",
                })

    return {"ok": True, "new_stage": node["stage"],
            "message": f"Advanced to: {node['stage']}"}


# ── Graph integrity self-tests ─────────────────────────────────────────────────

def run_self_tests() -> List[str]:
    """
    Run data integrity checks. Returns list of error strings (empty = all passed).
    Checks:
      1. All link endpoints reference existing nodes
      2. No self-loops
      3. No duplicate directed edges (same source+target+relType)
      4. All relTypes exist in REL_TYPES registry
      5. All workflow nodes have valid stage arrays
      6. All stage names exist in STAGE_TRANSITIONS for that subtype
      7. No workflow has multiple 'current' stages
      8. No orphan nodes (every node has at least one link)
      9. All subtypes conform to NODE_SCHEMA
    """
    from data_model import NODE_SCHEMA
    errors = []

    for link in LINKS:
        if link["source"] not in NODES:
            errors.append(f"Link source '{link['source']}' not in NODES")
        if link["target"] not in NODES:
            errors.append(f"Link target '{link['target']}' not in NODES")
        if link["source"] == link["target"]:
            errors.append(f"Self-loop on '{link['source']}'")
        if link["relType"] not in REL_TYPES:
            errors.append(f"Unknown relType '{link['relType']}'")

    edge_keys = set()
    for link in LINKS:
        key = f"{link['source']}→{link['target']}:{link['relType']}"
        if key in edge_keys:
            errors.append(f"Duplicate edge: {key}")
        edge_keys.add(key)

    for nid, node in NODES.items():
        linked = any(l["source"] == nid or l["target"] == nid for l in LINKS)
        if not linked:
            errors.append(f"Orphan node: '{nid}'")

        schema = NODE_SCHEMA.get(node.get("type", ""))
        if not schema:
            errors.append(f"Unknown type '{node.get('type')}' on node '{nid}'")
            continue
        if node.get("subtype") not in schema["subtypes"]:
            errors.append(f"Subtype '{node.get('subtype')}' invalid for type "
                          f"'{node.get('type')}' on node '{nid}'")

        if node.get("type") == "Workflow":
            stages = node.get("stages", [])
            if not stages:
                errors.append(f"Workflow '{nid}' has no stages")
                continue
            legal = STAGE_TRANSITIONS.get(node.get("subtype", ""), [])
            for s in stages:
                if s["name"] not in legal:
                    errors.append(f"Stage '{s['name']}' not in STAGE_TRANSITIONS"
                                  f"['{node.get('subtype')}'] for workflow '{nid}'")
            cur_count = sum(1 for s in stages if s.get("status") == "current")
            if cur_count > 1:
                errors.append(f"Workflow '{nid}' has {cur_count} 'current' stages (max 1)")

    return errors


# Run tests on import
_test_errors = run_self_tests()
if _test_errors:
    import warnings
    for err in _test_errors:
        warnings.warn(f"MRM Vault data integrity: {err}")
else:
    print(f"✓ MRM Vault self-tests passed — {len(NODES)} nodes, {len(LINKS)} links, "
          f"{len(REL_TYPES)} rel types")
