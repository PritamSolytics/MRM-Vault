"""
data_model.py — MRM Vault Data Model
Pure data and helper functions. No Streamlit, no DOM access.

Sources: All 10 KT session transcripts (Vault_KT.docx through Vault_KT_7.docx,
         Internal_KT_Vault_Implementation_Architecture.docx,
         MRM_Vault_Onboarding.docx, Document_Template.docx)

Design principles (from KT sessions):
  1. One master Entity Sheet — every model, assessment, subprocess, finding,
     use case, query is a row. Templates define which attributes (columns) each
     entity type has. Not all entities have all attributes.
  2. Typed, directed edges — each link has a relType from REL_TYPES,
     a semantic category, cardinality, and business-reason notes.
  3. Workflow state machine — STAGE_TRANSITIONS defines legal forward-only
     progressions per workflow subtype.
  4. Attribute library — NODE_SCHEMA defines legal subtypes; attributes have
     both a field name (used in formulas and document templates) and a
     display_name (shown on UI).
  5. Risk score derivation — computeRiskScore uses base risk + upstream
     dependency count + status penalties (simplified version of Vault's
     configurable derivation engine).
"""

ENTITY   = "Entity"
WORKFLOW = "Workflow"

# ── Relationship type registry ─────────────────────────────────────────────────
# category: lineage | governance | validation | monitoring
# directed: True means source→target is semantically significant
REL_TYPES = {
    "USES_DATASET":      {"label": "uses dataset",       "category": "lineage",     "directed": True},
    "USES_FEATURES":     {"label": "uses features",      "category": "lineage",     "directed": True},
    "FEEDS_INTO":        {"label": "feeds into",         "category": "lineage",     "directed": True},
    "SIBLING_MODEL":     {"label": "sibling model",      "category": "lineage",     "directed": False},
    "GOVERNED_BY":       {"label": "governed by",        "category": "governance",  "directed": True},
    "CHECKS_AGAINST":    {"label": "checks against",     "category": "governance",  "directed": True},
    "APPROVAL_GATE":     {"label": "approval gate",      "category": "governance",  "directed": True},
    "VALIDATED_THROUGH": {"label": "validated through",  "category": "validation",  "directed": True},
    "VALIDATES":         {"label": "validates",          "category": "validation",  "directed": True},
    "REQUIRES_DATA":     {"label": "requires data",      "category": "validation",  "directed": True},
    "MONITORED_BY":      {"label": "monitored by",       "category": "monitoring",  "directed": True},
    "GENERATES":         {"label": "generates",          "category": "monitoring",  "directed": True},
    "REPORTS_ON":        {"label": "reports on",         "category": "monitoring",  "directed": True},
}

# ── Entity subtype schema (from KT sessions) ──────────────────────────────────
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

# ── Risk score weights ────────────────────────────────────────────────────────
_RISK_BASE    = {"High": 80, "Medium": 50, "Low": 20}
_STATUS_PEN   = {"Under Review": 15, "In Progress": 10, "Not Started": 20,
                  "Active": 0, "Published": 0}

