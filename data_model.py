"""
data_model.py — MRM Vault Data Model (v2 — Enhanced)
Pure data. No Streamlit. No DOM.

Enhancements over v1:
  - SECTION_TYPE_REGISTRY: static / dynamic / system section classification
  - MASTER_PERMISSION_TABLE: full entity × section × stage × role matrix
  - PERMISSION_FUNCTION: derive permissions from section type (no hardcoding)
  - MASTER_ENTITY_TABLE: all entity types including workflow/stage/task as process entities
  - MASTER_RELATIONSHIP_TABLE: cardinality, category, subset classification
  - RELATIONSHIP_SUBSETS: lifecycle / dependency / governance / monitoring / issue / output
  - VERSION_REGISTRY: entity version history with parent lineage
  - AUDIT_LOG: field-level change log with causality tracking
  - EXECUTION_EVENTS: workflow event timeline
  - API_LOG: external API request/response log
  - WORKFLOW_ENTITY_TABLE, STAGE_ENTITY_TABLE, TASK_ENTITY_TABLE
"""

ENTITY   = "Entity"
WORKFLOW = "Workflow"

# ── Relationship type registry ─────────────────────────────────────────────────
REL_TYPES = {
    "USES_DATASET":      {"label": "uses dataset",       "category": "lineage",     "directed": True,  "cardinality_default": "N:1"},
    "USES_FEATURES":     {"label": "uses features",      "category": "lineage",     "directed": True,  "cardinality_default": "N:1"},
    "FEEDS_INTO":        {"label": "feeds into",         "category": "lineage",     "directed": True,  "cardinality_default": "1:1"},
    "SIBLING_MODEL":     {"label": "sibling model",      "category": "lineage",     "directed": False, "cardinality_default": "N:M"},
    "GOVERNED_BY":       {"label": "governed by",        "category": "governance",  "directed": True,  "cardinality_default": "N:M"},
    "CHECKS_AGAINST":    {"label": "checks against",     "category": "governance",  "directed": True,  "cardinality_default": "N:M"},
    "APPROVAL_GATE":     {"label": "approval gate",      "category": "governance",  "directed": True,  "cardinality_default": "1:1"},
    "VALIDATED_THROUGH": {"label": "validated through",  "category": "validation",  "directed": True,  "cardinality_default": "1:1"},
    "VALIDATES":         {"label": "validates",          "category": "validation",  "directed": True,  "cardinality_default": "1:N"},
    "REQUIRES_DATA":     {"label": "requires data",      "category": "validation",  "directed": True,  "cardinality_default": "N:M"},
    "MONITORED_BY":      {"label": "monitored by",       "category": "monitoring",  "directed": True,  "cardinality_default": "1:1"},
    "GENERATES":         {"label": "generates",          "category": "monitoring",  "directed": True,  "cardinality_default": "1:N"},
    "REPORTS_ON":        {"label": "reports on",         "category": "monitoring",  "directed": True,  "cardinality_default": "N:1"},
    "FOLLOWS":           {"label": "follows",            "category": "lifecycle",   "directed": True,  "cardinality_default": "N:1"},
    "HAS_STAGE":         {"label": "has stage",          "category": "lifecycle",   "directed": True,  "cardinality_default": "1:N"},
    "HAS_TASK":          {"label": "has task",           "category": "lifecycle",   "directed": True,  "cardinality_default": "1:N"},
    "HAS_FINDING":       {"label": "has finding",        "category": "issue",       "directed": True,  "cardinality_default": "1:N"},
    "IMPACTS":           {"label": "impacts",            "category": "issue",       "directed": True,  "cardinality_default": "N:1"},
    "SUMMARIZES":        {"label": "summarizes",         "category": "output",      "directed": True,  "cardinality_default": "N:1"},
    "INFORMS":           {"label": "informs",            "category": "output",      "directed": True,  "cardinality_default": "N:M"},
}

# ── Entity subtype schema ──────────────────────────────────────────────────────
NODE_SCHEMA = {
    ENTITY: {
        "subtypes": [
            "Statistical Model", "ML Model", "AI/GenAI Model", "Vendor Model",
            "Dataset", "Feature Set", "Policy Document", "Report", "Finding",
            "Use Case", "Query",
        ],
        "required_fields": ["owner", "status", "risk"],
    },
    WORKFLOW: {
        "subtypes": ["Validation", "Monitoring", "Approval", "Onboarding", "Remediation"],
        "required_fields": ["owner", "status", "stage", "stages"],
    },
}

# ── Lifecycle state machine ────────────────────────────────────────────────────
STAGE_TRANSITIONS = {
    "Validation":  [
        "Submission & Scoping",
        "Documentation Review",
        "Quantitative Testing",
        "Finding Resolution",
        "Validation Sign-off",
    ],
    "Monitoring":  [
        "Data Ingestion",
        "Metric Calculation",
        "Threshold Review",
        "Report Generation",
        "Committee Submission",
    ],
    "Approval":    [
        "Validation Complete",
        "Committee Review",
        "Senior Approval",
        "Audit Certification",
        "Model Approved",
    ],
    "Onboarding":  [
        "Model Registration",
        "Owner Assignment",
        "Policy Mapping",
        "Workflow Linkage",
        "Active",
    ],
    "Remediation": [
        "Finding Raised",
        "Root Cause Analysis",
        "Remediation Plan",
        "Remediation Execution",
        "Closure",
    ],
}

# ── Risk score weights ─────────────────────────────────────────────────────────
_RISK_BASE  = {"High": 80, "Medium": 50, "Low": 20}
_STATUS_PEN = {"Under Review": 15, "In Progress": 10, "Not Started": 20,
               "Active": 0, "Published": 0}

# ══════════════════════════════════════════════════════════════════════════════
# NEW: MASTER ENTITY TABLE (Business + Process entities)
# ══════════════════════════════════════════════════════════════════════════════
MASTER_ENTITY_TABLE = [
    # Business entities
    {"entity_type": "Model",        "category": "Business", "id_prefix": "MOD", "description": "Primary risk model — statistical, ML, AI, or vendor"},
    {"entity_type": "Validation",   "category": "Business", "id_prefix": "VLD", "description": "Independent validation subprocess linked to a model"},
    {"entity_type": "Finding",      "category": "Business", "id_prefix": "FND", "description": "Issue raised during validation; resolved by model owner"},
    {"entity_type": "Dataset",      "category": "Business", "id_prefix": "DS",  "description": "Input data source with quality and lineage tracking"},
    {"entity_type": "Feature Set",  "category": "Business", "id_prefix": "FS",  "description": "Derived feature contract shared across models"},
    {"entity_type": "Policy",       "category": "Business", "id_prefix": "POL", "description": "MRM governance policy governing model standards"},
    {"entity_type": "Assessment",   "category": "Business", "id_prefix": "ASA", "description": "Identification questionnaire — decides if model or non-model"},
    {"entity_type": "Use Case",     "category": "Business", "id_prefix": "UC",  "description": "Business purpose — links to one or many models"},
    {"entity_type": "Query",        "category": "Business", "id_prefix": "QRY", "description": "Justification query raised against a model"},
    # Output entities
    {"entity_type": "Report",       "category": "Output",   "id_prefix": "RPT", "description": "Monitoring or committee report — auto-generated"},
    # Process entities
    {"entity_type": "Workflow",     "category": "Process",  "id_prefix": "WF",  "description": "Lifecycle control structure — governs stage progression"},
    {"entity_type": "Stage",        "category": "Process",  "id_prefix": "ST",  "description": "Single step within a workflow lifecycle"},
    {"entity_type": "Task",         "category": "Process",  "id_prefix": "TSK", "description": "Atomic action within a stage, assigned to a role"},
]

# ══════════════════════════════════════════════════════════════════════════════
# NEW: WORKFLOW ENTITY TABLE
# ══════════════════════════════════════════════════════════════════════════════
WORKFLOW_ENTITY_TABLE = [
    {"workflow_id": "WF-001", "name": "Model Lifecycle",        "entity_type": "Model",      "subtype": "Validation",   "trigger": "Model registered"},
    {"workflow_id": "WF-002", "name": "Validation Workflow",    "entity_type": "Validation", "subtype": "Validation",   "trigger": "Validation requested"},
    {"workflow_id": "WF-003", "name": "Approval Workflow",      "entity_type": "Model",      "subtype": "Approval",     "trigger": "Validation Sign-off received"},
    {"workflow_id": "WF-004", "name": "Monitoring Workflow",    "entity_type": "Model",      "subtype": "Monitoring",   "trigger": "Model approved"},
    {"workflow_id": "WF-005", "name": "Remediation Workflow",   "entity_type": "Finding",    "subtype": "Remediation",  "trigger": "Finding raised"},
    {"workflow_id": "WF-006", "name": "Onboarding Workflow",    "entity_type": "Model",      "subtype": "Onboarding",   "trigger": "Assessment completes"},
]

# ══════════════════════════════════════════════════════════════════════════════
# NEW: STAGE ENTITY TABLE
# ══════════════════════════════════════════════════════════════════════════════
STAGE_ENTITY_TABLE = [
    {"stage_id": "ST-001", "workflow_id": "WF-001", "stage_name": "Registration",        "order": 1, "owner_role": "Analyst"},
    {"stage_id": "ST-002", "workflow_id": "WF-001", "stage_name": "Documentation Review","order": 2, "owner_role": "Validator"},
    {"stage_id": "ST-003", "workflow_id": "WF-001", "stage_name": "Validation",          "order": 3, "owner_role": "Validator"},
    {"stage_id": "ST-004", "workflow_id": "WF-001", "stage_name": "Approval",            "order": 4, "owner_role": "Approver"},
    {"stage_id": "ST-005", "workflow_id": "WF-001", "stage_name": "Monitoring",          "order": 5, "owner_role": "Analyst/System"},
    {"stage_id": "ST-006", "workflow_id": "WF-002", "stage_name": "Submission & Scoping","order": 1, "owner_role": "Analyst"},
    {"stage_id": "ST-007", "workflow_id": "WF-002", "stage_name": "Documentation Review","order": 2, "owner_role": "Validator"},
    {"stage_id": "ST-008", "workflow_id": "WF-002", "stage_name": "Quantitative Testing","order": 3, "owner_role": "Validator"},
    {"stage_id": "ST-009", "workflow_id": "WF-002", "stage_name": "Finding Resolution",  "order": 4, "owner_role": "Analyst"},
    {"stage_id": "ST-010", "workflow_id": "WF-002", "stage_name": "Validation Sign-off", "order": 5, "owner_role": "Validator"},
]

