import json
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterInput, ToolAdapter


class ZapAdapter(ToolAdapter):
    binary_name = "zap-full-scan.py"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        return ["zap-full-scan.py", "-t", adapter_input.target, "-J", str(output_path)]

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        findings = []
        for site in data.get("site", []):
            for alert in site.get("alerts", []):
                risk_desc = alert.get("riskdesc", "")
                risk = risk_desc.split(" ")[0].lower() if risk_desc else "info"
                findings.append(
                    {
                        "type": alert.get("alertRef", alert.get("pluginid", "unknown")),
                        "name": alert.get("name"),
                        "risk": risk,
                        "confidence": "medium",
                    }
                )

        return findings