# ── Node inventory ─────────────────────────────────────────────────────────────
NODES = {

    # ── ENTITIES ──────────────────────────────────────────────────────────────

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
            "intended_use":         {"display_name": "Intended use",         "data_type": "Text extended", "section": "General Information"},
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
        "summary": (
            "Gradient-boosted tree (XGBoost) predicting 12-month probability of default "
            "across retail lending. Sibling to Credit Risk Model — both share Dataset A "
            "and Feature Set Credit v4. Dataset A degradation impacts both models simultaneously. "
            "Bias testing completed; feature importance reviewed."
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
        "summary": (
            "Core customer credit bureau dataset: 24 months of transactional history, "
            "delinquency records, credit utilisation. Shared upstream dependency for "
            "both Credit Risk Model and Loan Default Model. Quality degradation here "
            "triggers a two-model impact — highest impact node in current inventory. "
            "Completeness 99.4% per Q1-2026 quality report."
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
        "summary": (
            "Enterprise MRM policy defining governance controls, model tiering criteria, "
            "validation standards, and approval thresholds. Aligned with SR 11-7 and "
            "PRA SS1/23. Currently under annual review — status 'Under Review' adds "
            "governance uncertainty to all governed models and their downstream workflows. "
            "Version 5.1 circulated for CRO comment."
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
        "summary": (
            "47-variable feature set for credit scoring and default prediction, "
            "derived from Dataset A via transformation pipeline. Both Credit Risk Model "
            "and Loan Default Model depend on this — a feature contract change requires "
            "coordinated revalidation of both sibling models. 3 features recently "
            "deprecated due to low importance scores."
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
        "summary": (
            "Quarterly monitoring report for Credit Risk Model. Contains PSI, KS statistic, "
            "Gini trend, input drift analysis, output distribution, and threshold breach summary. "
            "Published to model committee. All thresholds within limits — no breaches this quarter. "
            "Generated automatically by the Monitoring Workflow via NIMBUS integration."
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

    # ── WORKFLOWS ─────────────────────────────────────────────────────────────

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
        "summary": (
            "Independent validation of Credit Risk Model per SR 11-7. Covers conceptual "
            "soundness, data quality, performance benchmarking, and regulatory compliance. "
            "Currently at Quantitative Testing stage. Completion unblocks the Approval "
            "Workflow — a sequential governance gate. Reviewer: A. Mehta (Sr Validator)."
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
        "summary": (
            "Final governance workflow: triggered only after Validation Sign-off. "
            "Covers committee review, senior approval, audit certification, and "
            "official model approval. Currently blocked — awaiting Validation Workflow "
            "completion. Committee owner: D. Patel."
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

# ── Link registry ──────────────────────────────────────────────────────────────
# source, target, relType, cardinality, notes
LINKS = [
    {
        "source": "credit_risk_model", "target": "dataset_a",
        "relType": "USES_DATASET", "cardinality": "N:1",
        "notes": ("Credit Risk Model consumes Dataset A as its primary training and scoring "
                  "input. Any drift or quality issue in Dataset A directly degrades this model's outputs."),
    },
    {
        "source": "credit_risk_model", "target": "feature_set",
        "relType": "USES_FEATURES", "cardinality": "N:1",
        "notes": ("Credit Risk Model depends on Feature Set Credit v4. A feature definition "
                  "change or deprecation breaks the model's feature contract and requires revalidation."),
    },
    {
        "source": "credit_risk_model", "target": "policy_document",
        "relType": "GOVERNED_BY", "cardinality": "N:M",
        "notes": ("MRM Policy v5.1 defines the validation standards and approval thresholds "
                  "that govern this model. Status 'Under Review' adds governance uncertainty."),
    },
    {
        "source": "credit_risk_model", "target": "validation_workflow",
        "relType": "VALIDATED_THROUGH", "cardinality": "1:1",
        "notes": ("One active validation workflow per model version. Concurrent validations "
                  "of the same version are not permitted (1:1 constraint per SR 11-7)."),
    },
    {
        "source": "credit_risk_model", "target": "monitoring_workflow",
        "relType": "MONITORED_BY", "cardinality": "1:1",
        "notes": ("One monitoring workflow tracks this model's live performance. A model "
                  "cannot be in production without an active monitoring workflow (SR 11-7 requirement)."),
    },
    {
        "source": "loan_default_model", "target": "dataset_a",
        "relType": "USES_DATASET", "cardinality": "N:1",
        "notes": ("Loan Default Model shares Dataset A with Credit Risk Model — a shared "
                  "upstream dependency. Dataset A degradation impacts both models simultaneously."),
    },
    {
        "source": "loan_default_model", "target": "feature_set",
        "relType": "USES_FEATURES", "cardinality": "N:1",
        "notes": ("Both sibling models share Feature Set Credit v4. Feature changes require "
                  "coordinated revalidation of both."),
    },
    {
        "source": "loan_default_model", "target": "credit_risk_model",
        "relType": "SIBLING_MODEL", "cardinality": "N:M",
        "notes": ("Both models are in the Credit Risk family, share upstream data and features, "
                  "and their outputs are compared by governance for consistency."),
    },
    {
        "source": "validation_workflow", "target": "dataset_a",
        "relType": "REQUIRES_DATA", "cardinality": "N:M",
        "notes": ("The validation workflow requires Dataset A as evidence for data quality and "
                  "representativeness testing. Dataset is inspected, not consumed to produce outputs."),
    },
    {
        "source": "validation_workflow", "target": "policy_document",
        "relType": "CHECKS_AGAINST", "cardinality": "N:M",
        "notes": ("Validation tests are executed against criteria in MRM Policy v5.1. If the "
                  "policy is updated mid-validation, affected test cases must be re-checked."),
    },
    {
        "source": "validation_workflow", "target": "feature_set",
        "relType": "VALIDATES", "cardinality": "1:N",
        "notes": ("The validation workflow validates Feature Set Credit v4 as part of conceptual "
                  "soundness review — testing feature stability, coverage, and alignment with the model."),
    },
    {
        "source": "validation_workflow", "target": "approval_workflow",
        "relType": "FEEDS_INTO", "cardinality": "1:1",
        "notes": ("Approval Workflow has a hard dependency on Validation Sign-off. Sequential "
                  "gate — approval cannot start until validation reaches its final stage."),
    },
    {
        "source": "monitoring_workflow", "target": "monitoring_report",
        "relType": "GENERATES", "cardinality": "1:N",
        "notes": ("Each execution of the Monitoring Workflow generates one Monitoring Report. "
                  "Over time this creates a quarterly report history traceable to the same workflow."),
    },
    {
        "source": "monitoring_report", "target": "credit_risk_model",
        "relType": "REPORTS_ON", "cardinality": "N:1",
        "notes": ("The monitoring report is a read-only observability artefact. It reports on "
                  "the Credit Risk Model's live performance and produces evidence for committee review."),
    },
    {
        "source": "approval_workflow", "target": "credit_risk_model",
        "relType": "APPROVAL_GATE", "cardinality": "1:1",
        "notes": ("The approval workflow is the final governance gate before the Credit Risk Model "
                  "is officially approved for use. Completion updates model status to Approved."),
    },
]

# ── Quick access shortcuts ─────────────────────────────────────────────────────
QUICK_ACCESS = [
    {"id": "credit_risk_model",   "label": "Credit Risk Model"},
    {"id": "loan_default_model",  "label": "Loan Default Model"},
    {"id": "validation_workflow", "label": "Validation Workflow"},
    {"id": "monitoring_workflow", "label": "Monitoring Workflow"},
    {"id": "approval_workflow",   "label": "Approval Workflow"},
    {"id": "dataset_a",           "label": "Dataset A"},
    {"id": "feature_set",         "label": "Feature Set"},
]


# ── UI helper functions ────────────────────────────────────────────────────────
def get_risk_color(risk: str) -> tuple:
    """Return (background, text) color for a risk level."""
    return {
        "High":   ("#fee2e2", "#991b1b"),
        "Medium": ("#fef3c7", "#92400e"),
        "Low":    ("#dcfce7", "#166534"),
    }.get(risk, ("#f1f5f9", "#64748b"))


def get_status_color(status: str) -> tuple:
    """Return (foreground, background) color for a status value."""
    return {
        "Active":        ("#16a34a", "#dcfce7"),
        "In Progress":   ("#2563eb", "#dbeafe"),
        "Under Review":  ("#d97706", "#fef3c7"),
        "Published":     ("#0891b2", "#cffafe"),
        "Not Started":   ("#64748b", "#f1f5f9"),
    }.get(status, ("#64748b", "#f1f5f9"))


def get_rel_category_color(category: str) -> tuple:
    """Return (background, text) for a relationship category."""
    return {
        "lineage":    ("#dbeafe", "#1d4ed8"),
        "governance": ("#ede9fe", "#6d28d9"),
        "validation": ("#cffafe", "#0e7490"),
        "monitoring": ("#dcfce7", "#15803d"),
    }.get(category, ("#f1f5f9", "#64748b"))


# ══════════════════════════════════════════════════════════════════════════════
# MASTER TEMPLATE — attribute library, template configs, section rules
#
# This mirrors what an admin configures in MRM Vault's Entity Management:
#   1. ATTRIBUTE_LIBRARY  — all column definitions (field name, display name,
#                           data type, validation, section, visibility rules)
#   2. TEMPLATE_CONFIGS   — which attributes each template type exposes, and
#                           in which section (preliminary vs descriptive)
#   3. SECTION_RULES      — per-section visibility and edit permissions at each
#                           workflow stage (manage / view / hidden)
#   4. DOCUMENT_TEMPLATES — Word/PDF templates with {{placeholder}} mapping to
#                           attribute field names (not display names)
#   5. AUTOMATION_RULES   — trigger → action definitions
# ══════════════════════════════════════════════════════════════════════════════

ATTRIBUTE_LIBRARY = [
    # ── Common (present on all entity types) ──────────────────────────────────
    {
        "field_name": "entity_id",          "display_name": "Entity ID",
        "data_type": "Auto (prefix+counter)","section": "Preliminary",
        "entity_types": ["All"],            "required": True,
        "validation": "Unique, system-generated",
        "example": "MOD-001, ASA-012, VLD-003",
        "doc_placeholder": "{{entity_id}}",
    },
    {
        "field_name": "entity_name",        "display_name": "Name",
        "data_type": "Text (100 chars)",    "section": "Preliminary",
        "entity_types": ["All"],            "required": True,
        "validation": "Max 100 characters",
        "example": "Credit Risk Model",
        "doc_placeholder": "{{entity_name}}",
    },
    {
        "field_name": "owner",              "display_name": "Owner",
        "data_type": "Association (user)",  "section": "Preliminary",
        "entity_types": ["All"],            "required": True,
        "validation": "Must be active user in system",
        "example": "Risk Analytics Team",
        "doc_placeholder": "{{owner}}",
    },
    {
        "field_name": "status",             "display_name": "Status",
        "data_type": "Single-select",       "section": "Preliminary",
        "entity_types": ["All"],            "required": True,
        "validation": "Active | In Progress | Closed | Archived | Under Review | Published",
        "example": "Active",
        "doc_placeholder": "{{status}}",
    },
    {
        "field_name": "workflow_state",     "display_name": "Workflow state",
        "data_type": "Derived (system)",    "section": "Preliminary",
        "entity_types": ["All"],            "required": False,
        "validation": "Read-only — mirrors current workflow node name",
        "example": "Quantitative Testing",
        "doc_placeholder": "{{workflow_state}}",
    },
    {
        "field_name": "template_type",      "display_name": "Template type",
        "data_type": "Single-select (system)", "section": "Preliminary",
        "entity_types": ["All"],            "required": False,
        "validation": "Set at creation, immutable",
        "example": "Model",
        "doc_placeholder": "{{template_type}}",
    },
    {
        "field_name": "created_date",       "display_name": "Created date",
        "data_type": "Date (system)",       "section": "Preliminary",
        "entity_types": ["All"],            "required": False,
        "validation": "System timestamp, immutable",
        "example": "30 Apr 2026",
        "doc_placeholder": "{{created_date}}",
    },
    # ── Model-specific ────────────────────────────────────────────────────────
    {
        "field_name": "model_type",         "display_name": "Model type",
        "data_type": "Single-select",       "section": "Model Identification",
        "entity_types": ["Model"],          "required": True,
        "validation": "Statistical | ML | AI/GenAI | Vendor",
        "example": "Statistical",
        "doc_placeholder": "{{model_type}}",
    },
    {
        "field_name": "risk_tier",          "display_name": "Risk tier",
        "data_type": "Single-select",       "section": "Model Identification",
        "entity_types": ["Model"],          "required": True,
        "validation": "T1 (Material) | T2 | T3",
        "example": "T1 (Material)",
        "doc_placeholder": "{{risk_tier}}",
    },
    {
        "field_name": "regulation",         "display_name": "Regulation",
        "data_type": "Multi-select",        "section": "Governance",
        "entity_types": ["Model"],          "required": False,
        "validation": "SR 11-7 | PRA SS1/23 | OSFI E-23 | EU AI Act | NAIC",
        "example": "SR 11-7, OSFI E-23",
        "doc_placeholder": "{{regulation}}",
    },
    {
        "field_name": "business_unit",      "display_name": "Business unit",
        "data_type": "Single-select",       "section": "General Information",
        "entity_types": ["Model"],          "required": True,
        "validation": "AWM | Retail | Commercial | Treasury | Risk",
        "example": "Risk Analytics",
        "doc_placeholder": "{{business_unit}}",
    },
    {
        "field_name": "region",             "display_name": "Region",
        "data_type": "Conditional select",  "section": "General Information",
        "entity_types": ["Model"],          "required": False,
        "validation": "Options change based on business_unit value",
        "example": "India, Global",
        "doc_placeholder": "{{region}}",
    },
    {
        "field_name": "development_due_date","display_name": "Development due date",
        "data_type": "Date",               "section": "General Information",
        "entity_types": ["Model"],         "required": False,
        "validation": "Must be before validation_due_date",
        "example": "30 Sep 2025",
        "doc_placeholder": "{{development_due_date}}",
    },
    {
        "field_name": "validation_due_date","display_name": "Validation due date",
        "data_type": "Date",               "section": "General Information",
        "entity_types": ["Model"],         "required": False,
        "validation": "Time-based automation trigger",
        "example": "31 Oct 2025",
        "doc_placeholder": "{{validation_due_date}}",
    },
    {
        "field_name": "derived_risk_score", "display_name": "Risk score",
        "data_type": "Derived formula",    "section": "Hidden",
        "entity_types": ["Model"],         "required": False,
        "validation": "base(risk) + upstream_deps×3 + status_penalty + degraded×8. Capped 100.",
        "example": "91",
        "doc_placeholder": "{{derived_risk_score}}",
    },
    {
        "field_name": "model_family",       "display_name": "Model family",
        "data_type": "Single-select",       "section": "Model Identification",
        "entity_types": ["Model"],          "required": False,
        "validation": "Credit Risk | Fraud | Market Risk | ALM | Pricing",
        "example": "Credit Risk",
        "doc_placeholder": "{{model_family}}",
    },
    {
        "field_name": "intended_use",       "display_name": "Intended use",
        "data_type": "Text extended (10k)", "section": "General Information",
        "entity_types": ["Model"],          "required": True,
        "validation": "Max 10,000 characters",
        "example": "Credit risk scoring for retail portfolio",
        "doc_placeholder": "{{intended_use}}",
    },
    {
        "field_name": "financial_impact",   "display_name": "Financial impact",
        "data_type": "Single-select",       "section": "Model Identification",
        "entity_types": ["Model"],          "required": True,
        "validation": "High | Medium | Low — drives risk_tier derivation",
        "example": "High",
        "doc_placeholder": "{{financial_impact}}",
    },
    # ── Assessment-specific ───────────────────────────────────────────────────
    {
        "field_name": "final_model_det",    "display_name": "Final model determination",
        "data_type": "Single-select",       "section": "Model Identification",
        "entity_types": ["Assessment"],     "required": True,
        "validation": "Model | Non-model | AI-model — drives workflow branch",
        "example": "Model",
        "doc_placeholder": "{{final_model_det}}",
    },
    {
        "field_name": "involves_ai",        "display_name": "Involves AI/ML",
        "data_type": "Single-select",       "section": "Model Identification",
        "entity_types": ["Assessment"],     "required": True,
        "validation": "Yes | No — shows AI-specific conditional sections when Yes",
        "example": "No",
        "doc_placeholder": "{{involves_ai}}",
    },
    {
        "field_name": "linked_model_id",    "display_name": "Linked model",
        "data_type": "Association",         "section": "Preliminary",
        "entity_types": ["Assessment"],     "required": False,
        "validation": "Populated after assessment completes and model is created",
        "example": "MOD-001",
        "doc_placeholder": "{{linked_model_id}}",
    },
    # ── Finding-specific ──────────────────────────────────────────────────────
    {
        "field_name": "severity",           "display_name": "Severity",
        "data_type": "Single-select",       "section": "Preliminary",
        "entity_types": ["Finding"],        "required": True,
        "validation": "Critical | Major | Minor",
        "example": "Critical",
        "doc_placeholder": "{{severity}}",
    },
    {
        "field_name": "finding_type",       "display_name": "Finding type",
        "data_type": "Single-select",       "section": "Preliminary",
        "entity_types": ["Finding"],        "required": True,
        "validation": "Conceptual | Data | Performance | Documentation | Governance",
        "example": "Performance",
        "doc_placeholder": "{{finding_type}}",
    },
    {
        "field_name": "linked_validation",  "display_name": "Linked validation",
        "data_type": "Association",         "section": "Preliminary",
        "entity_types": ["Finding"],        "required": True,
        "validation": "Must reference a Subprocess entity of type Validation",
        "example": "VLD-003",
        "doc_placeholder": "{{linked_validation}}",
    },
    {
        "field_name": "due_date",           "display_name": "Resolution due date",
        "data_type": "Date",               "section": "General",
        "entity_types": ["Finding"],        "required": True,
        "validation": "Triggers reminder automation at T-7 and T-1 days",
        "example": "15 May 2026",
        "doc_placeholder": "{{due_date}}",
    },
    {
        "field_name": "resolution_notes",   "display_name": "Resolution notes",
        "data_type": "Text extended (10k)", "section": "Descriptive",
        "entity_types": ["Finding"],        "required": False,
        "validation": "Written by model owner on closure",
        "example": "Threshold recalibrated — PSI reduced to 0.04",
        "doc_placeholder": "{{resolution_notes}}",
    },
    # ── Subprocess-specific ───────────────────────────────────────────────────
    {
        "field_name": "subprocess_type",    "display_name": "Subprocess type",
        "data_type": "Single-select",       "section": "Preliminary",
        "entity_types": ["Subprocess"],     "required": True,
        "validation": "Validation | Annual Review | Monitoring | Retirement | Change | Attestation",
        "example": "Validation",
        "doc_placeholder": "{{subprocess_type}}",
    },
    {
        "field_name": "parent_model_id",    "display_name": "Parent model",
        "data_type": "Association",         "section": "Preliminary",
        "entity_types": ["Subprocess"],     "required": True,
        "validation": "Must reference a Model entity",
        "example": "MOD-001",
        "doc_placeholder": "{{parent_model_id}}",
    },
    {
        "field_name": "validator_assigned", "display_name": "Assigned validator",
        "data_type": "Association (user)",  "section": "Preliminary",
        "entity_types": ["Subprocess"],     "required": False,
        "validation": "Must be in Independent Validation group",
        "example": "A. Mehta",
        "doc_placeholder": "{{validator_assigned}}",
    },
    {
        "field_name": "sign_off_status",    "display_name": "Sign-off status",
        "data_type": "Single-select",       "section": "Descriptive",
        "entity_types": ["Subprocess"],     "required": False,
        "validation": "Signed off | Conditional | Rejected | Pending",
        "example": "Pending",
        "doc_placeholder": "{{sign_off_status}}",
    },
]

# ── Template configurations ────────────────────────────────────────────────────
# Each template type specifies which attributes appear in which section,
# and which workflow is attached by default.
TEMPLATE_CONFIGS = {
    "Model": {
        "description": "Primary entity. Created when an Assessment determines final_model_det = Model.",
        "id_prefix": "MOD",
        "workflow": "Validation → Monitoring → Approval",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","workflow_state",
                              "template_type","created_date"],
        "sections": {
            "General Information":    ["business_unit","region","development_due_date",
                                       "validation_due_date","intended_use"],
            "Model Identification":   ["model_type","risk_tier","model_family",
                                       "financial_impact","regulation"],
            "Governance":             ["regulation"],
            "Hidden":                 ["derived_risk_score"],
        },
        "conditional_sections": {
            "EU AI Act Compliance":   "regulation contains 'EU AI Act'",
            "AI/ML Extended Fields":  "model_type in ('ML', 'AI/GenAI')",
        },
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{owner}}","{{risk_tier}}",
                             "{{model_type}}","{{regulation}}","{{validation_due_date}}",
                             "{{derived_risk_score}}","{{model_family}}","{{intended_use}}"],
    },
    "Assessment": {
        "description": "Identification questionnaire. Creates a Model, Non-model, or AI-model via workflow branch.",
        "id_prefix": "ASA",
        "workflow": "Identification → Decision → Registration",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","workflow_state",
                              "template_type","linked_model_id"],
        "sections": {
            "Model Identification":   ["final_model_det","involves_ai"],
            "Business Context":       ["business_unit","financial_impact","intended_use"],
            "Conditional — AI":       ["model_type"],
        },
        "conditional_sections": {
            "AI/ML Specific":         "involves_ai = Yes",
            "Vendor Model":           "involves vendor model = Yes",
        },
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{owner}}",
                             "{{final_model_det}}","{{involves_ai}}","{{linked_model_id}}"],
    },
    "Subprocess": {
        "description": "Child of a Model. Types: Validation, Annual Review, Monitoring, Retirement, Change, Attestation.",
        "id_prefix": "VLD / MON / CHG",
        "workflow": "Depends on subprocess_type — see STAGE_TRANSITIONS",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","workflow_state",
                              "subprocess_type","parent_model_id","validator_assigned"],
        "sections": {
            "General":                ["val_start_date","val_end_date"],
            "Descriptive":            ["sign_off_status"],
        },
        "conditional_sections": {
            "Quantitative Testing":   "subprocess_type = Validation AND stage = Quantitative Testing",
        },
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{parent_model_id}}",
                             "{{validator_assigned}}","{{sign_off_status}}","{{subprocess_type}}"],
    },
    "Finding": {
        "description": "Raised during Validation. Child of a Subprocess. Resolved by model owner.",
        "id_prefix": "FND",
        "workflow": "Raised → Open → Remediation → Closed",
        "preliminary_attrs": ["entity_id","entity_name","owner","status","severity",
                              "finding_type","linked_validation","due_date"],
        "sections": {
            "Descriptive":            ["resolution_notes","closure_evidence"],
        },
        "conditional_sections": {},
        "doc_placeholders": ["{{entity_id}}","{{severity}}","{{finding_type}}",
                             "{{linked_validation}}","{{due_date}}","{{resolution_notes}}"],
    },
    "Use Case": {
        "description": "Documents why a model exists. One use case can be linked to many models.",
        "id_prefix": "UC",
        "workflow": "Registration → Active",
        "preliminary_attrs": ["entity_id","entity_name","owner","status"],
        "sections": {
            "Descriptive":            ["use_case_desc","linked_models"],
        },
        "conditional_sections": {},
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{use_case_desc}}","{{linked_models}}"],
    },
    "Query": {
        "description": "Tracks justification queries raised against any model.",
        "id_prefix": "QRY",
        "workflow": "Raised → In Review → Resolved",
        "preliminary_attrs": ["entity_id","entity_name","owner","status"],
        "sections": {
            "Descriptive":            ["query_text","raised_by","query_resolution"],
        },
        "conditional_sections": {},
        "doc_placeholders": ["{{entity_id}}","{{entity_name}}","{{query_text}}","{{query_resolution}}"],
    },
    "Access Request": {
        "description": "Permission proposal for accessing a model or dataset.",
        "id_prefix": "AR",
        "workflow": "Submitted → Approved / Rejected",
        "preliminary_attrs": ["entity_id","entity_name","owner","status"],
        "sections": {
            "Descriptive":            ["access_scope","justification","approved_by"],
        },
        "conditional_sections": {},
        "doc_placeholders": ["{{entity_id}}","{{access_scope}}","{{justification}}","{{approved_by}}"],
    },
}

