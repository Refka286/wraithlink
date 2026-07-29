import json
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterInput, ToolAdapter


class NucleiAdapter(ToolAdapter):
    binary_name = "nuclei"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        severity = adapter_input.params.get("severity", "low,medium,high,critical")

        return [
            "nuclei",
            "-target", adapter_input.target,
            "-severity", severity,
            "-jsonl",
            "-o", str(output_path),
            "-silent",
        ]

    def parse_output(self, output_path: Path, raw_stdout: str) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        findings = []
        for line in output_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            info = record.get("info", {})
            findings.append(
                {
                    "type": record.get("template-id", "unknown"),
                    "name": info.get("name"),
                    "severity": info.get("severity", "info"),
                    "matched_at": record.get("matched-at"),
                    "confidence": "high",
                }
            )
        return findings
