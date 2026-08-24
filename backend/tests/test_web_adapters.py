import json
from pathlib import Path

from app.adapters.base import AdapterInput
from app.adapters.sqlmap import SqlmapAdapter
from app.adapters.zap import ZapAdapter


def dummy_input(tool: str, params: dict | None = None) -> AdapterInput:
    return AdapterInput(
        tool=tool,
        target="http://target.local/login",
        params=params or {},
        risk_tier="approval",
        engagement_id="test-engagement",
    )


SQLMAP_STDOUT = """
sqlmap resumed the following injection point(s) from stored session:
---
Parameter: id (GET)
    Type: boolean-based blind
    Title: AND boolean-based blind - WHERE or HAVING clause
    Payload: id=1 AND 1=1

    Type: time-based blind
    Title: MySQL >= 5.0.12 AND time-based blind
    Payload: id=1 AND SLEEP(5)
---
the back-end DBMS is MySQL
"""


def test_sqlmap_parse_output_extracts_parameter_and_types(tmp_path: Path):
    output_path = tmp_path / "sqlmap.out"
    output_path.write_text(SQLMAP_STDOUT, encoding="utf-8")

    findings = SqlmapAdapter().parse_output(dummy_input("sqlmap"), output_path, SQLMAP_STDOUT)

    assert len(findings) == 2
    assert findings[0] == {
        "type": "sql_injection",
        "parameter": "id (GET)",
        "injection_type": "boolean-based blind",
        "confidence": "high",
    }
    assert findings[1]["injection_type"] == "time-based blind"


def test_sqlmap_parse_output_no_findings_when_clean(tmp_path: Path):
    output_path = tmp_path / "sqlmap.out"
    output_path.write_text("all tested parameters do not appear to be injectable", encoding="utf-8")

    findings = SqlmapAdapter().parse_output(dummy_input("sqlmap"), output_path, "")
    assert findings == []


def test_zap_parse_output_extracts_alerts(tmp_path: Path):
    output_path = tmp_path / "zap.json"
    output_path.write_text(
        json.dumps(
            {
                "site": [
                    {
                        "alerts": [
                            {
                                "pluginid": "40018",
                                "alertRef": "40018",
                                "name": "SQL Injection",
                                "riskdesc": "High (Medium)",
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    findings = ZapAdapter().parse_output(dummy_input("zap"), output_path, "")

    assert findings == [
        {"type": "40018", "name": "SQL Injection", "severity": "high", "confidence": "medium"}
    ]


def test_zap_parse_output_missing_file_returns_empty(tmp_path: Path):
    findings = ZapAdapter().parse_output(dummy_input("zap"), tmp_path / "missing.json", "")
    assert findings == []