# ── Section-level permission rules (per workflow stage) ────────────────────────
# manage = editable, view = read-only, hidden = not visible
SECTION_RULES = {
    "Model": {
        "General Information": {
            "Registration":  "manage",
            "Validation":    "view",
            "Monitoring":    "view",
            "Approved":      "view",
        },
        "Model Identification": {
            "Registration":  "manage",
            "Validation":    "view",
            "Monitoring":    "view",
            "Approved":      "view",
        },
        "Governance": {
            "Registration":  "view",
            "Validation":    "manage",
            "Monitoring":    "view",
            "Approved":      "view",
        },
        "Validation Results": {
            "Registration":  "hidden",
            "Validation":    "manage",
            "Monitoring":    "view",
            "Approved":      "view",
        },
        "Monitoring Metrics": {
            "Registration":  "hidden",
            "Validation":    "hidden",
            "Monitoring":    "manage",
            "Approved":      "view",
        },
        "Hidden": {
            "Registration":  "hidden",
            "Validation":    "hidden",
            "Monitoring":    "hidden",
            "Approved":      "hidden",
        },
    },
}

# ── Document template mapping ──────────────────────────────────────────────────
# Placeholder key = attribute field_name (NOT display_name)
# This is the exact rule from KT sessions: Word template uses {{field_name}}
DOCUMENT_TEMPLATES = [
    {
        "name": "Model Lifecycle Report",
        "entity_type": "Model",
        "format": "Word (.docx)",
        "description": "Full model lifecycle summary for committee distribution.",
        "placeholders": [
            {"placeholder": "{{entity_id}}",            "maps_to": "entity_id",            "display_name": "Entity ID"},
            {"placeholder": "{{entity_name}}",          "maps_to": "entity_name",          "display_name": "Name"},
            {"placeholder": "{{owner}}",                "maps_to": "owner",                "display_name": "Owner"},
            {"placeholder": "{{model_type}}",           "maps_to": "model_type",           "display_name": "Model type"},
            {"placeholder": "{{risk_tier}}",            "maps_to": "risk_tier",            "display_name": "Risk tier"},
            {"placeholder": "{{regulation}}",           "maps_to": "regulation",           "display_name": "Regulation"},
            {"placeholder": "{{development_due_date}}", "maps_to": "development_due_date", "display_name": "Dev due date"},
            {"placeholder": "{{validation_due_date}}",  "maps_to": "validation_due_date",  "display_name": "Val due date"},
            {"placeholder": "{{derived_risk_score}}",   "maps_to": "derived_risk_score",   "display_name": "Risk score"},
            {"placeholder": "{{workflow_state}}",       "maps_to": "workflow_state",       "display_name": "Current stage"},
            {"placeholder": "{{intended_use}}",         "maps_to": "intended_use",         "display_name": "Intended use"},
            {"placeholder": "{{financial_impact}}",     "maps_to": "financial_impact",     "display_name": "Financial impact"},
        ],
    },
    {
        "name": "Validation Sign-off Certificate",
        "entity_type": "Subprocess",
        "format": "PDF",
        "description": "Formal sign-off document generated at Validation Sign-off stage.",
        "placeholders": [
            {"placeholder": "{{entity_id}}",            "maps_to": "entity_id",            "display_name": "Entity ID"},
            {"placeholder": "{{parent_model_id}}",      "maps_to": "parent_model_id",      "display_name": "Parent model"},
            {"placeholder": "{{validator_assigned}}",   "maps_to": "validator_assigned",   "display_name": "Validator"},
            {"placeholder": "{{sign_off_status}}",      "maps_to": "sign_off_status",      "display_name": "Sign-off status"},
            {"placeholder": "{{subprocess_type}}",      "maps_to": "subprocess_type",      "display_name": "Type"},
            {"placeholder": "{{workflow_state}}",       "maps_to": "workflow_state",       "display_name": "Current stage"},
        ],
    },
    {
        "name": "Finding Closure Report",
        "entity_type": "Finding",
        "format": "Word (.docx)",
        "description": "Generated when a finding reaches Closed status.",
        "placeholders": [
            {"placeholder": "{{entity_id}}",            "maps_to": "entity_id",            "display_name": "Finding ID"},
            {"placeholder": "{{severity}}",             "maps_to": "severity",             "display_name": "Severity"},
            {"placeholder": "{{finding_type}}",         "maps_to": "finding_type",         "display_name": "Type"},
            {"placeholder": "{{linked_validation}}",    "maps_to": "linked_validation",    "display_name": "Linked validation"},
            {"placeholder": "{{due_date}}",             "maps_to": "due_date",             "display_name": "Due date"},
            {"placeholder": "{{resolution_notes}}",     "maps_to": "resolution_notes",     "display_name": "Resolution notes"},
            {"placeholder": "{{owner}}",                "maps_to": "owner",                "display_name": "Resolved by"},
        ],
    },
]

