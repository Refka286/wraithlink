from app.knowledge.compliance_mapping import format_reference, get_compliance_reference


def _open_port_description(port: int, service: str = "unknown") -> str:
    # matches the exact str(dict) format app/adapters/nmap.py's findings are
    # stored as (see app/tasks/run_action.py)
    return str({"type": "open_port", "port": port, "service": service, "confidence": "high"})


def test_standard_web_ports_are_not_flagged_as_cwe_200():
    for port in (80, 443):
        reference = get_compliance_reference("open_port", _open_port_description(port, "http"))
        assert reference["cwe"] is None
        assert format_reference(reference) != "CWE-200"


def test_database_and_admin_ports_are_flagged_as_cwe_200():
    for port, service in [(3306, "mysql"), (5432, "postgresql"), (22, "ssh"), (3389, "ms-wbt-server")]:
        reference = get_compliance_reference("open_port", _open_port_description(port, service))
        assert reference["cwe"] == "CWE-200"
        assert format_reference(reference) == "CWE-200"


def test_arbitrary_unexpected_port_is_flagged_as_cwe_200():
    reference = get_compliance_reference("open_port", _open_port_description(31337, "unknown"))
    assert reference["cwe"] == "CWE-200"


def test_unparseable_description_falls_back_to_flagged_not_silently_neutral():
    # safe default: if the port can't be determined, treat it as worth a
    # human look rather than silently downgrading it to "nothing to see here"
    reference = get_compliance_reference("open_port", "not a dict at all")
    assert reference["cwe"] == "CWE-200"

    reference_no_description = get_compliance_reference("open_port", None)
    assert reference_no_description["cwe"] == "CWE-200"


def test_standard_port_reference_formats_as_a_distinct_informational_note():
    reference = get_compliance_reference("open_port", _open_port_description(443, "https"))
    formatted = format_reference(reference)
    assert formatted != "Non cartographie"
    assert "CWE" not in formatted


def test_non_open_port_finding_types_are_unaffected_by_port_logic():
    reference = get_compliance_reference("sql_injection", "irrelevant for this type")
    assert reference["cwe"] == "CWE-89"