# ══════════════════════════════════════════════════════════════════════════════
# NEW: TASK ENTITY TABLE
# ══════════════════════════════════════════════════════════════════════════════
TASK_ENTITY_TABLE = [
    {"task_id": "TSK-001", "stage_id": "ST-001", "action": "Fill preliminary data",       "role": "Analyst",   "required": True},
    {"task_id": "TSK-002", "stage_id": "ST-001", "action": "Configure model identification","role": "Analyst",  "required": True},
    {"task_id": "TSK-003", "stage_id": "ST-002", "action": "Define governance regulation", "role": "Validator", "required": True},
    {"task_id": "TSK-004", "stage_id": "ST-003", "action": "Execute quantitative tests",   "role": "Validator", "required": True},
    {"task_id": "TSK-005", "stage_id": "ST-003", "action": "Review findings",              "role": "Validator", "required": False},
    {"task_id": "TSK-006", "stage_id": "ST-004", "action": "Committee review",             "role": "Approver",  "required": True},
    {"task_id": "TSK-007", "stage_id": "ST-004", "action": "Senior approval sign-off",    "role": "Approver",  "required": True},
    {"task_id": "TSK-008", "stage_id": "ST-005", "action": "Ingest performance metrics",  "role": "System",    "required": True},
    {"task_id": "TSK-009", "stage_id": "ST-005", "action": "Generate monitoring report",  "role": "System",    "required": True},
    {"task_id": "TSK-010", "stage_id": "ST-008", "action": "PSI / KS / Gini testing",    "role": "Validator", "required": True},
]

# ══════════════════════════════════════════════════════════════════════════════
# NEW: SECTION TYPE REGISTRY
# section_type: static | dynamic | system
# ══════════════════════════════════════════════════════════════════════════════
SECTION_TYPE_REGISTRY = {
    # Model sections
    "Preliminary":          {"type": "static",  "description": "Editable only at creation/registration"},
    "Model Identification": {"type": "static",  "description": "Editable only at creation"},
    "General Information":  {"type": "static",  "description": "Editable only at creation"},
    "Governance":           {"type": "dynamic", "description": "Editable during review/validation stages"},
    "Derived":              {"type": "system",  "description": "Never user-editable; computed by derivation engine"},
    "Hidden":               {"type": "system",  "description": "Internal system fields; never shown on UI"},
    # Dataset sections
    "Metadata":             {"type": "static",  "description": "Set at dataset creation"},
    "Quality Metrics":      {"type": "dynamic", "description": "Updated during validation"},
    "Lineage":              {"type": "system",  "description": "Auto-derived from upstream graph"},
    # Validation sections
    "Plan":                 {"type": "dynamic", "description": "Filled at submission"},
    "Testing":              {"type": "dynamic", "description": "Filled during testing stage"},
    "Findings":             {"type": "dynamic", "description": "Raised during testing"},
    "Sign-off":             {"type": "dynamic", "description": "Completed at sign-off stage"},
    # Approval sections
    "Review Notes":         {"type": "dynamic", "description": "Committee review notes"},
    "Decision":             {"type": "dynamic", "description": "Final approval decision"},
    "Audit Trail":          {"type": "system",  "description": "Auto-logged; never editable"},
    # Monitoring sections
    "Metrics":              {"type": "dynamic", "description": "Live performance metrics"},
    "Thresholds":           {"type": "dynamic", "description": "Configurable alert thresholds"},
    "Alerts":               {"type": "dynamic", "description": "Breach alerts"},
    "Reports":              {"type": "dynamic", "description": "Committee reports"},
    # Finding sections
    "Issue":                {"type": "dynamic", "description": "Issue description"},
    "Root Cause":           {"type": "dynamic", "description": "Root cause analysis"},
    "Remediation":          {"type": "dynamic", "description": "Remediation plan and execution"},
    "Status":               {"type": "dynamic", "description": "Finding status"},
    # Policy sections
    "Policy Definition":    {"type": "static",  "description": "Core policy text"},
    "Rules":                {"type": "dynamic", "description": "Policy rules — editable when active"},
    "Compliance Mapping":   {"type": "dynamic", "description": "Regulation-to-rule mapping"},
    # Report sections
    "Report Data":          {"type": "system",  "description": "Auto-aggregated from monitoring"},
    "Summary":              {"type": "dynamic", "description": "Human-readable summary"},
    "Distribution":         {"type": "dynamic", "description": "Distribution list"},
    # Descriptive (catch-all)
    "Descriptive":          {"type": "dynamic", "description": "Free text descriptive fields"},
    "Monitoring Config":    {"type": "dynamic", "description": "Monitoring configuration"},
    "Change Log":           {"type": "system",  "description": "System-managed change history"},
}

# ══════════════════════════════════════════════════════════════════════════════
# NEW: MASTER PERMISSION TABLE
# Full matrix: entity × section × stage × role
# M=Manage, V=View, H=Hidden
# ══════════════════════════════════════════════════════════════════════════════
MASTER_PERMISSION_TABLE = [
    # ── MODEL ENTITY ─────────────────────────────────────────────────────────
    # Preliminary (static)
    {"entity": "Model", "section": "Preliminary",          "section_type": "static",  "stage": "Registration",        "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Preliminary",          "section_type": "static",  "stage": "Documentation Review","analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Preliminary",          "section_type": "static",  "stage": "Validation",          "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Preliminary",          "section_type": "static",  "stage": "Approval",            "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Preliminary",          "section_type": "static",  "stage": "Monitoring",          "analyst": "V", "validator": "V", "approver": "V"},
    # Model Identification (static)
    {"entity": "Model", "section": "Model Identification", "section_type": "static",  "stage": "Registration",        "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Model Identification", "section_type": "static",  "stage": "Documentation Review","analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Model Identification", "section_type": "static",  "stage": "Validation",          "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Model Identification", "section_type": "static",  "stage": "Approval",            "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Model Identification", "section_type": "static",  "stage": "Monitoring",          "analyst": "V", "validator": "V", "approver": "V"},
    # General Information (static)
    {"entity": "Model", "section": "General Information",  "section_type": "static",  "stage": "Registration",        "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "General Information",  "section_type": "static",  "stage": "Documentation Review","analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "General Information",  "section_type": "static",  "stage": "Validation",          "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "General Information",  "section_type": "static",  "stage": "Approval",            "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "General Information",  "section_type": "static",  "stage": "Monitoring",          "analyst": "V", "validator": "V", "approver": "V"},
    # Governance (dynamic)
    {"entity": "Model", "section": "Governance",           "section_type": "dynamic", "stage": "Registration",        "analyst": "H", "validator": "H", "approver": "H"},
    {"entity": "Model", "section": "Governance",           "section_type": "dynamic", "stage": "Documentation Review","analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Model", "section": "Governance",           "section_type": "dynamic", "stage": "Validation",          "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Model", "section": "Governance",           "section_type": "dynamic", "stage": "Approval",            "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Governance",           "section_type": "dynamic", "stage": "Monitoring",          "analyst": "V", "validator": "V", "approver": "V"},
    # Derived (system)
    {"entity": "Model", "section": "Derived",              "section_type": "system",  "stage": "Registration",        "analyst": "H", "validator": "H", "approver": "H"},
    {"entity": "Model", "section": "Derived",              "section_type": "system",  "stage": "Documentation Review","analyst": "H", "validator": "H", "approver": "H"},
    {"entity": "Model", "section": "Derived",              "section_type": "system",  "stage": "Validation",          "analyst": "H", "validator": "H", "approver": "H"},
    {"entity": "Model", "section": "Derived",              "section_type": "system",  "stage": "Approval",            "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Model", "section": "Derived",              "section_type": "system",  "stage": "Monitoring",          "analyst": "M", "validator": "M", "approver": "M"},
    # ── DATASET ENTITY ────────────────────────────────────────────────────────
    {"entity": "Dataset", "section": "Metadata",           "section_type": "static",  "stage": "Creation",            "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Dataset", "section": "Metadata",           "section_type": "static",  "stage": "Validation",          "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Dataset", "section": "Quality Metrics",    "section_type": "dynamic", "stage": "Creation",            "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Dataset", "section": "Quality Metrics",    "section_type": "dynamic", "stage": "Validation",          "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Dataset", "section": "Lineage",            "section_type": "system",  "stage": "All",                 "analyst": "V", "validator": "V", "approver": "V"},
    # ── VALIDATION ENTITY ─────────────────────────────────────────────────────
    {"entity": "Validation", "section": "Plan",            "section_type": "dynamic", "stage": "Submission",          "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Validation", "section": "Testing",         "section_type": "dynamic", "stage": "Testing",             "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Validation", "section": "Findings",        "section_type": "dynamic", "stage": "Testing",             "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Validation", "section": "Sign-off",        "section_type": "dynamic", "stage": "Sign-off",            "analyst": "V", "validator": "M", "approver": "M"},
    # ── APPROVAL ENTITY ───────────────────────────────────────────────────────
    {"entity": "Approval", "section": "Review Notes",      "section_type": "dynamic", "stage": "Committee",           "analyst": "V", "validator": "V", "approver": "M"},
    {"entity": "Approval", "section": "Decision",          "section_type": "dynamic", "stage": "Approval",            "analyst": "H", "validator": "V", "approver": "M"},
    {"entity": "Approval", "section": "Audit Trail",       "section_type": "system",  "stage": "All",                 "analyst": "V", "validator": "V", "approver": "V"},
    # ── MONITORING ENTITY ─────────────────────────────────────────────────────
    {"entity": "Monitoring", "section": "Metrics",         "section_type": "dynamic", "stage": "Active",              "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Monitoring", "section": "Thresholds",      "section_type": "dynamic", "stage": "Active",              "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Monitoring", "section": "Alerts",          "section_type": "dynamic", "stage": "Active",              "analyst": "M", "validator": "M", "approver": "V"},
    {"entity": "Monitoring", "section": "Reports",         "section_type": "dynamic", "stage": "Review",              "analyst": "V", "validator": "V", "approver": "M"},
    # ── FINDING ENTITY ────────────────────────────────────────────────────────
    {"entity": "Finding", "section": "Issue",              "section_type": "dynamic", "stage": "Created",             "analyst": "M", "validator": "V", "approver": "V"},
    {"entity": "Finding", "section": "Root Cause",         "section_type": "dynamic", "stage": "Analysis",            "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Finding", "section": "Remediation",        "section_type": "dynamic", "stage": "Remediation",         "analyst": "V", "validator": "M", "approver": "V"},
    {"entity": "Finding", "section": "Status",             "section_type": "dynamic", "stage": "Closed",              "analyst": "V", "validator": "V", "approver": "V"},
    # ── POLICY ENTITY ─────────────────────────────────────────────────────────
    {"entity": "Policy", "section": "Policy Definition",   "section_type": "static",  "stage": "Draft",               "analyst": "V", "validator": "V", "approver": "M"},
    {"entity": "Policy", "section": "Rules",               "section_type": "dynamic", "stage": "Active",              "analyst": "V", "validator": "V", "approver": "M"},
    {"entity": "Policy", "section": "Compliance Mapping",  "section_type": "dynamic", "stage": "All",                 "analyst": "V", "validator": "M", "approver": "V"},
    # ── REPORT ENTITY ─────────────────────────────────────────────────────────
    {"entity": "Report", "section": "Report Data",         "section_type": "system",  "stage": "Generated",           "analyst": "V", "validator": "V", "approver": "V"},
    {"entity": "Report", "section": "Summary",             "section_type": "dynamic", "stage": "Review",              "analyst": "V", "validator": "V", "approver": "M"},
    {"entity": "Report", "section": "Distribution",        "section_type": "dynamic", "stage": "Final",               "analyst": "V", "validator": "V", "approver": "M"},
]