# ── Automation rules ───────────────────────────────────────────────────────────
AUTOMATION_RULES = [
    {
        "name": "Notify validator on model registration",
        "trigger_type": "Entity transition",
        "trigger_condition": "Model moves to Registration stage",
        "action": "Send email to validator group assigned to this model",
        "entity_type": "Model",
    },
    {
        "name": "Create validation subprocess",
        "trigger_type": "Entity transition",
        "trigger_condition": "Model moves to Validation stage",
        "action": "Auto-create a Subprocess entity (type=Validation) linked to this model",
        "entity_type": "Model",
    },
    {
        "name": "Validation due date reminder",
        "trigger_type": "Time-based",
        "trigger_condition": "Today = validation_due_date - 7 days",
        "action": "Send email reminder to owner and validator",
        "entity_type": "Model",
    },
    {
        "name": "Finding due date alert",
        "trigger_type": "Time-based",
        "trigger_condition": "Today = finding.due_date - 1 day",
        "action": "Send urgent alert to model owner and governance team",
        "entity_type": "Finding",
    },
    {
        "name": "Unlock approval workflow",
        "trigger_type": "Entity transition",
        "trigger_condition": "Validation Workflow reaches Validation Sign-off",
        "action": "Set Approval Workflow first stage from pending → current; status → In Progress",
        "entity_type": "Subprocess",
    },
    {
        "name": "Auto-generate monitoring report",
        "trigger_type": "Time-based",
        "trigger_condition": "Today = next_monitoring_date (quarterly)",
        "action": "Generate Monitoring Report document and notify committee",
        "entity_type": "Subprocess",
    },
    {
        "name": "Risk tier auto-derive",
        "trigger_type": "Attribute updated",
        "trigger_condition": "financial_impact attribute changes value",
        "action": "Recalculate risk_tier using derivation formula",
        "entity_type": "Model",
    },
    {
        "name": "Archive on retirement",
        "trigger_type": "Entity transition",
        "trigger_condition": "Model reaches Retired stage",
        "action": "Set status = Archived; close all open subprocesses; notify governance",
        "entity_type": "Model",
    },
]


def get_risk_score(node_id: str) -> int:
    """
    Derived risk score 0–100.

    Formula (simplified version of Vault's configurable derivation engine):
      base         = RISK_BASE[node.risk]
      status_pen   = STATUS_PEN[node.status]
      upstream_pen = upstream_count × 3
      degraded_pen = degraded_upstream_count × 8

    Capped at 100.
    """
    from graph_engine import upstream_trace
    node = NODES.get(node_id)
    if not node:
        return 0
    base      = _RISK_BASE.get(node.get("risk", ""), 0)
    status_p  = _STATUS_PEN.get(node.get("status", ""), 0)
    up        = upstream_trace(node_id)
    up_p      = len(up) * 3
    degraded  = [u for u in up if NODES.get(u, {}).get("status") in ("Under Review", "Not Started")]
    deg_p     = len(degraded) * 8
    return min(100, base + status_p + up_p + deg_p)
