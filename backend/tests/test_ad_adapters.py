import json
import zipfile
from pathlib import Path

from app.adapters.base import AdapterInput
from app.adapters.bloodhound import BloodHoundAdapter
from app.adapters.netexec import NetExecAdapter


def dummy_input(tool: str, params: dict | None = None) -> AdapterInput:
    return AdapterInput(
        tool=tool,
        target="dc01.goad.local",
        params=params or {},
        risk_tier="approval",
        engagement_id="test-engagement",
    )


def test_netexec_kerberoast_parses_hash_lines(tmp_path: Path):
    output_path = tmp_path / "nxc.out"
    output_path.write_text(
        "$krb5tgs$23$*svc_sql$GOAD.LOCAL$MSSQLSvc/dc01.goad.local*$abcdef0123456789\n",
        encoding="utf-8",
    )

    findings = NetExecAdapter().parse_output(
        dummy_input("netexec", {"profile": "kerberoast"}), output_path, ""
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "kerberoastable_account"
    assert findings[0]["account"] == "svc_sql"


def test_netexec_asreproast_uses_distinct_finding_type(tmp_path: Path):
    output_path = tmp_path / "nxc.out"
    output_path.write_text("$krb5asrep$23$jsmith@GOAD.LOCAL:deadbeef\n", encoding="utf-8")

    findings = NetExecAdapter().parse_output(
        dummy_input("netexec", {"profile": "asreproast"}), output_path, ""
    )

    assert findings[0]["type"] == "asrep_roastable_account"


def test_netexec_parse_output_missing_file_returns_empty(tmp_path: Path):
    findings = NetExecAdapter().parse_output(
        dummy_input("netexec"), tmp_path / "missing.out", ""
    )
    assert findings == []


def test_netexec_working_directory_is_none_by_default():
    assert NetExecAdapter().working_directory(Path("/tmp/whatever.out")) is None


def test_bloodhound_working_directory_is_output_parent(tmp_path: Path):
    output_path = tmp_path / "bloodhound-python-abcd1234.out"
    assert BloodHoundAdapter().working_directory(output_path) == tmp_path


def test_bloodhound_parse_output_counts_collected_objects(tmp_path: Path):
    output_path = tmp_path / "bloodhound-python-abcd1234.out"
    output_path.write_text("", encoding="utf-8")

    archive_path = tmp_path / "20260101120000_bloodhound.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("users.json", json.dumps({"data": [{"Name": "ADMIN"}, {"Name": "JDOE"}]}))
        archive.writestr("computers.json", json.dumps({"data": [{"Name": "DC01"}]}))
        archive.writestr("domains.json", json.dumps({"data": []}))

    findings = BloodHoundAdapter().parse_output(dummy_input("bloodhound"), output_path, "")

    findings_by_type = {finding["type"]: finding["count"] for finding in findings}
    assert findings_by_type["bloodhound_users_collected"] == 2
    assert findings_by_type["bloodhound_computers_collected"] == 1
    assert "bloodhound_domains_collected" not in findings_by_type


def test_bloodhound_parse_output_no_archive_returns_empty(tmp_path: Path):
    output_path = tmp_path / "bloodhound-python-abcd1234.out"
    output_path.write_text("", encoding="utf-8")

    findings = BloodHoundAdapter().parse_output(dummy_input("bloodhound"), output_path, "")

    assert findings == []