# ══════════════════════════════════════════════════════════════════════════════
# PERMISSION DERIVATION FUNCTION (replaces hardcoded matrix)
# ══════════════════════════════════════════════════════════════════════════════
def get_permission(section_type: str, stage: str, role: str) -> str:
    """
    Derive permission from section type, workflow stage, and user role.
    Returns: 'manage' | 'view' | 'hidden'

    Rules:
      static  → manage ONLY in Registration/Creation/Draft for Analyst/Approver
      dynamic → manage for the 'owning' role at the relevant stage
      system  → hidden pre-Approval; view post-Approval; manage for System role
    """
    st = section_type.lower()
    r  = role.lower()

    if st == "static":
        creation_stages = {"registration", "creation", "draft"}
        if stage.lower() in creation_stages and r == "analyst":
            return "manage"
        if stage.lower() in creation_stages and r == "approver" and "policy" in stage.lower():
            return "manage"
        return "view"

    if st == "dynamic":
        # Default: validator manages during active review stages
        active_stages = {"documentation review", "validation", "testing",
                         "sign-off", "analysis", "remediation", "active", "review", "committee"}
        if stage.lower() in active_stages:
            if r in ("validator", "analyst"):
                return "manage"
            if r == "approver" and stage.lower() in ("committee", "approval", "sign-off", "final"):
                return "manage"
        return "view"

    if st == "system":
        late_stages = {"approval", "monitoring", "active", "published", "generated", "final"}
        if stage.lower() in late_stages:
            return "view"
        return "hidden"

    return "view"  # safe default

# ══════════════════════════════════════════════════════════════════════════════
# MASTER RELATIONSHIP TABLE (extended with subset classification)
# ══════════════════════════════════════════════════════════════════════════════
MASTER_RELATIONSHIP_TABLE = [
    {"rel_id": "R-01", "from_entity": "Model",      "to_entity": "Validation", "rel_type": "VALIDATED_THROUGH", "cardinality": "1:1",   "category": "validation",  "subset": "Lifecycle",    "description": "One active validation workflow per model version"},
    {"rel_id": "R-02", "from_entity": "Model",      "to_entity": "Approval",   "rel_type": "APPROVAL_GATE",     "cardinality": "1:1",   "category": "governance",  "subset": "Lifecycle",    "description": "Final governance gate before model approval"},
    {"rel_id": "R-03", "from_entity": "Model",      "to_entity": "Dataset",    "rel_type": "USES_DATASET",      "cardinality": "N:1",   "category": "lineage",     "subset": "Dependency",   "description": "Model consumes dataset as primary input"},
    {"rel_id": "R-04", "from_entity": "Model",      "to_entity": "Feature Set","rel_type": "USES_FEATURES",     "cardinality": "N:1",   "category": "lineage",     "subset": "Dependency",   "description": "Feature contract shared across sibling models"},
    {"rel_id": "R-05", "from_entity": "Model",      "to_entity": "Policy",     "rel_type": "GOVERNED_BY",       "cardinality": "N:M",   "category": "governance",  "subset": "Governance",   "description": "MRM policy defines validation standards and thresholds"},
    {"rel_id": "R-06", "from_entity": "Model",      "to_entity": "Monitoring", "rel_type": "MONITORED_BY",      "cardinality": "1:1",   "category": "monitoring",  "subset": "Monitoring",   "description": "One monitoring workflow per approved model"},
    {"rel_id": "R-07", "from_entity": "Validation", "to_entity": "Finding",    "rel_type": "HAS_FINDING",       "cardinality": "1:N",   "category": "issue",       "subset": "Issue Tracking","description": "Findings raised during validation testing"},
    {"rel_id": "R-08", "from_entity": "Finding",    "to_entity": "Model",      "rel_type": "IMPACTS",           "cardinality": "N:1",   "category": "issue",       "subset": "Issue Tracking","description": "Finding impacts the parent model"},
    {"rel_id": "R-09", "from_entity": "Monitoring", "to_entity": "Report",     "rel_type": "GENERATES",         "cardinality": "1:N",   "category": "monitoring",  "subset": "Output",       "description": "Quarterly monitoring report generated per cycle"},
    {"rel_id": "R-10", "from_entity": "Report",     "to_entity": "Model",      "rel_type": "REPORTS_ON",        "cardinality": "N:1",   "category": "monitoring",  "subset": "Output",       "description": "Report is a read-only observability artefact"},
    {"rel_id": "R-11", "from_entity": "Model",      "to_entity": "Workflow",   "rel_type": "FOLLOWS",           "cardinality": "N:1",   "category": "lifecycle",   "subset": "Lifecycle",    "description": "Model follows a workflow lifecycle"},
    {"rel_id": "R-12", "from_entity": "Workflow",   "to_entity": "Stage",      "rel_type": "HAS_STAGE",         "cardinality": "1:N",   "category": "lifecycle",   "subset": "Lifecycle",    "description": "Workflow composed of ordered stages"},
    {"rel_id": "R-13", "from_entity": "Stage",      "to_entity": "Task",       "rel_type": "HAS_TASK",          "cardinality": "1:N",   "category": "lifecycle",   "subset": "Lifecycle",    "description": "Stage composed of atomic tasks"},
    {"rel_id": "R-14", "from_entity": "Validation", "to_entity": "Approval",   "rel_type": "FEEDS_INTO",        "cardinality": "1:1",   "category": "governance",  "subset": "Lifecycle",    "description": "Approval unlocked only on Validation Sign-off"},
    {"rel_id": "R-15", "from_entity": "Dataset",    "to_entity": "Feature Set","rel_type": "FEEDS_INTO",        "cardinality": "1:N",   "category": "lineage",     "subset": "Dependency",   "description": "Dataset transformed into feature set"},
    {"rel_id": "R-16", "from_entity": "Model",      "to_entity": "Model",      "rel_type": "SIBLING_MODEL",     "cardinality": "N:M",   "category": "lineage",     "subset": "Dependency",   "description": "Sibling models share upstream data and features"},
]

# ══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP SUBSETS
# ══════════════════════════════════════════════════════════════════════════════
RELATIONSHIP_SUBSETS = {
    "Lifecycle":     {"color": "#dbeafe", "text": "#1d4ed8", "description": "Process flow — how entities progress through lifecycle stages"},
    "Dependency":    {"color": "#fef3c7", "text": "#92400e", "description": "Data flow — upstream/downstream data and feature dependencies"},
    "Governance":    {"color": "#ede9fe", "text": "#6d28d9", "description": "Rules control — which policies govern which entities"},
    "Monitoring":    {"color": "#dcfce7", "text": "#15803d", "description": "Runtime tracking — live performance and threshold monitoring"},
    "Issue Tracking":{"color": "#fee2e2", "text": "#991b1b", "description": "Problem lifecycle — finding detection to closure"},
    "Output":        {"color": "#cffafe", "text": "#0e7490", "description": "Reporting — committee reports and audit artefacts"},
}

