import json
from pathlib import Path

from app.adapters.acunetix import AcunetixAdapter
from app.adapters.base import AdapterInput, ToolNotInstalledError
from app.adapters.ffuf import FfufAdapter
from app.adapters.nmap import NmapAdapter
from app.adapters.nuclei import NucleiAdapter

def dummy_input(tool: str, params: dict | None = None) -> AdapterInput:
    return AdapterInput(
        tool=tool,
        target="10.10.10.5",
        params=params or {},
        risk_tier="automatic",
        engagement_id="test-engagement",
    )


NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <ports>
      <port protocol="tcp" portid="445">
        <state state="open"/>
        <service name="smb"/>
      </port>
      <port protocol="tcp" portid="9999">
        <state state="closed"/>
        <service name="unknown"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


def test_nmap_parse_output_keeps_only_open_ports(tmp_path: Path):
    xml_path = tmp_path / "nmap.xml"
    xml_path.write_text(NMAP_XML, encoding="utf-8")

    findings = NmapAdapter().parse_output(dummy_input("nmap"), xml_path, "")

    assert findings == [
        {"type": "open_port", "port": 445, "service": "smb", "confidence": "high"}
    ]


def test_nmap_parse_output_missing_file_returns_empty(tmp_path: Path):
    findings = NmapAdapter().parse_output(dummy_input("nmap"), tmp_path / "missing.xml", "")
    assert findings == []


def test_ffuf_parse_output(tmp_path: Path):
    output_path = tmp_path / "ffuf.json"
    output_path.write_text(
        json.dumps(
            {
                "results": [
                    {"url": "http://target/admin", "status": 200, "length": 512},
                ]
            }
        ),
        encoding="utf-8",
    )

    findings = FfufAdapter().parse_output(dummy_input("ffuf"), output_path, "")

    assert findings == [
        {
            "type": "discovered_path",
            "url": "http://target/admin",
            "status": 200,
            "length": 512,
            "confidence": "medium",
        }
    ]


def test_nuclei_parse_output(tmp_path: Path):
    output_path = tmp_path / "nuclei.jsonl"
    record = {
        "template-id": "exposed-panel",
        "info": {"name": "Exposed Admin Panel", "severity": "medium"},
        "matched-at": "http://target/admin",
    }
    output_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    findings = NucleiAdapter().parse_output(dummy_input("nuclei"), output_path, "")

    assert findings == [
        {
            "type": "exposed-panel",
            "name": "Exposed Admin Panel",
            "severity": "medium",
            "matched_at": "http://target/admin",
            "confidence": "high",
        }
    ]


def test_adapter_run_reports_missing_binary():
    adapter = NmapAdapter()
    adapter.binary_name = "definitely-not-a-real-binary"

    output = adapter.run(
        AdapterInput(
            tool="nmap",
            target="10.10.10.5",
            params={},
            risk_tier="automatic",
            engagement_id="test-engagement",
        )
    )

    assert output.status == "error"
    assert "not installed" in output.error


def test_acunetix_run_reports_not_configured():
    # no ACUNETIX_API_KEY/ACUNETIX_BASE_URL is set in the test environment,
    # which mirrors production until a commercial license is available -
    # the adapter must fail clearly instead of crashing or hanging on a
    # real HTTP call
    output = AcunetixAdapter().run(dummy_input("acunetix"))

    assert output.status == "error"
    assert "not configure" in output.error.lower() or "licence" in output.error.lower()
