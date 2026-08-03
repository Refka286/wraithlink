import ast

# Maps finding types actually produced by the adapters (app/adapters/) to the
# relevant OWASP Top 10 2021 category and/or CWE identifier. Not exhaustive -
# covers what the platform produces today; extend as new finding types are
# introduced. Nuclei's finding type is the scanner's own template-id, which
# is effectively unbounded (one entry per template) - only the templates
# actually exercised so far are mapped explicitly.

# a service running on 80/443 is expected on practically any web-facing
# host and isn't itself an information-disclosure finding; anything else
# (database ports like 3306/5432, admin/remote-access ports like 22/3389,
# or any other unexpected port) is worth flagging as CWE-200
STANDARD_WEB_PORTS = {80, 443}

OPEN_PORT_REFERENCE = {
    "owasp": None,
    "cwe": "CWE-200",
    "cwe_label": "Exposure of Sensitive Information to an Unauthorized Actor",
}

STANDARD_PORT_REFERENCE = {
    "owasp": None,
    "cwe": None,
    "note": "Port standard - informationnel",
}

COMPLIANCE_MAPPING: dict[str, dict] = {
    "discovered_path": {
        "owasp": "A05:2021",
        "owasp_label": "Security Misconfiguration",
        "cwe": "CWE-538",
        "cwe_label": "Insertion of Sensitive Information into Externally-Accessible File or Directory",
    },
    "prometheus-metrics": {
        "owasp": "A05:2021",
        "owasp_label": "Security Misconfiguration",
        "cwe": "CWE-200",
        "cwe_label": "Exposure of Sensitive Information to an Unauthorized Actor",
    },
    "sql_injection": {
        "owasp": "A03:2021",
        "owasp_label": "Injection",
        "cwe": "CWE-89",
        "cwe_label": "SQL Injection",
    },
    "kerberoastable_account": {
        "owasp": None,
        "cwe": "CWE-522",
        "cwe_label": "Insufficiently Protected Credentials",
    },
    "asrep_roastable_account": {
        "owasp": None,
        "cwe": "CWE-522",
        "cwe_label": "Insufficiently Protected Credentials",
    },
}

# BloodHound produces one finding type per collected object category, named
# dynamically as f"bloodhound_{category}_collected" (see app/adapters/bloodhound.py)
_BLOODHOUND_SUFFIX = "_collected"
_BLOODHOUND_PREFIX = "bloodhound_"
_BLOODHOUND_DEFAULT = {
    "owasp": None,
    "cwe": "CWE-200",
    "cwe_label": "Exposure of Sensitive Information to an Unauthorized Actor",
}


def _extract_port(raw_description: str | None) -> int | None:
    # adapters store parsed findings as str(dict) (see app/tasks/run_action.py)
    if not raw_description:
        return None
    try:
        parsed = ast.literal_eval(raw_description)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(parsed, dict):
        return None
    port = parsed.get("port")
    return port if isinstance(port, int) else None


def get_compliance_reference(finding_type: str, description: str | None = None) -> dict | None:
    if finding_type == "open_port":
        port = _extract_port(description)
        if port in STANDARD_WEB_PORTS:
            return STANDARD_PORT_REFERENCE
        return OPEN_PORT_REFERENCE

    if finding_type in COMPLIANCE_MAPPING:
        return COMPLIANCE_MAPPING[finding_type]

    if finding_type.startswith(_BLOODHOUND_PREFIX) and finding_type.endswith(_BLOODHOUND_SUFFIX):
        return _BLOODHOUND_DEFAULT

    return None


def format_reference(reference: dict | None) -> str:
    if reference is None:
        return "Non cartographie"

    parts = []
    if reference.get("owasp"):
        parts.append(f"OWASP {reference['owasp']}")
    if reference.get("cwe"):
        parts.append(reference["cwe"])
    if parts:
        return " / ".join(parts)

    if reference.get("note"):
        return reference["note"]

    return "Non cartographie"