# ══════════════════════════════════════════════════════════════════════════════
# VERSION REGISTRY (entity version history with parent lineage)
# ══════════════════════════════════════════════════════════════════════════════
VERSION_REGISTRY = [
    {"version_id": "v1", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "parent_version": None,  "status": "Approved",   "created_by": "R. Analyst",   "created_at": "2025-04-01 09:00", "stage": "Monitoring",          "changes": "Initial model creation and validation"},
    {"version_id": "v2", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "parent_version": "v1",  "status": "Approved",   "created_by": "R. Analyst",   "created_at": "2025-08-15 14:30", "stage": "Monitoring",          "changes": "Risk tier updated T2→T1; regulation added OSFI E-23"},
    {"version_id": "v3", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "parent_version": "v2",  "status": "Active",     "created_by": "A. Kumar",     "created_at": "2026-01-10 11:00", "stage": "Quantitative Testing","changes": "Annual review — model revalidation in progress"},
    {"version_id": "v1", "entity_id": "loan_default_model","entity_name": "Loan Default Model","parent_version": None,  "status": "Active",     "created_by": "CS Team",      "created_at": "2025-06-01 10:00", "stage": "Validation",          "changes": "Initial creation — XGBoost model"},
    {"version_id": "v2", "entity_id": "loan_default_model","entity_name": "Loan Default Model","parent_version": "v1",  "status": "Active",     "created_by": "CS Team",      "created_at": "2026-01-20 09:15", "stage": "Validation",          "changes": "Bias testing passed; 3 features deprecated"},
    {"version_id": "v1", "entity_id": "policy_document",   "entity_name": "MRM Policy",        "parent_version": None,  "status": "Superseded", "created_by": "PG Team",      "created_at": "2024-01-01 00:00", "stage": "Published",           "changes": "Policy v4 — original"},
    {"version_id": "v5.1","entity_id": "policy_document",  "entity_name": "MRM Policy v5.1",   "parent_version": "v5.0","status": "Under Review","created_by": "PG Team",     "created_at": "2026-03-01 00:00", "stage": "Under Review",        "changes": "Annual review — EU AI Act alignment, CRO comment round"},
]

