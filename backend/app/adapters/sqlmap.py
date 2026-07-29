import re
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterInput, ToolAdapter

PARAMETER_LINE = re.compile(r"^Parameter:\s*(?P<parameter>.+)$")
TYPE_LINE = re.compile(r"^\s*Type:\s*(?P<injection_type>.+)$")


class SqlmapAdapter(ToolAdapter):
    binary_name = "sqlmap"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        level = adapter_input.params.get("level", 3)
        risk = adapter_input.params.get("risk", 2)

        # sqlmap has no single-file JSON report flag suitable for every
        # version; findings are parsed from its stdout instead, which
        # base.run() already captures into output_path when the command
        # itself doesn't reference an output file
        return [
            "sqlmap",
            "-u", adapter_input.target,
            "--batch",
            f"--level={level}",
            f"--risk={risk}",
        ]

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        if not output_path.exists():
            return []

        findings = []
        current_parameter: str | None = None

        for line in output_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parameter_match = PARAMETER_LINE.match(line.strip())
            if parameter_match:
                current_parameter = parameter_match.group("parameter")
                continue

            type_match = TYPE_LINE.match(line)
            if type_match and current_parameter:
                findings.append(
                    {
                        "type": "sql_injection",
                        "parameter": current_parameter,
                        "injection_type": type_match.group("injection_type").strip(),
                        "confidence": "high",
                    }
                )

        return findings