# ══════════════════════════════════════════════════════════════════════════════
# EXECUTION EVENTS (workflow execution timeline)
# ══════════════════════════════════════════════════════════════════════════════
EXECUTION_EVENTS = [
    {"event_id": "EVT-001", "timestamp": "2025-04-01 09:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Registration",        "action": "Entity created",           "actor": "R. Analyst",   "result": "Draft",          "api_call": "POST /entity",         "version": "v1"},
    {"event_id": "EVT-002", "timestamp": "2025-04-03 11:30", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Registration",        "action": "Owner assigned",           "actor": "R. Analyst",   "result": "Draft",          "api_call": "PATCH /entity/MOD-001","version": "v1"},
    {"event_id": "EVT-003", "timestamp": "2025-04-10 14:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Documentation Review","action": "Submitted for review",     "actor": "R. Analyst",   "result": "Under Review",   "api_call": "POST /workflow/advance","version": "v1"},
    {"event_id": "EVT-004", "timestamp": "2025-05-02 10:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Validation",          "action": "Validation started",      "actor": "A. Mehta",     "result": "In Progress",    "api_call": "POST /workflow/advance","version": "v1"},
    {"event_id": "EVT-005", "timestamp": "2025-07-15 16:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Approval",            "action": "Model approved",          "actor": "D. Patel",     "result": "Approved",       "api_call": "POST /workflow/approve","version": "v1"},
    {"event_id": "EVT-006", "timestamp": "2025-08-15 14:30", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Monitoring",          "action": "Risk tier changed T2→T1", "actor": "R. Analyst",   "result": "Active",         "api_call": "PATCH /entity/MOD-001","version": "v2"},
    {"event_id": "EVT-007", "timestamp": "2026-01-10 11:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Quantitative Testing","action": "Annual review initiated",  "actor": "A. Kumar",     "result": "In Progress",    "api_call": "POST /workflow/start", "version": "v3"},
    {"event_id": "EVT-008", "timestamp": "2026-04-28 09:15", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "stage": "Quantitative Testing","action": "Stage advanced",          "actor": "A. Mehta",     "result": "In Progress",    "api_call": "POST /workflow/advance","version": "v3"},
    {"event_id": "EVT-009", "timestamp": "2026-04-29 14:00", "entity_id": "validation_workflow","entity_name": "Validation Wkflw","stage": "Quantitative Testing","action": "Dataset A linked",         "actor": "A. Mehta",     "result": "In Progress",    "api_call": "POST /link",           "version": None},
    {"event_id": "EVT-010", "timestamp": "2026-04-30 10:00", "entity_id": "monitoring_workflow","entity_name": "Monitoring Wkflw","stage": "Committee Submission","action": "Q1-2026 report generated", "actor": "System",       "result": "Published",      "api_call": "POST /report/generate","version": None},
]

# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG (field-level change tracking)
# ══════════════════════════════════════════════════════════════════════════════
AUDIT_LOG = [
    {"audit_id": "AUD-001", "timestamp": "2025-04-01 09:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "status",        "old_value": None,        "new_value": "Draft",          "changed_by": "R. Analyst", "stage": "Registration",        "triggered_by": "Entity created"},
    {"audit_id": "AUD-002", "timestamp": "2025-04-03 11:30", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "owner",         "old_value": "Unassigned","new_value": "Risk Analytics",  "changed_by": "R. Analyst", "stage": "Registration",        "triggered_by": "Manual update"},
    {"audit_id": "AUD-003", "timestamp": "2025-04-10 14:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "status",        "old_value": "Draft",     "new_value": "Under Review",   "changed_by": "R. Analyst", "stage": "Documentation Review","triggered_by": "Workflow advance"},
    {"audit_id": "AUD-004", "timestamp": "2025-05-02 10:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "workflow_state","old_value": "Doc Review","new_value": "Validation",      "changed_by": "A. Mehta",   "stage": "Validation",          "triggered_by": "Workflow advance"},
    {"audit_id": "AUD-005", "timestamp": "2025-07-15 16:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "status",        "old_value": "In Progress","new_value": "Approved",       "changed_by": "D. Patel",   "stage": "Approval",            "triggered_by": "Approval workflow"},
    {"audit_id": "AUD-006", "timestamp": "2025-08-15 14:30", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "risk_tier",     "old_value": "T2",        "new_value": "T1 (Material)",  "changed_by": "R. Analyst", "stage": "Monitoring",          "triggered_by": "Manual update"},
    {"audit_id": "AUD-007", "timestamp": "2025-08-15 14:31", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "regulation",    "old_value": "SR 11-7",   "new_value": "SR 11-7, OSFI E-23","changed_by": "R. Analyst","stage": "Monitoring",         "triggered_by": "Manual update"},
    {"audit_id": "AUD-008", "timestamp": "2026-01-10 11:00", "entity_id": "credit_risk_model", "entity_name": "Credit Risk Model", "field": "workflow_state","old_value": "Monitoring","new_value": "Quantitative Testing","changed_by": "A. Kumar","stage": "Quantitative Testing","triggered_by": "Annual review"},
    {"audit_id": "AUD-009", "timestamp": "2026-03-01 00:00", "entity_id": "policy_document",   "entity_name": "MRM Policy",        "field": "status",        "old_value": "Active",    "new_value": "Under Review",   "changed_by": "PG Team",    "stage": "Under Review",        "triggered_by": "Annual review cycle"},
    {"audit_id": "AUD-010", "timestamp": "2026-04-28 09:15", "entity_id": "validation_workflow","entity_name": "Validation Wkflw","field": "stage",         "old_value": "Doc Review","new_value": "Quant Testing",   "changed_by": "A. Mehta",   "stage": "Quantitative Testing","triggered_by": "Workflow advance"},
]

# ══════════════════════════════════════════════════════════════════════════════
# API LOG (external API request/response log)
# ══════════════════════════════════════════════════════════════════════════════
API_LOG = [
    {"api_id": "API-001", "timestamp": "2025-04-01 09:00", "endpoint": "/api/v1/entity",               "method": "POST",  "status_code": 201, "entity_id": "credit_risk_model", "payload_summary": "Create entity: Credit Risk Model (type=Model)",     "response_summary": "id=MOD-001, status=created",          "latency_ms": 124, "actor": "R. Analyst"},
    {"api_id": "API-002", "timestamp": "2025-04-03 11:30", "endpoint": "/api/v1/entity/MOD-001",        "method": "PATCH", "status_code": 200, "entity_id": "credit_risk_model", "payload_summary": "Update owner → Risk Analytics Team",              "response_summary": "status=updated",                      "latency_ms": 87,  "actor": "R. Analyst"},
    {"api_id": "API-003", "timestamp": "2025-04-10 14:00", "endpoint": "/api/v1/workflow/advance",      "method": "POST",  "status_code": 200, "entity_id": "credit_risk_model", "payload_summary": "Advance: Registration → Documentation Review",    "response_summary": "new_stage=Documentation Review",      "latency_ms": 156, "actor": "R. Analyst"},
    {"api_id": "API-004", "timestamp": "2025-05-02 10:00", "endpoint": "/api/v1/workflow/advance",      "method": "POST",  "status_code": 200, "entity_id": "credit_risk_model", "payload_summary": "Advance: Documentation Review → Validation",     "response_summary": "new_stage=Validation; auto-created VLD-001", "latency_ms": 201, "actor": "A. Mehta"},
    {"api_id": "API-005", "timestamp": "2025-07-15 16:00", "endpoint": "/api/v1/workflow/approve",      "method": "POST",  "status_code": 200, "entity_id": "credit_risk_model", "payload_summary": "Senior approval sign-off by D. Patel",           "response_summary": "status=Approved; monitoring workflow unlocked", "latency_ms": 178, "actor": "D. Patel"},
    {"api_id": "API-006", "timestamp": "2026-01-10 11:00", "endpoint": "/api/v1/workflow/start",        "method": "POST",  "status_code": 200, "entity_id": "credit_risk_model", "payload_summary": "Start annual review validation (Validation v3)",  "response_summary": "workflow_id=WF-VAL-003 created",     "latency_ms": 143, "actor": "A. Kumar"},
    {"api_id": "API-007", "timestamp": "2026-04-28 09:15", "endpoint": "/api/v1/workflow/advance",      "method": "POST",  "status_code": 200, "entity_id": "validation_workflow","payload_summary": "Advance: Doc Review → Quantitative Testing",    "response_summary": "new_stage=Quantitative Testing",     "latency_ms": 99,  "actor": "A. Mehta"},
    {"api_id": "API-008", "timestamp": "2026-04-29 14:00", "endpoint": "/api/v1/link",                  "method": "POST",  "status_code": 201, "entity_id": "validation_workflow","payload_summary": "Link: Dataset A → Validation Workflow (evidence)","response_summary": "link_id=LNK-012 created",            "latency_ms": 67,  "actor": "A. Mehta"},
    {"api_id": "API-009", "timestamp": "2026-04-30 10:00", "endpoint": "/api/v1/report/generate",       "method": "POST",  "status_code": 201, "entity_id": "monitoring_workflow","payload_summary": "Generate Q1-2026 monitoring report",             "response_summary": "report_id=RPT-2026-Q1 created",      "latency_ms": 2340,"actor": "System"},
    {"api_id": "API-010", "timestamp": "2026-04-30 10:05", "endpoint": "/api/v1/entity/MOD-001/risk",   "method": "GET",   "status_code": 200, "entity_id": "credit_risk_model", "payload_summary": "Fetch derived risk score for Credit Risk Model",  "response_summary": "risk_score=91, risk=High",            "latency_ms": 45,  "actor": "Dashboard"},
]

# ══════════════════════════════════════════════════════════════════════════════
# NODE INVENTORY (unchanged from v1 but kept in full)
# ══════════════════════════════════════════════════════════════════════════════
NODES = {
    "credit_risk_model": {
        "id": "credit_risk_model",
        "name": "Credit Risk Model",
        "type": ENTITY, "subtype": "Statistical Model",
        "owner": "Risk Analytics Team", "owner_initials": "RA",
        "status": "Active", "risk": "High",
        "stage": None, "family": "Credit Risk",
        "jurisdiction": "SR 11-7 / OSFI E-23",
        "last_reviewed": "Feb 2026", "next_review": "Aug 2026",
        "workflow_state": "Monitoring",
        "current_version": "v3",
        "summary": (
            "Primary logistic regression model assessing credit risk exposure across "
            "retail and commercial portfolios. Outputs feed capital provisioning "
            "(Basel IV RWEA) and loan-origination decisions. Tier 1 (Material). "
            "Governed by MRM Policy v5.1 and validated per SR 11-7 requirements."
        ),
        "attributes": {
            "model_type":           "Statistical Model",
            "risk_tier":            "T1 (Material)",
            "regulation":           "SR 11-7, OSFI E-23",
            "business_unit":        "Risk Analytics",
            "region":               "Global",
            "development_due_date": "30 Sep 2025",
            "validation_due_date":  "31 Oct 2025",
            "model_family":         "Credit Risk",
            "intended_use":         "Credit risk assessment for retail and commercial portfolios",
            "financial_impact":     "High — feeds capital provisioning",
        },
        "attr_defs": {
            "model_type":           {"display_name": "Model type",           "data_type": "Single-select", "section": "Model Identification"},
            "risk_tier":            {"display_name": "Risk tier",            "data_type": "Single-select", "section": "Model Identification"},
            "regulation":           {"display_name": "Regulation",           "data_type": "Multi-select",  "section": "Governance"},
            "business_unit":        {"display_name": "Business unit",        "data_type": "Single-select", "section": "General Information"},
            "region":               {"display_name": "Region",               "data_type": "Conditional select","section": "General Information"},
            "development_due_date": {"display_name": "Development due date", "data_type": "Date",          "section": "General Information"},
            "validation_due_date":  {"display_name": "Validation due date",  "data_type": "Date",          "section": "General Information"},
            "model_family":         {"display_name": "Model family",         "data_type": "Single-select", "section": "Model Identification"},
            "intended_use":         {"display_name": "Intended use",         "data_type": "Text extended",  "section": "General Information"},
            "financial_impact":     {"display_name": "Financial impact",     "data_type": "Single-select", "section": "Model Identification"},
        },
        "artifacts": [
            "Model Documentation v3.2", "Validation Report Q4-2025",
            "Approval Evidence", "Source Code Repository", "Performance Baseline",
        ],
        "activity": [
            {"text": "Validation report uploaded by A. Kumar",     "time": "2h ago"},
            {"text": "Owner updated to Risk Analytics Team",       "time": "1d ago"},
            {"text": "Monitoring workflow linked",                 "time": "3d ago"},
            {"text": "Risk tier changed: Medium → High (T2 → T1)","time": "1w ago"},
        ],
    },

    "loan_default_model": {
        "id": "loan_default_model",
        "name": "Loan Default Model",
        "type": ENTITY, "subtype": "ML Model",
        "owner": "Credit Science Team", "owner_initials": "CS",
        "status": "Active", "risk": "High",
        "stage": None, "family": "Credit Risk",
        "jurisdiction": "SR 11-7",
        "last_reviewed": "Jan 2026", "next_review": "Jul 2026",
        "workflow_state": "Validation",
        "current_version": "v2",
        "summary": (
            "Gradient-boosted tree (XGBoost) predicting 12-month probability of default "
            "across retail lending. Sibling to Credit Risk Model — both share Dataset A "
            "and Feature Set Credit v4. Dataset A degradation impacts both models simultaneously."
        ),
        "attributes": {
            "model_type":    "ML Model",
            "risk_tier":     "T1 (Material)",
            "regulation":    "SR 11-7",
            "business_unit": "Retail Banking",
            "region":        "India, Global",
            "model_family":  "Credit Risk",
            "financial_impact": "High — feeds loan origination decisions",
        },
        "attr_defs": {
            "model_type":    {"display_name": "Model type",    "data_type": "Single-select", "section": "Model Identification"},
            "risk_tier":     {"display_name": "Risk tier",     "data_type": "Single-select", "section": "Model Identification"},
            "regulation":    {"display_name": "Regulation",    "data_type": "Multi-select",  "section": "Governance"},
            "business_unit": {"display_name": "Business unit", "data_type": "Single-select", "section": "General Information"},
            "region":        {"display_name": "Region",        "data_type": "Conditional select","section": "General Information"},
            "model_family":  {"display_name": "Model family",  "data_type": "Single-select", "section": "Model Identification"},
            "financial_impact": {"display_name": "Financial impact","data_type":"Single-select","section":"Model Identification"},
        },
        "artifacts": [
            "Model Card", "Bias Testing Report", "Feature Importance Analysis", "Backtesting Results",
        ],
        "activity": [
            {"text": "Bias test completed — passed all thresholds", "time": "1d ago"},
            {"text": "Linked to Credit Risk Model family",          "time": "5d ago"},
            {"text": "New training dataset ingested",               "time": "2w ago"},
        ],
    },

    "dataset_a": {
        "id": "dataset_a",
        "name": "Dataset A — Customer Credit",
        "type": ENTITY, "subtype": "Dataset",
        "owner": "Data Management Team", "owner_initials": "DM",
        "status": "Active", "risk": "Medium",
        "stage": None, "family": None,
        "jurisdiction": None,
        "last_reviewed": "Mar 2026", "next_review": "Sep 2026",
        "workflow_state": "Active",
        "current_version": "v1",
        "summary": (
            "Core customer credit bureau dataset: 24 months of transactional history, "
            "delinquency records, credit utilisation. Shared upstream dependency for "
            "both Credit Risk Model and Loan Default Model. Quality degradation here "
            "triggers a two-model impact — highest impact node in current inventory."
        ),
        "attributes": {
            "data_source":    "Credit Bureau",
            "coverage":       "24 months transactional",
            "completeness":   "99.4%",
            "refresh_freq":   "Monthly",
            "row_count":      "12.4M records",
            "columns":        "87 features",
            "quality_status": "Passed",
        },
        "attr_defs": {
            "data_source":  {"display_name": "Data source",         "data_type": "Single-select", "section": "General Information"},
            "coverage":     {"display_name": "Coverage period",     "data_type": "Text",          "section": "General Information"},
            "completeness": {"display_name": "Completeness (%)",    "data_type": "Number",        "section": "Quality Metrics"},
            "refresh_freq": {"display_name": "Refresh frequency",   "data_type": "Single-select", "section": "General Information"},
            "row_count":    {"display_name": "Row count",           "data_type": "Number",        "section": "Quality Metrics"},
            "columns":      {"display_name": "Feature count",       "data_type": "Number",        "section": "Quality Metrics"},
            "quality_status":{"display_name":"Quality status",      "data_type": "Single-select", "section": "Quality Metrics"},
        },
        "artifacts": [
            "Data Dictionary v2", "Source Mapping", "Quality Report Q1-2026", "Lineage Diagram",
        ],
        "activity": [
            {"text": "Quality report uploaded — 99.4% completeness", "time": "4h ago"},
            {"text": "Linked to Validation Workflow as evidence",    "time": "2d ago"},
            {"text": "Source mapping updated",                       "time": "1w ago"},
        ],
    },

    "policy_document": {
        "id": "policy_document",
        "name": "MRM Policy v5.1",
        "type": ENTITY, "subtype": "Policy Document",
        "owner": "Policy Governance Team", "owner_initials": "PG",
        "status": "Under Review", "risk": "Medium",
        "stage": None, "family": None,
        "jurisdiction": "SR 11-7 / PRA SS1/23",
        "last_reviewed": "Mar 2026", "next_review": "Apr 2026",
        "workflow_state": "Under Review",
        "current_version": "v5.1",
        "summary": (
            "Enterprise MRM policy defining governance controls, model tiering criteria, "
            "validation standards, and approval thresholds. Aligned with SR 11-7 and "
            "PRA SS1/23. Currently under annual review — status 'Under Review' adds "
            "governance uncertainty to all governed models and their downstream workflows."
        ),
        "attributes": {
            "policy_version": "5.1",
            "review_cycle":   "Annual",
            "approving_body": "Model Risk Committee",
            "regulations":    "SR 11-7, PRA SS1/23",
            "tiering_criteria": "Defined: T1/T2/T3 thresholds",
        },
        "attr_defs": {
            "policy_version":   {"display_name": "Policy version",   "data_type": "Text",   "section": "General Information"},
            "review_cycle":     {"display_name": "Review cycle",     "data_type": "Single-select","section": "General Information"},
            "approving_body":   {"display_name": "Approving body",   "data_type": "Text",   "section": "Governance"},
            "regulations":      {"display_name": "Regulations",      "data_type": "Multi-select","section": "Governance"},
            "tiering_criteria": {"display_name": "Tiering criteria", "data_type": "Text extended","section": "Descriptive"},
        },
        "artifacts": [
            "Policy PDF v5.1", "Change Log", "Regulatory Mapping", "Committee Approval Notes",
        ],
        "activity": [
            {"text": "Review comment added by Chief Risk Officer", "time": "6h ago"},
            {"text": "Policy linked to Credit Risk Model",         "time": "2d ago"},
            {"text": "Version 5.1 draft circulated",              "time": "1w ago"},
        ],
    },

    "feature_set": {
        "id": "feature_set",
        "name": "Feature Set — Credit v4",
        "type": ENTITY, "subtype": "Feature Set",
        "owner": "Data Science Team", "owner_initials": "DS",
        "status": "Active", "risk": "Low",
        "stage": None, "family": None,
        "jurisdiction": None,
        "last_reviewed": "Feb 2026", "next_review": "Aug 2026",
        "workflow_state": "Active",
        "current_version": "v4",
        "summary": (
            "47-variable feature set for credit scoring and default prediction, "
            "derived from Dataset A via transformation pipeline. Both Credit Risk Model "
            "and Loan Default Model depend on this — a feature contract change requires "
            "coordinated revalidation of both sibling models."
        ),
        "attributes": {
            "feature_count":      "47 active features",
            "source_dataset":     "Dataset A — Customer Credit",
            "transformation":     "StandardScaler + WOE encoding",
            "drift_threshold":    "PSI > 0.1 = alert",
            "deprecated_features": "3 deprecated (v3 → v4)",
        },
        "attr_defs": {
            "feature_count":       {"display_name": "Feature count",       "data_type": "Number",   "section": "General Information"},
            "source_dataset":      {"display_name": "Source dataset",      "data_type": "Association","section": "General Information"},
            "transformation":      {"display_name": "Transformation rules","data_type": "Text",      "section": "Descriptive"},
            "drift_threshold":     {"display_name": "Drift threshold",     "data_type": "Number",    "section": "Monitoring Config"},
            "deprecated_features": {"display_name": "Deprecated features", "data_type": "Number",    "section": "Change Log"},
        },
        "artifacts": [
            "Feature Catalogue v4", "Transformation Rules", "Feature Validation Report", "Drift Thresholds Config",
        ],
        "activity": [
            {"text": "Feature validation completed by DS lead",        "time": "3d ago"},
            {"text": "Linked with Dataset A (source)",                 "time": "1w ago"},
            {"text": "3 features deprecated — low importance score",  "time": "2w ago"},
        ],
    },

    "monitoring_report": {
        "id": "monitoring_report",
        "name": "Q1-2026 Monitoring Report",
        "type": ENTITY, "subtype": "Report",
        "owner": "Model Monitoring Team", "owner_initials": "MM",
        "status": "Published", "risk": "Low",
        "stage": None, "family": None,
        "jurisdiction": None,
        "last_reviewed": "Apr 2026", "next_review": "Jul 2026",
        "workflow_state": "Published",
        "current_version": "v1",
        "summary": (
            "Quarterly monitoring report for Credit Risk Model. Contains PSI, KS statistic, "
            "Gini trend, input drift analysis, output distribution, and threshold breach summary. "
            "Published to model committee. All thresholds within limits — no breaches this quarter."
        ),
        "attributes": {
            "report_period":  "Q1 2026 (Jan–Mar)",
            "psi_result":     "0.04 (within threshold <0.1)",
            "ks_statistic":   "0.42 (stable vs prior quarter)",
            "gini_trend":     "Stable (+0.02)",
            "breach_count":   "0 breaches",
            "distribution":   "Within expected bounds",
        },
        "attr_defs": {
            "report_period": {"display_name": "Report period",     "data_type": "Text",   "section": "General Information"},
            "psi_result":    {"display_name": "PSI result",        "data_type": "Number", "section": "Metrics"},
            "ks_statistic":  {"display_name": "KS statistic",     "data_type": "Number", "section": "Metrics"},
            "gini_trend":    {"display_name": "Gini trend",        "data_type": "Text",   "section": "Metrics"},
            "breach_count":  {"display_name": "Threshold breaches","data_type": "Number", "section": "Metrics"},
            "distribution":  {"display_name": "Output distribution","data_type": "Text",  "section": "Metrics"},
        },
        "artifacts": [
            "Monitoring PDF", "Drift Analysis Appendix", "KPI Snapshot Dashboard", "Threshold Evidence Log",
        ],
        "activity": [
            {"text": "Report published and distributed to committee", "time": "1d ago"},
            {"text": "Monitoring workflow completed",                 "time": "2d ago"},
            {"text": "PSI threshold review completed — within limits","time": "4d ago"},
        ],
    },

    # WORKFLOWS
    "validation_workflow": {
        "id": "validation_workflow",
        "name": "Model Validation Workflow",
        "type": WORKFLOW, "subtype": "Validation",
        "owner": "Independent Validation Team", "owner_initials": "IV",
        "status": "In Progress", "risk": None,
        "stage": "Quantitative Testing", "family": None,
        "jurisdiction": None,
        "last_reviewed": "Mar 2026", "next_review": None,
        "workflow_state": "Quantitative Testing",
        "current_version": None,
        "summary": (
            "Independent validation of Credit Risk Model per SR 11-7. Covers conceptual "
            "soundness, data quality, performance benchmarking, and regulatory compliance. "
            "Currently at Quantitative Testing stage. Completion unblocks the Approval Workflow."
        ),
        "artifacts": ["Validation Template v2", "Review Notes Draft", "Evidence Document", "Issue Log"],
        "activity": [
            {"text": "Stage advanced to Quantitative Testing", "time": "1h ago"},
            {"text": "Dataset A linked as evidence",           "time": "8h ago"},
            {"text": "Reviewer assigned: A. Mehta",           "time": "2d ago"},
        ],
        "stages": [
            {"name": "Submission & Scoping",  "status": "done"},
            {"name": "Documentation Review",  "status": "done"},
            {"name": "Quantitative Testing",  "status": "current"},
            {"name": "Finding Resolution",    "status": "pending"},
            {"name": "Validation Sign-off",   "status": "pending"},
        ],
    },

    "monitoring_workflow": {
        "id": "monitoring_workflow",
        "name": "Ongoing Monitoring Workflow",
        "type": WORKFLOW, "subtype": "Monitoring",
        "owner": "Model Monitoring Team", "owner_initials": "MM",
        "status": "Active", "risk": None,
        "stage": "Committee Submission", "family": None,
        "jurisdiction": None,
        "last_reviewed": "Apr 2026", "next_review": "Jul 2026",
        "workflow_state": "Committee Submission",
        "current_version": None,
        "summary": (
            "Recurring quarterly workflow: ingests performance metrics via NIMBUS integration, "
            "calculates PSI/KS/Gini, checks drift thresholds, generates the monitoring report, "
            "and submits to committee. Current cycle: Q1-2026 at Committee Submission stage."
        ),
        "artifacts": ["Monitoring Checklist", "Drift Report Template", "Threshold Evidence Form", "NIMBUS Config"],
        "activity": [
            {"text": "Q1-2026 monitoring report generated",  "time": "2d ago"},
            {"text": "PSI threshold checked — within limits","time": "3d ago"},
            {"text": "Owner confirmed for Q2 cycle",         "time": "1w ago"},
        ],
        "stages": [
            {"name": "Data Ingestion",       "status": "done"},
            {"name": "Metric Calculation",   "status": "done"},
            {"name": "Threshold Review",     "status": "done"},
            {"name": "Report Generation",    "status": "done"},
            {"name": "Committee Submission", "status": "current"},
        ],
    },

    "approval_workflow": {
        "id": "approval_workflow",
        "name": "Governance Approval Workflow",
        "type": WORKFLOW, "subtype": "Approval",
        "owner": "Model Risk Governance", "owner_initials": "MG",
        "status": "Not Started", "risk": None,
        "stage": "Validation Complete", "family": None,
        "jurisdiction": None,
        "last_reviewed": None, "next_review": None,
        "workflow_state": "Awaiting Validation Sign-off",
        "current_version": None,
        "summary": (
            "Final governance workflow: triggered only after Validation Sign-off. "
            "Covers committee review, senior approval, audit certification, and "
            "official model approval. Currently blocked — awaiting Validation Workflow completion."
        ),
        "artifacts": ["Approval Memo Template", "Committee Agenda", "Audit Trail", "Regulatory Submission Checklist"],
        "activity": [
            {"text": "Awaiting Validation Workflow completion (upstream blocker)", "time": "5d ago"},
            {"text": "Committee owner assigned: D. Patel",                         "time": "1w ago"},
            {"text": "Draft approval memo created",                                "time": "2w ago"},
        ],
        "stages": [
            {"name": "Validation Complete",  "status": "pending"},
            {"name": "Committee Review",     "status": "pending"},
            {"name": "Senior Approval",      "status": "pending"},
            {"name": "Audit Certification",  "status": "pending"},
            {"name": "Model Approved",       "status": "pending"},
        ],
    },
}

# LINKS registry (unchanged from v1)
LINKS = [
    {"source": "credit_risk_model", "target": "dataset_a",         "relType": "USES_DATASET",      "cardinality": "N:1",
     "notes": "Credit Risk Model consumes Dataset A as its primary training and scoring input. Any drift or quality issue in Dataset A directly degrades this model's outputs."},
    {"source": "credit_risk_model", "target": "feature_set",       "relType": "USES_FEATURES",     "cardinality": "N:1",
     "notes": "Credit Risk Model depends on Feature Set Credit v4. A feature definition change or deprecation breaks the model's feature contract and requires revalidation."},
    {"source": "credit_risk_model", "target": "policy_document",   "relType": "GOVERNED_BY",       "cardinality": "N:M",
     "notes": "MRM Policy v5.1 defines the validation standards and approval thresholds that govern this model. Status 'Under Review' adds governance uncertainty."},
    {"source": "credit_risk_model", "target": "validation_workflow","relType": "VALIDATED_THROUGH", "cardinality": "1:1",
     "notes": "One active validation workflow per model version. Concurrent validations of the same version are not permitted (1:1 constraint per SR 11-7)."},
    {"source": "credit_risk_model", "target": "monitoring_workflow","relType": "MONITORED_BY",      "cardinality": "1:1",
     "notes": "One monitoring workflow tracks this model's live performance. A model cannot be in production without an active monitoring workflow (SR 11-7 requirement)."},
    {"source": "loan_default_model","target": "dataset_a",         "relType": "USES_DATASET",      "cardinality": "N:1",
     "notes": "Loan Default Model shares Dataset A with Credit Risk Model — a shared upstream dependency. Dataset A degradation impacts both models simultaneously."},
    {"source": "loan_default_model","target": "feature_set",       "relType": "USES_FEATURES",     "cardinality": "N:1",
     "notes": "Both sibling models share Feature Set Credit v4. Feature changes require coordinated revalidation of both."},
    {"source": "loan_default_model","target": "credit_risk_model", "relType": "SIBLING_MODEL",     "cardinality": "N:M",
     "notes": "Both models are in the Credit Risk family, share upstream data and features, and their outputs are compared by governance for consistency."},
    {"source": "validation_workflow","target": "dataset_a",        "relType": "REQUIRES_DATA",     "cardinality": "N:M",
     "notes": "The validation workflow requires Dataset A as evidence for data quality and representativeness testing."},
    {"source": "validation_workflow","target": "policy_document",  "relType": "CHECKS_AGAINST",    "cardinality": "N:M",
     "notes": "Validation tests are executed against criteria in MRM Policy v5.1."},
    {"source": "validation_workflow","target": "feature_set",      "relType": "VALIDATES",         "cardinality": "1:N",
     "notes": "The validation workflow validates Feature Set Credit v4 as part of conceptual soundness review."},
    {"source": "validation_workflow","target": "approval_workflow", "relType": "FEEDS_INTO",        "cardinality": "1:1",
     "notes": "Approval Workflow has a hard dependency on Validation Sign-off. Sequential gate."},
    {"source": "monitoring_workflow","target": "monitoring_report", "relType": "GENERATES",         "cardinality": "1:N",
     "notes": "Each execution of the Monitoring Workflow generates one Monitoring Report."},
    {"source": "monitoring_report", "target": "credit_risk_model", "relType": "REPORTS_ON",        "cardinality": "N:1",
     "notes": "The monitoring report reports on the Credit Risk Model's live performance."},
    {"source": "approval_workflow", "target": "credit_risk_model", "relType": "APPROVAL_GATE",     "cardinality": "1:1",
     "notes": "The approval workflow is the final governance gate before the Credit Risk Model is officially approved."},
]

QUICK_ACCESS = [
    {"id": "credit_risk_model",   "label": "Credit Risk Model"},
    {"id": "loan_default_model",  "label": "Loan Default Model"},
    {"id": "validation_workflow", "label": "Validation Workflow"},
    {"id": "monitoring_workflow", "label": "Monitoring Workflow"},
    {"id": "approval_workflow",   "label": "Approval Workflow"},
    {"id": "dataset_a",           "label": "Dataset A"},
    {"id": "feature_set",         "label": "Feature Set"},
]

# ── UI helpers ─────────────────────────────────────────────────────────────────
def get_risk_color(risk: str) -> tuple:
    return {
        "High":   ("#fee2e2", "#991b1b"),
        "Medium": ("#fef3c7", "#92400e"),
        "Low":    ("#dcfce7", "#166534"),
    }.get(risk, ("#f1f5f9", "#64748b"))

def get_status_color(status: str) -> tuple:
    return {
        "Active":        ("#16a34a", "#dcfce7"),
        "In Progress":   ("#2563eb", "#dbeafe"),
        "Under Review":  ("#d97706", "#fef3c7"),
        "Published":     ("#0891b2", "#cffafe"),
        "Not Started":   ("#64748b", "#f1f5f9"),
    }.get(status, ("#64748b", "#f1f5f9"))

def get_rel_category_color(category: str) -> tuple:
    return {
        "lineage":    ("#dbeafe", "#1d4ed8"),
        "governance": ("#ede9fe", "#6d28d9"),
        "validation": ("#cffafe", "#0e7490"),
        "monitoring": ("#dcfce7", "#15803d"),
        "lifecycle":  ("#fef3c7", "#92400e"),
        "issue":      ("#fee2e2", "#991b1b"),
        "output":     ("#f0fdf4", "#166534"),
    }.get(category, ("#f1f5f9", "#64748b"))

# ── ATTRIBUTE_LIBRARY, TEMPLATE_CONFIGS, SECTION_RULES, etc. (preserved) ──────
ATTRIBUTE_LIBRARY = [
    {"field_name": "entity_id",          "display_name": "Entity ID",          "data_type": "Auto (prefix+counter)",  "section": "Preliminary",        "entity_types": ["All"],       "required": True,  "validation": "Unique, system-generated", "example": "MOD-001", "doc_placeholder": "{{entity_id}}"},
    {"field_name": "entity_name",        "display_name": "Name",               "data_type": "Text (100 chars)",        "section": "Preliminary",        "entity_types": ["All"],       "required": True,  "validation": "Max 100 chars",            "example": "Credit Risk Model", "doc_placeholder": "{{entity_name}}"},
    {"field_name": "owner",              "display_name": "Owner",              "data_type": "Association (user)",     "section": "Preliminary",        "entity_types": ["All"],       "required": True,  "validation": "Must be active user",      "example": "Risk Analytics Team", "doc_placeholder": "{{owner}}"},
    {"field_name": "status",             "display_name": "Status",             "data_type": "Single-select",          "section": "Preliminary",        "entity_types": ["All"],       "required": True,  "validation": "Active|In Progress|Closed|Archived|Under Review|Published", "example": "Active", "doc_placeholder": "{{status}}"},
    {"field_name": "workflow_state",     "display_name": "Workflow state",     "data_type": "Derived (system)",       "section": "Preliminary",        "entity_types": ["All"],       "required": False, "validation": "Read-only — mirrors workflow node", "example": "Quantitative Testing", "doc_placeholder": "{{workflow_state}}"},
    {"field_name": "template_type",      "display_name": "Template type",      "data_type": "Single-select (system)","section": "Preliminary",        "entity_types": ["All"],       "required": False, "validation": "Set at creation, immutable", "example": "Model", "doc_placeholder": "{{template_type}}"},
    {"field_name": "created_date",       "display_name": "Created date",       "data_type": "Date (system)",          "section": "Preliminary",        "entity_types": ["All"],       "required": False, "validation": "System timestamp, immutable", "example": "30 Apr 2026", "doc_placeholder": "{{created_date}}"},
    {"field_name": "model_type",         "display_name": "Model type",         "data_type": "Single-select",          "section": "Model Identification","entity_types": ["Model"],     "required": True,  "validation": "Statistical|ML|AI/GenAI|Vendor", "example": "Statistical", "doc_placeholder": "{{model_type}}"},
    {"field_name": "risk_tier",          "display_name": "Risk tier",          "data_type": "Single-select",          "section": "Model Identification","entity_types": ["Model"],     "required": True,  "validation": "T1 (Material)|T2|T3",      "example": "T1 (Material)", "doc_placeholder": "{{risk_tier}}"},
    {"field_name": "regulation",         "display_name": "Regulation",         "data_type": "Multi-select",           "section": "Governance",         "entity_types": ["Model"],     "required": False, "validation": "SR 11-7|PRA SS1/23|OSFI E-23|EU AI Act|NAIC", "example": "SR 11-7, OSFI E-23", "doc_placeholder": "{{regulation}}"},
    {"field_name": "business_unit",      "display_name": "Business unit",      "data_type": "Single-select",          "section": "General Information","entity_types": ["Model"],     "required": True,  "validation": "AWM|Retail|Commercial|Treasury|Risk", "example": "Risk Analytics", "doc_placeholder": "{{business_unit}}"},
    {"field_name": "region",             "display_name": "Region",             "data_type": "Conditional select",     "section": "General Information","entity_types": ["Model"],     "required": False, "validation": "Options change based on business_unit", "example": "India, Global", "doc_placeholder": "{{region}}"},
    {"field_name": "development_due_date","display_name": "Development due date","data_type": "Date",                "section": "General Information","entity_types": ["Model"],     "required": False, "validation": "Must be before validation_due_date", "example": "30 Sep 2025", "doc_placeholder": "{{development_due_date}}"},
    {"field_name": "validation_due_date","display_name": "Validation due date","data_type": "Date",                   "section": "General Information","entity_types": ["Model"],     "required": False, "validation": "Time-based automation trigger", "example": "31 Oct 2025", "doc_placeholder": "{{validation_due_date}}"},
    {"field_name": "derived_risk_score", "display_name": "Risk score",         "data_type": "Derived formula",        "section": "Hidden",             "entity_types": ["Model"],     "required": False, "validation": "base(risk)+upstream_deps×3+status_penalty+degraded×8. Capped 100.", "example": "91", "doc_placeholder": "{{derived_risk_score}}"},
    {"field_name": "model_family",       "display_name": "Model family",       "data_type": "Single-select",          "section": "Model Identification","entity_types": ["Model"],     "required": False, "validation": "Credit Risk|Fraud|Market Risk|ALM|Pricing", "example": "Credit Risk", "doc_placeholder": "{{model_family}}"},
    {"field_name": "intended_use",       "display_name": "Intended use",       "data_type": "Text extended (10k)",    "section": "General Information","entity_types": ["Model"],     "required": True,  "validation": "Max 10,000 characters", "example": "Credit risk scoring for retail portfolio", "doc_placeholder": "{{intended_use}}"},
    {"field_name": "financial_impact",   "display_name": "Financial impact",   "data_type": "Single-select",          "section": "Model Identification","entity_types": ["Model"],     "required": True,  "validation": "High|Medium|Low — drives risk_tier derivation", "example": "High", "doc_placeholder": "{{financial_impact}}"},
    {"field_name": "severity",           "display_name": "Severity",           "data_type": "Single-select",          "section": "Preliminary",        "entity_types": ["Finding"],   "required": True,  "validation": "Critical|Major|Minor", "example": "Critical", "doc_placeholder": "{{severity}}"},
    {"field_name": "finding_type",       "display_name": "Finding type",       "data_type": "Single-select",          "section": "Preliminary",        "entity_types": ["Finding"],   "required": True,  "validation": "Conceptual|Data|Performance|Documentation|Governance", "example": "Performance", "doc_placeholder": "{{finding_type}}"},
    {"field_name": "due_date",           "display_name": "Resolution due date","data_type": "Date",                   "section": "General",            "entity_types": ["Finding"],   "required": True,  "validation": "Triggers reminder automation at T-7 and T-1 days", "example": "15 May 2026", "doc_placeholder": "{{due_date}}"},
    {"field_name": "resolution_notes",   "display_name": "Resolution notes",   "data_type": "Text extended (10k)",    "section": "Descriptive",        "entity_types": ["Finding"],   "required": False, "validation": "Written by model owner on closure", "example": "Threshold recalibrated", "doc_placeholder": "{{resolution_notes}}"},
]

TEMPLATE_CONFIGS = {
    "Model": {
        "description": "Primary entity. Created when an Assessment determines final_model_det = Model.",
        "id_prefix": "MOD",
        "workflow": "Validation → Monitoring → Approval",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","workflow_state","template_type","created_date"],
        "sections": {
            "General Information":    ["business_unit","region","development_due_date","validation_due_date","intended_use"],
            "Model Identification":   ["model_type","risk_tier","model_family","financial_impact"],
            "Governance":             ["regulation"],
            "Hidden":                 ["derived_risk_score"],
        },
        "conditional_sections": {
            "EU AI Act Compliance":   "regulation contains 'EU AI Act'",
            "AI/ML Extended Fields":  "model_type in ('ML', 'AI/GenAI')",
        },
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{owner}}","{{risk_tier}}","{{model_type}}","{{regulation}}","{{validation_due_date}}","{{derived_risk_score}}","{{model_family}}","{{intended_use}}"],
    },
    "Assessment": {
        "description": "Identification questionnaire. Creates a Model, Non-model, or AI-model via workflow branch.",
        "id_prefix": "ASA",
        "workflow": "Identification → Decision → Registration",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","workflow_state","template_type"],
        "sections": {
            "Model Identification":   ["final_model_det","involves_ai"],
            "Business Context":       ["business_unit","financial_impact","intended_use"],
        },
        "conditional_sections": {"AI/ML Specific": "involves_ai = Yes"},
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{owner}}","{{final_model_det}}","{{involves_ai}}"],
    },
    "Finding": {
        "description": "Raised during Validation. Child of a Subprocess. Resolved by model owner.",
        "id_prefix": "FND",
        "workflow": "Raised → Open → Remediation → Closed",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","severity","finding_type","due_date"],
        "sections": {"Descriptive": ["resolution_notes"]},
        "conditional_sections": {},
        "doc_placeholders": ["{{entity_id}}","{{severity}}","{{finding_type}}","{{due_date}}","{{resolution_notes}}"],
    },
}

SECTION_RULES = {
    "Model": {
        "General Information": {
            "Registration": "manage", "Validation": "view", "Monitoring": "view", "Approved": "view",
        },
        "Model Identification": {
            "Registration": "manage", "Validation": "view", "Monitoring": "view", "Approved": "view",
        },
        "Governance": {
            "Registration": "view", "Validation": "manage", "Monitoring": "view", "Approved": "view",
        },
        "Validation Results": {
            "Registration": "hidden", "Validation": "manage", "Monitoring": "view", "Approved": "view",
        },
        "Monitoring Metrics": {
            "Registration": "hidden", "Validation": "hidden", "Monitoring": "manage", "Approved": "view",
        },
        "Hidden": {
            "Registration": "hidden", "Validation": "hidden", "Monitoring": "hidden", "Approved": "hidden",
        },
    },
}

DOCUMENT_TEMPLATES = [
    {
        "name": "Model Lifecycle Report", "entity_type": "Model", "format": "Word (.docx)",
        "description": "Full model lifecycle summary for committee distribution.",
        "placeholders": [
            {"placeholder": "{{entity_id}}",            "maps_to": "entity_id",            "display_name": "Entity ID"},
            {"placeholder": "{{entity_name}}",          "maps_to": "entity_name",          "display_name": "Name"},
            {"placeholder": "{{owner}}",                "maps_to": "owner",                "display_name": "Owner"},
            {"placeholder": "{{model_type}}",           "maps_to": "model_type",           "display_name": "Model type"},
            {"placeholder": "{{risk_tier}}",            "maps_to": "risk_tier",            "display_name": "Risk tier"},
            {"placeholder": "{{regulation}}",           "maps_to": "regulation",           "display_name": "Regulation"},
            {"placeholder": "{{derived_risk_score}}",   "maps_to": "derived_risk_score",   "display_name": "Risk score"},
            {"placeholder": "{{workflow_state}}",       "maps_to": "workflow_state",       "display_name": "Current stage"},
            {"placeholder": "{{intended_use}}",         "maps_to": "intended_use",         "display_name": "Intended use"},
            {"placeholder": "{{financial_impact}}",     "maps_to": "financial_impact",     "display_name": "Financial impact"},
        ],
    },
]

AUTOMATION_RULES = [
    {"name": "Notify validator on model registration",  "trigger_type": "Entity transition", "trigger_condition": "Model moves to Registration stage",          "action": "Send email to validator group assigned to this model", "entity_type": "Model"},
    {"name": "Create validation subprocess",            "trigger_type": "Entity transition", "trigger_condition": "Model moves to Validation stage",            "action": "Auto-create a Subprocess entity (type=Validation) linked to this model", "entity_type": "Model"},
    {"name": "Validation due date reminder",            "trigger_type": "Time-based",        "trigger_condition": "Today = validation_due_date - 7 days",       "action": "Send email reminder to owner and validator", "entity_type": "Model"},
    {"name": "Finding due date alert",                  "trigger_type": "Time-based",        "trigger_condition": "Today = finding.due_date - 1 day",           "action": "Send urgent alert to model owner and governance team", "entity_type": "Finding"},
    {"name": "Unlock approval workflow",                "trigger_type": "Entity transition", "trigger_condition": "Validation Workflow reaches Validation Sign-off","action": "Set Approval Workflow first stage from pending → current; status → In Progress", "entity_type": "Subprocess"},
    {"name": "Auto-generate monitoring report",         "trigger_type": "Time-based",        "trigger_condition": "Today = next_monitoring_date (quarterly)",   "action": "Generate Monitoring Report document and notify committee", "entity_type": "Subprocess"},
    {"name": "Risk tier auto-derive",                   "trigger_type": "Attribute updated", "trigger_condition": "financial_impact attribute changes value",   "action": "Recalculate risk_tier using derivation formula", "entity_type": "Model"},
    {"name": "Archive on retirement",                   "trigger_type": "Entity transition", "trigger_condition": "Model reaches Retired stage",               "action": "Set status = Archived; close all open subprocesses; notify governance", "entity_type": "Model"},
]

def get_risk_score(node_id: str) -> int:
    """Derived risk score 0-100."""
    from graph_engine import upstream_trace
    node = NODES.get(node_id)
    if not node:
        return 0
    base     = _RISK_BASE.get(node.get("risk", ""), 0)
    status_p = _STATUS_PEN.get(node.get("status", ""), 0)
    up       = upstream_trace(node_id)
    up_p     = len(up) * 3
    degraded = [u for u in up if NODES.get(u, {}).get("status") in ("Under Review", "Not Started")]
    deg_p    = len(degraded) * 8
    return min(100, base + status_p + up_p + deg_p)
